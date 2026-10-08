"""The whole graph, offline: fan-out, reconcile, write, stop for review, resume, promote."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

from docintel.cli import main
from docintel.config import Settings
from docintel.graph import Pipeline, mermaid, resume, run, sqlite_checkpointer

PROVIDED = Path("data/provided")


def _settings(tmp_path: Path) -> Settings:
    return Settings(extractor="fixture", ocr=False, output_dir=tmp_path, max_concurrency=4)


def test_graph_runs_to_the_review_stop_and_resumes(tmp_path: Path) -> None:
    pipeline = Pipeline(_settings(tmp_path))
    checkpointer = MemorySaver()
    result = run(pipeline, PROVIDED, thread_id="t1", checkpointer=checkpointer)
    assert result["interrupted"] and result["next"] == ["review"]
    values = result["values"]
    assert len(values["documents"]) == 8
    assert values["review"]["records"] == 37  # 4+3+4+5+6+3+6+6 provided lines, unmerged
    assert values["review"]["needs_review"] > 0
    assert Path(values["outputs"]["csv"]).exists() and Path(values["outputs"]["report"]).exists()
    previews = list((tmp_path / "sources").rglob("page-1.jpg"))
    assert len(previews) >= 4  # two scans and two PDFs get a page a reviewer can look at
    with Path(values["outputs"]["csv"]).open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 37
    assert any(
        r["source_document"].startswith("scan_03") and r["needs_review"] == "True" for r in rows
    )

    final = resume(pipeline, thread_id="t1", approved=True, checkpointer=checkpointer)
    assert final["approved"] is True
    assert 0 < final["promoted"] < 37, "clean records promoted, flagged ones held back"


def test_reject_promotes_nothing(tmp_path: Path) -> None:
    pipeline = Pipeline(_settings(tmp_path))
    checkpointer = MemorySaver()
    run(pipeline, PROVIDED, thread_id="t2", checkpointer=checkpointer)
    final = resume(pipeline, thread_id="t2", approved=False, checkpointer=checkpointer)
    assert final["promoted"] == 0


def test_sqlite_checkpoint_survives_a_new_graph_instance(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    db = tmp_path / "checkpoints.sqlite"
    run(Pipeline(settings), PROVIDED, thread_id="t3", checkpointer=sqlite_checkpointer(db))
    # a fresh process would build a new graph against the same database
    final = resume(
        Pipeline(settings), thread_id="t3", approved=True, checkpointer=sqlite_checkpointer(db)
    )
    assert final["promoted"] > 0


def test_failed_and_malformed_inputs_become_rows_not_crashes(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "empty.pdf").write_bytes(b"")
    (folder / "noise.bin").write_bytes(bytes(range(256)) * 4)
    (folder / "broken.json").write_text('{"items": [1, 2,], "note": "x"', encoding="utf-8")
    out = tmp_path / "out"
    result = run(
        Pipeline(Settings(extractor="fixture", ocr=False, output_dir=out)), folder, thread_id="t4"
    )
    docs = {d["name"]: d for d in result["values"]["documents"]}
    assert docs["empty.pdf"]["status"] == "failed" and docs["noise.bin"]["status"] == "failed"
    records = result["values"]["final_records"]
    assert {r["status"] for r in records} >= {"failed"}
    assert all(r["needs_review"] for r in records)


def test_mermaid_and_cli_draw(capsys) -> None:  # type: ignore[no-untyped-def]
    text = mermaid(Pipeline(Settings(extractor="fixture", ocr=False)))
    assert "process_document" in text and "review" in text
    assert main(["draw"]) == 0
    assert "reconcile" in capsys.readouterr().out


def test_single_file_input_and_review_page(tmp_path: Path) -> None:
    pipeline = Pipeline(_settings(tmp_path))
    one = next(PROVIDED.glob("zenith*.json"))
    result = run(pipeline, one, thread_id="t5")
    values = result["values"]
    assert len(values["documents"]) == 1 and values["review"]["records"] == 4
    html = Path(values["outputs"]["html"]).read_text(encoding="utf-8")
    assert "<title>Quotation Review</title>" in html and "Zenamox 500/125" in html
    source = values["documents"][0]["source"]
    assert source["text"] and not source["pages"]  # JSON shows as text with evidence marked


def test_decisions_from_the_review_page_drive_promote(tmp_path: Path) -> None:
    pipeline = Pipeline(_settings(tmp_path))
    checkpointer = MemorySaver()
    result = run(pipeline, PROVIDED, thread_id="t6", checkpointer=checkpointer)
    ids = [r["record_id"] for r in result["values"]["final_records"]]
    decisions = {ids[0]: "approve", ids[1]: "approve", ids[2]: "reject"}
    final = resume(
        pipeline, thread_id="t6", approved=True, checkpointer=checkpointer, decisions=decisions
    )
    assert final["promoted"] == 2 and final["rejected"] == 1 and final["held"] == len(ids) - 3
    applied = json.loads((tmp_path / "decisions_applied.json").read_text(encoding="utf-8"))
    assert applied[ids[0]] == "approved" and applied[ids[2]] == "rejected"
    with (tmp_path / "approved.csv").open(encoding="utf-8") as fh:
        approved = list(csv.DictReader(fh))
    assert [r["record_id"] for r in approved] == ids[:2]
    assert all(r["status"] == "approved" for r in approved)


def test_a_fixture_that_does_not_fit_the_schema_flags_the_document_not_the_run(
    tmp_path: Path,
) -> None:
    bad_root = tmp_path / "fixtures"
    bad_root.mkdir()
    one = next(PROVIDED.glob("zenith*.json"))
    (bad_root / f"{one.stem}.json").write_text(
        '{"contains_prices": true, "lines": [{"product_name": 5, "evidence": {"moq_packs": 50}}]}',
        encoding="utf-8",
    )
    settings = Settings(extractor="fixture", ocr=False, output_dir=tmp_path, fixtures=[bad_root])
    result = run(Pipeline(settings), one, thread_id="t7")
    records = result["values"]["final_records"]
    assert len(records) == 1 and records[0]["needs_review"]
    assert any(f["code"] == "extraction_failed" for f in records[0]["flags"])
