"""The pipeline as a LangGraph state graph.

discover -> process_document (one per file, in parallel) -> reconcile -> write
-> review (stops here for a person) -> promote

The framework earns its place at exactly these points: fan-out with a concurrency
cap, a retry policy per document, a checkpoint after every node so a crash resumes
rather than restarts, and the interrupt that hands the written table to a reviewer
and waits. Everything inside the nodes is the plain Python built so far.
"""

from __future__ import annotations

import json
import logging
import operator
import sqlite3
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy, Send, interrupt

from docintel.config import Settings
from docintel.documents import Document, Severity
from docintel.extract.extractor import (
    Extractor,
    FixtureExtractor,
    ModelExtractor,
    build_llm,
    dump_result,
)
from docintel.extract.schema import ExtractionResult
from docintel.extract.vision import (
    ModelTranscriber,
    OcrEngine,
    OcrTranscriber,
    Transcriber,
    ocr_engine,
    ocr_pages,
)
from docintel.ingest import load
from docintel.reconcile import reconcile
from docintel.records import Record
from docintel.review import apply_corrections
from docintel.store import write_all
from docintel.store.sources import save_source
from docintel.store.writer import write_csv
from docintel.verify import Sources, build_records, failed_record

log = logging.getLogger(__name__)
_USAGE_LOCK = threading.Lock()
# About 100k tokens: a 2,000-row price list would otherwise blow the context and the bill.
# Chunked extraction is the proper answer and is on the backlog; until then the cut is flagged.
MAX_MODEL_CHARS = 400_000

SKIP_NAMES = {"truth.json", "manifest.json", "README.md", ".DS_Store", "Thumbs.db"}
VISION_FLAGS = {"no_text_layer", "scanned_with_text_layer", "text_layer_untrusted"}


class RunState(TypedDict, total=False):
    input_dir: str
    thread_id: str
    paths: list[str]
    records: Annotated[list[dict[str, Any]], operator.add]
    documents: Annotated[list[dict[str, Any]], operator.add]
    final_records: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    duplicates: list[dict[str, Any]]
    outputs: dict[str, str]
    review: dict[str, Any]
    approved: bool
    decisions: dict[str, str]
    corrections: dict[str, dict[str, Any]]
    promoted: int
    held: int
    rejected: int
    approved_csv: str
    corrected: int
    started: str


class DocState(TypedDict):
    path: str


class Pipeline:
    """Holds the swappable components and builds the graph around them."""

    def __init__(
        self,
        settings: Settings,
        *,
        extractor: Extractor | None = None,
        transcriber: Transcriber | None = None,
        ocr: OcrEngine | None = None,
    ) -> None:
        self.settings = settings
        self.extractor = extractor or self._default_extractor()
        self.ocr = ocr if ocr is not None else (ocr_engine() if settings.ocr else None)
        self.transcriber = transcriber or self._default_transcriber()

    def _default_extractor(self) -> Extractor:
        if self.settings.extractor == "model":
            llm = build_llm(self.settings.model, **self.settings.model_kwargs())
            # Tool calling is the structured-output path. Anthropic's strict JSON-schema mode
            # rejects a schema this size ("compiled grammar is too large"); tool calling warns
            # on the newest models but has produced a valid result on every run, with retries.
            return ModelExtractor(llm)
        return FixtureExtractor(self.settings.fixtures)

    def _default_transcriber(self) -> Transcriber | None:
        if self.settings.extractor == "model":
            llm = build_llm(self.settings.effective_vision_model, **self.settings.model_kwargs())
            return ModelTranscriber(llm)
        return OcrTranscriber(self.ocr) if self.ocr else None

    # ------------------------------------------------------------------ per document

    def process(self, doc: Document) -> list[Record]:
        """One document and its attachments, depth first."""
        out: list[Record] = []
        for d in doc.walk():
            out += self._process_one(d)
        return out

    def _process_one(self, doc: Document) -> list[Record]:
        if doc.failed:
            return [failed_record(doc)]
        vision = bool(doc.images) and (not doc.text or any(doc.has_flag(f) for f in VISION_FLAGS))
        if vision:
            return self._vision(doc)
        sources = Sources(primary=doc.text, extra=[c.text for c in doc.children if c.text])
        result = self._extract(doc)
        return build_records(
            doc,
            result,
            sources=sources,
            extractor_name=self.extractor.name,
            as_of=self.settings.as_of,
        )

    def _extract(self, doc: Document, transcript: str | None = None) -> ExtractionResult:
        """One document's failure is that document's problem, not the batch's.

        The model backend already retries; a recorded fixture that does not fit the
        schema, or a backend that gives up, becomes a flagged empty result so the run
        finishes and the reviewer sees why this file produced nothing.
        """
        text = transcript if transcript is not None else doc.text
        if len(text) > MAX_MODEL_CHARS:
            doc.flag(
                "truncated_for_model",
                Severity.WARNING,
                f"{len(text):,} characters of text; only the first {MAX_MODEL_CHARS:,} were read. "
                "Lines beyond that point are not in the table.",
            )
            transcript = text[:MAX_MODEL_CHARS]
        try:
            result = self.extractor.extract(doc, transcript)
            if self.settings.extractor == "model":
                dump_result(result, self.settings.output_dir / "extractions" / f"{doc.id}.json")
                self._log_usage(doc, "extract", getattr(self.extractor, "last_usage", None))
            return result
        except Exception as exc:  # noqa: BLE001 - the reason travels on the record
            log.exception("extraction failed for %s", doc.name)
            doc.flag("extraction_failed", Severity.HIGH, f"{type(exc).__name__}: {exc}"[:500])
            return ExtractionResult(
                contains_prices=False,
                warnings=[f"extraction failed for {doc.name}: {type(exc).__name__}"],
            )

    def _log_usage(self, doc: Document, stage: str, usage: dict[str, Any] | None) -> None:
        """Tokens per call, appended beside the recordings, so cost per document is a fact."""
        if not usage:
            return
        path = self.settings.output_dir / "extractions" / "usage.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"doc_id": doc.id, "name": doc.name, "stage": stage, **usage})
        with _USAGE_LOCK, path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def _recorded_transcript(self, doc: Document) -> str:
        """In fixture mode a transcript recorded by a live run replays with its extraction,
        so a paid run is reproduced exactly, grounding included."""
        if self.settings.extractor != "fixture":
            return ""
        for root in self.settings.fixtures:
            for stem in (doc.id, Path(doc.name).stem):
                path = root / f"{stem}.transcript.md"
                if path.is_file():
                    return path.read_text(encoding="utf-8")
        return ""

    def _vision(self, doc: Document) -> list[Record]:
        ocr_text: str | None = None
        label = "ocr"
        if self.ocr is not None:
            ocr = ocr_pages(self.ocr, doc.images)
            ocr_text = ocr.text
            label = self.ocr.name
            doc.metadata["ocr_mean_score"] = round(ocr.mean_score, 3)
            doc.flag(
                "ocr_read",
                Severity.INFO,
                f"{self.ocr.name}: {len(ocr.lines)} lines, mean score {ocr.mean_score:.2f}",
            )
        transcript = self._recorded_transcript(doc)
        if transcript:
            doc.flag("vision_path", Severity.INFO, "transcript recorded by an earlier live run")
        elif self.transcriber is not None:
            transcript = self.transcriber.transcribe(doc.images)
            doc.flag("vision_path", Severity.INFO, f"pages transcribed by {self.transcriber.name}")
            if self.settings.extractor == "model":
                path = self.settings.output_dir / "extractions" / f"{doc.id}.transcript.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(transcript, encoding="utf-8", newline="\n")
                self._log_usage(doc, "transcribe", getattr(self.transcriber, "last_usage", None))
        else:
            doc.flag(
                "vision_path",
                Severity.WARNING,
                "no transcriber available; image read only by fixtures",
            )
        primary = transcript or ocr_text or doc.text
        extra = [t for t in (doc.text, ocr_text) if t and t != primary]
        sources = Sources(primary=primary, secondary=ocr_text, secondary_label=label, extra=extra)
        result = self._extract(doc, transcript=primary or None)
        return build_records(
            doc,
            result,
            sources=sources,
            extractor_name=self.extractor.name,
            as_of=self.settings.as_of,
        )

    # ------------------------------------------------------------------ nodes

    def discover(self, state: RunState) -> dict[str, Any]:
        root = Path(state["input_dir"])
        if root.is_file():
            return {
                "paths": [str(root)],
                "started": datetime.now(UTC).isoformat(timespec="seconds"),
            }
        paths = sorted(
            str(p)
            for p in root.rglob("*")
            if p.is_file() and p.name not in SKIP_NAMES and not p.name.startswith(".")
        )
        log.info("discovered %d files under %s", len(paths), root)
        return {"paths": paths, "started": datetime.now(UTC).isoformat(timespec="seconds")}

    @staticmethod
    def fan_out(state: RunState) -> list[Send]:
        return [Send("process_document", {"path": p}) for p in state["paths"]]

    def process_document(self, state: DocState) -> dict[str, Any]:
        doc = load(Path(state["path"]))
        records = self.process(doc)
        summaries = [
            {
                "name": d.name,
                "id": d.id,
                "kind": d.kind.value,
                "status": d.status,
                "parent": d.parent_id,
                "flags": [f.code for f in d.flags],
                "records": sum(1 for r in records if r.source_id == d.id),
                "source": save_source(d, self.settings.output_dir),
            }
            for d in doc.walk()
        ]
        return {"records": [r.model_dump(mode="json") for r in records], "documents": summaries}

    @staticmethod
    def reconcile_node(state: RunState) -> dict[str, Any]:
        records = [Record.model_validate(r) for r in state.get("records", [])]
        conflicts, duplicates = reconcile(records)
        return {
            "final_records": [r.model_dump(mode="json") for r in records],
            "conflicts": [c.model_dump() for c in conflicts],
            "duplicates": [d.model_dump() for d in duplicates],
        }

    def write_node(self, state: RunState) -> dict[str, Any]:
        from docintel.reconcile import Conflict, Duplicate

        records = [Record.model_validate(r) for r in state.get("final_records", [])]
        conflicts = [Conflict.model_validate(c) for c in state.get("conflicts", [])]
        duplicates = [Duplicate.model_validate(d) for d in state.get("duplicates", [])]
        docs = state.get("documents", [])
        run = {
            "input_dir": state.get("input_dir"),
            "thread_id": state.get("thread_id"),
            "started": state.get("started"),
            "documents": len(docs),
            "failed_documents": sum(1 for d in docs if d["status"] == "failed"),
            **self.settings.describe(),
        }
        paths = write_all(
            records,
            conflicts,
            duplicates,
            self.settings.output_dir,
            run=run,
            sources=[d["source"] for d in docs if d.get("source")],
        )
        needs = sum(1 for r in records if r.needs_review)
        return {
            "outputs": {k: str(v) for k, v in paths.items()},
            "review": {
                "records": len(records),
                "needs_review": needs,
                "report": str(paths["report"]),
            },
        }

    @staticmethod
    def review_node(state: RunState) -> dict[str, Any]:
        """Stops the run. The table is on disk; a person edits it and resumes with a decision."""
        decision = interrupt(
            {
                "message": "Review table written. Resume with {'approved': true} to promote.",
                **state.get("review", {}),
                "outputs": state.get("outputs", {}),
            }
        )
        approved = bool(decision.get("approved")) if isinstance(decision, dict) else bool(decision)
        decisions = decision.get("decisions", {}) if isinstance(decision, dict) else {}
        corrections = decision.get("corrections", {}) if isinstance(decision, dict) else {}
        return {
            "approved": approved,
            "decisions": dict(decisions),
            "corrections": dict(corrections),
        }

    def promote_node(self, state: RunState) -> dict[str, Any]:
        """Stub for the hand-off to systems of record.

        With per-row decisions from the review page, exactly the approved rows go on and
        the statuses are written back. Without them, rows needing review are held.
        """
        if not state.get("approved"):
            return {"promoted": 0, "held": len(state.get("final_records", [])), "rejected": 0}
        records = [Record.model_validate(r) for r in state.get("final_records", [])]
        decisions = state.get("decisions") or {}
        corrected = apply_corrections(records, state.get("corrections") or {})
        if decisions or corrected:
            for r in records:
                d = decisions.get(r.record_id)
                if d == "approve":
                    r.status = "approved"
                elif d == "reject":
                    r.status = "rejected"
            ready = [r for r in records if r.status == "approved"]
            out = self.settings.output_dir / "decisions_applied.json"
            out.write_text(
                json.dumps(
                    {
                        "decisions": {r.record_id: r.status for r in records},
                        "corrections": corrected,
                    },
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
                newline="\n",
            )
        else:
            ready = [r for r in records if r.status == "pending_review" and not r.needs_review]
            for r in ready:
                r.status = "approved"
        rejected = sum(1 for r in records if r.status == "rejected")
        approved_csv = self.settings.output_dir / "approved.csv"
        write_csv(ready, approved_csv)
        write_csv(records, self.settings.output_dir / "final.csv")  # every line, final status
        log.info(
            "promote: %d lines approved, %d rejected, %d held, %d corrected",
            len(ready),
            rejected,
            len(records) - len(ready) - rejected,
            len(corrected),
        )
        return {
            "promoted": len(ready),
            "rejected": rejected,
            "held": len(records) - len(ready) - rejected,
            "approved_csv": str(approved_csv),
            "corrected": len(corrected),
        }

    # ------------------------------------------------------------------ graph

    def build(self, checkpointer: Any | None = None) -> Any:
        g = StateGraph(RunState)
        g.add_node("discover", self.discover)
        g.add_node(
            "process_document",
            self.process_document,
            retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0, backoff_factor=2.0),
        )
        g.add_node("reconcile", self.reconcile_node)
        g.add_node("write", self.write_node)
        g.add_node("review", self.review_node)
        g.add_node("promote", self.promote_node)
        g.add_edge(START, "discover")
        g.add_conditional_edges("discover", self.fan_out, ["process_document"])
        g.add_edge("process_document", "reconcile")
        g.add_edge("reconcile", "write")
        g.add_edge("write", "review")
        g.add_edge("review", "promote")
        g.add_edge("promote", END)
        return g.compile(checkpointer=checkpointer or MemorySaver())


def sqlite_checkpointer(path: Path) -> SqliteSaver:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    return SqliteSaver(conn)


def _progress(done: int, total: int) -> None:
    if sys.stderr.isatty():
        print(f"\r  documents {done}/{total}", end="", file=sys.stderr, flush=True)
    else:
        log.info("documents %d/%d", done, total)


def run(
    pipeline: Pipeline, input_dir: Path, *, thread_id: str, checkpointer: Any | None = None
) -> dict[str, Any]:
    """Run to the review stop. Returns the final state, which carries the interrupt payload."""
    graph = pipeline.build(checkpointer)
    config = {
        "configurable": {"thread_id": thread_id},
        "max_concurrency": pipeline.settings.max_concurrency,
    }
    total = done = 0
    for update in graph.stream(
        {"input_dir": str(input_dir), "thread_id": thread_id}, config=config, stream_mode="updates"
    ):
        for node, value in update.items():
            if node == "discover" and isinstance(value, dict):
                total = len(value.get("paths", []))
            elif node == "process_document":
                done += 1
                _progress(done, total)
    if done:
        print(file=sys.stderr)
    state = graph.get_state(config)
    return {"values": state.values, "interrupted": bool(state.next), "next": list(state.next)}


def resume(
    pipeline: Pipeline,
    *,
    thread_id: str,
    approved: bool,
    checkpointer: Any,
    decisions: dict[str, str] | None = None,
    corrections: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    graph = pipeline.build(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    payload: dict[str, Any] = {
        "approved": approved,
        "decisions": decisions or {},
        "corrections": corrections or {},
    }
    result = graph.invoke(Command(resume=payload), config=config)
    return dict(result)


def mermaid(pipeline: Pipeline) -> str:
    return str(pipeline.build().get_graph().draw_mermaid())
