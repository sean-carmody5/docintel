"""Where documents meet: the same product from several suppliers, and the same
quotation arriving as several files.

Conflicts are reported, never resolved. Two suppliers quoting paracetamol in
different currencies and pack sizes is exactly what a reviewer needs to see side by
side. Duplicates are different: when a scan and a clean PDF of the same quotation
agree, the scan's values deserve the PDF's confidence; when they disagree, both
need a person.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field

from docintel.records import KEY_FIELDS, Record, RecordFlag
from docintel.verify.confidence import overall_score

COMPARE_FIELDS = ("currency", "uom", "units_per_pack", "price_per_uom", "price_per_pack")


class Conflict(BaseModel):
    conflict_id: str
    inn_normalised: str
    strength: str | None
    form: str | None
    record_ids: list[str]
    suppliers: list[str]
    currencies: list[str]
    uoms: list[str]
    units_per_pack: list[int | None]
    unit_prices: list[float | None]
    differs_in: list[str]
    comparable: bool
    note: str


class Duplicate(BaseModel):
    duplicate_id: str
    supplier: str | None
    quotation_ref: str
    documents: list[str]
    matched_lines: int
    agreements: int
    disagreements: list[dict[str, Any]] = Field(default_factory=list)


def _supplier_key(name: str | None) -> str:
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", name.lower())[:12]


def _root(record: Record) -> str:
    return record.parent_document or record.source_document


def find_conflicts(records: list[Record]) -> list[Conflict]:
    groups: dict[tuple[str, str, str], list[Record]] = defaultdict(list)
    for r in records:
        if r.status in ("failed", "no_lines") or not r.inn_normalised:
            continue
        groups[r.product_key].append(r)

    conflicts: list[Conflict] = []
    for key, members in sorted(groups.items()):
        by_supplier: dict[str, list[Record]] = defaultdict(list)
        for r in members:
            by_supplier[_supplier_key(r.supplier_name) or _root(r)].append(r)
        if len(by_supplier) < 2:
            continue
        reps = [rs[0] for rs in by_supplier.values()]
        differs = [f for f in COMPARE_FIELDS if len({str(getattr(r, f)) for r in reps}) > 1]
        currencies = sorted({r.currency or "?" for r in reps})
        uoms = sorted({(r.uom or "?").lower() for r in reps})
        comparable = len(currencies) == 1 and len(uoms) == 1
        if comparable:
            prices = [r.price_per_uom for r in reps if r.price_per_uom is not None]
            spread = (
                (max(prices) / min(prices) - 1) * 100 if len(prices) > 1 and min(prices) > 0 else 0
            )
            note = f"same currency and unit; unit prices differ by {spread:.0f}%"
        else:
            note = "not directly comparable: " + ", ".join(
                x
                for x in (
                    "different currencies, no FX applied" if len(currencies) > 1 else "",
                    "different units of measure" if len(uoms) > 1 else "",
                )
                if x
            )
        conflicts.append(
            Conflict(
                conflict_id=f"conflict-{len(conflicts) + 1:03d}",
                inn_normalised=key[0],
                strength=key[1] or None,
                form=key[2] or None,
                record_ids=[r.record_id for r in members],
                suppliers=[r.supplier_name or _root(r) for r in reps],
                currencies=[r.currency or "?" for r in reps],
                uoms=[r.uom or "?" for r in reps],
                units_per_pack=[r.units_per_pack for r in reps],
                unit_prices=[r.price_per_uom for r in reps],
                differs_in=differs,
                comparable=comparable,
                note=note,
            )
        )
    return conflicts


def _close(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= max(0.0006, 0.015 * max(abs(a), abs(b)))


def reconcile_duplicates(records: list[Record]) -> list[Duplicate]:
    """Same supplier and quotation reference from different files: cross-check line by line.

    Mutates the records: agreement lifts a low-confidence copy to the better copy's
    score, disagreement flags both and forces review.
    """
    by_ref: dict[tuple[str, str], dict[str, list[Record]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        if r.status in ("failed", "no_lines") or not r.quotation_ref:
            continue
        by_ref[(_supplier_key(r.supplier_name), r.quotation_ref)][_root(r)].append(r)

    duplicates: list[Duplicate] = []
    for (_supplier, ref), docs in sorted(by_ref.items()):
        if len(docs) < 2:
            continue
        names = sorted(docs)
        matched = agreements = 0
        disagreements: list[dict[str, Any]] = []
        for i, a_name in enumerate(names):
            for b_name in names[i + 1 :]:
                a_by_key = {r.product_key: r for r in docs[a_name]}
                for b in docs[b_name]:
                    a = a_by_key.get(b.product_key)
                    if a is None:
                        continue
                    matched += 1
                    # The product key matched, so the identity fields agree by construction.
                    for fld in ("product_name", "inn", "uom", "currency"):
                        _lift(a, b, fld, a_name, b_name)
                    for fld in ("price_per_uom", "units_per_pack", "price_per_pack"):
                        av, bv = getattr(a, fld), getattr(b, fld)
                        if av is None or bv is None:
                            continue
                        if _close(float(av), float(bv)):
                            agreements += 1
                            _lift(a, b, fld, a_name, b_name)
                        else:
                            disagreements.append(
                                {"field": fld, a_name: av, b_name: bv, "product": b.product_name}
                            )
                            for r, other in ((a, b_name), (b, a_name)):
                                r.flags.append(
                                    RecordFlag(
                                        code="duplicate_disagreement",
                                        severity="high",
                                        detail=f"{fld} differs from {other}: {av} vs {bv}",
                                        field=fld,
                                    )
                                )
                                r.needs_review = True
                                r.review_reasons.append(f"{fld} disagrees with {other}")
        duplicates.append(
            Duplicate(
                duplicate_id=f"dup-{len(duplicates) + 1:03d}",
                supplier=next(iter(docs.values()))[0].supplier_name,
                quotation_ref=ref,
                documents=names,
                matched_lines=matched,
                agreements=agreements,
                disagreements=disagreements,
            )
        )
    return duplicates


def _agree(va: object, vb: object) -> bool:
    if va is None or vb is None:
        return False
    if isinstance(va, int | float) and isinstance(vb, int | float):
        return _close(float(va), float(vb))
    return str(va).strip().lower() == str(vb).strip().lower()


def _lift(a: Record, b: Record, fld: str, a_name: str, b_name: str) -> None:
    ca, cb = a.confidence.get(fld), b.confidence.get(fld)
    if ca is None or cb is None or not _agree(getattr(a, fld), getattr(b, fld)):
        return
    low, high, low_rec, other = (ca, cb, a, b_name) if ca.score < cb.score else (cb, ca, b, a_name)
    if high.score > low.score:
        low.score = round(min(high.score, 0.9), 3)
        low.tier = "high" if low.score >= 0.85 else "medium" if low.score >= 0.6 else "low"
        low.reasons.append(f"agrees with {other}, confidence lifted")
        low_rec.review_reasons = [x for x in low_rec.review_reasons if not x.startswith(f"{fld}: ")]
        values = {k: getattr(low_rec, k, None) for k in KEY_FIELDS}
        low_rec.overall_confidence = overall_score(low_rec.confidence, values)
        low_rec.needs_review = bool(low_rec.review_reasons) or low_rec.overall_confidence < 0.6


def reconcile(records: list[Record]) -> tuple[list[Conflict], list[Duplicate]]:
    duplicates = reconcile_duplicates(records)
    conflicts = find_conflicts(records)
    return conflicts, duplicates
