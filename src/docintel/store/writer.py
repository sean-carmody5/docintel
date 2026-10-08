"""The review table: CSV for a spreadsheet, SQLite for queries, Markdown for a first read.

One module behind one function. A customer system that wants something else gets
another writer here and nothing upstream changes.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docintel.reconcile import Conflict, Duplicate
from docintel.records import KEY_FIELDS, Record
from docintel.store.review_html import render_review_html

CSV_COLUMNS = [
    "record_id",
    "status",
    "needs_review",
    "overall_confidence",
    "review_reasons",
    "source_document",
    "source_path",
    "parent_document",
    "source_kind",
    "source_locator",
    "supplier_name",
    "supplier_country",
    "quotation_ref",
    "buyer_reference",
    "document_date",
    "valid_until",
    "document_type",
    "incoterm",
    "named_place",
    "payment_terms",
    "line_no",
    "product_name",
    "inn",
    "inn_normalised",
    "strength",
    "dosage_form",
    "uom",
    "units_per_pack",
    "packaging",
    "price_per_uom",
    "price_per_pack",
    "net_price_per_uom",
    "price_basis",
    "discount_pct",
    "price_tiers",
    "currency",
    "quantity",
    "extended_amount",
    "moq_packs",
    "lead_time_days",
    "cold_chain",
    "superseded",
    "evidence",
    *[f"conf_{k}" for k in KEY_FIELDS],
    "confidence",
    "flags",
    "notes",
    "extractor",
]


def _cell(value: Any) -> Any:
    if isinstance(value, list | dict):
        return json.dumps(value, ensure_ascii=False)
    return value


def _row(r: Record) -> dict[str, Any]:
    d = r.model_dump(mode="json")
    row = {c: _cell(d.get(c)) for c in CSV_COLUMNS if c in d}
    row["review_reasons"] = " | ".join(r.review_reasons)
    row["flags"] = json.dumps([f.model_dump() for f in r.flags], ensure_ascii=False)
    row["notes"] = " | ".join(r.notes)
    row["confidence"] = json.dumps(
        {k: v.model_dump() for k, v in r.confidence.items()}, ensure_ascii=False
    )
    for k in KEY_FIELDS:
        row[f"conf_{k}"] = r.confidence[k].score if k in r.confidence else None
    return row


def write_csv(records: list[Record], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in records:
            w.writerow(_row(r))


def write_sqlite(
    records: list[Record],
    conflicts: list[Conflict],
    duplicates: list[Duplicate],
    path: Path,
    run: dict[str, Any],
) -> None:
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    try:
        cols = ", ".join(f'"{c}"' for c in CSV_COLUMNS)
        con.execute(f"CREATE TABLE records ({cols})")
        con.execute(
            "CREATE TABLE flags (record_id TEXT, code TEXT, severity TEXT, field TEXT, detail TEXT)"
        )
        con.execute(
            "CREATE TABLE conflicts (conflict_id TEXT, inn_normalised TEXT, strength TEXT, form TEXT, "
            "comparable INTEGER, differs_in TEXT, suppliers TEXT, currencies TEXT, uoms TEXT, "
            "units_per_pack TEXT, unit_prices TEXT, record_ids TEXT, note TEXT)"
        )
        con.execute(
            "CREATE TABLE duplicates (duplicate_id TEXT, supplier TEXT, quotation_ref TEXT, documents TEXT, "
            "matched_lines INTEGER, agreements INTEGER, disagreements TEXT)"
        )
        con.execute("CREATE TABLE runs (key TEXT, value TEXT)")
        placeholders = ", ".join("?" for _ in CSV_COLUMNS)
        for r in records:
            row = _row(r)
            con.execute(
                f"INSERT INTO records VALUES ({placeholders})", [row.get(c) for c in CSV_COLUMNS]
            )
            for f in r.flags:
                con.execute(
                    "INSERT INTO flags VALUES (?, ?, ?, ?, ?)",
                    (r.record_id, f.code, f.severity, f.field, f.detail),
                )
        for c in conflicts:
            con.execute(
                "INSERT INTO conflicts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    c.conflict_id,
                    c.inn_normalised,
                    c.strength,
                    c.form,
                    int(c.comparable),
                    json.dumps(c.differs_in),
                    json.dumps(c.suppliers),
                    json.dumps(c.currencies),
                    json.dumps(c.uoms),
                    json.dumps(c.units_per_pack),
                    json.dumps(c.unit_prices),
                    json.dumps(c.record_ids),
                    c.note,
                ),
            )
        for d in duplicates:
            con.execute(
                "INSERT INTO duplicates VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    d.duplicate_id,
                    d.supplier,
                    d.quotation_ref,
                    json.dumps(d.documents),
                    d.matched_lines,
                    d.agreements,
                    json.dumps(d.disagreements, ensure_ascii=False),
                ),
            )
        for k, v in run.items():
            con.execute("INSERT INTO runs VALUES (?, ?)", (k, json.dumps(v, default=str)))
        con.commit()
    finally:
        con.close()


def write_report(
    records: list[Record],
    conflicts: list[Conflict],
    duplicates: list[Duplicate],
    path: Path,
    run: dict[str, Any],
) -> None:
    by_status = Counter(r.status for r in records)
    review = [r for r in records if r.needs_review and r.status == "pending_review"]
    clean = [r for r in records if not r.needs_review and r.status == "pending_review"]
    failed = [r for r in records if r.status in ("failed", "no_lines")]
    tiers = Counter(
        r.confidence["price_per_uom"].tier for r in records if "price_per_uom" in r.confidence
    )

    def money(v: float | None) -> str:
        return "" if v is None else f"{v:g}"

    lines = [
        "# Review report",
        "",
        f"Run: {run.get('started')} | extractor: {run.get('extractor')} | model: {run.get('model') or 'none'} | "
        f"input: {run.get('input_dir')}",
        "",
        "## At a glance",
        "",
        f"- Documents: {run.get('documents')} loaded, {run.get('failed_documents')} failed to load",
        f"- Records: {len(records)} ({', '.join(f'{k}: {v}' for k, v in sorted(by_status.items()))})",
        f"- Needs review: {len(review)} | clean: {len(clean)} | no lines or failed: {len(failed)}",
        f"- Unit price confidence: high {tiers.get('high', 0)}, medium {tiers.get('medium', 0)}, low {tiers.get('low', 0)}",
        f"- Conflicts across suppliers: {len(conflicts)} | duplicate quotations: {len(duplicates)}",
        "",
        "## Look at these first",
        "",
        "| Record | Document | Product | Unit price | Currency | Overall | Why |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(review, key=lambda x: x.overall_confidence):
        why = "; ".join(r.review_reasons[:3])
        lines.append(
            f"| {r.record_id} | {r.source_document} | {r.product_name or ''} | {money(r.price_per_uom)} | "
            f"{r.currency or ''} | {r.overall_confidence:.2f} | {why} |"
        )
    if failed:
        lines += [
            "",
            "## Documents with no usable lines",
            "",
            "| Document | Status | Reason |",
            "|---|---|---|",
        ]
        for r in failed:
            lines.append(
                f"| {r.source_document} | {r.status} | {'; '.join(r.review_reasons[:2])} |"
            )
    if conflicts:
        lines += [
            "",
            "## Same product, more than one supplier",
            "",
            "| INN | Strength | Form | Suppliers | Currencies | Units/pack | Unit prices | Note |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for c in conflicts:
            lines.append(
                f"| {c.inn_normalised} | {c.strength or ''} | {c.form or ''} | {', '.join(c.suppliers)} | "
                f"{', '.join(c.currencies)} | {', '.join(str(u) for u in c.units_per_pack)} | "
                f"{', '.join(money(p) for p in c.unit_prices)} | {c.note} |"
            )
    if duplicates:
        lines += [
            "",
            "## Same quotation, more than one file",
            "",
            "| Supplier | Reference | Files | Matched lines | Agreements | Disagreements |",
            "|---|---|---|---|---|---|",
        ]
        for d in duplicates:
            lines.append(
                f"| {d.supplier or ''} | {d.quotation_ref} | {', '.join(d.documents)} | {d.matched_lines} | "
                f"{d.agreements} | {len(d.disagreements)} |"
            )
    lines += [
        "",
        "## Clean records",
        "",
        "| Record | Document | Product | Unit price | Currency | Overall |",
        "|---|---|---|---|---|---|",
    ]
    for r in clean:
        lines.append(
            f"| {r.record_id} | {r.source_document} | {r.product_name or ''} | {money(r.price_per_uom)} | "
            f"{r.currency or ''} | {r.overall_confidence:.2f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_all(
    records: list[Record],
    conflicts: list[Conflict],
    duplicates: list[Duplicate],
    out_dir: Path,
    run: dict[str, Any] | None = None,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    run = dict(run or {})
    run.setdefault("started", datetime.now(UTC).isoformat(timespec="seconds"))
    paths = {
        "csv": out_dir / "records.csv",
        "sqlite": out_dir / "review.sqlite",
        "report": out_dir / "review_report.md",
        "conflicts": out_dir / "conflicts.json",
        "html": out_dir / "review.html",
    }
    write_csv(records, paths["csv"])
    write_sqlite(records, conflicts, duplicates, paths["sqlite"], run)
    write_report(records, conflicts, duplicates, paths["report"], run)
    paths["html"].write_text(
        render_review_html(records, conflicts, duplicates, run), encoding="utf-8", newline="\n"
    )
    paths["conflicts"].write_text(
        json.dumps(
            {
                "conflicts": [c.model_dump() for c in conflicts],
                "duplicates": [d.model_dump() for d in duplicates],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return paths
