"""Turn a rendered PDF page into the kind of image a supplier actually sends."""

from __future__ import annotations

import io
import random
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFilter, ImageOps

Degrade = Callable[[Image.Image, random.Random], Image.Image]


def render_page(pdf_path: Path, page: int = 0, dpi: int = 150) -> Image.Image:
    with pymupdf.open(pdf_path) as doc:
        pix = doc[page].get_pixmap(dpi=dpi)
        return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def _noise(im: Image.Image, rng: random.Random, sigma: float) -> Image.Image:
    arr = np.asarray(im).astype(np.float32)
    noise = np.random.default_rng(rng.getrandbits(32)).normal(0, sigma, arr.shape)
    return Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8), im.mode)


def _salt_pepper(im: Image.Image, rng: random.Random, fraction: float) -> Image.Image:
    arr = np.array(im)
    g = np.random.default_rng(rng.getrandbits(32))
    mask = g.random(arr.shape[:2]) < fraction
    arr[mask] = g.choice([0, 255], size=int(mask.sum()))
    return Image.fromarray(arr, im.mode)


def _perspective_coeffs(
    src: list[tuple[float, float]], dst: list[tuple[float, float]]
) -> list[float]:
    """Coefficients mapping output quad (dst) back to input quad (src) for PIL PERSPECTIVE."""
    rows = []
    for (x, y), (u, v) in zip(dst, src, strict=True):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    a = np.array(rows, dtype=np.float64)
    b = np.array([c for (u, v) in src for c in (u, v)], dtype=np.float64)
    return [float(c) for c in np.linalg.solve(a, b)]


def _glare(im: Image.Image, rng: random.Random, strength: float) -> Image.Image:
    w, h = im.size
    cx, cy = rng.uniform(0.3, 0.8) * w, rng.uniform(0.1, 0.5) * h
    radius = rng.uniform(0.35, 0.55) * max(w, h)
    yy, xx = np.mgrid[0:h, 0:w]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    glow = np.clip(1 - dist / radius, 0, 1) ** 1.6 * 255 * strength
    arr = np.asarray(im).astype(np.float32) + glow[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def _shadow_edge(im: Image.Image, rng: random.Random) -> Image.Image:
    w, h = im.size
    side = rng.choice(("left", "right"))
    xx = np.linspace(0, 1, w)
    ramp = (1 - xx) if side == "left" else xx
    dark = 1 - np.clip(ramp - 0.55, 0, 1) * rng.uniform(0.35, 0.6)
    arr = np.asarray(im).astype(np.float32) * dark[None, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def _finger(im: Image.Image, rng: random.Random) -> Image.Image:
    w, h = im.size
    layer = im.copy()
    d = ImageDraw.Draw(layer)
    x = rng.choice((-0.1, 0.85)) * w
    y = rng.uniform(0.6, 0.9) * h
    d.ellipse([x, y, x + 0.26 * w, y + 0.22 * h], fill=(214, 168, 142))
    d.ellipse([x + 0.04 * w, y + 0.03 * h, x + 0.22 * w, y + 0.19 * h], fill=(226, 184, 158))
    layer = layer.filter(ImageFilter.GaussianBlur(3))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).ellipse([x - 4, y - 4, x + 0.26 * w + 4, y + 0.22 * h + 4], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(6))
    return Image.composite(layer, im, mask)


def degrade_fax(im: Image.Image, rng: random.Random) -> Image.Image:
    """Low resolution grayscale, slight skew, speckle, crushed contrast, like a fax or cheap scanner."""
    g = ImageOps.grayscale(im)
    scale = rng.uniform(0.6, 0.7)
    g = g.resize((int(g.width * scale), int(g.height * scale)), Image.BILINEAR)
    g = g.rotate(rng.uniform(-2.2, 2.2), resample=Image.BICUBIC, expand=True, fillcolor=255)
    g = _noise(g, rng, rng.uniform(6, 11))
    g = g.point(lambda p: 0 if p < 70 else (255 if p > 200 else int(30 + (p - 70) * 1.7)))
    g = _salt_pepper(g, rng, rng.uniform(0.002, 0.006))
    # a streak from a dirty roller
    d = ImageDraw.Draw(g)
    x = rng.randint(int(g.width * 0.05), int(g.width * 0.95))
    d.line(
        [(x, 0), (x + rng.randint(-6, 6), g.height)],
        fill=rng.randint(120, 200),
        width=rng.randint(1, 3),
    )
    return g


def degrade_photo(im: Image.Image, rng: random.Random) -> Image.Image:
    """Phone photo: keystone, glare, uneven light, slight blur, colour cast, a thumb in the corner."""
    w, h = im.size
    bg = (rng.randint(60, 110), rng.randint(55, 95), rng.randint(50, 85))
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    k = 0.06
    dst = [
        (w * rng.uniform(0.02, k), h * rng.uniform(0.02, k)),
        (w * (1 - rng.uniform(0.0, k)), h * rng.uniform(0.0, k * 1.5)),
        (w * (1 - rng.uniform(0.0, k * 1.5)), h * (1 - rng.uniform(0.0, k))),
        (w * rng.uniform(0.0, k * 1.5), h * (1 - rng.uniform(0.02, k * 1.5))),
    ]
    out = im.transform(
        (w, h), Image.PERSPECTIVE, _perspective_coeffs(src, dst), Image.BICUBIC, fillcolor=bg
    )
    out = _shadow_edge(out, rng)
    out = _glare(out, rng, rng.uniform(0.45, 0.8))
    out = out.filter(ImageFilter.GaussianBlur(rng.uniform(0.6, 1.3)))
    cast = np.array(
        [rng.uniform(1.0, 1.08), rng.uniform(0.96, 1.02), rng.uniform(0.88, 0.98)], dtype=np.float32
    )
    arr = np.clip(np.asarray(out).astype(np.float32) * cast, 0, 255).astype(np.uint8)
    out = Image.fromarray(arr, "RGB")
    out = _noise(out, rng, rng.uniform(3, 7))
    if rng.random() < 0.8:
        out = _finger(out, rng)
    scale = rng.uniform(0.55, 0.75)
    return out.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


def degrade_crop(im: Image.Image, rng: random.Random) -> Image.Image:
    """Partial capture: a region of the page, tilted, mid-quality JPEG. Some rows will be missing."""
    w, h = im.size
    left = rng.uniform(0.0, 0.12) * w
    top = rng.uniform(0.18, 0.4) * h
    right = rng.uniform(0.72, 0.95) * w
    bottom = min(h, top + rng.uniform(0.35, 0.55) * h)
    out = im.crop((int(left), int(top), int(right), int(bottom)))
    out = out.rotate(
        rng.uniform(-3.5, 3.5), resample=Image.BICUBIC, expand=True, fillcolor=(235, 232, 226)
    )
    out = _noise(out, rng, 4)
    return out


def degrade_heavy(im: Image.Image, rng: random.Random) -> Image.Image:
    """Everything at once: big rotation, blur, noise, low resolution. Expected to be mostly unreadable."""
    out = im.rotate(
        rng.uniform(5, 9) * rng.choice((-1, 1)),
        resample=Image.BICUBIC,
        expand=True,
        fillcolor=(230, 230, 230),
    )
    out = out.filter(ImageFilter.GaussianBlur(rng.uniform(2.2, 2.8)))
    out = _noise(out, rng, rng.uniform(22, 30))
    scale = rng.uniform(0.36, 0.42)
    out = out.resize((int(out.width * scale), int(out.height * scale)), Image.BILINEAR)
    return ImageOps.grayscale(out).convert("RGB")


def degrade_scanner(im: Image.Image, rng: random.Random) -> Image.Image:
    """A flatbed or sheet-fed scanner: grayscale, faint skew, light noise, a little soft."""
    g = ImageOps.grayscale(im)
    g = g.rotate(rng.uniform(-1.2, 1.2), resample=Image.BICUBIC, expand=False, fillcolor=250)
    g = _noise(g, rng, rng.uniform(4, 8))
    g = g.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 0.7)))
    g = g.point(lambda p: int(max(0, min(255, (p - 20) * 1.12))))
    return g.convert("RGB")


def degrade_glare_wipe(im: Image.Image, rng: random.Random) -> Image.Image:
    """A phone photo where a reflection saturates a band across the table.

    Rows under the band are gone, not degraded. The expected outcome is partial
    extraction with low confidence on whatever sits near the band, never a guess.
    """
    w, h = im.size
    out = degrade_photo(im, rng)
    ow, oh = out.size
    arr = np.asarray(out).astype(np.float32)
    # a diagonal band, fully blown out in the middle, feathered at the edges
    yy, xx = np.mgrid[0:oh, 0:ow]
    angle = rng.uniform(-0.35, 0.35)
    centre = rng.uniform(0.38, 0.62) * oh
    dist = np.abs((yy - centre) - angle * (xx - ow / 2))
    half = rng.uniform(0.07, 0.11) * oh
    wipe = np.clip(1 - (dist - half) / (half * 0.8), 0, 1)
    arr = arr + wipe[..., None] * (255 - arr)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    return out.filter(ImageFilter.GaussianBlur(rng.uniform(0.4, 0.9)))


DEGRADATIONS: dict[str, tuple[Degrade, str]] = {
    "fax": (degrade_fax, "png"),
    "photo": (degrade_photo, "jpg"),
    "crop": (degrade_crop, "jpg"),
    "heavy": (degrade_heavy, "jpg"),
    "glare_wipe": (degrade_glare_wipe, "jpg"),
}


def write_image(
    pdf_path: Path, out_path: Path, kind: str, rng: random.Random, page: int = 0
) -> Path:
    fn, ext = DEGRADATIONS[kind]
    out = fn(render_page(pdf_path, page=page), rng)
    target = out_path.with_suffix("." + ext)
    if ext == "jpg":
        quality = rng.randint(28, 36) if kind == "heavy" else rng.randint(42, 68)
        out.convert("RGB").save(target, "JPEG", quality=quality, optimize=True)
    else:
        out.save(target, "PNG", optimize=True)
    return target
