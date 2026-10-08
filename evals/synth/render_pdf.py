"""PDF quotations in three unrelated layouts, built with ReportLab."""

from __future__ import annotations

import random
from collections.abc import Callable
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from evals.synth import vocab
from evals.synth.truth import Line, Quotation, fmt_money, plural

Layout = Callable[[Quotation, random.Random, Path, str | None, object | None], None]


def _shown_unit(line: Line) -> float:
    if line.superseded and line.superseded.field == "price_per_uom":
        return line.superseded.old
    return line.price_per_uom


def _shown_pack(line: Line) -> float:
    if line.superseded and line.superseded.field == "price_per_pack":
        return line.superseded.old
    return line.price_per_pack


def _st(name: str, **kw: object) -> ParagraphStyle:
    base = {"fontName": "Helvetica", "fontSize": 9, "leading": 11}
    base.update(kw)
    return ParagraphStyle(name, **base)  # type: ignore[arg-type]


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def _hidden(text: str) -> Paragraph:
    """White, one-point text. Invisible when rendered, present in the text layer."""
    return Paragraph(escape(text), _st("hidden", fontSize=1, leading=1, textColor=colors.white))


def _cur(value: float, q: Quotation) -> str:
    symbol = "symbol_currency" in q.features and q.currency in ("USD", "EUR", "GBP")
    return (
        fmt_money(value, q.currency if symbol else None, symbol=True)
        if symbol
        else fmt_money(value)
    )


def _lead(line: Line, q: Quotation) -> str:
    d = line.lead_time_days or 0
    return f"{d // 7} weeks" if "lead_time_weeks" in q.features else f"{d} days"


def _correction_note(q: Quotation) -> str | None:
    for ln in q.lines:
        if ln.superseded:
            c = ln.superseded
            label = "unit price" if c.field == "price_per_uom" else "pack price"
            txt = (
                f"Correction to item {ln.line_no:02d} ({ln.product_name}): the {label} should read "
                f"{q.currency} {fmt_money(c.new)}, not {q.currency} {fmt_money(c.old)} as printed "
                f"in the schedule above. Our list was updated this month; apologies for the error."
            )
            if ln.extended_amount is not None:
                txt += f" The extended amount for the line becomes {q.currency} {fmt_money(ln.extended_amount)}."
            return txt
    return None


# --------------------------------------------------------------------------- classic proforma


def classic_proforma(
    q: Quotation,
    rng: random.Random,
    path: Path,
    hidden_text: str | None,
    encrypt: object | None = None,
) -> None:
    s = q.supplier
    maroon = colors.HexColor("#6b2233")
    gold = colors.HexColor("#a8812f")
    ink = colors.HexColor("#2b2b2b")
    body = _st("body", fontName="Times-Roman", fontSize=9.5, leading=12.5, textColor=ink)
    small = _st("small", fontName="Times-Roman", fontSize=7.6, leading=9.5, textColor=ink)
    cell = _st("cell", fontName="Times-Roman", fontSize=7.8, leading=9.6, textColor=ink)
    cellb = _st("cellb", fontName="Times-Bold", fontSize=7.8, leading=9.6, textColor=ink)
    cellr = _st(
        "cellr",
        fontName="Times-Roman",
        fontSize=7.8,
        leading=9.6,
        textColor=ink,
        alignment=TA_RIGHT,
    )
    head = _st(
        "head",
        fontName="Times-Bold",
        fontSize=7.4,
        leading=9,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    h1 = _st(
        "h1", fontName="Times-Bold", fontSize=16, leading=19, textColor=maroon, alignment=TA_CENTER
    )
    sub = _st(
        "sub", fontName="Times-Italic", fontSize=9, leading=11, textColor=gold, alignment=TA_CENTER
    )
    sec = _st(
        "sec", fontName="Times-Bold", fontSize=10, leading=13, textColor=maroon, spaceBefore=8
    )
    addr = _st(
        "addr",
        fontName="Times-Roman",
        fontSize=8.5,
        leading=10.5,
        textColor=ink,
        alignment=TA_RIGHT,
    )

    def on_page(canvas, doc):  # type: ignore[no-untyped-def]
        canvas.saveState()
        canvas.setStrokeColor(maroon)
        canvas.setLineWidth(1.2)
        canvas.line(
            18 * mm, doc.pagesize[1] - 16 * mm, doc.pagesize[0] - 18 * mm, doc.pagesize[1] - 16 * mm
        )
        canvas.setFillColor(gold)
        canvas.rect(12 * mm, 20 * mm, 1.6 * mm, doc.pagesize[1] - 40 * mm, stroke=0, fill=1)
        canvas.setFont("Times-Italic", 7)
        canvas.setFillColor(ink)
        canvas.drawString(
            18 * mm, 12 * mm, f"{s.name}  -  Licence {s.registration}  -  exports@{s.email_domain}"
        )
        canvas.drawRightString(
            doc.pagesize[0] - 18 * mm, 12 * mm, f"{q.quotation_ref}  |  page {doc.page}"
        )
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(path),
        invariant=1,
        encrypt=encrypt,
        pagesize=LETTER,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title=f"Proforma Quotation {q.quotation_ref} - {s.name}",
        author=s.name,
        subject=f"Proforma quotation - Axmed RFQ {q.buyer_reference}",
    )
    story: list[object] = []
    tagline, subtitle = vocab.TAGLINE_BY_COUNTRY.get(s.country, vocab.DEFAULT_TAGLINE)
    header = Table(
        [
            [
                [
                    Paragraph(
                        f"<b>{escape(s.name.upper())}</b>",
                        _st("co", fontName="Times-Bold", fontSize=15, leading=18, textColor=maroon),
                    ),
                    Paragraph(
                        escape(f"{tagline} - {s.city}"),
                        _st("tag", fontName="Times-Italic", fontSize=8.5, textColor=gold),
                    ),
                ],
                [
                    _p(s.address, addr),
                    _p(f"Tel. {s.phone}", addr),
                    _p(f"www.{s.email_domain}", addr),
                ],
            ]
        ],
        colWidths=[95 * mm, 84 * mm],
    )
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [
        header,
        Spacer(1, 6 * mm),
        _p("PROFORMA QUOTATION", h1),
        _p(subtitle, sub),
        Spacer(1, 4 * mm),
    ]

    validity = (q.valid_until - q.document_date).days
    meta_left = [
        ("Quotation ref.", q.quotation_ref),
        ("Date of issue", q.document_date.strftime("%d %B %Y")),
        (
            "Validity",
            f"{validity} calendar days from issue (to {q.valid_until.strftime('%d %b %Y')})",
        ),
        ("Currency", f"{q.currency}"),
        ("Incoterms 2020", f"{q.incoterm} {q.named_place}"),
    ]
    meta_right = [
        ("Addressed to", "Axmed Ltd - Procurement"),
        ("Attention", q.buyer_contact),
        ("Against RFQ", q.buyer_reference),
        ("Final destination", q.destination),
        ("Payment", q.payment_terms),
    ]
    meta_rows = [
        [_p(a, cellb), _p(b, cell), _p(c, cellb), _p(d, cell)]
        for (a, b), (c, d) in zip(meta_left, meta_right, strict=True)
    ]
    meta = Table(meta_rows, colWidths=[26 * mm, 62 * mm, 30 * mm, 61 * mm])
    meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7f2e8")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9b99a")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story += [meta, Spacer(1, 4 * mm)]

    story.append(
        _p(
            f"Dear {q.buyer_contact.split()[0] if ' ' in q.buyer_contact else 'Sir or Madam'},",
            body,
        )
    )
    story.append(Spacer(1, 2 * mm))
    story.append(
        _p(
            f"With reference to your request for quotation {q.buyer_reference}, we are pleased to submit our "
            f"proforma quotation for the {len(q.lines)} presentations set out below. All items are manufactured "
            f"at our licensed {s.city} site.",
            body,
        )
    )
    if hidden_text:
        story.append(_hidden(hidden_text))
    story.append(_p("1.  Schedule of prices", sec))

    has_qty = any(ln.quantity is not None for ln in q.lines)
    has_disc = any(ln.discount_pct is not None for ln in q.lines)
    pack_only = "pack_price_only" in q.features
    cols = ["Item", "Product", "INN", "Presentation", "UOM"]
    widths = [10 * mm, 22 * mm, 30 * mm, 37 * mm, 13 * mm]
    if has_qty:
        cols += ["Qty\n(UOM)"]
        widths += [17 * mm]
    if pack_only:
        cols += ["Pack", f"Pack price\n{q.currency}"]
        widths += [11 * mm, 19 * mm]
    else:
        cols += [f"Unit price\n{q.currency}/UOM"]
        widths += [19 * mm]
    if has_disc:
        cols += ["Disc.\n%"]
        widths += [10 * mm]
    if has_qty:
        cols += [f"Extended\n{q.currency}"]
        widths += [22 * mm]
    else:
        cols += ["MOQ\npacks"]
        widths += [14 * mm]
    rows: list[list[object]] = [[Paragraph(escape(c).replace("\n", "<br/>"), head) for c in cols]]
    total = 0.0
    for ln in q.lines:
        pres = f"{ln.strength} {ln.dosage_form.lower()}\n{ln.packaging}, {plural(ln.units_per_pack, ln.uom)} per pack"
        row: list[object] = [
            _p(f"{ln.line_no:02d}", cell),
            _p(ln.product_name, cellb),
            _p(ln.inn, cell),
            Paragraph(escape(pres).replace("\n", "<br/>"), cell),
            _p(ln.uom, cell),
        ]
        if has_qty:
            row.append(_p(f"{ln.quantity:,}", cellr))
        if pack_only:
            row += [_p(str(ln.units_per_pack), cellr), _p(_cur(_shown_pack(ln), q), cellr)]
        else:
            row.append(_p(_cur(_shown_unit(ln), q), cellr))
        if has_disc:
            row.append(_p(f"{ln.discount_pct or 0.0:.1f}", cellr))
        if has_qty:
            qty = ln.quantity or 0
            shown_ext = round(qty * _shown_unit(ln) * (1 - (ln.discount_pct or 0.0) / 100), 2)
            total += shown_ext
            row.append(_p(fmt_money(shown_ext), cellr))
        else:
            row.append(_p(f"{ln.moq_packs:,}", cellr))
        rows.append(row)
    tbl = Table(rows, colWidths=widths, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), maroon),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b9a98a")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#faf6ee")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(tbl)
    if has_qty:
        totals = Table(
            [
                [
                    _p(f"Subtotal, {q.incoterm} {q.named_place}", cellb),
                    _p(fmt_money(round(total, 2)), cellr),
                ],
                [
                    _p("Freight and insurance", cell),
                    _p(
                        "not applicable" if q.incoterm in ("EXW", "FCA", "FOB") else "included",
                        cellr,
                    ),
                ],
                [
                    _p(f"TOTAL OFFER VALUE ({q.currency})", cellb),
                    _p(fmt_money(round(total, 2)), cellr),
                ],
            ],
            colWidths=[140 * mm, 40 * mm],
        )
        totals.setStyle(
            TableStyle(
                [("LINEABOVE", (0, 2), (-1, 2), 0.8, maroon), ("ALIGN", (1, 0), (1, -1), "RIGHT")]
            )
        )
        story += [
            totals,
            Spacer(1, 2 * mm),
            _p(
                "Extended amounts are quantity x unit price, less the discount shown, rounded to two decimals. "
                "Quantities are the indicative annual volumes stated in your RFQ.",
                small,
            ),
        ]
    story.append(_p("2.  Notes to the schedule", sec))
    notes = list(q.notes)
    corr = _correction_note(q)
    if corr:
        notes.append(corr)
    for i, n in enumerate(notes, start=1):
        story.append(_p(f"({i})  {n}", small))
    story.append(PageBreak())
    story.append(_p("3.  Banking and shipping details", sec))
    bank = Table(
        [
            [_p(f"BENEFICIARY  {s.name}", cell), _p(f"PORT OF LOADING  {q.named_place}", cell)],
            [_p(f"BANK  {s.bank_name}", cell), _p(f"DESTINATION  {q.destination}", cell)],
            [
                _p(f"SWIFT/BIC  {s.swift}", cell),
                _p(f"TRANSIT TIME  {rng.randint(18, 40)} days", cell),
            ],
            [
                _p(f"ACCOUNT ({q.currency})  {s.account}", cell),
                _p("PACKING  Export cartons on ISPM-15 pallets", cell),
            ],
            [
                _p(f"REFERENCE  {q.quotation_ref}", cell),
                _p(
                    f"HS CODES  {' / '.join(sorted({'3004.' + c for c in ('10', '20', '90')}))}",
                    cell,
                ),
            ],
        ],
        colWidths=[90 * mm, 90 * mm],
    )
    bank.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9b99a")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#faf6ee")),
            ]
        )
    )
    story += [
        bank,
        Spacer(1, 8 * mm),
        _p("Yours faithfully,", body),
        Spacer(1, 8 * mm),
        _p(s.contact_name, _st("sig", fontName="Times-Italic", fontSize=9.5)),
        _p("________________________________", body),
        _p(s.contact_name, cellb),
        _p(s.contact_title, cell),
        _p(s.name, cell),
        _p(f"{s.contact_name.split()[0].lower()}@{s.email_domain}", cell),
    ]
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


# --------------------------------------------------------------------------- modern quote


def modern_quote(
    q: Quotation,
    rng: random.Random,
    path: Path,
    hidden_text: str | None,
    encrypt: object | None = None,
) -> None:
    s = q.supplier
    navy = colors.HexColor("#123a5f")
    teal = colors.HexColor("#1f7a8c")
    grey = colors.HexColor("#5a6672")
    body = _st("mbody", fontSize=9, leading=12)
    small = _st("msmall", fontSize=7.6, leading=9.6, textColor=grey)
    cell = _st("mcell", fontSize=7.8, leading=9.6)
    cellb = _st("mcellb", fontName="Helvetica-Bold", fontSize=7.8, leading=9.6)
    cellr = _st("mcellr", fontSize=7.8, leading=9.6, alignment=TA_RIGHT)
    head = _st("mhead", fontName="Helvetica-Bold", fontSize=7.4, leading=9, textColor=colors.white)
    headr = _st(
        "mheadr",
        fontName="Helvetica-Bold",
        fontSize=7.4,
        leading=9,
        textColor=colors.white,
        alignment=TA_RIGHT,
    )
    h1 = _st("mh1", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=navy)
    sec = _st(
        "msec",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=teal,
        spaceBefore=8,
        spaceAfter=3,
    )
    lab = _st("mlab", fontName="Helvetica-Bold", fontSize=8, leading=10)

    def on_page(canvas, doc):  # type: ignore[no-untyped-def]
        canvas.saveState()
        w, h = doc.pagesize
        canvas.setFillColor(navy)
        canvas.rect(0, h - 15 * mm, w, 15 * mm, stroke=0, fill=1)
        canvas.setFillColor(teal)
        canvas.rect(0, h - 15.8 * mm, w, 0.8 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(18 * mm, h - 9.5 * mm, s.name.upper())
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(w - 18 * mm, h - 9.2 * mm, s.address.split(",")[0] + ", " + s.city)
        canvas.setFillColor(grey)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(
            18 * mm, 10 * mm, f"{s.name}  |  Reg. {s.registration}  |  export@{s.email_domain}"
        )
        canvas.drawRightString(w - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(path),
        invariant=1,
        encrypt=encrypt,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=22 * mm,
        bottomMargin=16 * mm,
        title=f"Quotation {q.quotation_ref} - {s.name}",
        author=s.name,
        subject=f"Supplier quotation in response to {q.buyer_reference}",
    )
    story: list[object] = []
    top = Table(
        [
            [
                _p("SUPPLIER QUOTATION", h1),
                [
                    Paragraph(
                        f"Quotation no. <b>{escape(q.quotation_ref)}</b>",
                        _st("r1", fontSize=8.5, alignment=TA_RIGHT, textColor=grey),
                    ),
                    Paragraph(
                        f"Issue date: <b>{q.document_date.strftime('%d %B %Y')}</b>",
                        _st("r2", fontSize=8.5, alignment=TA_RIGHT, textColor=grey),
                    ),
                    Paragraph(
                        f"Valid until: <b>{q.valid_until.strftime('%d %B %Y')}</b>",
                        _st("r3", fontSize=8.5, alignment=TA_RIGHT, textColor=grey),
                    ),
                ],
            ]
        ],
        colWidths=[110 * mm, 64 * mm],
    )
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [
        top,
        Spacer(1, 4 * mm),
        _p("In response to", sec),
        _p(
            f"Request for quotation {q.buyer_reference} issued by Axmed Ltd for delivery to {q.destination}.",
            body,
        ),
        Spacer(1, 3 * mm),
    ]
    if hidden_text:
        story.append(_hidden(hidden_text))
    info = Table(
        [
            [
                _p("Supplier", lab),
                _p(s.name, cell),
                _p("Buyer", lab),
                _p("Axmed Ltd (aggregation agent)", cell),
            ],
            [
                _p("Manufacturing site", lab),
                _p(s.address, cell),
                _p("Destination", lab),
                _p(q.destination, cell),
            ],
            [
                _p("Quality status", lab),
                _p(", ".join(s.quality), cell),
                _p("Currency", lab),
                _p(q.currency, cell),
            ],
            [
                _p("Contact", lab),
                _p(f"{s.contact_name}, {s.contact_title}, {s.phone}", cell),
                _p("Incoterms 2020", lab),
                _p(f"{q.incoterm} {q.named_place}", cell),
            ],
            [_p("", lab), _p("", cell), _p("Payment terms", lab), _p(q.payment_terms, cell)],
        ],
        colWidths=[28 * mm, 60 * mm, 28 * mm, 58 * mm],
    )
    info.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef3f8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story += [info, _p("Quoted line items", sec)]

    pack_only = "pack_price_only" in q.features
    cols: list[object] = [
        _p("#", head),
        _p("Product name", head),
        _p("INN (active moiety)", head),
        _p("Strength / form", head),
        _p("Pack", head),
        _p("UOM", head),
    ]
    widths = [6 * mm, 24 * mm, 30 * mm, 27 * mm, 25 * mm, 15 * mm]
    if not pack_only:
        cols.append(Paragraph(f"Unit price<br/>{q.currency} / UOM", headr))
        widths.append(16 * mm)
    cols += [
        Paragraph(f"Pack price<br/>{q.currency}", headr),
        Paragraph("MOQ<br/>packs", headr),
        Paragraph("Lead<br/>days", headr),
    ]
    widths += [16 * mm, 13 * mm, 9 * mm]
    rows: list[list[object]] = [cols]
    for ln in q.lines:
        row: list[object] = [
            _p(str(ln.line_no), cell),
            _p(ln.product_name, cellb),
            _p(ln.inn, cell),
            Paragraph(f"{escape(ln.strength)}<br/>{escape(ln.dosage_form)}", cell),
            Paragraph(
                f"{escape(ln.packaging)}<br/>{escape(plural(ln.units_per_pack, ln.uom))}/pack", cell
            ),
            _p(ln.uom, cell),
        ]
        if not pack_only:
            row.append(_p(_cur(_shown_unit(ln), q), cellr))
        row += [
            _p(_cur(_shown_pack(ln), q), cellr),
            _p(f"{ln.moq_packs:,}", cellr),
            _p(str(ln.lead_time_days), cellr),
        ]
        rows.append(row)
    tbl = Table(rows, colWidths=widths, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#c8d2dc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f9")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(tbl)
    story.append(
        _p(
            (
                "Pack price is the price per pack of the stated number of units; unit price is not quoted separately."
                if pack_only
                else "Unit price is the price per unit of measure (UOM) shown. Pack price is unit price multiplied by "
                "units per pack, provided for convenience; in case of discrepancy the unit price governs."
            ),
            small,
        )
    )

    story.append(_p("Regulatory and product information", sec))
    reg_rows: list[list[object]] = [
        [
            _p("#", head),
            _p("WHO PQ / SRA status", head),
            _p("Registered at destination", head),
            _p("Shelf life", head),
            _p("Storage", head),
        ]
    ]
    for ln in q.lines:
        pq = rng.choice(
            (
                "Not PQ; national registrations only",
                f"WHO PQ ref. {rng.choice('ABHMNRT')}{rng.choice('ABHMNRT')}{rng.randint(100, 999)}",
                "Not PQ; EU-GMP site",
            )
        )
        reg = rng.choice(("Yes", "Yes", "Application filed", "No - waiver requested"))
        reg_rows.append(
            [
                _p(str(ln.line_no), cell),
                _p(pq, cell),
                _p(reg, cell),
                _p(f"{rng.choice((24, 36))} months", cell),
                _p("2-8 C, do not freeze" if ln.cold_chain else "Below 30 C, dry", cell),
            ]
        )
    reg = Table(reg_rows, colWidths=[6 * mm, 60 * mm, 44 * mm, 22 * mm, 42 * mm], repeatRows=1)
    reg.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#c8d2dc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f9")]),
            ]
        )
    )
    story += [reg, _p("Terms and conditions", sec)]
    notes = list(q.notes)
    corr = _correction_note(q)
    if corr:
        notes.append(corr)
    for i, n in enumerate(notes, start=1):
        story.append(_p(f"{i}.  {n}", small))
    story += [Spacer(1, 6 * mm)]
    sign = Table(
        [
            [
                [
                    _p(f"For and on behalf of {s.name}", lab),
                    Spacer(1, 10 * mm),
                    _p("_______________________________", cell),
                    _p(s.contact_name, cell),
                    _p(s.contact_title, cell),
                    _p(q.document_date.strftime("%d %B %Y"), cell),
                ],
                [
                    _p("Bank details", lab),
                    _p(f"Beneficiary: {s.name}", cell),
                    _p(f"Bank: {s.bank_name}", cell),
                    _p(f"SWIFT: {s.swift}", cell),
                    _p(f"Account ({q.currency}): {s.account}", cell),
                ],
            ]
        ],
        colWidths=[87 * mm, 87 * mm],
    )
    sign.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef3f8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(sign)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


# --------------------------------------------------------------------------- letter style


def letter_style(
    q: Quotation,
    rng: random.Random,
    path: Path,
    hidden_text: str | None,
    encrypt: object | None = None,
) -> None:
    s = q.supplier
    ink = colors.HexColor("#1f1f1f")
    body = _st(
        "lbody", fontName="Times-Roman", fontSize=10.5, leading=14.5, textColor=ink, spaceAfter=6
    )
    small = _st(
        "lsmall",
        fontName="Times-Roman",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#555555"),
    )
    right = _st(
        "lright",
        fontName="Times-Roman",
        fontSize=9.5,
        leading=12,
        textColor=ink,
        alignment=TA_RIGHT,
    )
    bold = _st("lbold", fontName="Times-Bold", fontSize=10.5, leading=14.5, textColor=ink)

    def on_page(canvas, doc):  # type: ignore[no-untyped-def]
        canvas.saveState()
        canvas.setFont("Times-Roman", 7.5)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawCentredString(doc.pagesize[0] / 2, 12 * mm, f"{s.name} - {s.address}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(path),
        invariant=1,
        encrypt=encrypt,
        pagesize=A4,
        leftMargin=24 * mm,
        rightMargin=24 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title=f"Quotation {q.quotation_ref}",
        author=s.name,
    )
    story: list[object] = [
        Paragraph(
            f"<b>{escape(s.name)}</b>",
            _st("lco", fontName="Times-Bold", fontSize=13, leading=16, textColor=ink),
        ),
        _p(s.address, small),
        _p(f"{s.phone}  |  {s.contact_name.split()[0].lower()}@{s.email_domain}", small),
        Spacer(1, 8 * mm),
        _p(f"{s.city}, {q.document_date.strftime('%d %B %Y')}", right),
        _p(f"Our ref.: {q.quotation_ref}", right),
        _p(f"Your ref.: {q.buyer_reference}", right),
        Spacer(1, 6 * mm),
        _p("Axmed Ltd, Procurement", body),
        _p(f"Attn. {q.buyer_contact}", body),
        Spacer(1, 4 * mm),
        Paragraph(
            f"<b>Subject: Quotation for {len(q.lines)} products, {escape(q.incoterm)} {escape(q.named_place)}</b>",
            body,
        ),
        _p(f"Dear {q.buyer_contact.split()[0] if ' ' in q.buyer_contact else 'colleagues'},", body),
        _p(
            f"Thank you for your enquiry {q.buyer_reference}. We are pleased to quote as follows. All prices are in "
            f"{q.currency}, {q.incoterm} {q.named_place}, and remain valid until {q.valid_until.strftime('%d %B %Y')}. "
            f"Payment terms: {q.payment_terms.rstrip('.')}.",
            body,
        ),
    ]
    if hidden_text:
        story.append(_hidden(hidden_text))
    pack_only = "pack_price_only" in q.features
    for ln in q.lines:
        pack_txt = f"{ln.packaging.lower()} of {plural(ln.units_per_pack, ln.uom)}"
        if ln.price_tiers:
            tiers = "; ".join(
                f"{q.currency} {fmt_money(t.price_per_pack)} per pack for {t.min_packs:,}"
                + (f" to {t.max_packs:,}" if t.max_packs else " or more")
                + " packs"
                for t in ln.price_tiers
            )
            price_txt = f"Volume pricing applies: {tiers}."
        elif pack_only:
            price_txt = f"Price {q.currency} {fmt_money(_shown_pack(ln))} per pack."
        else:
            price_txt = (
                f"Price {q.currency} {fmt_money(_shown_unit(ln))} per {ln.uom}, "
                f"that is {q.currency} {fmt_money(_shown_pack(ln))} per pack."
            )
        story.append(
            Paragraph(
                f"<b>Item {ln.line_no}.</b> {escape(ln.product_name)} ({escape(ln.inn)} {escape(ln.strength)}, "
                f"{escape(ln.dosage_form.lower())}), supplied as {escape(pack_txt)}. {escape(price_txt)} "
                f"Minimum order {ln.moq_packs:,} packs, lead time {escape(_lead(ln, q))} from order confirmation."
                + (" Cold chain item, shipped at 2-8 C." if ln.cold_chain else ""),
                body,
            )
        )
    for n in q.notes:
        story.append(_p(n, body))
    story += [
        _p(
            "We look forward to your order and remain at your disposal for any clarification.", body
        ),
        Spacer(1, 4 * mm),
        _p("Yours sincerely,", body),
        Spacer(1, 10 * mm),
        _p(s.contact_name, bold),
        _p(s.contact_title, body),
    ]
    corr = _correction_note(q)
    if corr:
        story += [Spacer(1, 6 * mm), Paragraph(f"<b>P.S.</b> {escape(corr)}", body)]
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


LAYOUTS: dict[str, Layout] = {
    "classic_proforma": classic_proforma,
    "modern_quote": modern_quote,
    "letter_style": letter_style,
}


def write_pdf(
    q: Quotation,
    rng: random.Random,
    layout: str,
    path: Path,
    *,
    hidden_text: str | None = None,
    encrypt: object | None = None,
) -> None:
    LAYOUTS[layout](q, rng, path, hidden_text, encrypt)
