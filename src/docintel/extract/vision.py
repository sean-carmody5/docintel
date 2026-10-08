"""The vision path: page images to a verbatim Markdown transcript, plus independent OCR.

The transcript is what the shared extraction prompt reads. The OCR text is never the
primary source; it is a second, independent reading used by verification to score
agreement, with a confidence that tracks legibility.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol

from docintel.documents import PageImage
from docintel.extract.prompt import transcription_messages

log = logging.getLogger(__name__)


@dataclass
class OcrLine:
    text: str
    score: float


@dataclass
class OcrResult:
    text: str
    lines: list[OcrLine] = field(default_factory=list)

    @property
    def mean_score(self) -> float:
        return sum(ln.score for ln in self.lines) / len(self.lines) if self.lines else 0.0


class OcrEngine(Protocol):
    name: str

    def read(self, png: bytes) -> OcrResult: ...


class RapidOcrEngine:
    """PP-OCR models on ONNX Runtime. Per-line confidence in 0 to 1."""

    name = "rapidocr"

    def __init__(self) -> None:
        from rapidocr import RapidOCR

        rapid_log = logging.getLogger("RapidOCR")  # the import sets it to INFO with a handler
        rapid_log.setLevel(logging.WARNING)
        for h in rapid_log.handlers:
            h.setLevel(logging.WARNING)
        self._engine = RapidOCR()

    def read(self, png: bytes) -> OcrResult:
        import numpy as np
        from PIL import Image

        image = np.asarray(Image.open(BytesIO(png)).convert("RGB"))
        result = self._engine(image)
        # The engine returns a union of stage outputs; only the full output carries text.
        txts = list(getattr(result, "txts", None) or [])
        scores = list(getattr(result, "scores", None) or [])
        lines = [OcrLine(t, float(s)) for t, s in zip(txts, scores, strict=False)]
        return OcrResult(text="\n".join(txts), lines=lines)


class TesseractEngine:
    """Fallback when RapidOCR is unavailable. Word confidences from the TSV output."""

    name = "tesseract"

    def read(self, png: bytes) -> OcrResult:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "page.png"
            path.write_bytes(png)
            proc = subprocess.run(
                ["tesseract", str(path), "-", "--psm", "6", "tsv"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        lines: list[OcrLine] = []
        for row in proc.stdout.splitlines()[1:]:
            cols = row.split("\t")
            if len(cols) == 12 and cols[11].strip():
                try:
                    lines.append(OcrLine(cols[11], float(cols[10]) / 100))
                except ValueError:
                    continue
        return OcrResult(text=" ".join(ln.text for ln in lines), lines=lines)


def ocr_engine(preferred: str = "rapidocr") -> OcrEngine | None:
    """Best available engine, or None. Never raises: OCR is a cross-check, not a requirement."""
    if preferred == "rapidocr":
        try:
            return RapidOcrEngine()
        except Exception as err:  # missing package, model download failure, no onnxruntime
            log.warning("RapidOCR unavailable (%s); trying tesseract", err)
    if shutil.which("tesseract"):
        return TesseractEngine()
    log.warning("no OCR engine available; agreement checks will be skipped")
    return None


def ocr_pages(engine: OcrEngine, images: list[PageImage]) -> OcrResult:
    merged = OcrResult(text="")
    parts: list[str] = []
    for page in images:
        result = engine.read(page.png)
        parts.append(result.text)
        merged.lines.extend(result.lines)
    merged.text = "\n\n".join(parts)
    return merged


class Transcriber(Protocol):
    name: str

    def transcribe(self, images: list[PageImage]) -> str: ...


class ModelTranscriber:
    """A vision chat model reads each page into verbatim Markdown."""

    name = "model"

    def __init__(self, llm: Any) -> None:
        self.llm = llm

    def transcribe(self, images: list[PageImage]) -> str:
        parts: list[str] = []
        for i, page in enumerate(images, start=1):
            response = self.llm.invoke(transcription_messages(page.png, i, len(images)))
            content = response.content if hasattr(response, "content") else str(response)
            if isinstance(content, list):  # some providers return content blocks
                content = "\n".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in content
                )
            parts.append(f"<!-- page {i} of {len(images)} -->\n{str(content).strip()}")
        return "\n\n".join(parts)


class OcrTranscriber:
    """No vision model (offline runs): OCR text stands in as the transcript, flagged upstream."""

    name = "ocr"

    def __init__(self, engine: OcrEngine) -> None:
        self.engine = engine

    def transcribe(self, images: list[PageImage]) -> str:
        return ocr_pages(self.engine, images).text
