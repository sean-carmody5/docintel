"""Turn an ExtractionResult into review-table Records with computed confidence.

Per field, the score starts at 1.0 and loses a configured weight for each failed
signal: not grounded in the source, evidence quote missing or false, a failed
arithmetic or plausibility check, disagreement with a second reading, or the model
itself saying it could not read the field. Every deduction is written down as a
reason. Nothing here asks the model how sure it is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from docintel.documents import Document
from docintel.extract.schema import ExtractionResult, QuotationLine
from docintel.records import KEY_FIELDS, FieldConfidence, Record, RecordFlag, Tier
from docintel.verify.checks import Finding, check_header, check_line
from docintel.verify.grounding import ground, value_in_text
from docintel.verify.normalise import normalise_form, normalise_inn, normalise_strength

LINE_FIELDS = (
    "product_name",
    "inn",
    "strength",
    "dosage_form",
    "uom",
    "units_per_pack",
    "price_per_pack",
    "price_per_uom",
    "discount_pct",
    "currency",
    "quantity",
    "extended_amount",
    "moq_packs",
    "lead_time_days",
)
HEADER_FIELDS = ("quotation_ref", "currency", "incoterm", "document_date", "valid_until")
SECOND_SOURCE_FIELDS = {
    "price_per_uom",
    "price_per_pack",
    "units_per_pack",
    "quantity",
    "extended_amount",
}


@dataclass
class Weights:
    not_grounded: float = 0.5
    evidence_missing: float = 0.15
    evidence_false: float = 0.3
    check_failed: float = 0.3
    disagreement: float = 0.3
    illegible: float = 0.8
    derived: float = 0.05
    high_flag: float = 0.1
    high_tier: float = 0.85
    medium_tier: float = 0.6


@dataclass
class Sources:
    """Texts a value can be grounded in. Primary is what the extractor read."""

    primary: str
    secondary: str | None = None
    secondary_label: str = "ocr"
    extra: list[str] = field(default_factory=list)


def _tier(score: float, w: Weights) -> Tier:
    if score >= w.high_tier:
        return "high"
    if score >= w.medium_tier:
        return "medium"
    return "low"


def _found_anywhere(name: str, value: object, sources: Sources) -> tuple[bool, str | None]:
    if value_in_text(value, sources.primary):
        return True, None
    if (
        name == "lead_time_days"
        and isinstance(value, int)
        and value % 7 == 0
        and value_in_text(f"{value // 7} week", sources.primary)
    ):
        return True, "stated in weeks"
    if any(value_in_text(value, t) for t in sources.extra):
        return True, "found in an attachment or part, not the main text"
    return False, None


def score_field(
    name: str,
    value: object,
    evidence: str | None,
    sources: Sources,
    findings: list[Finding],
    illegible: bool,
    w: Weights,
) -> FieldConfidence:
    reasons: list[str] = []
    score = 1.0
    if value is None:
        reason = "model could not read this field" if illegible else "not stated"
        return FieldConfidence(score=0.0, tier="low", reasons=[reason])
    if illegible:
        score -= w.illegible
        reasons.append("model marked this field illegible yet gave a value")

    found, note = _found_anywhere(name, value, sources)
    if note:
        reasons.append(note)
    if not found:
        score -= w.not_grounded
        reasons.append("value not found in the source text")
    g = ground(value, evidence, sources.primary)
    if not evidence:
        score -= w.evidence_missing
        reasons.append("no evidence quote")
    elif found and not g.evidence_found:
        score -= w.evidence_false
        reasons.append("evidence quote not found in the source")
    elif found and not g.evidence_has_value:
        score -= w.evidence_false / 2
        reasons.append("evidence quote does not contain the value")

    if sources.secondary is not None and name in SECOND_SOURCE_FIELDS:
        if value_in_text(value, sources.secondary):
            reasons.append(f"agrees with {sources.secondary_label}")
        else:
            score -= w.disagreement
            reasons.append(f"not found by {sources.secondary_label}")

    for fld, code, detail in findings:
        if fld == name:
            score -= w.check_failed
            reasons.append(f"{code}: {detail}")

    score = round(max(0.0, min(1.0, score)), 3)
    return FieldConfidence(score=score, tier=_tier(score, w), reasons=reasons)


def _derived_price(
    conf: dict[str, FieldConfidence], findings: list[Finding], w: Weights
) -> FieldConfidence:
    """A derived unit price is as trustworthy as the pack price and pack size it came from."""
    parents = [conf[k] for k in ("price_per_pack", "units_per_pack") if k in conf]
    score = min((p.score for p in parents), default=0.0) - w.derived
    reasons = ["derived from pack price and units per pack"]
    for fld, code, detail in findings:
        if fld == "price_per_uom":
            score -= w.check_failed
            reasons.append(f"{code}: {detail}")
    score = round(max(0.0, score), 3)
    return FieldConfidence(score=score, tier=_tier(score, w), reasons=reasons)


def _locator(line: QuotationLine, index: int) -> str:
    return f"line {line.line_no}" if line.line_no is not None else f"item {index + 1}"


def _base(doc: Document, result: ExtractionResult, extractor_name: str, suffix: str) -> dict:  # type: ignore[type-arg]
    return {
        "record_id": f"{doc.id}:{suffix}",
        "source_document": doc.name,
        "source_path": str(doc.source_path),
        "source_id": doc.id,
        "source_kind": doc.kind.value,
        "parent_document": doc.metadata.get("attachment_of") or doc.metadata.get("member_of"),
        "supplier_name": result.supplier.name if result.supplier else None,
        "supplier_country": result.supplier.country if result.supplier else None,
        "quotation_ref": result.quotation_ref,
        "buyer_reference": result.buyer_reference,
        "document_date": result.document_date,
        "valid_until": result.valid_until,
        "incoterm": result.incoterm,
        "named_place": result.named_place,
        "payment_terms": result.payment_terms,
        "document_type": result.document_type,
        "extractor": extractor_name,
    }


def build_records(
    doc: Document,
    result: ExtractionResult,
    *,
    sources: Sources,
    extractor_name: str,
    weights: Weights | None = None,
    as_of: date | None = None,
) -> list[Record]:
    """`as_of` enables the expiry check; None means validity is not judged against a date."""
    w = weights or Weights()
    header_findings = check_header(
        result.document_date, result.valid_until, result.incoterm, as_of=as_of
    )
    doc_flags = [
        RecordFlag(code=f.code, severity=f.severity.value, detail=f.detail, field=f.field)
        for f in doc.flags
    ]
    high_flags = [f for f in doc_flags if f.severity == "high"]
    header_conf = {
        name: score_field(
            name,
            getattr(result, name),
            result.evidence.get(name),
            sources,
            header_findings,
            False,
            w,
        )
        for name in HEADER_FIELDS
    }

    records: list[Record] = []
    for index, line in enumerate(result.lines):
        findings = check_line(line, result.currency) + header_findings
        conf: dict[str, FieldConfidence] = dict(header_conf)
        for name in LINE_FIELDS:
            value = getattr(line, name)
            evidence = line.evidence.get(name)
            if name == "currency" and value is None:
                value, evidence = result.currency, result.evidence.get("currency")
            conf[name] = score_field(
                name, value, evidence, sources, findings, name in line.illegible, w
            )
        if line.price_basis in ("derived", "tiered") and line.price_per_uom is not None:
            conf["price_per_uom"] = _derived_price(conf, findings, w)
        if high_flags:
            for c in conf.values():
                if c.score > 0:
                    c.score = round(max(0.0, c.score - w.high_flag), 3)
                    c.tier = _tier(c.score, w)

        key_scores = [
            conf[k].score for k in KEY_FIELDS if k in conf and getattr(line, k, None) is not None
        ]
        overall = round(min(key_scores), 3) if key_scores else 0.0
        reasons = [
            f"{k}: " + "; ".join(conf[k].reasons[:2])
            for k in KEY_FIELDS
            if k in conf and conf[k].tier == "low"
        ]
        reasons += [f"{f.code}: {f.detail[:80]}" for f in high_flags]
        reasons += [f"{code}: {detail}" for _, code, detail in findings if code == "expired"]
        if line.superseded is not None:
            s = line.superseded
            reasons.append(f"{s.field} corrected in the document from {s.old} to {s.new}")
        if line.price_basis == "tiered":
            reasons.append("tiered pricing; lowest-quantity tier shown")
        elif line.price_basis == "derived":
            reasons.append("unit price derived, not stated")
        needs_review = bool(reasons) or overall < w.medium_tier or not result.contains_prices

        net = None
        if line.price_per_uom is not None:
            net = round(line.price_per_uom * (1 - (line.discount_pct or 0.0) / 100), 6)
        records.append(
            Record(
                **_base(doc, result, extractor_name, str(index + 1)),
                source_locator=_locator(line, index),
                line_no=line.line_no,
                product_name=line.product_name,
                inn=line.inn,
                inn_normalised=normalise_inn(line.inn),
                strength=line.strength,
                strength_normalised=normalise_strength(line.strength),
                dosage_form=line.dosage_form,
                form_normalised=normalise_form(line.dosage_form),
                uom=line.uom,
                units_per_pack=line.units_per_pack,
                packaging=line.packaging,
                price_per_pack=line.price_per_pack,
                price_per_uom=line.price_per_uom,
                net_price_per_uom=net,
                price_basis=line.price_basis,
                discount_pct=line.discount_pct,
                price_tiers=[t.model_dump() for t in line.price_tiers]
                if line.price_tiers
                else None,
                currency=line.currency or result.currency,
                quantity=line.quantity,
                extended_amount=line.extended_amount,
                moq_packs=line.moq_packs,
                lead_time_days=line.lead_time_days,
                cold_chain=line.cold_chain,
                superseded=line.superseded.model_dump() if line.superseded else None,
                confidence=conf,
                overall_confidence=overall,
                needs_review=needs_review,
                review_reasons=reasons,
                flags=doc_flags
                + [
                    RecordFlag(code=f"check:{code}", severity="warning", detail=d, field=fld)
                    for fld, code, d in findings
                ],
                notes=list(line.notes) + list(result.warnings),
                status="pending_review",
            )
        )

    if not records:
        records.append(
            Record(
                **_base(doc, result, extractor_name, "0"),
                overall_confidence=0.0,
                needs_review=True,
                review_reasons=["no quotation lines extracted", *result.warnings],
                flags=doc_flags,
                notes=list(result.warnings),
                status="no_lines",
            )
        )
    return records


def failed_record(doc: Document) -> Record:
    """A document that could not be loaded still gets a row, so nothing vanishes."""
    return Record(
        record_id=f"{doc.id}:0",
        source_document=doc.name,
        source_path=str(doc.source_path),
        source_id=doc.id,
        source_kind=doc.kind.value,
        parent_document=doc.metadata.get("attachment_of") or doc.metadata.get("member_of"),
        overall_confidence=0.0,
        needs_review=True,
        review_reasons=[f.detail or f.code for f in doc.flags if f.code.startswith("load_failed")],
        flags=[
            RecordFlag(code=f.code, severity=f.severity.value, detail=f.detail) for f in doc.flags
        ],
        status="failed",
    )
