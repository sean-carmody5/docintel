"""Run settings. Environment variables, all prefixed DOCINTEL_, with explicit overrides.

The model is a `provider:model` string so swapping providers is a config change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "anthropic:claude-sonnet-5-5"
DEFAULT_FIXTURES = (Path("tests/fixtures/synthetic"), Path("tests/fixtures/provided"))


@dataclass
class Settings:
    extractor: str = "fixture"  # fixture | model
    model: str = DEFAULT_MODEL
    vision_model: str | None = None  # defaults to model
    second_pass_model: str | None = None  # a different family, e.g. google_genai:gemini-2.5-flash
    ocr: bool = True
    max_concurrency: int = 4
    output_dir: Path = Path("output")
    checkpoint_db: Path = Path("output/checkpoints.sqlite")
    fixtures: list[Path] = field(default_factory=lambda: list(DEFAULT_FIXTURES))
    as_of: date | None = None
    temperature: float | None = (
        None  # the model's default unless set; newer models reject other values
    )
    max_tokens: int = 32768  # a 40-line price list with an evidence quote per field runs past 8k

    @classmethod
    def from_env(cls, **overrides: Any) -> Settings:
        env = os.environ
        values: dict[str, Any] = {}
        if v := env.get("DOCINTEL_EXTRACTOR"):
            values["extractor"] = v
        if v := env.get("DOCINTEL_MODEL"):
            values["model"] = v
        if v := env.get("DOCINTEL_VISION_MODEL"):
            values["vision_model"] = v
        if v := env.get("DOCINTEL_SECOND_PASS_MODEL"):
            values["second_pass_model"] = v
        if v := env.get("DOCINTEL_OCR"):
            values["ocr"] = v.lower() not in ("0", "false", "off", "no")
        if v := env.get("DOCINTEL_MAX_CONCURRENCY"):
            values["max_concurrency"] = int(v)
        if v := env.get("DOCINTEL_OUTPUT_DIR"):
            values["output_dir"] = Path(v)
        if v := env.get("DOCINTEL_AS_OF"):
            values["as_of"] = date.fromisoformat(v)
        values.update({k: v for k, v in overrides.items() if v is not None})
        settings = cls(**values)
        if settings.extractor not in ("fixture", "model"):
            raise ValueError(
                f"DOCINTEL_EXTRACTOR must be fixture or model, got {settings.extractor!r}"
            )
        return settings

    def model_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"max_tokens": self.max_tokens}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        return kwargs

    @property
    def effective_vision_model(self) -> str:
        return self.vision_model or self.model

    def describe(self) -> dict[str, Any]:
        return {
            "extractor": self.extractor,
            "fixtures": [str(p) for p in self.fixtures] if self.extractor == "fixture" else None,
            "model": self.model if self.extractor == "model" else None,
            "vision_model": self.effective_vision_model if self.extractor == "model" else None,
            "second_pass_model": self.second_pass_model,
            "ocr": self.ocr,
            "as_of": self.as_of.isoformat() if self.as_of else None,
        }
