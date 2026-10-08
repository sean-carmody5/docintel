"""Download the public sample documents listed in sources.json into data/public.

    uv run python -m evals.public.fetch            # fetch what is missing
    uv run python -m evals.public.fetch --force    # re-download everything
    uv run python -m evals.public.fetch --only kemsa_pricelist_2017 msd_tanzania_catalogue_2018_csv

Each file's magic bytes are checked against its declared format, and a manifest with
sizes, hashes and fetch dates is written beside the files. The folder is git-ignored
because several publishers assert all rights reserved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SOURCES = Path(__file__).with_name("sources.json")
DEFAULT_OUT = Path("data/public")
USER_AGENT = "docintel-evals/0.1 (+https://github.com/sean-carmody5/axmed-docintel)"

MAGIC: dict[str, tuple[bytes, ...]] = {
    "pdf": (b"%PDF",),
    "xlsx": (b"PK\x03\x04",),
    "docx": (b"PK\x03\x04",),
    "xls": (b"\xd0\xcf\x11\xe0",),
    "doc": (b"\xd0\xcf\x11\xe0",),
}


def _looks_like(fmt: str, head: bytes) -> bool:
    if fmt in MAGIC:
        return any(head.startswith(m) for m in MAGIC[fmt])
    if fmt == "csv":
        try:
            text = head.decode("utf-8")
        except UnicodeDecodeError:
            text = head.decode("latin-1")
        return ("," in text or ";" in text) and "<html" not in text.lower()
    return True


def _download(url: str, target: Path, *, insecure_tls: bool) -> int:
    ctx = ssl.create_default_context()
    if insecure_tls:
        # Some government hosts serve an incomplete certificate chain.
        # Browsers cope, urllib does not.
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, context=ctx, timeout=120) as resp, target.open("wb") as fh:
        size = 0
        while chunk := resp.read(1 << 16):
            fh.write(chunk)
            size += len(chunk)
    return size


def fetch(out: Path, *, force: bool = False, only: set[str] | None = None) -> dict[str, Any]:
    spec = json.loads(SOURCES.read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    manifest: dict[str, Any] = {"fetched": {}, "failed": {}}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.setdefault("fetched", {})
        manifest.setdefault("failed", {})

    for src in spec["sources"]:
        sid = src["id"]
        if only and sid not in only:
            continue
        target = out / f"{sid}.{src['format']}"
        if target.exists() and target.stat().st_size > 0 and not force:
            print(f"  have   {sid}")
            continue
        try:
            size = _download(src["url"], target, insecure_tls=bool(src.get("insecure_tls")))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            print(f"  FAIL   {sid}: {exc}")
            manifest["failed"][sid] = {"error": str(exc), "at": datetime.now(UTC).isoformat()}
            target.unlink(missing_ok=True)
            continue
        head = target.read_bytes()[:64]
        if not _looks_like(src["format"], head):
            print(f"  FAIL   {sid}: content does not look like {src['format']} ({head[:12]!r})")
            manifest["failed"][sid] = {
                "error": "unexpected content",
                "at": datetime.now(UTC).isoformat(),
            }
            target.unlink(missing_ok=True)
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        manifest["fetched"][sid] = {
            "file": target.name,
            "bytes": size,
            "sha256": digest,
            "url": src["url"],
            "publisher": src["publisher"],
            "licence": src["licence"],
            "tags": src["tags"],
            "at": datetime.now(UTC).isoformat(),
        }
        manifest["failed"].pop(sid, None)
        print(f"  ok     {sid} ({size / 1024:.0f} KB)")

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out / "README.md").write_text(_readme(spec, manifest), encoding="utf-8", newline="\n")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args()
    m = fetch(args.out, force=args.force, only=set(args.only) if args.only else None)
    print(f"{len(m['fetched'])} fetched, {len(m['failed'])} failed, in {args.out}")
    if m["failed"]:
        sys.exit(1)


def _readme(spec: dict[str, Any], manifest: dict[str, Any]) -> str:
    rows = []
    for src in spec["sources"]:
        got = manifest["fetched"].get(src["id"])
        size = f"{got['bytes'] / 1024:.0f} KB" if got else "not fetched"
        committed = "yes" if src.get("redistributable") else "no, fetch on demand"
        rows.append(
            f"| {src['name']} | {src['publisher']} | {src['format']} | {size} | "
            f"{', '.join(src['tags'])} | {src['licence']} | {committed} |"
        )
    n_open = sum(1 for s in spec["sources"] if s.get("redistributable"))
    return f"""# Public sample documents

Real price lists, catalogues and request-for-quotation forms, used as robustness
smoke tests. They carry no ground truth. The pipeline is expected to degrade into
flags on them, never to crash and never to guess with confidence.

Fetched by `uv run python -m evals.public.fetch`. Sources, licences and tags live in
`evals/public/sources.json`; `manifest.json` here records size, SHA-256 and fetch date.

## Licences

{n_open} of {len(spec["sources"])} files are under an explicit open licence (CC BY, CC BY-NC with
attribution, Open Jordanian Licence) and are committed. The rest state no licence or
assert all rights reserved (MSH, Ghana NHIS) and are fetched on demand, never
redistributed, not even in a private repository. Three government hosts serve broken
certificate chains and are fetched with verification off; they are marked in the sources file.

| Document | Publisher | Format | Size | Tags | Licence | Committed |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}
"""


if __name__ == "__main__":
    main()
