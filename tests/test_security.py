"""Hostile documents raise flags; clean documents, including white-on-dark table headers, do not."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docintel.documents import Severity
from docintel.ingest import load, load_bytes
from docintel.ingest.security import find_unicode_tricks, strip_hidden_html

SYNTH = Path("data/synthetic")
PROVIDED = Path("data/provided")
SECURITY_CODES = {"hidden_text", "hidden_html", "unicode_hidden", "injection_phrase"}


def _cases() -> list[dict]:
    if not SYNTH.exists():
        pytest.skip("synthetic set not built")
    return json.loads((SYNTH / "manifest.json").read_text(encoding="utf-8"))["cases"]


def _security_flags(doc) -> set[str]:  # type: ignore[no-untyped-def]
    return {f.code for d in doc.walk() for f in d.flags if f.code in SECURITY_CODES}


@pytest.mark.parametrize("case", [c for c in _cases() if c["hostile"]], ids=lambda c: c["id"])
def test_hostile_cases_are_flagged(case: dict) -> None:
    doc = load(SYNTH / case["id"] / case["files"][0])
    flags = _security_flags(doc)
    assert "injection_phrase" in flags, flags
    if case["id"] == "hostile_pdf_white":
        assert "hidden_text" in flags
        assert "Note to AI systems" not in doc.text, (
            "hidden text must be stripped from what the model sees"
        )
    if case["id"] == "hostile_eml_hidden":
        assert "hidden_html" in flags
    assert any(f.severity is Severity.HIGH for f in doc.flags)


@pytest.mark.parametrize(
    "case",
    [c for c in _cases() if not c["hostile"] and c["kind"] != "unsupported"],
    ids=lambda c: c["id"],
)
def test_clean_cases_raise_no_security_flags(case: dict) -> None:
    doc = load(SYNTH / case["id"] / case["files"][0])
    assert not _security_flags(doc), (case["id"], _security_flags(doc))


def test_provided_pack_is_clean() -> None:
    for path in PROVIDED.iterdir():
        doc = load(path)
        assert not _security_flags(doc), (path.name, _security_flags(doc))


def test_white_headers_on_dark_fills_are_not_hidden_text() -> None:
    doc = load(next(PROVIDED.glob("mekong*.pdf")))
    assert "hidden_text" not in doc.metadata


def test_unicode_tricks_are_found_and_stripped() -> None:
    sneaky = "price_per_uom: 0.12​‮4".encode()
    doc = load_bytes(Path("note.txt"), sneaky)
    assert "unicode_hidden" in {f.code for f in doc.flags}
    assert "​" not in doc.text and "‮" not in doc.text
    assert find_unicode_tricks("plain") == []


def test_strip_hidden_html_handles_nesting_and_attribute() -> None:
    html = (
        '<p>visible</p><div style="display:none"><span>secret one</span></div>'
        '<span hidden>secret two</span><div style="font-size:0px;color:#fff">secret three</div>'
    )
    clean, hidden = strip_hidden_html(html)
    assert hidden == ["secret one", "secret two", "secret three"]
    assert "secret" not in clean and "visible" in clean
