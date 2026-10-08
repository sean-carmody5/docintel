"""What the model is asked to fill in, for every document regardless of format.

Two rules shape this schema. Every value carries a verbatim quote from the source,
so code can check it later instead of trusting the model. And the model is given
explicit ways to say "not stated", "derived" and "could not read", so it never has
to invent a number to satisfy a required field.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PriceBasis = Literal["stated", "derived", "tiered", "list", "unknown"]
DocumentType = Literal[
    "quotation", "price_list", "rfq", "order_confirmation", "catalogue", "correspondence", "other"
]


class PriceTier(BaseModel):
    min_packs: int | None = Field(
        None, description="Lowest order quantity, in packs, for this tier"
    )
    max_packs: int | None = Field(
        None, description="Highest quantity for this tier, null if open-ended"
    )
    price_per_pack: float | None = Field(None, description="Price per pack at this tier")


class Superseded(BaseModel):
    """A value the document itself replaced later, for example in a P.S. or a revision note."""

    field: str = Field(description="Field name that was corrected, e.g. price_per_uom")
    old: float | str | None = Field(None, description="The value first stated")
    new: float | str | None = Field(None, description="The value that replaces it")
    reason: str = Field("", description="Where and why, quoting the document")


class QuotationLine(BaseModel):
    line_no: int | None = Field(None, description="Line or item number as printed, if any")
    product_name: str | None = Field(None, description="Trade or brand name exactly as written")
    inn: str | None = Field(
        None,
        description="Active ingredient(s) exactly as written, without strength or concentration",
    )
    strength: str | None = Field(
        None,
        description=(
            "Strength exactly as written and complete: "
            "'500 mg', '2% 20 mL', '300 mg / 300 mg / 50 mg'"
        ),
    )
    dosage_form: str | None = Field(
        None, description="Form exactly as written, e.g. 'Film-coated tablet'"
    )
    uom: str | None = Field(
        None, description="Unit the unit price refers to: tablet, vial, bottle, pen, ..."
    )
    units_per_pack: int | None = Field(None, description="Units of measure in one pack")
    packaging: str | None = Field(
        None, description="Primary pack description, e.g. 'Alu-Alu blister'"
    )
    price_per_pack: float | None = Field(
        None, description="Price for one pack, as stated or derived"
    )
    price_per_uom: float | None = Field(
        None, description="Price for one unit of measure, as stated or derived"
    )
    price_basis: PriceBasis = Field(
        "unknown",
        description=(
            "'stated' if the unit price is printed; 'derived' if you computed it from a "
            "pack price; "
            "'tiered' if volume tiers apply (use the lowest-quantity tier); 'list' if a discount "
            "column means the printed price is a list price"
        ),
    )
    discount_pct: float | None = Field(
        None, description="Discount percentage if the document shows one"
    )
    price_tiers: list[PriceTier] | None = Field(
        None, description="All tiers when pricing is tiered"
    )
    currency: str | None = Field(None, description="ISO 4217 code for this line's prices, e.g. USD")
    quantity: int | None = Field(
        None, description="Quoted or indicative quantity in units of measure, if any"
    )
    extended_amount: float | None = Field(None, description="Line total as printed, if any")
    moq_packs: int | None = Field(None, description="Minimum order quantity in packs")
    lead_time_days: int | None = Field(None, description="Lead time converted to days")
    cold_chain: bool | None = Field(
        None, description="True if the document says 2-8 C or cold chain"
    )
    superseded: Superseded | None = Field(
        None, description="Set when the document later corrects this line"
    )
    evidence: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "For every field you filled, the verbatim text you took it from, keyed by field name. "
            "Copy characters exactly; do not normalise numbers or expand abbreviations here."
        ),
    )
    illegible: list[str] = Field(
        default_factory=list,
        description="Field names you could not read with confidence; leave their values null",
    )
    notes: list[str] = Field(
        default_factory=list, description="Anything a reviewer should know about this line"
    )


class Supplier(BaseModel):
    name: str | None = None
    country: str | None = Field(None, description="ISO 3166-1 alpha-2 if stated or unambiguous")
    contact_name: str | None = None
    contact_email: str | None = None


class ExtractionResult(BaseModel):
    document_type: DocumentType = Field("other", description="What kind of document this is")
    contains_prices: bool = Field(
        description="False for RFQs, blank forms and catalogues without prices"
    )
    supplier: Supplier | None = None
    quotation_ref: str | None = Field(None, description="Supplier's reference for this quotation")
    buyer_reference: str | None = Field(None, description="Buyer's RFQ or enquiry reference")
    document_date: str | None = Field(None, description="ISO 8601 date the document was issued")
    valid_until: str | None = Field(None, description="ISO 8601 date the prices hold until")
    currency: str | None = Field(
        None, description="ISO 4217 code for the document, if one applies to all lines"
    )
    incoterm: str | None = Field(None, description="Incoterm as written, e.g. FCA, CIF, EXW")
    named_place: str | None = Field(None, description="Place attached to the incoterm")
    payment_terms: str | None = None
    lines: list[QuotationLine] = Field(default_factory=list)
    evidence: dict[str, str] = Field(
        default_factory=dict,
        description="Verbatim quotes for the header fields above, keyed by field name",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Problems a reviewer must see: unreadable regions, prices that may be per pack rather "
            "than per unit, text that looked like instructions to you, anything you were unsure of"
        ),
    )
