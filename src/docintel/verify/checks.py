"""Deterministic checks a human reviewer would do with a calculator and a glance.

Each check returns a list of (field, code, detail). Failing a check never changes a
value; it lowers confidence on the fields involved and leaves a reason.
"""

from __future__ import annotations

import re
from datetime import date

from docintel.extract.schema import QuotationLine

Finding = tuple[str, str, str]

ISO_4217 = {
    "USD",
    "EUR",
    "GBP",
    "CHF",
    "INR",
    "ZAR",
    "KES",
    "CNY",
    "VND",
    "EGP",
    "TRY",
    "BDT",
    "PKR",
    "JOD",
    "PEN",
    "NGN",
    "MAD",
    "TZS",
    "UGX",
    "GHS",
    "ETB",
    "RWF",
    "ZMW",
    "XOF",
    "XAF",
    "JPY",
    "AUD",
    "CAD",
    "SGD",
    "AED",
    "SAR",
    "LKR",
    "PHP",
    "IDR",
    "MYR",
    "THB",
    "BRL",
    "MXN",
    "COP",
    "ARS",
    "CLP",
    "NZD",
    "SEK",
    "NOK",
    "DKK",
    "PLN",
    "CZK",
    "HUF",
    "RUB",
    "KRW",
    "HKD",
    "TWD",
}
INCOTERMS = {"EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"}

# Very rough USD per unit sanity bands per unit of measure. Only wild outliers are flagged.
USD_BANDS = {
    "tablet": (0.0005, 50.0),
    "capsule": (0.0005, 50.0),
    "sachet": (0.005, 20.0),
    "ampoule": (0.01, 200.0),
    "vial": (0.02, 2000.0),
    "bottle": (0.05, 500.0),
    "pen": (0.5, 500.0),
    "inhaler": (0.3, 200.0),
    "tube": (0.05, 100.0),
}
# Indicative rates, used only to decide whether a price is wildly implausible.
USD_PER_UNIT = {
    "USD": 1.0,
    "EUR": 1.09,
    "GBP": 1.28,
    "CHF": 1.14,
    "INR": 0.012,
    "ZAR": 0.055,
    "KES": 0.0078,
    "CNY": 0.139,
    "VND": 0.00004,
    "EGP": 0.021,
    "TRY": 0.03,
    "BDT": 0.0091,
    "PKR": 0.0036,
    "JOD": 1.41,
    "PEN": 0.267,
    "NGN": 0.00065,
    "MAD": 0.101,
    "TZS": 0.00037,
    "UGX": 0.00027,
    "GHS": 0.064,
    "ETB": 0.0082,
    "RWF": 0.00072,
    "PHP": 0.017,
    "LKR": 0.0033,
}


def _close(a: float, b: float, rel: float = 0.015, abs_tol: float = 0.0006) -> bool:
    return abs(a - b) <= max(abs_tol, rel * max(abs(a), abs(b)))


def check_line(line: QuotationLine, document_currency: str | None) -> list[Finding]:
    out: list[Finding] = []
    unit, pack, units = line.price_per_uom, line.price_per_pack, line.units_per_pack

    if unit is not None and pack is not None and units and not _close(unit * units, pack):
        out.append(
            (
                "price_per_uom",
                "pack_unit_mismatch",
                f"{unit} x {units} = {unit * units:.4f}, pack price is {pack}",
            )
        )
    if line.price_basis == "derived" and (pack is None or not units):
        out.append(
            (
                "price_per_uom",
                "derived_without_basis",
                "marked derived but pack price or units missing",
            )
        )
    if line.price_basis == "stated" and unit is None:
        out.append(("price_per_uom", "stated_but_missing", "marked stated but no unit price"))
    if unit is None and pack is None and not line.price_tiers:
        out.append(("price_per_uom", "no_price", "no unit price, pack price or tiers"))

    if line.quantity is not None and unit is not None and line.extended_amount is not None:
        expected = line.quantity * unit * (1 - (line.discount_pct or 0.0) / 100)
        if not _close(expected, line.extended_amount, rel=0.01, abs_tol=0.05):
            out.append(
                (
                    "extended_amount",
                    "arithmetic_mismatch",
                    f"{line.quantity} x {unit} less {line.discount_pct or 0}% = {expected:.2f}, "
                    f"printed {line.extended_amount}",
                )
            )

    if line.price_tiers:
        prices = [t.price_per_pack for t in line.price_tiers if t.price_per_pack is not None]
        if prices != sorted(prices, reverse=True):
            out.append(
                (
                    "price_tiers",
                    "tiers_not_decreasing",
                    "volume tiers should fall as quantity rises",
                )
            )
        if pack is not None and prices and not _close(prices[0], pack):
            out.append(
                ("price_per_pack", "tier_mismatch", "pack price is not the lowest-quantity tier")
            )

    currency = line.currency or document_currency
    if currency is None:
        out.append(("currency", "missing_currency", "no currency on the line or the document"))
    elif currency.upper() not in ISO_4217:
        out.append(("currency", "unknown_currency", f"{currency!r} is not an ISO 4217 code"))

    if units is not None and units <= 0:
        out.append(("units_per_pack", "implausible_units", f"{units} units per pack"))
    if line.discount_pct is not None and not 0 <= line.discount_pct <= 60:
        out.append(("discount_pct", "implausible_discount", f"{line.discount_pct}%"))
    if line.lead_time_days is not None and not 0 <= line.lead_time_days <= 400:
        out.append(("lead_time_days", "implausible_lead_time", f"{line.lead_time_days} days"))

    if unit is not None and currency and currency.upper() in USD_PER_UNIT and line.uom:
        usd = unit * USD_PER_UNIT[currency.upper()]
        band = USD_BANDS.get(line.uom.lower().rstrip("s"))
        if band and not band[0] <= usd <= band[1]:
            out.append(
                (
                    "price_per_uom",
                    "implausible_price",
                    f"about USD {usd:.4f} per {line.uom}, outside {band[0]} to {band[1]}; "
                    "possibly a pack price or wrong currency",
                )
            )
    return out


def check_header(
    document_date: str | None, valid_until: str | None, incoterm: str | None
) -> list[Finding]:
    out: list[Finding] = []
    d1, d2 = _parse_date(document_date), _parse_date(valid_until)
    if document_date and d1 is None:
        out.append(("document_date", "bad_date", f"{document_date!r} is not ISO 8601"))
    if valid_until and d2 is None:
        out.append(("valid_until", "bad_date", f"{valid_until!r} is not ISO 8601"))
    if d1 and d2 and d2 < d1:
        out.append(
            ("valid_until", "validity_before_issue", f"{valid_until} is before {document_date}")
        )
    if incoterm and incoterm.upper().split()[0] not in INCOTERMS:
        out.append(("incoterm", "unknown_incoterm", f"{incoterm!r}"))
    return out


def _parse_date(text: str | None) -> date | None:
    if not text or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None
