"""Expected extractions for the synthetic set, derived from truth.

    uv run python -m evals.synth.fixtures

Writes tests/fixtures/synthetic/<case_id>.json in the ExtractionResult shape. These
let the whole pipeline run offline, and they are the targets the scorer compares
live model output against. Evidence quotes are the values formatted the way the
renderers print them, which is what a careful model would copy.
"""

from __future__ import annotations

import email
import email.policy
import json
from pathlib import Path
from typing import Any

from evals.synth.truth import fmt_money

MANIFEST = Path("data/synthetic/manifest.json")
OUT = Path("tests/fixtures/synthetic")


def _line(ln: dict[str, Any], q: dict[str, Any]) -> dict[str, Any]:
    pack_only = "pack_price_only" in q["features"]
    basis = ln["price_basis"]
    evidence: dict[str, str] = {
        "product_name": ln["product_name"],
        "inn": ln["inn"],
        "strength": ln["strength"],
        "dosage_form": ln["dosage_form"],
        "units_per_pack": str(ln["units_per_pack"]),
        "price_per_pack": fmt_money(ln["price_per_pack"]),
    }
    if not pack_only and basis != "tiered":
        evidence["price_per_uom"] = fmt_money(ln["price_per_uom"])
    out: dict[str, Any] = {
        "line_no": ln["line_no"],
        "product_name": ln["product_name"],
        "inn": ln["inn"],
        "strength": ln["strength"],
        "dosage_form": ln["dosage_form"],
        "uom": ln["uom"],
        "units_per_pack": ln["units_per_pack"],
        "packaging": ln["packaging"],
        "price_per_pack": ln["price_per_pack"],
        "price_per_uom": ln["price_per_uom"],
        "price_basis": basis,
        "discount_pct": ln["discount_pct"],
        "price_tiers": ln["price_tiers"],
        "currency": q["currency"],
        "quantity": ln["quantity"],
        "extended_amount": ln["extended_amount"],
        "moq_packs": ln["moq_packs"],
        "lead_time_days": ln["lead_time_days"],
        "cold_chain": ln["cold_chain"] or None,
        "superseded": None,
        "evidence": evidence,
        "illegible": [],
        "notes": [],
    }
    if ln["superseded"]:
        c = ln["superseded"]
        out["superseded"] = {
            "field": c["field"],
            "old": c["old"],
            "new": c["new"],
            "reason": c["reason"],
        }
        out["notes"].append(f"{c['field']} corrected later in the document")
    if basis == "derived":
        out["notes"].append("unit price derived from pack price and units per pack")
    return out


def fixture_for(case: dict[str, Any], truth: dict[str, Any]) -> dict[str, Any]:
    q = truth["quotation"]
    supplier = q["supplier_name"]
    result: dict[str, Any] = {
        "document_type": "quotation",
        "contains_prices": True,
        "supplier": {
            "name": supplier,
            "country": None,
            "contact_name": None,
            "contact_email": None,
        },
        "quotation_ref": q["quotation_ref"],
        "buyer_reference": q["buyer_reference"],
        "document_date": q["document_date"],
        "valid_until": q["valid_until"],
        "currency": q["currency"],
        "incoterm": q["incoterm"],
        "named_place": q["named_place"],
        "payment_terms": q["payment_terms"],
        "lines": [_line(ln, q) for ln in q["lines"]],
        "evidence": {"quotation_ref": q["quotation_ref"], "currency": q["currency"]},
        "warnings": [],
    }
    if case["hostile"]:
        result["warnings"].append(
            "document contains text addressed to an automated reader; ignored"
        )
    if case["expect"] in ("partial", "low_confidence"):
        result["warnings"].append("parts of the page are unreadable; some lines may be missing")
    return result


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    n = 0
    for case in manifest["cases"]:
        if "truth" not in case:
            continue
        truth = json.loads((MANIFEST.parent / case["truth"]).read_text(encoding="utf-8"))
        fixture = fixture_for(case, truth)
        stem = Path(case["files"][0]).stem
        if case["kind"] == "eml" and case["variant"] == "with_attachment":
            # The figures live in the attachment, which is its own Document downstream.
            source = MANIFEST.parent / case["id"] / case["files"][0]
            msg = email.message_from_bytes(source.read_bytes(), policy=email.policy.default)
            names = [p.get_filename() for p in msg.walk() if p.get_filename()]
            for name in names:
                _write(OUT / f"{Path(name).stem}.json", fixture)
                n += 1
            fixture = {
                "document_type": "correspondence",
                "contains_prices": False,
                "supplier": fixture["supplier"],
                "quotation_ref": fixture["quotation_ref"],
                "buyer_reference": fixture["buyer_reference"],
                "currency": fixture["currency"],
                "lines": [],
                "warnings": ["cover note only; the quotation is in the attached PDF"],
            }
        _write(OUT / f"{stem}.json", fixture)
        n += 1
    print(f"wrote {n} fixtures to {OUT}")


if __name__ == "__main__":
    main()
