"""PDF and image loading across clean, scanned, garbled, truncated and encrypted cases."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docintel.documents import Kind
from docintel.ingest import load
from docintel.ingest.quality import QUALITY_THRESHOLD, text_quality

SYNTH = Path("data/synthetic")
PROVIDED = Path("data/provided")
PUBLIC = Path("data/public")


def _cases() -> list[dict]:
    if not SYNTH.exists():
        pytest.skip("synthetic set not built")
    return json.loads((SYNTH / "manifest.json").read_text(encoding="utf-8"))["cases"]


def _truth(case: dict) -> dict:
    return json.loads((SYNTH / case["truth"]).read_text(encoding="utf-8"))["quotation"]


@pytest.mark.parametrize("case", [c for c in _cases() if c["kind"] == "pdf"], ids=lambda c: c["id"])
def test_clean_pdf_text_layer_is_trusted_and_complete(case: dict) -> None:
    doc = load(SYNTH / case["id"] / case["files"][0])
    assert doc.kind is Kind.PDF and not doc.failed
    assert doc.text_quality is not None and doc.text_quality >= QUALITY_THRESHOLD, doc.text_quality
    assert not doc.images, "clean text layer should not trigger rendering"
    for line in _truth(case)["lines"]:
        assert line["product_name"] in doc.text, (case["id"], line["product_name"])


@pytest.mark.parametrize(
    "case", [c for c in _cases() if c["kind"] == "scanned_pdf"], ids=lambda c: c["id"]
)
def test_scanned_pdf_routes_to_vision(case: dict) -> None:
    doc = load(SYNTH / case["id"] / case["files"][0])
    assert not doc.failed
    assert doc.images, "scanned PDF must render pages"
    if case["variant"] in ("image_only", "cover_sheet"):
        assert doc.has_flag("no_text_layer") and doc.text == ""
    else:
        assert doc.has_flag("scanned_with_text_layer")
        assert doc.text, "the OCR layer is kept for cross-checks"
        # Routing is structural; quality is informational and must only sit below clean.
        assert doc.text_quality is not None and doc.text_quality < 0.9, doc.text_quality


def test_encrypted_pdf_is_refused_with_reason() -> None:
    case = next(c for c in _cases() if c["variant"] == "pdf_encrypted")
    doc = load(SYNTH / case["id"] / case["files"][0])
    assert doc.failed and doc.has_flag("load_failed:encrypted")


def test_truncated_pdf_is_read_and_flagged() -> None:
    case = next(c for c in _cases() if c["variant"] == "pdf_truncated")
    doc = load(SYNTH / case["id"] / case["files"][0])
    assert not doc.failed
    assert doc.has_flag("repaired")
    assert doc.text, "surviving pages should still yield text"


def test_misnamed_pdf_loads_as_pdf() -> None:
    case = next(c for c in _cases() if c["id"] == "misnamed_pdf_as_dat")
    doc = load(SYNTH / case["id"] / case["files"][0])
    assert doc.kind is Kind.PDF and not doc.failed and doc.text


@pytest.mark.parametrize(
    "case", [c for c in _cases() if c["kind"] == "image"], ids=lambda c: c["id"]
)
def test_images_become_page_images(case: dict) -> None:
    doc = load(SYNTH / case["id"] / case["files"][0])
    assert doc.kind is Kind.IMAGE and not doc.failed
    assert len(doc.images) == 1 and doc.images[0].png.startswith(b"\x89PNG")
    assert doc.text == "" and doc.text_quality is None


def test_provided_pdfs_and_scans() -> None:
    for path in PROVIDED.glob("*.pdf"):
        doc = load(path)
        assert not doc.failed and not doc.images, path.name
        assert doc.text_quality is not None and doc.text_quality >= QUALITY_THRESHOLD, path.name
    for path in list(PROVIDED.glob("*.png")) + list(PROVIDED.glob("*.jpg")):
        doc = load(path)
        assert doc.kind is Kind.IMAGE and doc.images


@pytest.mark.parametrize(
    "name",
    [
        "drap_20drugs_2023_scanned.pdf",
        "quezon_city_rfq_scanned.pdf",
        "gmc_baramati_quotation_scanned.pdf",
    ],
)
def test_real_scanned_pdfs_are_detected(name: str) -> None:
    path = PUBLIC / name
    if not path.exists():
        pytest.skip("public set not fetched")
    doc = load(path)
    assert doc.has_flag("scanned_with_text_layer") or doc.has_flag("no_text_layer"), [
        f.code for f in doc.flags
    ]
    assert doc.images


def test_quality_separates_clean_from_garbled() -> None:
    clean = (
        "Unit price is the price per unit of measure shown. "
        "Pack price is unit price multiplied by units."
    )
    garbled = (
        "Unjt pr~ice js fhe pr1ce per uujt of mcosure sh0wn. Pock pr'ice js uujt prjce mu1tiplied."
    )
    assert text_quality(clean) >= 0.9
    assert text_quality(garbled) < QUALITY_THRESHOLD
    assert text_quality("") == 0.0
