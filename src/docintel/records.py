"""The review table row. One per quotation line, plus one per document that produced none.

Everything a reviewer needs to decide sits on the row: the values, where they came
from, how sure the pipeline is of each one and why, and what to look at first.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Tier = Literal["high", "medium", "low"]
Status = Literal["pending_review", "approved", "rejected", "failed", "no_lines"]

KEY_FIELDS = ("product_name", "inn", "price_per_uom", "currency", "units_per_pack", "uom")


class FieldConfidence(BaseModel):
    score: float
    tier: Tier
    reasons: list[str] = Field(default_factory=list)


class RecordFlag(BaseModel):
    code: str
    severity: str
    detail: str = ""
    field: str | None = None


class Record(BaseModel):
    record_id: str
    source_document: str
    source_path: str = ""
    source_id: str
    source_kind: str
    source_locator: str = ""
    parent_document: str | None = None

    supplier_name: str | None = None
    supplier_country: str | None = None
    quotation_ref: str | None = None
    buyer_reference: str | None = None
    document_date: str | None = None
    valid_until: str | None = None
    incoterm: str | None = None
    named_place: str | None = None
    payment_terms: str | None = None
    document_type: str = "other"

    line_no: int | None = None
    product_name: str | None = None
    inn: str | None = None
    inn_normalised: str | None = None
    strength: str | None = None
    strength_normalised: str | None = None
    dosage_form: str | None = None
    form_normalised: str | None = None
    uom: str | None = None
    units_per_pack: int | None = None
    packaging: str | None = None

    price_per_pack: float | None = None
    price_per_uom: float | None = None
    net_price_per_uom: float | None = None
    price_basis: str = "unknown"
    discount_pct: float | None = None
    price_tiers: list[dict[str, Any]] | None = None
    currency: str | None = None
    quantity: int | None = None
    extended_amount: float | None = None
    moq_packs: int | None = None
    lead_time_days: int | None = None
    cold_chain: bool | None = None
    superseded: dict[str, Any] | None = None

    confidence: dict[str, FieldConfidence] = Field(default_factory=dict)
    overall_confidence: float = 0.0
    needs_review: bool = True
    review_reasons: list[str] = Field(default_factory=list)
    flags: list[RecordFlag] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    status: Status = "pending_review"
    extractor: str = ""

    @property
    def product_key(self) -> tuple[str, str, str]:
        return (
            self.inn_normalised or "",
            self.strength_normalised or "",
            self.form_normalised or "",
        )
