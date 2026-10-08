"""XML export, saved HTML page and plain-text dump. Formats a generic text path must absorb."""

from __future__ import annotations

import random
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

from evals.synth.truth import Line, Quotation, fmt_money, plural


def _shown_unit(line: Line) -> float:
    if line.superseded and line.superseded.field == "price_per_uom":
        return line.superseded.old
    return line.price_per_uom


def _shown_pack(line: Line) -> float:
    if line.superseded and line.superseded.field == "price_per_pack":
        return line.superseded.old
    return line.price_per_pack


def write_xml(q: Quotation, rng: random.Random, path: Path) -> None:
    """An ERP-style XML export with attributes and elements mixed, as real exports do."""
    s = q.supplier
    pack_only = "pack_price_only" in q.features
    root = ET.Element(
        "Quotation",
        {
            "reference": q.quotation_ref,
            "issued": q.document_date.isoformat(),
            "validUntil": q.valid_until.isoformat(),
            "currency": q.currency,
            "schemaVersion": "2.1",
        },
    )
    sup = ET.SubElement(root, "Supplier", {"code": f"{s.short[:3].upper()}{rng.randint(100, 999)}"})
    ET.SubElement(sup, "Name").text = s.name
    ET.SubElement(sup, "Country").text = s.country
    ET.SubElement(sup, "Address").text = s.address
    contact = ET.SubElement(sup, "Contact")
    ET.SubElement(contact, "Name").text = s.contact_name
    ET.SubElement(contact, "Role").text = s.contact_title
    ET.SubElement(contact, "Email").text = f"{s.contact_name.split()[0].lower()}@{s.email_domain}"
    buyer = ET.SubElement(root, "Buyer")
    ET.SubElement(buyer, "Name").text = "Axmed Ltd"
    ET.SubElement(buyer, "Reference").text = q.buyer_reference
    ET.SubElement(buyer, "Destination").text = q.destination
    terms = ET.SubElement(root, "Terms")
    ET.SubElement(terms, "Incoterm", {"place": q.named_place}).text = q.incoterm
    ET.SubElement(terms, "Payment").text = q.payment_terms
    lines = ET.SubElement(root, "Lines", {"count": str(len(q.lines))})
    for ln in q.lines:
        el = ET.SubElement(lines, "Line", {"no": str(ln.line_no)})
        ET.SubElement(el, "Product").text = ln.product_name
        ET.SubElement(el, "INN").text = ln.inn
        ET.SubElement(el, "Strength").text = ln.strength
        ET.SubElement(el, "Form").text = ln.dosage_form
        ET.SubElement(
            el, "Pack", {"units": str(ln.units_per_pack), "uom": ln.uom}
        ).text = ln.packaging
        if ln.price_tiers:
            tiers = ET.SubElement(el, "PriceTiers")
            for t in ln.price_tiers:
                attrs = {"minPacks": str(t.min_packs)}
                if t.max_packs is not None:
                    attrs["maxPacks"] = str(t.max_packs)
                ET.SubElement(tiers, "Tier", attrs).text = f"{t.price_per_pack}"
        else:
            if not pack_only:
                ET.SubElement(el, "UnitPrice", {"currency": q.currency}).text = f"{_shown_unit(ln)}"
            ET.SubElement(el, "PackPrice", {"currency": q.currency}).text = f"{_shown_pack(ln)}"
        ET.SubElement(el, "MOQ", {"unit": "pack"}).text = str(ln.moq_packs)
        ET.SubElement(el, "LeadTime", {"unit": "days"}).text = str(ln.lead_time_days)
        if ln.cold_chain:
            ET.SubElement(el, "ColdChain").text = "true"
    notes = ET.SubElement(root, "Notes")
    for n in q.notes:
        ET.SubElement(notes, "Note").text = n
    for ln in q.lines:
        if ln.superseded:
            c = ln.superseded
            ET.SubElement(
                notes, "Revision", {"line": str(ln.line_no), "field": c.field}
            ).text = f"Revised from {fmt_money(c.old)} to {fmt_money(c.new)}; the earlier figure no longer applies."
    ET.indent(root, space="  ")
    xml = ET.tostring(root, encoding="unicode")
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n' + xml + "\n", encoding="utf-8", newline="\n"
    )


def write_html(q: Quotation, rng: random.Random, path: Path) -> None:
    """A quotation page saved from a supplier portal, with navigation chrome around the table."""
    s = q.supplier
    pack_only = "pack_price_only" in q.features
    rows = []
    for ln in q.lines:
        if ln.price_tiers:
            price = "<br>".join(
                f"{fmt_money(t.price_per_pack)} from {t.min_packs:,} packs" for t in ln.price_tiers
            )
        elif pack_only:
            price = f"{fmt_money(_shown_pack(ln))} / pack"
        else:
            price = f"{fmt_money(_shown_unit(ln))} / {escape(ln.uom)}"
        rows.append(
            "<tr>"
            f"<td>{ln.line_no}</td><td><strong>{escape(ln.product_name)}</strong><br>"
            f"<small>{escape(ln.inn)} {escape(ln.strength)}, {escape(ln.dosage_form.lower())}</small></td>"
            f"<td>{escape(plural(ln.units_per_pack, ln.uom))}<br><small>{escape(ln.packaging)}</small></td>"
            f'<td class="num">{price}</td><td class="num">{ln.moq_packs:,}</td>'
            f'<td class="num">{ln.lead_time_days}</td></tr>'
        )
    revisions = "".join(
        f'<p class="alert">Revision: {escape(ln.product_name)} '
        f"{escape((ln.superseded.field if ln.superseded else '').replace('_', ' '))} is now "
        f"{fmt_money(ln.superseded.new if ln.superseded else 0)} (was {fmt_money(ln.superseded.old if ln.superseded else 0)}).</p>"
        for ln in q.lines
        if ln.superseded
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Quotation {escape(q.quotation_ref)} | {escape(s.short)} Supplier Portal</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;color:#222}}
nav{{background:#1b3a5c;color:#fff;padding:10px 24px}} nav a{{color:#cfe0f3;margin-right:18px;text-decoration:none}}
main{{max-width:960px;margin:24px auto;padding:0 16px}}
dl{{display:grid;grid-template-columns:160px 1fr;gap:4px 12px;font-size:14px}} dt{{color:#666}}
table{{border-collapse:collapse;width:100%;font-size:14px;margin-top:16px}}
th,td{{border-bottom:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}} th{{background:#f0f4f8}}
.num{{text-align:right;white-space:nowrap}} .alert{{background:#fff4e5;border-left:4px solid #e08a00;padding:8px 12px}}
footer{{color:#777;font-size:12px;margin-top:32px}}
</style>
</head>
<body>
<nav><a href="#">Dashboard</a><a href="#">Quotations</a><a href="#">Orders</a><a href="#">Documents</a>
<span style="float:right">Signed in as {escape(q.buyer_contact)}</span></nav>
<main>
<h1>Quotation {escape(q.quotation_ref)}</h1>
<dl>
<dt>Supplier</dt><dd>{escape(s.name)}, {escape(s.city)} ({escape(s.country)})</dd>
<dt>Issued</dt><dd>{q.document_date.strftime("%d %b %Y")}</dd>
<dt>Valid until</dt><dd>{q.valid_until.strftime("%d %b %Y")}</dd>
<dt>Currency</dt><dd>{escape(q.currency)}</dd>
<dt>Delivery</dt><dd>{escape(q.incoterm)} {escape(q.named_place)}</dd>
<dt>Payment</dt><dd>{escape(q.payment_terms)}</dd>
<dt>Your reference</dt><dd>{escape(q.buyer_reference)}</dd>
</dl>
<table>
<thead><tr><th>#</th><th>Product</th><th>Pack</th><th class="num">Price ({escape(q.currency)})</th><th class="num">MOQ (packs)</th><th class="num">Lead (days)</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody>
</table>
{revisions}
<h2>Notes</h2>
<ul>{"".join(f"<li>{escape(n)}</li>" for n in q.notes)}</ul>
</main>
<footer>{escape(s.name)} supplier portal. Prices shown are as submitted by the supplier and are not an order confirmation. Page generated {q.document_date.isoformat()}.</footer>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8", newline="\n")


def write_txt(q: Quotation, rng: random.Random, path: Path) -> list[tuple[Line, str, str]]:
    """A fixed-width text dump, the kind an old ERP prints to a .txt file.

    Returns the cells the column widths cut short, as (line, field, text as printed), so
    the truth can say what the page says rather than what the ERP knew.
    """
    s = q.supplier
    cut: list[tuple[Line, str, str]] = []

    def cell(ln: Line, f: str, width: int) -> str:
        value = str(getattr(ln, f))
        shown = value[:width]
        if shown != value:
            cut.append((ln, f, shown))
        return shown

    pack_only = "pack_price_only" in q.features
    w = 118
    out = [
        s.name.upper().center(w),
        s.address.center(w),
        "",
        "QUOTATION".center(w),
        "=" * w,
        f"Ref: {q.quotation_ref:<28} Date: {q.document_date.strftime('%d-%b-%Y'):<16} "
        f"Valid: {q.valid_until.strftime('%d-%b-%Y'):<16} Currency: {q.currency}",
        f"To: Axmed Ltd / {q.buyer_contact:<24} Your ref: {q.buyer_reference:<24} "
        f"Terms: {q.incoterm} {q.named_place}",
        "=" * w,
    ]
    head = f"{'NO':<4}{'PRODUCT':<22}{'INN':<34}{'STRENGTH':<16}{'PACK':<16}"
    head += f"{'PACK PRICE':>12}" if pack_only else f"{'UNIT PRICE':>12}{'PACK PRICE':>12}"
    head += f"{'MOQ':>8}{'LEAD':>6}"
    out += [head, "-" * w]
    for ln in q.lines:
        row = (
            f"{ln.line_no:<4}{cell(ln, 'product_name', 21):<22}{cell(ln, 'inn', 33):<34}"
            f"{cell(ln, 'strength', 15):<16}"
            f"{(str(ln.units_per_pack) + ' ' + ln.uom)[:15]:<16}"
        )
        if pack_only:
            row += f"{fmt_money(_shown_pack(ln)):>12}"
        else:
            row += f"{fmt_money(_shown_unit(ln)):>12}{fmt_money(_shown_pack(ln)):>12}"
        row += f"{ln.moq_packs:>8}{ln.lead_time_days:>6}"
        out.append(row)
        out.append(f"{'':<4}{cell(ln, 'dosage_form', 21):<22}{cell(ln, 'packaging', 33):<34}")
    out += ["-" * w, "NOTES:"]
    out += [f"  - {n}" for n in q.notes]
    for ln in q.lines:
        if ln.superseded:
            c = ln.superseded
            out.append(
                f"  - REVISION line {ln.line_no}: {c.field.replace('_', ' ')} {fmt_money(c.new)} replaces {fmt_money(c.old)}"
            )
    out += [
        "",
        f"Payment: {q.payment_terms}",
        f"Contact: {s.contact_name}, {s.contact_title}, {s.phone}",
        "",
    ]
    path.write_text("\n".join(out), encoding="utf-8", newline="\n")
    return cut
