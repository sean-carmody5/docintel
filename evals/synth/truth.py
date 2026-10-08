"""Ground truth for one synthetic quotation, generated before any rendering."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

from evals.synth import vocab
from evals.synth.vocab import PACKAGING_BY_UOM, USD_TO, Product, Supplier

# Feature switches a case can carry. Renderers and the truth generator both read them.
FEATURES = frozenset(
    {
        "pack_price_only",  # document states pack price only; unit price must be derived
        "tiered",  # volume tiers instead of a single price
        "discount",  # list price plus a discount column
        "quantity_extended",  # indicative quantity and extended amount per line
        "correction",  # a later passage corrects one line's price
        "distractor_alt_price",  # a note quotes a price for a presentation that is not a line
        "vat_note",  # prices exclude VAT, stated in a note
        "symbol_currency",  # currency shown as a symbol, never as an ISO code
        "inn_variant",  # INN written in a non-canonical form
        "strength_variant",  # strength written in a non-canonical form
        "lead_time_weeks",  # lead time expressed in weeks, not days
        "mixed_uom",  # tablets, vials and bottles in one document
        "long",  # twelve or more lines
        "cold_chain",  # at least one cold-chain line with storage notes
        "expired",  # issued months ago; validity has passed by the evaluation date
        "distractor_rfq_prices",  # the quoted RFQ carries the buyer's target prices
        "ambiguous_price_basis",  # a price is stated with no unit: per pack or per tablet?
    }
)


@dataclass
class Tier:
    min_packs: int
    max_packs: int | None
    price_per_pack: float


@dataclass
class Correction:
    field: str
    old: float
    new: float
    reason: str


@dataclass
class Line:
    line_no: int
    product_key: str
    product_name: str
    inn: str
    inn_canonical: str
    strength: str
    dosage_form: str
    packaging: str
    uom: str
    units_per_pack: int
    price_per_uom: float
    price_per_pack: float
    price_basis: str
    discount_pct: float | None = None
    price_tiers: list[Tier] | None = None
    moq_packs: int | None = None
    lead_time_days: int | None = None
    quantity: int | None = None
    extended_amount: float | None = None
    superseded: Correction | None = None
    cold_chain: bool = False
    atc: str = ""

    @property
    def net_price_per_uom(self) -> float:
        if self.discount_pct:
            return round(self.price_per_uom * (1 - self.discount_pct / 100), 6)
        return self.price_per_uom


@dataclass
class Quotation:
    supplier_key: str
    supplier_name: str
    quotation_ref: str
    document_date: date
    valid_until: date
    currency: str
    incoterm: str
    named_place: str
    buyer_reference: str
    destination: str
    buyer_contact: str
    payment_terms: str
    features: list[str]
    lines: list[Line]
    notes: list[str] = field(default_factory=list)
    alt_price_note: str | None = None

    @property
    def supplier(self) -> Supplier:
        return vocab.SUPPLIER_BY_KEY[self.supplier_key]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["document_date"] = self.document_date.isoformat()
        d["valid_until"] = self.valid_until.isoformat()
        for line, src in zip(d["lines"], self.lines, strict=True):
            line["net_price_per_uom"] = src.net_price_per_uom
        return d


def plural(n: int, uom: str) -> str:
    return f"{n} {uom}" if n == 1 else f"{n} {uom}s"


def packaging_for(rng: random.Random, uom: str, units: int) -> str:
    if uom in ("tablet", "capsule"):
        for limit, options in vocab.ORAL_SOLID_PACKAGING:
            if units <= limit:
                return rng.choice(options)
    return rng.choice(PACKAGING_BY_UOM[uom])


def money_decimals(value: float) -> int:
    """How many decimals a document would plausibly print for this magnitude."""
    if value >= 100:
        return 2
    if value >= 1:
        return 3
    return 4


def round_money(value: float) -> float:
    return round(value, money_decimals(value))


def _unit_price(rng: random.Random, product: Product, currency: str) -> float:
    lo, hi = product.usd_range
    usd = rng.uniform(lo, hi)
    local = usd * USD_TO[currency]
    return round_money(local)


def _brand(rng: random.Random, supplier: Supplier, product: Product) -> str:
    stem = product.stem.capitalize()
    short = product.strength.split("/")[0].strip()
    short = short.replace(" mg", "").replace(" mcg", "").replace(" IU/mL", "").replace(",", "")
    short = short.split()[0] if short else ""
    style = rng.choice(("prefix", "stem", "prefix_strength"))
    if style == "prefix":
        return f"{supplier.brand_prefix}{product.stem} {short}".strip()
    if style == "stem":
        return f"{stem}ex {short}".strip()
    return f"{supplier.brand_prefix}{stem.lower()} {short}".strip()


def _pick_products(
    rng: random.Random, pool: list[Product], n: int, features: set[str]
) -> list[Product]:
    chosen = rng.sample(pool, min(n, len(pool)))
    if "mixed_uom" in features:
        uoms = {p.uom for p in chosen}
        extras = [p for p in pool if p.uom not in uoms and p not in chosen]
        rng.shuffle(extras)
        for p in extras[:2]:
            chosen[rng.randrange(len(chosen))] = p
    if "cold_chain" in features and not any(p.cold_chain for p in chosen):
        cold = [p for p in pool if p.cold_chain]
        if cold:
            chosen[-1] = rng.choice(cold)
    return chosen


def make_quotation(
    rng: random.Random,
    supplier: Supplier,
    product_pool: list[Product],
    features: set[str],
    *,
    n_lines: int | None = None,
    seq: int,
) -> Quotation:
    unknown = features - FEATURES
    if unknown:
        raise ValueError(f"unknown features: {sorted(unknown)}")

    if n_lines is None:
        n_lines = rng.randint(12, 16) if "long" in features else rng.randint(2, 7)
    products = _pick_products(rng, product_pool, n_lines, features)

    if "expired" in features:
        doc_date = date(2025, rng.randint(10, 12), rng.randint(1, 28))
        validity_days = rng.choice((30, 45, 60))
    else:
        doc_date = date(2026, rng.randint(6, 9), rng.randint(1, 28))
        validity_days = rng.choice((30, 45, 60, 90))
    incoterm, place = rng.choice(supplier.incoterms)
    destination, _, _ = rng.choice(vocab.DESTINATIONS)
    currency = supplier.currency
    ref = supplier.ref_format.format(yy=doc_date.strftime("%y"), n=seq)

    lines: list[Line] = []
    for i, product in enumerate(products, start=1):
        inn = product.inn
        if "inn_variant" in features and product.inn_variants and rng.random() < 0.7:
            inn = rng.choice(product.inn_variants)
        strength = product.strength
        if "strength_variant" in features and product.strength_variants and rng.random() < 0.6:
            strength = rng.choice(product.strength_variants)
        form = product.form
        if product.form_variants and rng.random() < 0.3:
            form = rng.choice(product.form_variants)

        units = rng.choice(product.pack_options)
        unit_price = _unit_price(rng, product, currency)
        pack_price = round_money(unit_price * units)
        basis = "stated"
        tiers: list[Tier] | None = None
        discount: float | None = None
        qty: int | None = None
        extended: float | None = None

        if "pack_price_only" in features:
            basis = "derived"
            unit_price = round(pack_price / units, 4)
        elif "tiered" in features:
            basis = "tiered"
            t1 = pack_price
            t2 = round_money(t1 * rng.uniform(0.88, 0.95))
            t3 = round_money(t2 * rng.uniform(0.88, 0.95))
            b1 = rng.choice((100, 200, 250, 500))
            b2 = b1 * rng.choice((5, 10))
            b3 = b2 * rng.choice((4, 5))
            tiers = [Tier(b1, b2 - 1, t1), Tier(b2, b3 - 1, t2), Tier(b3, None, t3)]
            unit_price = round(t1 / units, 4)
        elif "discount" in features:
            basis = "list"
            discount = rng.choice((0.0, 2.5, 3.0, 5.0, 7.5, 10.0))

        if "quantity_extended" in features:
            qty = units * rng.choice((500, 1000, 2000, 5000, 10000, 20000))
            net = unit_price * (1 - (discount or 0.0) / 100)
            extended = round(qty * net, 2)

        moq = rng.choice((500, 1000, 2000, 5000, 10000, 20000, 50000))
        lead = rng.choice((21, 28, 30, 35, 42, 45, 56, 60, 63, 75, 90))
        if "lead_time_weeks" in features:
            lead = rng.choice((3, 4, 5, 6, 8, 9, 10, 12)) * 7

        lines.append(
            Line(
                line_no=i,
                product_key=product.key,
                product_name=_brand(rng, supplier, product),
                inn=inn,
                inn_canonical=product.inn,
                strength=strength,
                dosage_form=form,
                packaging=packaging_for(rng, product.uom, units),
                uom=product.uom,
                units_per_pack=units,
                price_per_uom=unit_price,
                price_per_pack=pack_price,
                price_basis=basis,
                discount_pct=discount,
                price_tiers=tiers,
                moq_packs=moq,
                lead_time_days=lead,
                quantity=qty,
                extended_amount=extended,
                cold_chain=product.cold_chain,
                atc=product.atc,
            )
        )

    if "correction" in features:
        target = rng.choice(lines)
        factor = rng.choice((1.03, 1.047, 1.05, 0.96, 0.92))
        if target.price_basis == "derived":
            old = target.price_per_pack
            target.price_per_pack = round_money(old * factor)
            target.price_per_uom = round(target.price_per_pack / target.units_per_pack, 4)
            target.superseded = Correction(
                "price_per_pack", old, target.price_per_pack, "corrected later in the same document"
            )
        else:
            old = target.price_per_uom
            target.price_per_uom = round_money(old * factor)
            target.price_per_pack = round_money(target.price_per_uom * target.units_per_pack)
            if target.quantity is not None:
                net = target.price_per_uom * (1 - (target.discount_pct or 0.0) / 100)
                target.extended_amount = round(target.quantity * net, 2)
            target.superseded = Correction(
                "price_per_uom", old, target.price_per_uom, "corrected later in the same document"
            )

    notes = rng.sample(vocab.NOTE_POOL, rng.randint(2, 4))
    if "vat_note" in features:
        notes.insert(0, "Prices exclude 15% VAT where applicable.")
    alt_note = None
    if "distractor_alt_price" in features:
        alt_line = rng.choice(lines)
        alt_price = round_money(alt_line.price_per_uom * rng.uniform(1.2, 1.6))
        alt_note = (
            f"A larger presentation of {alt_line.product_name} is available on request at "
            f"{currency} {alt_price} per {alt_line.uom}; not included in this offer."
        )
        notes.append(alt_note)

    return Quotation(
        supplier_key=supplier.key,
        supplier_name=supplier.name,
        quotation_ref=ref,
        document_date=doc_date,
        valid_until=doc_date + timedelta(days=validity_days),
        currency=currency,
        incoterm=incoterm,
        named_place=place,
        buyer_reference=f"AXMED-RFQ-2026-{rng.randint(240, 420):04d}",
        destination=destination,
        buyer_contact=rng.choice(vocab.BUYER_CONTACTS),
        payment_terms=supplier.payment_terms,
        features=sorted(features),
        lines=lines,
        notes=notes,
        alt_price_note=alt_note,
    )


def fmt_money(value: float, currency: str | None = None, *, symbol: bool = False) -> str:
    """Format a price the way a document would, with thousands separators where sensible."""
    decimals = money_decimals(value)
    text = f"{value:,.{decimals}f}" if value >= 1000 else f"{value:.{decimals}f}"
    if currency is None:
        return text
    if symbol:
        return f"{vocab.CURRENCY_SYMBOL.get(currency, currency)}{text}"
    return f"{currency} {text}"


def fmt_money_eu(value: float) -> str:
    """European style: dot thousands, comma decimals."""
    decimals = money_decimals(value)
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")
