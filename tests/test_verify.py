"""Grounding, checks and confidence behave as the plan says on every synthetic and provided case."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from docintel.extract.extractor import FixtureExtractor
from docintel.extract.schema import ExtractionResult, QuotationLine
from docintel.ingest import load
from docintel.verify import Sources, build_records
from docintel.verify.checks import check_line
from docintel.verify.grounding import number_forms, value_in_text
from docintel.verify.normalise import normalise_form, normalise_inn, normalise_strength

SYNTH = Path("data/synthetic")
PROVIDED = Path("data/provided")
FIXTURES = [Path("tests/fixtures/synthetic"), Path("tests/fixtures/provided")]
TEXT_KINDS = {"json", "pdf", "eml", "xlsx", "docx", "csv", "chat", "xml", "html", "txt"}


def _cases() -> list[dict]:
    if not SYNTH.exists():
        pytest.skip("synthetic set not built")
    return json.loads((SYNTH / "manifest.json").read_text(encoding="utf-8"))["cases"]


def _records(path: Path):  # type: ignore[no-untyped-def]
    doc = load(path)
    if doc.children:  # a cover email is judged on its attachment
        doc = doc.children[0]
    result = FixtureExtractor(FIXTURES).extract(doc)
    return (
        doc,
        result,
        build_records(doc, result, sources=Sources(primary=doc.text), extractor_name="fixture"),
    )


def test_number_forms_cover_document_conventions() -> None:
    assert "0.0128" in number_forms(0.0128) and "0,0128" in number_forms(0.0128)
    assert "52,962.00" in number_forms(52962.0) and "52962" in number_forms(52962.0)
    assert value_in_text(0.0128, "Unit price 0.0128 per tablet")
    assert value_in_text(0.0128, "Preis je Einheit;0,0128")
    assert not value_in_text(0.012, "Unit price 0.0128 per tablet"), "no partial digit matches"
    assert value_in_text("Dolostop 500", "01 | Dolostop 500 | Paracetamol")


def test_normalisation_merges_variants_and_keeps_distinct_forms() -> None:
    assert normalise_inn("Amoxicillin + Clavulanic acid") == normalise_inn("Co-amoxiclav")
    assert normalise_inn("Amoxicillin/Clavulanate") == normalise_inn(
        "Amoxicillin and clavulanate potassium"
    )
    assert normalise_inn("Amlodipine besylate") == normalise_inn("Amlodipine")
    assert normalise_inn("Acetaminophen") == normalise_inn("Paracetamol")
    assert normalise_inn("TDF/3TC/DTG") == normalise_inn(
        "Tenofovir disoproxil fumarate + Lamivudine + Dolutegravir"
    )
    assert normalise_inn("Amoxicillin") != normalise_inn("Amoxicillin + Clavulanic acid")
    assert (
        normalise_strength("500mg") == normalise_strength("500 mg") == normalise_strength("0.5 g")
    )
    assert normalise_form("Syrup") != normalise_form("Pressurised inhalation, suspension")
    assert normalise_form("Film-coated tablet") == normalise_form("Tablets") == "tablet"


def test_checks_catch_arithmetic_and_plausibility() -> None:
    bad = QuotationLine(
        price_per_uom=0.5, price_per_pack=3.0, units_per_pack=10, currency="USD", uom="tablet"
    )
    codes = {c for _, c, _ in check_line(bad, "USD")}
    assert "pack_unit_mismatch" in codes
    wild = QuotationLine(price_per_uom=950.0, currency="USD", uom="tablet")
    assert "implausible_price" in {c for _, c, _ in check_line(wild, "USD")}
    ok = QuotationLine(
        price_per_uom=0.0128, price_per_pack=0.384, units_per_pack=30, currency="USD", uom="tablet"
    )
    assert not check_line(ok, "USD")


@pytest.mark.parametrize(
    "case",
    [c for c in _cases() if c["kind"] in TEXT_KINDS and not c["hostile"]],
    ids=lambda c: c["id"],
)
def test_text_cases_ground_their_key_fields(case: dict) -> None:
    doc, result, records = _records(SYNTH / case["id"] / case["files"][0])
    assert len(records) == len(result.lines)
    for rec in records:
        assert rec.confidence["product_name"].tier == "high", (
            case["id"],
            rec.confidence["product_name"],
        )
        assert rec.confidence["inn"].tier == "high", (case["id"], rec.confidence["inn"])
        if rec.price_basis in ("stated", "list"):
            assert rec.confidence["price_per_uom"].tier == "high", (
                case["id"],
                rec.confidence["price_per_uom"],
            )
        else:
            assert "derived" in " ".join(rec.confidence["price_per_uom"].reasons)


def test_hostile_cases_are_sent_to_review() -> None:
    for case in (c for c in _cases() if c["hostile"]):
        _, _, records = _records(SYNTH / case["id"] / case["files"][0])
        assert all(r.needs_review for r in records), case["id"]
        assert any("injection_phrase" in reason for r in records for reason in r.review_reasons), (
            case["id"]
        )


def test_fabricated_value_scores_low() -> None:
    doc = load(next(PROVIDED.glob("zenith*.json")))
    result = FixtureExtractor(FIXTURES).extract(doc)
    result.lines[0].price_per_uom = 0.0999  # not in the document
    result.lines[0].evidence["price_per_uom"] = "0.0999"
    records = build_records(
        doc, result, sources=Sources(primary=doc.text), extractor_name="fixture"
    )
    c = records[0].confidence["price_per_uom"]
    assert c.tier == "low" and any("not found" in r for r in c.reasons)
    assert records[0].needs_review


def test_provided_pack_review_decisions() -> None:
    by_name = {}
    for path in PROVIDED.iterdir():
        _, _, records = _records(path)
        by_name[path.name] = records
    zenith = by_name["zenith_pharma_quotation_ZPL-Q-2026-4471.json"]
    assert all(not r.needs_review for r in zenith), [r.review_reasons for r in zenith]
    novara = by_name["RE_RFQ-2026-0244_Novara_quotation.eml"]
    assert novara[0].needs_review and any("corrected" in r for r in novara[0].review_reasons)
    sanova = by_name["sanova_offer_export_2026-08-03.json"]
    assert all(r.price_basis == "derived" and r.needs_review for r in sanova)
    glare = by_name["scan_03_glare_partial_andina_p1.jpg"]
    assert all(r.needs_review for r in glare)
    assert glare[0].confidence["price_per_uom"].score == 0.0


def test_no_lines_and_failed_loads_still_produce_rows() -> None:
    empty = next(c for c in _cases() if c["variant"] == "empty")
    doc = load(SYNTH / empty["id"] / empty["files"][0])
    from docintel.verify import failed_record

    rec = failed_record(doc)
    assert (
        rec.status == "failed" and rec.needs_review and "zero bytes" in " ".join(rec.review_reasons)
    )
    result = ExtractionResult(contains_prices=False, warnings=["RFQ without prices"])
    rows = build_records(doc, result, sources=Sources(primary=""), extractor_name="fixture")
    assert rows[0].status == "no_lines" and rows[0].needs_review


def test_expired_quotation_is_flagged_only_when_an_as_of_date_is_given() -> None:
    case = next(c for c in _cases() if c["id"] == "pdf_modern_04")
    doc = load(SYNTH / case["id"] / case["files"][0])
    result = FixtureExtractor(FIXTURES).extract(doc)
    dated = build_records(
        doc,
        result,
        sources=Sources(primary=doc.text),
        extractor_name="fixture",
        as_of=date(2026, 10, 8),
    )
    assert all(r.needs_review and any("expired" in x for x in r.review_reasons) for r in dated)
    undated = build_records(
        doc, result, sources=Sources(primary=doc.text), extractor_name="fixture"
    )
    assert not any("expired" in x for r in undated for x in r.review_reasons)


def test_a_name_the_ocr_reads_differently_is_not_high_confidence() -> None:
    """On a scan the model's own transcript cannot vouch for the model; the OCR reading can."""
    from docintel.verify.confidence import Sources, Weights, score_field

    src = Sources(primary="Pacetam 500 Paracetamol", secondary="Paccetam 500 Paracetamol")
    c = score_field("product_name", "Pacetam 500", "Pacetam 500", src, [], False, Weights())
    assert c.tier != "high" and any("not found by" in r for r in c.reasons)
    agreed = Sources(primary="Paccetam 500 Paracetamol", secondary="Paccetam 500 Paracetamol")
    ok = score_field("product_name", "Paccetam 500", "Paccetam 500", agreed, [], False, Weights())
    assert ok.tier == "high"


def test_repairs_move_a_concentration_out_of_the_inn_and_derive_the_other_price() -> None:
    from docintel.extract.schema import QuotationLine
    from docintel.verify.confidence import _empty_line, _repair_line

    line = QuotationLine(
        product_name="Lidoex 2%",
        inn="Lidocaine hydrochloride 2%",
        strength="20 mL",
        units_per_pack=10,
        price_per_uom=0.9,
        uom="vial",
    )
    notes = _repair_line(line)
    assert line.inn == "Lidocaine hydrochloride" and line.strength == "2%, 20 mL"
    assert line.price_per_pack == 9.0 and any("pack price derived" in n for n in notes)
    other = QuotationLine(
        product_name="X", inn="Zinc sulfate", units_per_pack=100, price_per_pack=1.55, uom="tablet"
    )
    _repair_line(other)
    assert other.price_per_uom == 0.0155 and other.price_basis == "derived"
    assert _empty_line(QuotationLine()) and not _empty_line(line)


def test_normalised_inn_ignores_a_trailing_concentration() -> None:
    from docintel.verify.normalise import normalise_inn

    assert normalise_inn("Lidocaine hydrochloride 2%") == normalise_inn("Lidocaine hydrochloride")
