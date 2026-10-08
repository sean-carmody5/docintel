"""Turn a Document into an ExtractionResult. Two backends behind one interface.

`ModelExtractor` is the real thing: a LangChain chat model with structured output,
retries and tracing. `FixtureExtractor` replays recorded results by document id so
the whole graph runs offline in tests and CI. The graph never knows which it has.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Protocol

from docintel.documents import Document
from docintel.extract.prompt import extraction_messages
from docintel.extract.schema import ExtractionResult

log = logging.getLogger(__name__)


class Extractor(Protocol):
    name: str

    def extract(self, doc: Document, transcript: str | None = None) -> ExtractionResult: ...


class FixtureExtractor:
    """Replay recorded extractions. Looks up by document id, then by file name."""

    name = "fixture"

    def __init__(self, roots: list[Path]) -> None:
        self.by_key: dict[str, Path] = {}
        for root in roots:
            for path in sorted(root.rglob("*.json")):
                self.by_key[path.stem] = path

    def extract(self, doc: Document, transcript: str | None = None) -> ExtractionResult:
        path = (
            self.by_key.get(doc.id)
            or self.by_key.get(doc.name)
            or self.by_key.get(Path(doc.name).stem)
        )
        if path is None:
            log.warning("no fixture for %s (id %s); returning an empty result", doc.name, doc.id)
            return ExtractionResult(
                contains_prices=False,
                warnings=[f"no recorded extraction for {doc.name}; fixture mode cannot read it"],
            )
        return ExtractionResult.model_validate_json(path.read_text(encoding="utf-8"))


class ModelExtractor:
    """A LangChain chat model constrained to the schema, with retries."""

    name = "model"

    def __init__(self, llm: Any, *, max_retries: int = 2) -> None:
        self.llm = llm
        self.structured = llm.with_structured_output(ExtractionResult).with_retry(
            stop_after_attempt=max_retries + 1
        )
        self.last_usage: dict[str, Any] | None = None  # tokens of the most recent call

    def extract(self, doc: Document, transcript: str | None = None) -> ExtractionResult:
        from langchain_core.callbacks import UsageMetadataCallbackHandler

        messages = extraction_messages(doc, transcript)
        usage = UsageMetadataCallbackHandler()
        result = self.structured.invoke(messages, config={"callbacks": [usage]})
        self.last_usage = flatten_usage(usage.usage_metadata)
        if isinstance(result, ExtractionResult):
            return result
        if isinstance(result, dict):  # some providers hand back the raw dict
            return ExtractionResult.model_validate(result)
        raise TypeError(f"unexpected structured output type {type(result).__name__}")


def flatten_usage(by_model: dict[str, Any]) -> dict[str, Any] | None:
    """LangChain reports usage per model name; one call is one model, so sum and keep the name."""
    if not by_model:
        return None
    inp = sum(int(u.get("input_tokens", 0)) for u in by_model.values())
    out = sum(int(u.get("output_tokens", 0)) for u in by_model.values())
    return {"model": ", ".join(by_model), "input_tokens": inp, "output_tokens": out}


def build_llm(model: str, **kwargs: Any) -> Any:
    """`provider:model` string to a LangChain chat model. One place to swap providers."""
    from langchain.chat_models import init_chat_model

    return init_chat_model(model, **kwargs)


def dump_result(result: ExtractionResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
