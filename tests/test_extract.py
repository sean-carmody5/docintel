"""The schema accepts every fixture; the fixture backend serves every document offline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docintel.extract.extractor import FixtureExtractor
from docintel.extract.prompt import extraction_messages, transcription_messages
from docintel.extract.schema import ExtractionResult
from docintel.ingest import load

SYNTH = Path("data/synthetic")
PROVIDED = Path("data/provided")
FIXTURES = [Path("tests/fixtures/synthetic"), Path("tests/fixtures/provided")]


def _cases() -> list[dict]:
    if not SYNTH.exists():
        pytest.skip("synthetic set not built")
    return json.loads((SYNTH / "manifest.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize(
    "path", sorted(p for root in FIXTURES for p in root.glob("*.json")), ids=lambda p: p.stem
)
def test_every_fixture_validates(path: Path) -> None:
    result = ExtractionResult.model_validate_json(path.read_text(encoding="utf-8"))
    assert result.lines or not result.contains_prices
    for line in result.lines:
        for field in line.evidence:
            assert hasattr(line, field), f"{path.stem}: evidence for unknown field {field}"


@pytest.mark.parametrize("case", [c for c in _cases() if "truth" in c], ids=lambda c: c["id"])
def test_fixture_backend_matches_truth_line_count(case: dict) -> None:
    doc = load(SYNTH / case["id"] / case["files"][0])
    result = FixtureExtractor(FIXTURES).extract(doc)
    truth = json.loads((SYNTH / case["truth"]).read_text(encoding="utf-8"))["quotation"]
    assert len(result.lines) == len(truth["lines"])
    assert result.quotation_ref == truth["quotation_ref"]


def test_provided_pack_has_a_fixture_each() -> None:
    extractor = FixtureExtractor(FIXTURES)
    for path in PROVIDED.iterdir():
        doc = load(path)
        result = extractor.extract(doc)
        assert result.contains_prices, path.name
        assert result.lines, path.name


def test_novara_fixture_keeps_the_correction() -> None:
    doc = load(next(PROVIDED.glob("*.eml")))
    result = FixtureExtractor(FIXTURES).extract(doc)
    first = result.lines[0]
    assert first.price_per_uom == 0.134
    assert first.superseded is not None and first.superseded.old == 0.128


def test_prompt_frames_document_as_data() -> None:
    doc = load(next(PROVIDED.glob("*.json")))
    messages = extraction_messages(doc)
    assert messages[0]["role"] == "system" and "untrusted" in messages[0]["content"]
    assert "<document>" in messages[1]["content"] and doc.name in messages[1]["content"]
    pages = transcription_messages(b"\x89PNG", 1, 2)
    assert pages[1]["content"][1]["type"] == "image_url"
