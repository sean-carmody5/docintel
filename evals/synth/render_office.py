"""Excel, Word and CSV renderings. The formats nobody warned you about."""

from __future__ import annotations

import csv
import random
from pathlib import Path

from docx import Document
from docx.shared import Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from evals.synth.truth import Line, Quotation, fmt_money, fmt_money_eu, plural


def _shown_unit(line: Line) -> float:
    if line.superseded and line.superseded.field == "price_per_uom":
        return line.superseded.old
    return line.price_per_uom


def _shown_pack(line: Line) -> float:
    if line.superseded and line.superseded.field == "price_per_pack":
        return line.superseded.old
    return line.price_per_pack


def write_xlsx(q: Quotation, rng: random.Random, path: Path) -> None:
    s = q.supplier
    wb = Workbook()
    ws = wb.active
    ws.title = "Price List"
    bold = Font(bold=True)
    fill = PatternFill("solid", fgColor="DDE7F0")

    ws.merge_cells("A1:J1")
    ws["A1"] = f"{s.name} - Institutional Price List"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = "Reference"
    ws["B2"] = q.quotation_ref
    ws["D2"] = "Valid from"
    ws["E2"] = q.document_date
    ws["F2"] = "to"
    ws["G2"] = q.valid_until
    ws["A3"] = "Currency"
    ws["B3"] = q.currency
    ws["D3"] = "Delivery"
    ws["E3"] = f"{q.incoterm} {q.named_place}"
    ws["A4"] = "Buyer ref"
    ws["B4"] = q.buyer_reference
    ws["D4"] = "Payment"
    ws["E4"] = q.payment_terms
    for c in ("A2", "D2", "F2", "A3", "D3", "A4", "D4"):
        ws[c].font = bold
    ws["E2"].number_format = "DD/MM/YYYY"
    ws["G2"].number_format = "DD/MM/YYYY"

    tiered = any(ln.price_tiers for ln in q.lines)
    pack_only = "pack_price_only" in q.features
    header = ["Item code", "Product", "INN", "Strength", "Form", "Pack size", "UOM", "Packaging"]
    if tiered:
        header += [
            "Tier 1 from (packs)",
            "Tier 1 price/pack",
            "Tier 2 from (packs)",
            "Tier 2 price/pack",
            "Tier 3 from (packs)",
            "Tier 3 price/pack",
        ]
    else:
        if not pack_only:
            header += ["Unit price"]
        header += ["Pack price"]
    header += ["MOQ (packs)", "Lead time (days)", "Cold chain"]
    ws.append([])
    ws.append(header)
    hdr_row = ws.max_row
    for col in range(1, len(header) + 1):
        c = ws.cell(row=hdr_row, column=col)
        c.font = bold
        c.fill = fill
        c.alignment = Alignment(wrap_text=True, vertical="top")
    for ln in q.lines:
        row: list[object] = [
            f"{s.short[:3].upper()}-{ln.product_key.upper()[:8]}",
            ln.product_name,
            ln.inn,
            ln.strength,
            ln.dosage_form,
            ln.units_per_pack,
            ln.uom,
            ln.packaging,
        ]
        if tiered and ln.price_tiers:
            for t in ln.price_tiers:
                row += [t.min_packs, t.price_per_pack]
            row += [None] * (6 - 2 * len(ln.price_tiers))
        else:
            if not pack_only:
                row.append(_shown_unit(ln))
            row.append(_shown_pack(ln))
        row += [ln.moq_packs, ln.lead_time_days, "Yes" if ln.cold_chain else "No"]
        ws.append(row)
    for col in range(1, len(header) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 16
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 34
    ws.freeze_panes = ws.cell(row=hdr_row + 1, column=1)

    terms = wb.create_sheet("Terms")
    terms["A1"] = "Terms and notes"
    terms["A1"].font = bold
    for i, n in enumerate(q.notes, start=3):
        terms.cell(row=i, column=1, value=n)
    corr = [ln for ln in q.lines if ln.superseded]
    for ln in corr:
        c = ln.superseded
        if c:
            terms.cell(
                row=terms.max_row + 2,
                column=1,
                value=f"Revision: {ln.product_name} {c.field.replace('_', ' ')} is {fmt_money(c.new)} "
                f"(replaces {fmt_money(c.old)} shown on the Price List sheet).",
            )
    contacts = wb.create_sheet("Contact")
    contacts.append(["Name", s.contact_name])
    contacts.append(["Title", s.contact_title])
    contacts.append(["Email", f"{s.contact_name.split()[0].lower()}@{s.email_domain}"])
    contacts.append(["Phone", s.phone])
    contacts.append(["Address", s.address])
    wb.save(path)


def write_docx(q: Quotation, rng: random.Random, path: Path) -> None:
    s = q.supplier
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    doc.add_heading(f"Quotation {q.quotation_ref}", level=1)
    doc.add_paragraph(f"{s.name}\n{s.address}\n{s.phone}")
    doc.add_paragraph(
        f"To: Axmed Ltd, Procurement (attn. {q.buyer_contact})\n"
        f"Your reference: {q.buyer_reference}\n"
        f"Date: {q.document_date.strftime('%d %B %Y')}\n"
        f"Valid until: {q.valid_until.strftime('%d %B %Y')}"
    )
    doc.add_paragraph(
        f"All prices in {q.currency}, {q.incoterm} {q.named_place}. Payment: {q.payment_terms}."
    )
    pack_only = "pack_price_only" in q.features
    cols = [
        "#",
        "Product",
        "INN",
        "Strength / form",
        "Pack",
        "Price per pack" if pack_only else "Unit price",
        "MOQ",
        "Lead time",
    ]
    table = doc.add_table(rows=1, cols=len(cols))
    table.style = "Table Grid"
    for i, c in enumerate(cols):
        table.rows[0].cells[i].text = c
    for ln in q.lines:
        cells = table.add_row().cells
        cells[0].text = str(ln.line_no)
        cells[1].text = ln.product_name
        cells[2].text = ln.inn
        cells[3].text = f"{ln.strength}, {ln.dosage_form.lower()}"
        cells[4].text = f"{plural(ln.units_per_pack, ln.uom)}, {ln.packaging.lower()}"
        cells[5].text = (
            fmt_money(_shown_pack(ln)) if pack_only else f"{fmt_money(_shown_unit(ln))} / {ln.uom}"
        )
        cells[6].text = f"{ln.moq_packs:,} packs"
        cells[7].text = f"{ln.lead_time_days} days"
    doc.add_paragraph()
    for n in q.notes:
        doc.add_paragraph(n, style="List Bullet")
    for ln in q.lines:
        if ln.superseded:
            c = ln.superseded
            doc.add_paragraph(
                f"Please note: the {c.field.replace('_', ' ')} for {ln.product_name} has been revised to "
                f"{q.currency} {fmt_money(c.new)} since the table above was prepared; {fmt_money(c.old)} no longer applies."
            )
    doc.add_paragraph(f"\nYours faithfully,\n\n{s.contact_name}\n{s.contact_title}")
    doc.save(path)


def write_csv(q: Quotation, rng: random.Random, path: Path, *, style: str = "standard") -> None:
    """'standard' is comma separated with dot decimals. 'eu' is semicolon separated, comma decimals, German headers."""
    pack_only = "pack_price_only" in q.features
    with path.open("w", newline="", encoding="utf-8") as fh:
        if style == "standard":
            w = csv.writer(fh)
            w.writerow(["supplier", q.supplier_name])
            w.writerow(["quotation_ref", q.quotation_ref])
            w.writerow(["date", q.document_date.isoformat()])
            w.writerow(["valid_until", q.valid_until.isoformat()])
            w.writerow(["currency", q.currency])
            w.writerow(["incoterm", f"{q.incoterm} {q.named_place}"])
            w.writerow([])
            w.writerow(
                [
                    "line",
                    "product",
                    "inn",
                    "strength",
                    "form",
                    "units_per_pack",
                    "uom",
                    "unit_price",
                    "pack_price",
                    "moq_packs",
                    "lead_days",
                ]
            )
            for ln in q.lines:
                w.writerow(
                    [
                        ln.line_no,
                        ln.product_name,
                        ln.inn,
                        ln.strength,
                        ln.dosage_form,
                        ln.units_per_pack,
                        ln.uom,
                        "" if pack_only else _shown_unit(ln),
                        _shown_pack(ln),
                        ln.moq_packs,
                        ln.lead_time_days,
                    ]
                )
        else:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["Lieferant", q.supplier_name])
            w.writerow(["Angebotsnummer", q.quotation_ref])
            w.writerow(["Datum", q.document_date.strftime("%d.%m.%Y")])
            w.writerow(["Gueltig bis", q.valid_until.strftime("%d.%m.%Y")])
            w.writerow(["Waehrung", q.currency])
            w.writerow(["Lieferbedingung", f"{q.incoterm} {q.named_place}"])
            w.writerow([])
            w.writerow(
                [
                    "Pos.",
                    "Produkt",
                    "Wirkstoff",
                    "Staerke",
                    "Darreichungsform",
                    "Packungsgroesse",
                    "Einheit",
                    "Preis je Einheit",
                    "Preis je Packung",
                    "Mindestbestellmenge (Pack.)",
                    "Lieferzeit (Tage)",
                ]
            )
            for ln in q.lines:
                w.writerow(
                    [
                        ln.line_no,
                        ln.product_name,
                        ln.inn,
                        ln.strength,
                        ln.dosage_form,
                        ln.units_per_pack,
                        ln.uom,
                        "" if pack_only else fmt_money_eu(_shown_unit(ln)),
                        fmt_money_eu(_shown_pack(ln)),
                        f"{ln.moq_packs:,}".replace(",", "."),
                        ln.lead_time_days,
                    ]
                )
