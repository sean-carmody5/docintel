"""Email with attachments, Excel, Word, archives and the generic long tail."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from docintel.documents import Kind
from docintel.ingest import load, load_bytes

SYNTH = Path("data/synthetic")
PROVIDED = Path("data/provided")
PUBLIC = Path("data/public")


def _cases() -> list[dict]:
    if not SYNTH.exists():
        pytest.skip("synthetic set not built")
    return json.loads((SYNTH / "manifest.json").read_text(encoding="utf-8"))["cases"]


def _truth(case: dict) -> dict:
    return json.loads((SYNTH / case["truth"]).read_text(encoding="utf-8"))["quotation"]


def _names_present(text: str, case: dict) -> None:
    for line in _truth(case)["lines"]:
        assert line["product_name"] in text, (case["id"], line["product_name"])


@pytest.mark.parametrize("case", [c for c in _cases() if c["kind"] == "eml"], ids=lambda c: c["id"])
def test_email_bodies_or_attachments_carry_every_line(case: dict) -> None:
    doc = load(SYNTH / case["id"] / case["files"][0])
    assert doc.kind is Kind.EMAIL and not doc.failed
    assert doc.metadata["subject"] and doc.metadata["from"] and doc.metadata["date"]
    if case["variant"] == "with_attachment":
        assert len(doc.children) == 1
        child = doc.children[0]
        assert child.kind is Kind.PDF and child.parent_id == doc.id and not child.failed
        _names_present(child.text, case)
    else:
        _names_present(doc.text, case)
    if case["variant"] == "html_table_only":
        assert doc.has_flag("html_part_appended") or doc.has_flag("html_body_used")


def test_provided_email_keeps_the_correction() -> None:
    doc = load(next(PROVIDED.glob("*.eml")))
    assert "0.134" in doc.text and "0.128" in doc.text
    assert not doc.has_flag("html_part_appended"), "equivalent HTML part must not be duplicated"


@pytest.mark.parametrize(
    "case", [c for c in _cases() if c["kind"] == "xlsx"], ids=lambda c: c["id"]
)
def test_excel_sheets_become_markdown(case: dict) -> None:
    doc = load(SYNTH / case["id"] / case["files"][0])
    assert doc.kind is Kind.SPREADSHEET and not doc.failed
    assert "## Sheet: Price List" in doc.text and "## Sheet: Terms" in doc.text
    assert "|" in doc.text, "the price table should render as a markdown table"
    _names_present(doc.text, case)


def test_word_tables_and_paragraphs_in_order() -> None:
    case = next(c for c in _cases() if c["kind"] == "docx")
    doc = load(SYNTH / case["id"] / case["files"][0])
    assert doc.kind is Kind.WORD and not doc.failed
    assert doc.metadata["tables"] == 1
    _names_present(doc.text, case)
    assert doc.text.index("## Quotation") < doc.text.index("|")


def test_zip_members_become_children() -> None:
    json_case = next(c for c in _cases() if c["id"] == "json_flat_lines_01")
    pdf_case = next(c for c in _cases() if c["id"] == "pdf_modern_01")
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for case in (json_case, pdf_case):
            p = SYNTH / case["id"] / case["files"][0]
            zf.write(p, arcname=f"bundle/{p.name}")
        zf.writestr("__MACOSX/._junk", b"junk")
    doc = load_bytes(Path("supplier_bundle.zip"), buf.getvalue())
    assert doc.kind is Kind.ARCHIVE and not doc.failed
    assert {c.kind for c in doc.children} == {Kind.JSON, Kind.PDF}
    assert all(c.parent_id == doc.id for c in doc.children)
    assert len(doc.walk()) == 3


def test_legacy_word_is_handled_or_refused_with_reason() -> None:
    path = PUBLIC / "spc_sri_lanka_awards_2012_doc.doc"
    if not path.exists():
        pytest.skip("public set not fetched")
    doc = load(path)
    assert doc.failed or doc.text
    if doc.failed:
        assert doc.has_flag("load_failed:unsupported")
