"""Cross-supplier conflicts, duplicate cross-checks, and the written review table."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

from docintel.extract.extractor import FixtureExtractor
from docintel.ingest import load
from docintel.reconcile import reconcile
from docintel.records import Record
from docintel.store import write_all
from docintel.verify import Sources, build_records

PROVIDED = Path("data/provided")
FIXTURES = [Path("tests/fixtures/synthetic"), Path("tests/fixtures/provided")]


def _provided_records() -> list[Record]:
    out: list[Record] = []
    extractor = FixtureExtractor(FIXTURES)
    for path in sorted(PROVIDED.iterdir()):
        doc = load(path)
        result = extractor.extract(doc)
        out += build_records(
            doc, result, sources=Sources(primary=doc.text), extractor_name="fixture"
        )
    return out


def test_conflicts_group_the_pack_as_the_brief_promises() -> None:
    records = _provided_records()
    conflicts, duplicates = reconcile(records)
    by_inn = {c.inn_normalised: c for c in conflicts}
    assert "amoxicillin+clavulanic acid" in by_inn, sorted(by_inn)
    amox = by_inn["amoxicillin+clavulanic acid"]
    assert set(amox.suppliers) == {"Zenith Pharma Laboratories Ltd.", "Mekong Pharma JSC"}
    assert amox.comparable and "units_per_pack" in amox.differs_in
    assert "paracetamol" in by_inn and not by_inn["paracetamol"].comparable  # ZAR vs USD
    assert "amlodipine" in by_inn and not by_inn["amlodipine"].comparable  # EUR vs USD
    tld = next(c for c in conflicts if "tenofovir" in c.inn_normalised)
    assert set(tld.currencies) == {"EUR", "USD"}
    # salbutamol syrup and inhaler must not be grouped as one product
    assert not any(c.inn_normalised == "salbutamol" for c in conflicts)


def test_duplicates_cross_check_the_andina_copies() -> None:
    records = _provided_records()
    conflicts, duplicates = reconcile(records)
    andina = next(d for d in duplicates if d.quotation_ref == "FA-COT-2026-118")
    assert len(andina.documents) == 3
    assert andina.agreements > 0
    assert not andina.disagreements, andina.disagreements
    fax = [r for r in records if r.source_document.startswith("scan_02")]
    assert any(
        "confidence lifted" in reason
        for r in fax
        for c in r.confidence.values()
        for reason in c.reasons
    )


def test_disagreeing_duplicate_is_flagged() -> None:
    records = _provided_records()
    fax_line = next(
        r for r in records if r.source_document.startswith("scan_02") and r.line_no == 2
    )
    fax_line.price_per_uom = 0.0182
    conflicts, duplicates = reconcile(records)
    andina = next(d for d in duplicates if d.quotation_ref == "FA-COT-2026-118")
    assert andina.disagreements and andina.disagreements[0]["field"] == "price_per_uom"
    assert fax_line.needs_review and any(f.code == "duplicate_disagreement" for f in fax_line.flags)


def test_writer_produces_csv_sqlite_and_report(tmp_path: Path) -> None:
    records = _provided_records()
    conflicts, duplicates = reconcile(records)
    paths = write_all(
        records,
        conflicts,
        duplicates,
        tmp_path,
        run={
            "input_dir": "data/provided",
            "extractor": "fixture",
            "documents": 8,
            "failed_documents": 0,
        },
    )
    with paths["csv"].open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(records)
    assert {"needs_review", "conf_price_per_uom", "review_reasons", "source_document"} <= set(
        rows[0]
    )
    con = sqlite3.connect(paths["sqlite"])
    assert con.execute("SELECT COUNT(*) FROM records").fetchone()[0] == len(records)
    assert con.execute("SELECT COUNT(*) FROM conflicts").fetchone()[0] == len(conflicts)
    assert con.execute("SELECT COUNT(*) FROM records WHERE needs_review = 1").fetchone()[0] > 0
    con.close()
    report = paths["report"].read_text(encoding="utf-8")
    assert "## Look at these first" in report and "Same product, more than one supplier" in report
    assert json.loads(paths["conflicts"].read_text(encoding="utf-8"))["duplicates"]
