"""JSON exports in dialects that share nothing but the facts.

Each dialect mimics a different supplier system. None of them use the same
field names, nesting or number formatting, which is the point.
"""

from __future__ import annotations

import json
import random
import re
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from evals.synth import vocab
from evals.synth.truth import Line, Quotation, fmt_money, plural

Dialect = Callable[[Quotation, random.Random], dict[str, Any]]

_STRENGTH_RE = re.compile(r"^(\d+(?:\.\d+)?) (mg|mcg|g|IU)$")


def _shown_unit(line: Line) -> float:
    """Price the document prints: the superseded value if a correction follows."""
    if line.superseded and line.superseded.field == "price_per_uom":
        return line.superseded.old
    return line.price_per_uom


def _shown_pack(line: Line) -> float:
    if line.superseded and line.superseded.field == "price_per_pack":
        return line.superseded.old
    return line.price_per_pack


def _strength_obj(strength: str) -> dict[str, Any] | str:
    m = _STRENGTH_RE.match(strength)
    if not m:
        return strength
    return {"value": float(m.group(1)), "unit": m.group(2), "label": strength}


def _iso_dt(q: Quotation, rng: random.Random) -> str:
    return f"{q.document_date.isoformat()}T{rng.randint(7, 17):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d}Z"


def erp_nested(q: Quotation, rng: random.Random) -> dict[str, Any]:
    s = q.supplier
    pack_only = "pack_price_only" in q.features
    products = []
    for ln in q.lines:
        commercials: dict[str, Any] = {
            "price_per_pack": _shown_pack(ln),
            "minimum_order_quantity_packs": ln.moq_packs,
        }
        if not pack_only:
            commercials["price_per_unit"] = _shown_unit(ln)
        if "lead_time_weeks" in q.features and ln.lead_time_days:
            commercials["lead_time_weeks"] = ln.lead_time_days // 7
        else:
            commercials["lead_time_days"] = ln.lead_time_days
        products.append(
            {
                "sku": f"{s.short[:3].upper()}-{ln.product_key[:6].upper()}-{ln.units_per_pack}",
                "trade_name": ln.product_name,
                "generic_name": [p.strip() for p in ln.inn.split("+")],
                "strength": _strength_obj(ln.strength),
                "form": ln.dosage_form,
                "packaging": {
                    "primary": ln.packaging,
                    "units_per_pack": ln.units_per_pack,
                    "unit_label": ln.uom,
                    "packs_per_shipper": rng.choice((4, 12, 24, 50, 100)),
                },
                "commercials": commercials,
                "regulatory": {
                    "who_prequalified": rng.random() < 0.4,
                    "registered_markets": rng.sample(["NG", "KE", "TZ", "ZM", "UG", "GH", "ET"], 3),
                },
                "shelf_life_months": rng.choice((24, 36, 48)),
                "storage": "Below 30 C, protect from moisture"
                if not ln.cold_chain
                else "2-8 C, do not freeze",
            }
        )
    return {
        "meta": {
            "source_system": f"{s.short.replace(' ', '')}ERP",
            "export_version": f"{rng.randint(2, 4)}.{rng.randint(0, 9)}.{rng.randint(0, 9)}",
            "generated_at": _iso_dt(q, rng),
            "record_count": len(products),
            "document_class": "OFFER",
        },
        "vendor": {
            "name": s.name,
            "vendor_code": f"{s.short[:3].upper()}-{rng.randint(100, 999):04d}",
            "registered_country": s.country,
            "site_of_manufacture": s.address,
            "quality_status": {
                qs.lower().replace(" ", "_").replace("-", "_"): True for qs in s.quality
            },
            "commercial_contact": {
                "name": s.contact_name,
                "role": s.contact_title,
                "email": f"{s.contact_name.split()[0].lower()}@{s.email_domain}",
                "phone": s.phone,
            },
        },
        "offer": {
            "offer_reference": q.quotation_ref,
            "offer_date": q.document_date.isoformat(),
            "expiry_date": q.valid_until.isoformat(),
            "against_enquiry": q.buyer_reference,
            "price_basis": {
                "currency": q.currency,
                "incoterms": q.incoterm,
                "named_place": q.named_place,
            },
            "payment_terms": q.payment_terms,
            "note_on_pricing": (
                "Unit prices not stated separately; pack price and pack composition given."
                if pack_only
                else "Prices per pack and per unit as stated."
            ),
            "products": products,
            "notes": q.notes,
        },
    }


def flat_lines(q: Quotation, rng: random.Random) -> dict[str, Any]:
    s = q.supplier
    pack_only = "pack_price_only" in q.features
    items = []
    for ln in q.lines:
        item: dict[str, Any] = {
            "line_no": ln.line_no,
            "product_name": ln.product_name,
            "inn": ln.inn,
            "strength": ln.strength,
            "dosage_form": ln.dosage_form,
            "unit_of_measure": ln.uom,
            "units_per_pack": ln.units_per_pack,
            "pack_description": f"{ln.packaging}, {plural(ln.units_per_pack, ln.uom)} per pack",
        }
        if not pack_only:
            item["price_per_uom"] = _shown_unit(ln)
        item["price_per_pack"] = _shown_pack(ln)
        if ln.discount_pct is not None:
            item["discount_pct"] = ln.discount_pct
        item.update(
            {
                "minimum_order_quantity_packs": ln.moq_packs,
                "lead_time_days": ln.lead_time_days,
                "manufacturer": s.name,
                "country_of_origin": s.country,
                "shelf_life_months": rng.choice((24, 36)),
                "atc_code": ln.atc,
            }
        )
        if ln.cold_chain:
            item["cold_chain_required"] = True
        items.append(item)
    out: dict[str, Any] = {
        "document_type": "supplier_quotation",
        "schema_version": "1.0",
        "quotation_id": q.quotation_ref,
        "issued_date": q.document_date.isoformat(),
        "valid_until": q.valid_until.isoformat(),
        "buyer_reference": q.buyer_reference,
        "supplier": {
            "legal_name": s.name,
            "short_name": s.short,
            "country": s.country,
            "address": s.address,
            "contact_person": s.contact_name,
            "contact_email": f"{s.contact_name.split()[0].lower()}.{s.contact_name.split()[-1].lower()}@{s.email_domain}",
            "gmp_certifications": list(s.quality),
            "manufacturing_licence": s.registration,
        },
        "commercial_terms": {
            "currency": q.currency,
            "incoterm": q.incoterm,
            "named_place": q.named_place,
            "payment_terms": q.payment_terms,
            "price_validity_days": (q.valid_until - q.document_date).days,
            "partial_shipment_allowed": rng.random() < 0.6,
        },
        "line_items": items,
        "notes": q.notes,
    }
    if q.lines and q.lines[0].superseded is None and "correction" in q.features:
        pass
    corrected = [ln for ln in q.lines if ln.superseded]
    if corrected:
        out["revisions"] = [
            {
                "line_no": ln.line_no,
                "field": ln.superseded.field,
                "previous_value": ln.superseded.old,
                "revised_value": ln.superseded.new,
                "reason": "price list update",
            }
            for ln in corrected
            if ln.superseded
        ]
    return out


def catalogue_tiers(q: Quotation, rng: random.Random) -> dict[str, Any]:
    s = q.supplier
    products = []
    for ln in q.lines:
        entry: dict[str, Any] = {
            "item_code": f"{s.short[:3].upper()}-{ln.product_key.upper()[:8]}",
            "product_name": ln.product_name,
            "inn": ln.inn,
            "strength": ln.strength,
            "dosage_form": ln.dosage_form,
            "unit_of_measure": ln.uom,
            "pack": {
                "units_per_pack": ln.units_per_pack,
                "description": f"{ln.packaging}, {plural(ln.units_per_pack, ln.uom)}",
            },
        }
        if ln.price_tiers:
            entry["price_tiers"] = [
                {
                    "tier": i,
                    "min_packs": t.min_packs,
                    "max_packs": t.max_packs,
                    "price_per_pack": t.price_per_pack,
                }
                for i, t in enumerate(ln.price_tiers, start=1)
            ]
        else:
            entry["price_per_pack"] = _shown_pack(ln)
        entry["lead_time_days"] = ln.lead_time_days
        entry["shelf_life_months"] = rng.choice((24, 36, 48))
        if ln.cold_chain:
            entry["cold_chain_required"] = True
            entry["storage_note"] = "Cold chain 2-8 C"
        products.append(entry)
    return {
        "catalogue": {
            "title": f"Institutional Price List - Q{(q.document_date.month - 1) // 3 + 1} {q.document_date.year}",
            "issuer": s.name,
            "issuer_country": s.country,
            "issuer_site": s.address,
            "list_reference": q.quotation_ref,
            "effective_from": q.document_date.isoformat(),
            "effective_to": q.valid_until.isoformat(),
            "quotation_currency": q.currency,
            "delivery_terms": f"{q.incoterm} {q.named_place}",
            "price_note": " ".join(q.notes[:2]),
            "contact": f"tenders@{s.email_domain}",
        },
        "products": products,
    }


def camel_api(q: Quotation, rng: random.Random) -> dict[str, Any]:
    s = q.supplier
    pack_only = "pack_price_only" in q.features
    items = []
    for ln in q.lines:
        item: dict[str, Any] = {
            "lineNumber": ln.line_no,
            "productName": ln.product_name,
            "activeIngredient": ln.inn,
            "strength": ln.strength,
            "dosageForm": ln.dosage_form,
            "packSize": {"quantity": ln.units_per_pack, "unit": ln.uom},
            "packaging": ln.packaging,
        }
        if not pack_only:
            item["unitPrice"] = {"amount": f"{_shown_unit(ln)}", "currency": q.currency}
        item["packPrice"] = {"amount": f"{_shown_pack(ln)}", "currency": q.currency}
        item["minimumOrder"] = {"quantity": ln.moq_packs, "unit": "pack"}
        item["leadTimeDays"] = ln.lead_time_days
        item["flags"] = {"coldChain": ln.cold_chain, "whoPrequalified": rng.random() < 0.3}
        items.append(item)
    return {
        "status": "ok",
        "data": {
            "quote": {
                "quoteId": q.quotation_ref,
                "supplierId": f"SUP-{rng.randint(1000, 9999)}",
                "supplierName": s.name,
                "supplierCountry": s.country,
                "issuedAt": _iso_dt(q, rng),
                "expiresAt": f"{q.valid_until.isoformat()}T23:59:59Z",
                "currencyCode": q.currency,
                "deliveryTerms": {"incoterm": q.incoterm, "location": q.named_place},
                "paymentTerms": q.payment_terms,
                "buyerRef": q.buyer_reference,
                "items": items,
                "remarks": q.notes,
            }
        },
        "meta": {
            "requestId": str(uuid.UUID(int=rng.getrandbits(128))),
            "generatedBy": "QuoteAPI v2.3",
        },
    }


def attribute_list(q: Quotation, rng: random.Random) -> dict[str, Any]:
    s = q.supplier
    symbol = "symbol_currency" in q.features
    pack_only = "pack_price_only" in q.features
    items = []
    for ln in q.lines:
        attrs = [
            {"name": "Trade name", "value": ln.product_name},
            {"name": "INN", "value": ln.inn},
            {"name": "Strength", "value": ln.strength},
            {"name": "Form", "value": ln.dosage_form},
            {"name": "Pack", "value": f"{ln.units_per_pack} x {ln.uom}, {ln.packaging}"},
            {
                "name": "Pack price",
                "value": f"{fmt_money(_shown_pack(ln), q.currency, symbol=symbol)} per pack",
            },
        ]
        if not pack_only:
            attrs.append(
                {
                    "name": "Unit price",
                    "value": f"{fmt_money(_shown_unit(ln), q.currency, symbol=symbol)} per {ln.uom}",
                }
            )
        attrs.append({"name": "MOQ", "value": f"{ln.moq_packs:,} packs"})
        lead = ln.lead_time_days or 0
        attrs.append(
            {
                "name": "Lead time",
                "value": f"{lead // 7} weeks"
                if "lead_time_weeks" in q.features
                else f"{lead} days",
            }
        )
        items.append({"id": f"ITM-{ln.line_no:03d}", "attributes": attrs})
    fields = [
        {"key": "Supplier", "value": s.name},
        {"key": "Supplier country", "value": s.country},
        {"key": "Reference", "value": q.quotation_ref},
        {"key": "Date", "value": q.document_date.strftime("%d %B %Y")},
        {"key": "Valid until", "value": q.valid_until.strftime("%d %B %Y")},
        {"key": "Delivery", "value": f"{q.incoterm} {q.named_place}"},
        {"key": "Payment", "value": q.payment_terms},
        {"key": "Buyer reference", "value": q.buyer_reference},
    ]
    if not symbol:
        fields.insert(3, {"key": "Currency", "value": q.currency})
    return {
        "export": {
            "system": f"{s.short} CRM",
            "entity": "Quotation",
            "id": q.quotation_ref,
            "fields": fields,
            "items": items,
            "notes": q.notes,
        }
    }


def table_dump(q: Quotation, rng: random.Random) -> dict[str, Any]:
    pack_only = "pack_price_only" in q.features
    columns = [
        "#",
        "Product",
        "INN",
        "Strength",
        "Form",
        "Pk Sz",
        "UOM",
        "Unit Px",
        "Pack Px",
        "MOQ (pk)",
        "Lead (d)",
    ]
    rows: list[list[Any]] = []
    for ln in q.lines:
        rows.append(
            [
                ln.line_no,
                ln.product_name,
                ln.inn,
                ln.strength,
                ln.dosage_form,
                ln.units_per_pack,
                ln.uom,
                None if pack_only else _shown_unit(ln),
                _shown_pack(ln),
                ln.moq_packs,
                ln.lead_time_days,
            ]
        )
    return {
        "sheet": "Quotation",
        "exported": _iso_dt(q, rng),
        "header_rows": [
            ["Supplier", q.supplier_name],
            ["Ref", q.quotation_ref],
            ["Date", q.document_date.strftime("%d/%m/%Y")],
            ["Valid to", q.valid_until.strftime("%d/%m/%Y")],
            ["Currency", q.currency],
            ["Terms", f"{q.incoterm} {q.named_place}"],
            ["Buyer ref", q.buyer_reference],
        ],
        "columns": columns,
        "rows": rows,
        "footer": q.notes,
    }


DIALECTS: dict[str, Dialect] = {
    "erp_nested": erp_nested,
    "flat_lines": flat_lines,
    "catalogue_tiers": catalogue_tiers,
    "camel_api": camel_api,
    "attribute_list": attribute_list,
    "table_dump": table_dump,
}


def write_json(
    q: Quotation,
    rng: random.Random,
    dialect: str,
    path: Path,
    *,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = DIALECTS[dialect](q, rng)
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


__all__ = ["DIALECTS", "write_json", "vocab"]
