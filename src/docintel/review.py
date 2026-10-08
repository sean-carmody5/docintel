"""What the reviewer sends back: corrections to values, then decisions per line.

A correction is a person reading the source and setting a value the pipeline could not
read or got wrong. It is applied before decisions, so a corrected line can be approved
in the same breath. The original stays in the audit; the corrected field scores 1.0
with the reason "set by reviewer".
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from docintel.records import KEY_FIELDS, FieldConfidence, Record, RecordFlag
from docintel.verify.confidence import overall_score

PROTECTED = frozenset(
    {
        "record_id",
        "source_document",
        "source_path",
        "source_id",
        "source_kind",
        "source_locator",
        "parent_document",
        "line_no",
        "evidence",
        "confidence",
        "overall_confidence",
        "needs_review",
        "review_reasons",
        "flags",
        "status",
    }
)


def apply_corrections(
    records: list[Record], corrections: dict[str, dict[str, Any]]
) -> dict[str, dict[str, dict[str, Any]]]:
    """Apply {record_id: {field: value}} in place. Returns what happened, per field."""
    by_id = {r.record_id: r for r in records}
    applied: dict[str, dict[str, dict[str, Any]]] = {}
    for record_id, fields in corrections.items():
        record = by_id.get(record_id)
        if record is None or not isinstance(fields, dict):
            continue
        outcome: dict[str, dict[str, Any]] = {}
        for field, value in fields.items():
            old = getattr(record, field, None)
            if field in PROTECTED or field not in Record.model_fields:
                outcome[field] = {"from": old, "to": value, "error": "not a correctable field"}
                continue
            try:
                checked = Record.model_validate({**record.model_dump(), field: value})
            except ValidationError:
                outcome[field] = {"from": old, "to": value, "error": "invalid value for this field"}
                continue
            new = getattr(checked, field)
            setattr(record, field, new)
            record.confidence[field] = FieldConfidence(
                score=1.0, tier="high", reasons=["set by reviewer"]
            )
            record.flags.append(
                RecordFlag(
                    code="corrected_by_reviewer",
                    severity="info",
                    detail=f"{field}: {old!r} -> {new!r}",
                    field=field,
                )
            )
            record.review_reasons = [
                x for x in record.review_reasons if field not in x.split(":")[0].split()
            ]
            outcome[field] = {"from": old, "to": new}
        values = {k: getattr(record, k, None) for k in KEY_FIELDS}
        record.overall_confidence = overall_score(record.confidence, values)
        record.needs_review = bool(record.review_reasons) or any(
            f.severity == "high" for f in record.flags
        )
        applied[record_id] = outcome
    return applied
