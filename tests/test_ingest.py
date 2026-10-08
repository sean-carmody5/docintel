"""Sniffing and loading across the whole synthetic set, plus the provided files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docintel.documents import Kind
from docintel.ingest import load, registered, sniff

SYNTH = Path("data/synthetic")
PROVIDED = Path("data/provided")

EXPECTED_MEDIA = {
    "json": "application/json",
    "pdf": "application/pdf",
    "eml": "message/rfc822",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "csv": "text/csv",
    "chat": "text/x-chat",
    "xml": "application/xml",
    "html": "text/html",
    "txt": "text/plain",
    "scanned_pdf": "application/pdf",
}


def _cases() -> list[dict]:
    if not SYNTH.exists():
        pytest.skip("synthetic set not built")
    return json.loads((SYNTH / "manifest.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c["id"])
def test_sniff_ignores_extension(case: dict) -> None:
    path = SYNTH / case["id"] / case["files"][0]
    media = sniff(path.read_bytes(), path.suffix)
    if case["kind"] == "image":
        assert media.startswith("image/")
    elif case["kind"] == "misnamed":
        assert media in ("application/json", "application/pdf")
    elif case["kind"] == "unsupported":
        assert media == "application/octet-stream"
    elif case["kind"] == "malformed":
        expected = {
            "empty": "inode/x-empty",
            "pdf_truncated": "application/pdf",
            "pdf_encrypted": "application/pdf",
            "json_broken": "application/json",
        }
        assert media == expected[case["variant"]]
    else:
        assert media == EXPECTED_MEDIA[case["kind"]], case["id"]


def test_registry_lists_loaders() -> None:
    assert "application/json" in registered()
    assert "text/*" in registered()


@pytest.mark.parametrize(
    "case", [c for c in _cases() if c["kind"] == "json"], ids=lambda c: c["id"]
)
def test_json_loads_any_dialect(case: dict) -> None:
    doc = load(SYNTH / case["id"] / case["files"][0])
    assert doc.kind is Kind.JSON and not doc.failed
    truth = json.loads((SYNTH / case["truth"]).read_text(encoding="utf-8"))
    for line in truth["quotation"]["lines"]:
        assert line["product_name"] in doc.text, (case["id"], line["product_name"])


def test_broken_json_is_repaired_and_flagged() -> None:
    case = next(c for c in _cases() if c["variant"] == "json_broken")
    doc = load(SYNTH / case["id"] / case["files"][0])
    assert not doc.failed
    assert doc.has_flag("parsed_leniently")
    assert "items" in doc.text


def test_misnamed_json_loads_as_json() -> None:
    case = next(c for c in _cases() if c["id"] == "misnamed_json_as_txt")
    doc = load(SYNTH / case["id"] / case["files"][0])
    assert doc.kind is Kind.JSON and not doc.failed


def test_empty_and_unknown_fail_with_reasons() -> None:
    empty = next(c for c in _cases() if c["variant"] == "empty")
    doc = load(SYNTH / empty["id"] / empty["files"][0])
    assert doc.failed and doc.has_flag("load_failed:empty")
    noise = next(c for c in _cases() if c["kind"] == "unsupported")
    doc = load(SYNTH / noise["id"] / noise["files"][0])
    assert doc.failed and doc.has_flag("load_failed:unsupported")


@pytest.mark.parametrize("kind", ["chat", "xml", "html", "txt", "csv"])
def test_text_family_loads_with_product_names(kind: str) -> None:
    for case in (c for c in _cases() if c["kind"] == kind):
        doc = load(SYNTH / case["id"] / case["files"][0])
        assert not doc.failed, case["id"]
        truth = json.loads((SYNTH / case["truth"]).read_text(encoding="utf-8"))
        for line in truth["quotation"]["lines"]:
            assert line["product_name"] in doc.text, (case["id"], line["product_name"])


def test_same_bytes_same_id() -> None:
    a = load(SYNTH / "json_flat_lines_01" / "yuantai_export_2026-08-01.json")
    b = load(SYNTH / "misnamed_json_as_txt" / "yuantai_export_2026-08-01.txt")
    assert a.id == b.id


def test_provided_json_files_load() -> None:
    for path in PROVIDED.glob("*.json"):
        doc = load(path)
        assert doc.kind is Kind.JSON and not doc.failed and "price" in doc.text.lower()
