"""Email quotations: prose, tables, threads, attachments and a hidden-HTML hostile variant."""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.policy import default as default_policy
from email.utils import format_datetime
from html import escape
from pathlib import Path

from evals.synth import vocab
from evals.synth.truth import Line, Quotation, fmt_money, plural

Variant = Callable[[Quotation, random.Random, Path, Path | None, str | None], None]


def _shown_unit(line: Line) -> float:
    if line.superseded and line.superseded.field == "price_per_uom":
        return line.superseded.old
    return line.price_per_uom


def _shown_pack(line: Line) -> float:
    if line.superseded and line.superseded.field == "price_per_pack":
        return line.superseded.old
    return line.price_per_pack


def _sender(q: Quotation) -> tuple[str, str]:
    s = q.supplier
    first, last = s.contact_name.split()[0], s.contact_name.split()[-1]
    return s.contact_name, f"{first.lower()}.{last.lower()}@{s.email_domain}"


def _signature(q: Quotation) -> str:
    s = q.supplier
    _, email = _sender(q)
    return f"{s.contact_name}\n{s.contact_title} | {s.name}\n{s.address}\nT {s.phone}\n{email}"


def _lead(ln: Line, q: Quotation) -> str:
    d = ln.lead_time_days or 0
    return f"{d // 7} weeks" if "lead_time_weeks" in q.features else f"{d} days"


def _price_sentence(ln: Line, q: Quotation) -> str:
    cur = q.currency
    if ln.price_tiers:
        parts = [
            f"{fmt_money(t.price_per_pack)} per pack for {t.min_packs:,}"
            + (f"-{t.max_packs:,}" if t.max_packs else "+")
            + " packs"
            for t in ln.price_tiers
        ]
        return f"Price ({cur}): " + "; ".join(parts)
    if "pack_price_only" in q.features:
        return f"Price: {cur} {fmt_money(_shown_pack(ln))} per pack of {ln.units_per_pack}"
    return f"Price: {fmt_money(_shown_unit(ln))} per {ln.uom}"


def _ps_correction(q: Quotation) -> str | None:
    for ln in q.lines:
        if ln.superseded:
            c = ln.superseded
            what = f"per {ln.uom}" if c.field == "price_per_uom" else "per pack"
            return (
                f"Correction on line {ln.line_no} - I quoted you last quarter's price. {ln.product_name} is "
                f"{fmt_money(c.new)} {what} as of this month's list, not {fmt_money(c.old)}. Sorry about that. "
                f"The other lines are unchanged."
            )
    return None


def _headers(
    msg: EmailMessage, q: Quotation, rng: random.Random, subject: str, *, reply: bool = True
) -> None:
    name, email = _sender(q)
    tz = timezone(timedelta(hours=vocab.COUNTRY_TZ_HOURS.get(q.supplier.country, 0)))
    sent = datetime(
        q.document_date.year,
        q.document_date.month,
        q.document_date.day,
        rng.randint(8, 18),
        rng.randint(0, 59),
        tzinfo=tz,
    )
    msg["From"] = f"{name} <{email}>"
    msg["To"] = "procurement@axmed.com"
    msg["Cc"] = (
        f"{q.buyer_contact} <{q.buyer_contact.split()[0].lower()}@axmed.com>"
        if " " in q.buyer_contact
        else "procurement@axmed.com"
    )
    msg["Subject"] = subject
    msg["Date"] = format_datetime(sent)
    msg["Message-ID"] = (
        f"<{rng.getrandbits(64):016x}.{rng.getrandbits(32):08x}@{q.supplier.email_domain}>"
    )
    if reply:
        parent = f"<{q.buyer_reference.lower()}.{rng.getrandbits(32):08x}@mail.axmed.com>"
        msg["In-Reply-To"] = parent
        msg["References"] = parent
    msg["X-Mailer"] = rng.choice(
        ("Microsoft Outlook 16.0", "Apple Mail (2.3774.600.62)", "Zimbra 10.0.6")
    )
    msg["MIME-Version"] = "1.0"


def _html_table(q: Quotation) -> str:
    pack_only = "pack_price_only" in q.features
    head = ["#", "Product", "INN / strength", "Pack", "Price", "MOQ", "Lead time"]
    rows = []
    for ln in q.lines:
        if ln.price_tiers:
            price = "<br>".join(
                f"{fmt_money(t.price_per_pack)} per pack from {t.min_packs:,} packs"
                for t in ln.price_tiers
            )
        elif pack_only:
            price = f"{fmt_money(_shown_pack(ln))} per pack of {ln.units_per_pack}"
        else:
            price = f"{fmt_money(_shown_unit(ln))} per {escape(ln.uom)}"
        rows.append(
            "<tr>"
            + "".join(
                f'<td style="border:1px solid #c3ccd8;padding:6px">{c}</td>'
                for c in (
                    ln.line_no,
                    escape(ln.product_name),
                    f"{escape(ln.inn)} {escape(ln.strength)}, {escape(ln.dosage_form.lower())}",
                    f"{escape(ln.packaging)}, {escape(plural(ln.units_per_pack, ln.uom))}",
                    price,
                    f"{ln.moq_packs:,} packs",
                    escape(_lead(ln, q)),
                )
            )
            + "</tr>"
        )
    th = "".join(
        f'<th align="left" style="border:1px solid #c3ccd8;padding:6px">{h}</th>' for h in head
    )
    return (
        f'<table cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:10.5pt">'
        f'<tr style="background:#eef2f7">{th}</tr>{"".join(rows)}</table>'
    )


def _pin_boundary(msg: EmailMessage, rng: random.Random) -> None:
    """The stdlib picks a random boundary at serialisation time; pin it to the seed."""
    msg.set_boundary(f"================{rng.getrandbits(62):020d}==")


def _write(msg: EmailMessage, path: Path) -> None:
    path.write_bytes(msg.as_bytes(policy=default_policy))


def plain_numbered_ps(
    q: Quotation, rng: random.Random, path: Path, attachment: Path | None, hidden_html: str | None
) -> None:
    """Numbered items in prose, HTML alternative with a table, correction in a P.S."""
    s = q.supplier
    first = q.buyer_contact.split()[0] if " " in q.buyer_contact else "all"
    lines = []
    for ln in q.lines:
        lines.append(
            f"{ln.line_no}) {ln.product_name} ({ln.inn.lower()} {ln.strength} {ln.dosage_form.lower()})\n"
            f"   Pack: {ln.packaging.lower()} of {plural(ln.units_per_pack, ln.uom)}\n"
            f"   {_price_sentence(ln, q)}\n"
            f"   MOQ: {ln.moq_packs:,} packs, lead time {_lead(ln, q)}"
            + ("\n   Cold chain, 2-8 C" if ln.cold_chain else "")
        )
    ps = _ps_correction(q)
    text = (
        f"Dear {first},\n\n"
        f"Thank you for {q.buyer_reference} and apologies for the slight delay. Please find our indicative offer "
        f"below for the {len(q.lines)} lines you asked about. All prices are in {q.currency}, {q.incoterm} "
        f"{q.named_place}, and hold until {q.valid_until.strftime('%d %B %Y')}.\n\n"
        + "\n\n".join(lines)
        + "\n\n"
        f"{q.payment_terms.rstrip('.')}. {' '.join(q.notes[:2])}\n\n"
        f"Happy to jump on a call if useful.\n\nBest regards,\n\n{_signature(q)}\n"
        + (f"\nP.S. {ps}\n" if ps else "")
    )
    html_body = (
        f'<html><body style="font-family:Calibri,Arial,sans-serif;font-size:11pt;color:#1f1f1f">'
        f"<p>Dear {escape(first)},</p>"
        f"<p>Thank you for {escape(q.buyer_reference)} and apologies for the slight delay. Please find our indicative "
        f"offer below. <b>All prices are in {escape(q.currency)}, {escape(q.incoterm)} {escape(q.named_place)}</b>, and hold until "
        f"{q.valid_until.strftime('%d %B %Y')}.</p>{_html_table(q)}"
        f'<p style="font-size:10pt;color:#555">{escape(q.payment_terms)} {escape(" ".join(q.notes[:2]))}</p>'
        f"<p>Happy to jump on a call if useful.</p><p>Best regards,</p>"
        f'<p style="font-size:10pt">{escape(_signature(q)).replace(chr(10), "<br>")}</p>'
        + (f"<p><b>P.S.</b> {escape(ps)}</p>" if ps else "")
        + (hidden_html or "")
        + "</body></html>"
    )
    msg = EmailMessage()
    _headers(
        msg,
        q,
        rng,
        f"RE: {q.buyer_reference} - {s.short} quotation ({len(q.lines)} lines, {q.currency} {q.incoterm})",
    )
    msg.set_content(text)
    msg.add_alternative(html_body, subtype="html")
    _pin_boundary(msg, rng)
    _write(msg, path)


def html_table_only(
    q: Quotation, rng: random.Random, path: Path, attachment: Path | None, hidden_html: str | None
) -> None:
    """The figures exist only in the HTML part. The plain part just points at it."""
    s = q.supplier
    first = q.buyer_contact.split()[0] if " " in q.buyer_contact else "all"
    text = (
        f"Dear {first},\n\nPlease see our quotation table below (this message is best viewed in HTML).\n\n"
        f"Regards,\n{s.contact_name}\n"
    )
    html_body = (
        f'<html><body style="font-family:Arial,sans-serif;font-size:10.5pt;color:#222">'
        f"<p>Dear {escape(first)},</p>"
        f"<p>Further to {escape(q.buyer_reference)}, our offer ref. <b>{escape(q.quotation_ref)}</b> dated "
        f"{q.document_date.strftime('%d/%m/%Y')}, valid to {q.valid_until.strftime('%d/%m/%Y')}. Currency "
        f"<b>{escape(q.currency)}</b>, delivery <b>{escape(q.incoterm)} {escape(q.named_place)}</b>, "
        f"payment {escape(q.payment_terms.lower())}.</p>"
        f"{_html_table(q)}"
        f'<p style="font-size:9.5pt;color:#555">{escape(" ".join(q.notes))}</p>'
        f"<p>Regards,<br>{escape(s.contact_name)}<br>{escape(s.contact_title)}, {escape(s.name)}</p>"
        + (hidden_html or "")
        + "</body></html>"
    )
    msg = EmailMessage()
    _headers(msg, q, rng, f"Quotation {q.quotation_ref} / {q.buyer_reference}")
    msg.set_content(text)
    msg.add_alternative(html_body, subtype="html")
    _pin_boundary(msg, rng)
    _write(msg, path)


def thread_prose(
    q: Quotation, rng: random.Random, path: Path, attachment: Path | None, hidden_html: str | None
) -> None:
    """Plain-text reply with prices in running prose, an inline revision, and the quoted RFQ below."""
    s = q.supplier
    first = q.buyer_contact.split()[0] if " " in q.buyer_contact else "there"
    sentences = []
    for ln in q.lines:
        if ln.price_tiers:
            price = (
                f"we can do {q.currency} {fmt_money(ln.price_tiers[0].price_per_pack)} per pack up to "
                f"{ln.price_tiers[0].max_packs:,} packs, dropping to {fmt_money(ln.price_tiers[-1].price_per_pack)} "
                f"from {ln.price_tiers[-1].min_packs:,} packs"
            )
        elif "pack_price_only" in q.features:
            price = f"we can do {q.currency} {fmt_money(_shown_pack(ln))} per pack of {ln.units_per_pack}"
        else:
            price = f"we can do {q.currency} {fmt_money(_shown_unit(ln))} per {ln.uom}"
        sent = (
            f"On {ln.inn} {ln.strength} ({ln.product_name}, {ln.dosage_form.lower()}, {ln.packaging.lower()} "
            f"of {ln.units_per_pack}) {price}, MOQ {ln.moq_packs:,} packs, {_lead(ln, q)} lead time."
        )
        if ln.superseded:
            c = ln.superseded
            what = f"per {ln.uom}" if c.field == "price_per_uom" else "per pack"
            sent += (
                f" Actually, having checked with production this morning, make that {fmt_money(c.new)} "
                f"{what} - the {fmt_money(c.old)} figure was the old list."
            )
        sentences.append(sent)
    rfq_date = q.document_date - timedelta(days=rng.randint(2, 9))
    quoted = (
        f"> From: {q.buyer_contact} <procurement@axmed.com>\n"
        f"> Sent: {rfq_date.strftime('%A, %d %B %Y')}\n"
        f"> Subject: {q.buyer_reference} - request for quotation\n>\n"
        f"> Dear {s.contact_name.split()[0]},\n>\n"
        f"> Could you quote the following for delivery to {q.destination}, {q.incoterm} preferred?\n"
        + "".join(f"> - {ln.inn} {ln.strength} {ln.dosage_form.lower()}\n" for ln in q.lines)
        + f">\n> Validity 60 days please. Many thanks,\n> {q.buyer_contact}\n"
    )
    text = (
        f"Hi {first},\n\n"
        f"Thanks for the enquiry. Quick answer below, formal document to follow. Everything {q.incoterm} "
        f"{q.named_place} in {q.currency}, good until {q.valid_until.strftime('%d %B')}.\n\n"
        + "\n\n".join(sentences)
        + "\n\n"
        f"{q.payment_terms}. {q.notes[0]}\n\nBest,\n{s.contact_name.split()[0]}\n\n{_signature(q)}\n\n"
        f"On {rfq_date.strftime('%d %b %Y')}, {q.buyer_contact} wrote:\n\n{quoted}"
    )
    msg = EmailMessage()
    _headers(msg, q, rng, f"Re: {q.buyer_reference} - request for quotation")
    msg.set_content(text)
    _write(msg, path)


def with_attachment(
    q: Quotation, rng: random.Random, path: Path, attachment: Path | None, hidden_html: str | None
) -> None:
    """Short cover note; the quotation is a PDF attachment."""
    if attachment is None:
        raise ValueError("with_attachment needs an attachment path")
    s = q.supplier
    first = q.buyer_contact.split()[0] if " " in q.buyer_contact else "all"
    text = (
        f"Dear {first},\n\nPlease find attached our quotation {q.quotation_ref} against {q.buyer_reference}, "
        f"covering {len(q.lines)} lines, {q.incoterm} {q.named_place}. Prices are in {q.currency} and valid to "
        f"{q.valid_until.strftime('%d %B %Y')}.\n\nDo let me know if you need samples or registration dossiers.\n\n"
        f"Kind regards,\n\n{_signature(q)}\n"
    )
    msg = EmailMessage()
    _headers(msg, q, rng, f"{s.short} quotation {q.quotation_ref} - {q.buyer_reference}")
    msg.set_content(text)
    msg.add_attachment(
        attachment.read_bytes(), maintype="application", subtype="pdf", filename=attachment.name
    )
    _pin_boundary(msg, rng)
    _write(msg, path)


VARIANTS: dict[str, Variant] = {
    "plain_numbered_ps": plain_numbered_ps,
    "html_table_only": html_table_only,
    "thread_prose": thread_prose,
    "with_attachment": with_attachment,
}


def write_eml(
    q: Quotation,
    rng: random.Random,
    variant: str,
    path: Path,
    *,
    attachment: Path | None = None,
    hidden_html: str | None = None,
) -> None:
    VARIANTS[variant](q, rng, path, attachment, hidden_html)
