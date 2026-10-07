"""WhatsApp chat export: a negotiation thread where the figures live in messages.

Format follows the "Export chat" text file WhatsApp produces, including the
media placeholder and the buyer's own messages interleaved with the supplier's.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
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


def _price_msg(ln: Line, q: Quotation) -> str:
    if ln.price_tiers:
        t0, t_last = ln.price_tiers[0], ln.price_tiers[-1]
        return (
            f"{ln.product_name} ({ln.inn} {ln.strength}) {q.currency} {fmt_money(t0.price_per_pack)} "
            f"per pack of {ln.units_per_pack} up to {t0.max_packs:,} packs, "
            f"{fmt_money(t_last.price_per_pack)} from {t_last.min_packs:,} packs"
        )
    if "pack_price_only" in q.features:
        return (
            f"{ln.product_name} ({ln.inn} {ln.strength}, {ln.dosage_form.lower()}) "
            f"{q.currency} {fmt_money(_shown_pack(ln))} per pack of {plural(ln.units_per_pack, ln.uom)}"
        )
    return (
        f"{ln.product_name} ({ln.inn} {ln.strength}, {ln.dosage_form.lower()}) "
        f"{q.currency} {fmt_money(_shown_unit(ln))}/{ln.uom}, pack of {ln.units_per_pack}"
    )


def write_whatsapp(q: Quotation, rng: random.Random, path: Path) -> None:
    s = q.supplier
    supplier_name = s.contact_name
    buyer = q.buyer_contact if " " in q.buyer_contact else "Axmed Procurement"
    buyer_first = buyer.split()[0]
    t = datetime(
        q.document_date.year,
        q.document_date.month,
        q.document_date.day,
        rng.randint(9, 15),
        rng.randint(0, 59),
    )

    def stamp() -> str:
        nonlocal t
        t += timedelta(minutes=rng.randint(1, 14), seconds=rng.randint(0, 59))
        return t.strftime("[%d/%m/%Y, %H:%M:%S]")

    lines: list[str] = []

    def say(who: str, text: str) -> None:
        lines.append(f"{stamp()} {who}: {text}")

    lines.append(
        f"{t.strftime('[%d/%m/%Y, %H:%M:%S]')} Messages and calls are end-to-end encrypted. "
        "No one outside of this chat, not even WhatsApp, can read or listen to them."
    )
    say(
        buyer,
        f"Hi {supplier_name.split()[0]}, following up on {q.buyer_reference}. Any news on pricing?",
    )
    say(supplier_name, f"Hi {buyer_first}, yes just got sign off. Sending now 👍")
    say(
        supplier_name,
        f"All {q.currency}, {q.incoterm} {q.named_place}. Valid to {q.valid_until.strftime('%d %b')}.",
    )
    for ln in q.lines:
        say(supplier_name, _price_msg(ln, q))
        if rng.random() < 0.5:
            say(supplier_name, f"MOQ {ln.moq_packs:,} packs, lead time {ln.lead_time_days} days")
    if rng.random() < 0.6:
        say(supplier_name, "<Media omitted>")
        say(supplier_name, "That's the CoA for the last batch fyi")
    corrected = [ln for ln in q.lines if ln.superseded]
    if corrected:
        ln = corrected[0]
        c = ln.superseded
        assert c is not None
        what = f"per {ln.uom}" if c.field == "price_per_uom" else "per pack"
        if c.new < c.old:
            say(
                buyer,
                f"Thanks. {ln.product_name} looks high vs what we had last quarter, any room?",
            )
            say(supplier_name, "Let me check with the plant")
            t += timedelta(hours=rng.randint(1, 3))
            say(
                supplier_name,
                f"Ok {buyer_first} we can do {fmt_money(c.new)} {what} on {ln.product_name}. "
                f"Forget the {fmt_money(c.old)}",
            )
            say(buyer, "Great, appreciated")
        else:
            say(buyer, "Thanks, that's clear")
            t += timedelta(hours=rng.randint(1, 3))
            say(
                supplier_name,
                f"Sorry {buyer_first}, one correction. {ln.product_name} should be {fmt_money(c.new)} "
                f"{what}, not {fmt_money(c.old)}. The {fmt_money(c.old)} was last quarter's list",
            )
            say(buyer, "Noted, thanks for flagging")
    else:
        say(buyer, "Thanks, that's clear")
    say(buyer, f"Payment terms as before? {q.payment_terms.rstrip('.')}?")
    say(supplier_name, "Yes same terms")
    if q.alt_price_note:
        say(supplier_name, q.alt_price_note)
    say(supplier_name, f"Formal quotation {q.quotation_ref} to follow by email tomorrow")
    say(buyer, "Perfect, thanks 🙏")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
