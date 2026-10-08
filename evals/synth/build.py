"""Build the synthetic set: truth first, then every rendering, then a manifest.

uv run python -m evals.synth.build --out data/synthetic --seed 2026
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from reportlab.lib.pdfencrypt import StandardEncryption

from evals.synth import hostile, vocab
from evals.synth.render_chat import write_whatsapp
from evals.synth.render_eml import write_eml
from evals.synth.render_image import write_image
from evals.synth.render_json import write_json
from evals.synth.render_markup import write_html, write_txt, write_xml
from evals.synth.render_office import write_csv, write_docx, write_xlsx
from evals.synth.render_pdf import write_pdf
from evals.synth.render_scan import write_scanned_pdf
from evals.synth.truth import Quotation, make_quotation

GENERATOR_VERSION = "1"


@dataclass(frozen=True)
class Case:
    id: str
    kind: str
    variant: str
    supplier: str = ""
    features: tuple[str, ...] = ()
    n_lines: int | None = None
    source: str | None = None
    hostile: str | None = None
    expect: str = "extract"
    note: str = ""


CASES: tuple[Case, ...] = (
    # JSON: six dialects, nothing in common but the facts
    Case("json_erp_nested_01", "json", "erp_nested", "meridian", ("pack_price_only", "cold_chain")),
    Case(
        "json_erp_nested_02",
        "json",
        "erp_nested",
        "nilgiri",
        ("pack_price_only", "distractor_alt_price", "inn_variant"),
    ),
    Case("json_flat_lines_01", "json", "flat_lines", "yuantai"),
    Case(
        "json_flat_lines_02",
        "json",
        "flat_lines",
        "indus",
        ("long", "inn_variant", "strength_variant"),
    ),
    Case("json_catalogue_tiers_01", "json", "catalogue_tiers", "highveld", ("tiered", "vat_note")),
    Case("json_catalogue_tiers_02", "json", "catalogue_tiers", "baobab", ("tiered", "mixed_uom")),
    Case("json_camel_api_01", "json", "camel_api", "dongnai", ("cold_chain",)),
    Case("json_camel_api_02", "json", "camel_api", "amman", ("pack_price_only", "lead_time_weeks")),
    Case(
        "json_attribute_list_01",
        "json",
        "attribute_list",
        "anatolia",
        ("symbol_currency", "lead_time_weeks"),
    ),
    Case(
        "json_attribute_list_02",
        "json",
        "attribute_list",
        "helvetia",
        ("pack_price_only", "strength_variant"),
    ),
    Case("json_table_dump_01", "json", "table_dump", "jiangnan", ("inn_variant",)),
    Case("json_table_dump_02", "json", "table_dump", "dhaka", ("pack_price_only", "mixed_uom")),
    Case(
        "json_erp_fr_01",
        "json",
        "erp_fr",
        "atlas",
        ("pack_price_only",),
        note="Every key in French. No field map can anticipate this.",
    ),
    # PDF: three layouts
    Case(
        "pdf_classic_01", "pdf", "classic_proforma", "pacifico", ("quantity_extended", "discount")
    ),
    Case(
        "pdf_classic_02",
        "pdf",
        "classic_proforma",
        "kaveri",
        ("quantity_extended", "discount", "correction", "inn_variant"),
    ),
    Case("pdf_classic_03", "pdf", "classic_proforma", "lagosbio", ("long", "quantity_extended")),
    Case("pdf_modern_01", "pdf", "modern_quote", "dongnai", ("cold_chain", "mixed_uom")),
    Case(
        "pdf_modern_02",
        "pdf",
        "modern_quote",
        "meridian",
        ("pack_price_only", "distractor_alt_price"),
    ),
    Case(
        "pdf_modern_03",
        "pdf",
        "modern_quote",
        "highveld",
        ("vat_note", "inn_variant", "correction"),
    ),
    Case("pdf_letter_01", "pdf", "letter_style", "deltafarm", ("correction", "lead_time_weeks")),
    Case("pdf_letter_02", "pdf", "letter_style", "helvetia", ("pack_price_only",)),
    Case("pdf_letter_03", "pdf", "letter_style", "baobab", ("tiered",)),
    Case(
        "pdf_modern_04",
        "pdf",
        "modern_quote",
        "amman",
        ("expired",),
        expect="extract_and_flag",
        note="Issued last year, validity long past. Values are right; the record must be flagged expired.",
    ),
    # Images derived from the PDFs above, so truth is shared and cross-checkable
    Case("img_fax_01", "image", "fax", source="pdf_classic_01"),
    Case("img_photo_01", "image", "photo", source="pdf_modern_01"),
    Case(
        "img_crop_01",
        "image",
        "crop",
        source="pdf_classic_02",
        expect="partial",
        note="Only part of the page is captured; some lines are legitimately missing.",
    ),
    Case(
        "img_heavy_01",
        "image",
        "heavy",
        source="pdf_letter_01",
        expect="low_confidence",
        note="Mostly unreadable by design. Correct behaviour is low confidence, not confident values.",
    ),
    Case("img_fax_02", "image", "fax", source="pdf_modern_02"),
    Case("img_photo_02", "image", "photo", source="pdf_classic_03"),
    Case("img_crop_02", "image", "crop", source="pdf_modern_03", expect="partial"),
    Case(
        "img_glare_wipe_01",
        "image",
        "glare_wipe",
        source="pdf_classic_02",
        expect="partial",
        note="A reflection wipes a band through the table, like the provided scan_03. "
        "Lines under the band are unreadable; the correct result omits or flags them.",
    ),
    Case("img_glare_wipe_02", "image", "glare_wipe", source="pdf_modern_03", expect="partial"),
    Case(
        "img_rotated_01",
        "image",
        "rotated",
        source="pdf_letter_03",
        note="Portrait page scanned on its side. Orientation must be handled, not guessed around.",
    ),
    # Scanned PDFs: image-only, or with the garbage OCR layer scanners add
    Case(
        "pdf_scanned_image_only_01",
        "scanned_pdf",
        "image_only",
        source="pdf_classic_01",
        note="No text layer at all. Must route to the vision path.",
    ),
    Case(
        "pdf_scanned_garbled_layer_01",
        "scanned_pdf",
        "garbled_layer",
        source="pdf_modern_01",
        expect="extract_and_flag",
        note="Invisible OCR layer full of substitutions. Trusting it yields confident garbage.",
    ),
    Case(
        "pdf_scanned_garbled_layer_02",
        "scanned_pdf",
        "garbled_layer",
        source="pdf_letter_02",
        expect="extract_and_flag",
    ),
    Case(
        "pdf_scanned_cover_sheet_01",
        "scanned_pdf",
        "cover_sheet",
        source="pdf_classic_01",
        note="Fax cover page first, then the quotation. The cover page must yield no lines.",
    ),
    # Email
    Case("eml_plain_ps_01", "eml", "plain_numbered_ps", "lowlands", ("correction",)),
    Case("eml_html_table_01", "eml", "html_table_only", "nilevalley"),
    Case("eml_thread_prose_01", "eml", "thread_prose", "baobab", ("correction", "lead_time_weeks")),
    Case("eml_thread_prose_02", "eml", "thread_prose", "pacifico", ("pack_price_only",)),
    Case(
        "eml_thread_prose_03",
        "eml",
        "thread_prose",
        "dhaka",
        ("distractor_rfq_prices",),
        note="The quoted RFQ below the reply carries the buyer's target prices. They are not the quote.",
    ),
    Case(
        "eml_plain_ps_02",
        "eml",
        "plain_numbered_ps",
        "helvetia",
        ("ambiguous_price_basis", "pack_price_only"),
        expect="extract_and_flag",
        note="Prices stated with no unit. Per pack or per tablet is ambiguous and must be flagged.",
    ),
    Case(
        "eml_attachment_01",
        "eml",
        "with_attachment",
        "amman",
        ("cold_chain",),
        note="Figures live in the attached PDF, not the body.",
    ),
    # Chat exports: the negotiation is the document
    Case(
        "chat_whatsapp_01",
        "chat",
        "whatsapp",
        "meridian",
        ("correction", "pack_price_only"),
        note="WhatsApp export. Prices in messages, one revised mid-thread after the buyer pushes back.",
    ),
    Case(
        "chat_whatsapp_02",
        "chat",
        "whatsapp",
        "baobab",
        ("tiered", "distractor_alt_price", "inn_variant"),
    ),
    # Markup and text: the generic path must absorb these with no code per format
    Case("xml_export_01", "xml", "erp_xml", "jiangnan", ("correction",)),
    Case(
        "html_portal_01",
        "html",
        "portal_page",
        "nilgiri",
        ("tiered",),
        note="Saved supplier-portal page with navigation chrome around the table.",
    ),
    Case(
        "txt_fixed_width_01",
        "txt",
        "fixed_width",
        "indus",
        ("inn_variant",),
        note="Fixed-width ERP print-out.",
    ),
    # Office formats
    Case(
        "xlsx_pricelist_03",
        "xlsx",
        "pricelist",
        "meridian",
        ("long", "mixed_uom"),
        n_lines=40,
        note="Forty lines. Tests chunking and that nothing is dropped from a long table.",
    ),
    Case("xlsx_pricelist_01", "xlsx", "pricelist", "highveld", ("tiered", "vat_note")),
    Case("xlsx_pricelist_02", "xlsx", "pricelist", "kaveri", ("correction",)),
    Case("docx_letter_01", "docx", "letter", "deltafarm", ("pack_price_only",)),
    Case("csv_standard_01", "csv", "standard", "yuantai"),
    Case(
        "csv_eu_01",
        "csv",
        "eu",
        "anatolia",
        note="Semicolon separated, comma decimals, German headers.",
    ),
    # Hostile: ordinary truth, planted instructions
    Case(
        "hostile_json_visible",
        "json",
        "flat_lines",
        "indus",
        hostile="price_override",
        expect="extract_and_flag",
    ),
    Case(
        "hostile_json_comment",
        "json",
        "camel_api",
        "dhaka",
        hostile="role_swap",
        expect="extract_and_flag",
    ),
    Case(
        "hostile_pdf_white",
        "pdf",
        "classic_proforma",
        "lowlands",
        ("quantity_extended",),
        hostile="polite",
        expect="extract_and_flag",
        note="Injection is white 1pt text in the text layer.",
    ),
    Case(
        "hostile_eml_hidden",
        "eml",
        "plain_numbered_ps",
        "nilevalley",
        hostile="exfil",
        expect="extract_and_flag",
        note="Injection is in a display:none div in the HTML part.",
    ),
    # Malformed: arrived, but cannot be read as sent
    Case(
        "malformed_empty_file",
        "malformed",
        "empty",
        expect="unsupported",
        note="Zero bytes. Reason: empty.",
    ),
    Case(
        "malformed_pdf_truncated",
        "malformed",
        "pdf_truncated",
        source="pdf_classic_03",
        expect="malformed",
        note="First 55% of the bytes of a three-page PDF. Pages that survive may be read, flagged truncated.",
    ),
    Case(
        "malformed_pdf_encrypted",
        "malformed",
        "pdf_encrypted",
        source="pdf_modern_02",
        expect="unsupported",
        note="128-bit standard encryption with a user password. Reason: encrypted. No attempt to open it.",
    ),
    Case(
        "malformed_json_broken",
        "malformed",
        "json_broken",
        source="json_camel_api_01",
        expect="malformed",
        note="Trailing comma and a stray control character. Lenient parse, flagged, or read as text.",
    ),
    # Wrong extensions and genuinely unsupported bytes
    Case(
        "misnamed_json_as_txt",
        "misnamed",
        ".txt",
        source="json_flat_lines_01",
        note="JSON content with a .txt extension. Content sniffing should still load it.",
    ),
    Case(
        "misnamed_pdf_as_dat",
        "misnamed",
        ".dat",
        source="pdf_modern_01",
        note="PDF bytes with a .dat extension.",
    ),
    Case(
        "unsupported_noise_bin",
        "unsupported",
        "noise",
        expect="unsupported",
        note="Random bytes. Must produce an unsupported record, not a crash and not a guess.",
    ),
)


def _slug(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in text)


def _doc_name(case: Case, q: Quotation) -> str:
    s = q.supplier
    short = _slug(s.short.lower().replace(" ", "_"))
    ref = _slug(q.quotation_ref)
    date = q.document_date.isoformat()
    return {
        "json": f"{short}_export_{date}.json",
        "pdf": f"{short}_quotation_{ref}.pdf",
        "eml": f"RE_{q.buyer_reference}_{short}_quotation.eml",
        "xlsx": f"{short}_price_list_{date}.xlsx",
        "docx": f"{short}_quotation_{ref}.docx",
        "csv": f"{short}_export_{date}.csv",
        "chat": f"WhatsApp Chat with {q.supplier.contact_name}.txt",
        "xml": f"{short}_quotation_{ref}.xml",
        "html": f"Quotation {ref} _ {q.supplier.short} Supplier Portal.html",
        "txt": f"{short}_QUOT_{ref}.txt",
    }[case.kind]


def _truth_payload(case: Case, q: Quotation, files: list[str]) -> dict[str, Any]:
    return {
        "case_id": case.id,
        "kind": case.kind,
        "variant": case.variant,
        "expect": case.expect,
        "hostile": case.hostile,
        "source_case": case.source,
        "files": files,
        "quotation": q.to_dict(),
    }


def build(out: Path, seed: int) -> dict[str, Any]:
    pool = list(vocab.PRODUCTS)
    if out.exists():
        for child in out.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
    out.mkdir(parents=True, exist_ok=True)
    scratch = out / "_tmp"
    scratch.mkdir(exist_ok=True)

    built: dict[str, dict[str, Any]] = {}
    quotations: dict[str, Quotation] = {}
    manifest_cases: list[dict[str, Any]] = []
    seq = 100

    for case in CASES:
        rng = random.Random(f"{seed}/{case.id}")
        case_dir = out / case.id
        case_dir.mkdir()
        files: list[str] = []
        q: Quotation | None = None

        if case.kind in ("json", "pdf", "eml", "xlsx", "docx", "csv", "chat", "xml", "html", "txt"):
            seq += 1
            supplier = vocab.SUPPLIER_BY_KEY[case.supplier]
            q = make_quotation(
                rng, supplier, pool, set(case.features), n_lines=case.n_lines, seq=seq
            )
            name = _doc_name(case, q)
            target = case_dir / name
            payload = hostile.INJECTIONS[case.hostile] if case.hostile else None
            if case.kind == "json":
                extra: dict[str, Any] | None = None
                if payload:
                    extra = (
                        {"notes": [*q.notes, payload]}
                        if case.variant == "flat_lines"
                        else {"_comment": payload}
                    )
                write_json(q, rng, case.variant, target, extra=extra)
            elif case.kind == "pdf":
                write_pdf(q, rng, case.variant, target, hidden_text=payload)
            elif case.kind == "eml":
                attachment = None
                if case.variant == "with_attachment":
                    attachment = (
                        scratch
                        / f"{_slug(q.supplier.short.lower())}_quotation_{_slug(q.quotation_ref)}.pdf"
                    )
                    write_pdf(q, rng, "modern_quote", attachment)
                hidden = hostile.HIDDEN_HTML_DIV.format(payload=payload) if payload else None
                write_eml(q, rng, case.variant, target, attachment=attachment, hidden_html=hidden)
            elif case.kind == "xlsx":
                write_xlsx(q, rng, target)
            elif case.kind == "docx":
                write_docx(q, rng, target)
            elif case.kind == "csv":
                write_csv(q, rng, target, style=case.variant)
            elif case.kind == "chat":
                write_whatsapp(q, rng, target)
            elif case.kind == "xml":
                write_xml(q, rng, target)
            elif case.kind == "html":
                write_html(q, rng, target)
            elif case.kind == "txt":
                write_txt(q, rng, target)
            files.append(name)

        elif case.kind == "image":
            src = built[case.source or ""]
            src_pdf = out / src["id"] / src["files"][0]
            q = quotations[src["id"]]
            target = write_image(
                src_pdf,
                case_dir / f"scan_{case.variant}_{_slug(q.supplier.short.lower())}_p1",
                case.variant,
                rng,
            )
            files.append(target.name)

        elif case.kind == "scanned_pdf":
            src = built[case.source or ""]
            src_pdf = out / src["id"] / src["files"][0]
            q = quotations[src["id"]]
            target = write_scanned_pdf(
                src_pdf,
                case_dir / f"scan_{_slug(q.supplier.short.lower())}_{case.variant}.pdf",
                case.variant,
                rng,
            )
            files.append(target.name)

        elif case.kind == "misnamed":
            src = built[case.source or ""]
            src_file = out / src["id"] / src["files"][0]
            q = quotations[src["id"]]
            target = case_dir / (Path(src["files"][0]).stem + case.variant)
            shutil.copyfile(src_file, target)
            files.append(target.name)

        elif case.kind == "malformed":
            if case.variant == "empty":
                target = case_dir / "quotation.pdf"
                target.write_bytes(b"")
            else:
                src = built[case.source or ""]
                src_file = out / src["id"] / src["files"][0]
                q = quotations[src["id"]]
                target = case_dir / src["files"][0]
                if case.variant == "pdf_truncated":
                    data = src_file.read_bytes()
                    target.write_bytes(data[: int(len(data) * 0.55)])
                elif case.variant == "pdf_encrypted":
                    write_pdf(
                        q,
                        rng,
                        src["variant"],
                        target,
                        encrypt=StandardEncryption(
                            "axmed2026", "supplier", canModify=0, strength=128
                        ),
                    )
                elif case.variant == "json_broken":
                    text = src_file.read_text(encoding="utf-8")
                    text = text.replace("\n  }\n}", ",\n  }\n}", 1).replace(
                        '"items"', '"items\x07"', 1
                    )
                    target.write_text(text, encoding="utf-8", newline="\n")
            files.append(target.name)

        elif case.kind == "unsupported":
            target = case_dir / "export_20260812.bin"
            target.write_bytes(bytes(rng.getrandbits(8) for _ in range(4096)))
            files.append(target.name)

        entry: dict[str, Any] = {**asdict(case), "files": files, "dir": case.id}
        if q is not None:
            quotations[case.id] = q
            (case_dir / "truth.json").write_text(
                json.dumps(_truth_payload(case, q, files), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            entry["truth"] = f"{case.id}/truth.json"
            entry["supplier"] = q.supplier_key
            entry["currency"] = q.currency
            entry["n_lines"] = len(q.lines)
            entry["features"] = list(q.features)
        built[case.id] = entry
        manifest_cases.append(entry)

    shutil.rmtree(scratch)

    # Products quoted by more than one root document, for reconciliation tests.
    root_of = {c["id"]: (c.get("source") or c["id"]) for c in manifest_cases}
    groups: dict[str, list[dict[str, Any]]] = {}
    for cid, q in quotations.items():
        if root_of[cid] != cid:
            continue
        for ln in q.lines:
            groups.setdefault(ln.product_key, []).append(
                {
                    "case": cid,
                    "line_no": ln.line_no,
                    "supplier": q.supplier_key,
                    "currency": q.currency,
                    "units_per_pack": ln.units_per_pack,
                    "price_per_uom": ln.price_per_uom,
                    "inn_as_written": ln.inn,
                }
            )
    reconcile = {k: v for k, v in groups.items() if len(v) >= 2}
    duplicates = {}
    for cid, root in root_of.items():
        if root != cid:
            duplicates.setdefault(root, []).append(cid)

    manifest = {
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "case_count": len(manifest_cases),
        "cases": manifest_cases,
        "reconcile_groups": reconcile,
        "duplicate_sets": duplicates,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    (out / "README.md").write_text(_readme(manifest), encoding="utf-8", newline="\n")
    return manifest


def _readme(manifest: dict[str, Any]) -> str:
    rows = []
    for c in manifest["cases"]:
        feats = ", ".join(c.get("features", [])) or ""
        extra = c["note"] or ""
        if c["hostile"]:
            extra = f"injection: {c['hostile']}. {extra}".strip()
        if c["source"]:
            extra = f"from {c['source']}. {extra}".strip()
        rows.append(
            f"| `{c['id']}` | {c['kind']} | {c['variant']} | {c.get('supplier', '')} | "
            f"{c.get('currency', '')} | {c.get('n_lines', '')} | {feats} | {c['expect']} | {extra} |"
        )
    kinds: dict[str, int] = {}
    for c in manifest["cases"]:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    kind_line = ", ".join(f"{v} {k}" for k, v in kinds.items())
    return f"""# Synthetic quotation set

Generated by `evals/synth`. Ground truth is written first, then rendered into every format,
so every value in every document is known exactly. Seed {manifest["seed"]},
generator version {manifest["generator_version"]}, {manifest["case_count"]} cases: {kind_line}.

Regenerate (deterministic for a given seed):

```
uv run python -m evals.synth.build --out data/synthetic --seed {manifest["seed"]}
```

Every supplier, person, address, bank and reference number is invented. Product names are
international nonproprietary names with plausible but made-up prices.

## Layout

```
<case_id>/
  <document>        the file a supplier would send
  truth.json        the quotation it was rendered from, in the pipeline's target shape
manifest.json       every case, its features, what a correct pipeline should do with it,
                    products quoted by more than one supplier, and duplicate sets
```

## What `expect` means

| Value | Correct behaviour |
|---|---|
| extract | Every line in truth.json is recovered with the right values. |
| extract_and_flag | As above, plus a security flag. The planted instruction is never obeyed. |
| partial | Only part of the page is visible. Missing lines are fine, invented lines are not. |
| low_confidence | Mostly unreadable. Low confidence on what is returned, no confident guesses. |
| unsupported | An unsupported-document record, not a crash and not a guess. |
| malformed | Read what can be read, flag what happened (truncated, parsed leniently, parsed as text). Nothing invented. |

## Feature flags

| Feature | Meaning |
|---|---|
| pack_price_only | Only the pack price is stated. Unit price must be derived and marked as derived. |
| tiered | Volume tiers instead of one price. Truth uses the lowest-quantity tier. |
| discount | A discount column. `price_per_uom` is the list price, net is separate. |
| quantity_extended | Indicative quantity and extended amount per line, so arithmetic can be checked. |
| correction | A later passage corrects one line. The document shows the old value, truth holds the new, `superseded` holds both. |
| distractor_alt_price | A note quotes a price for a presentation that is not a line. It must not become one. |
| vat_note | Prices exclude VAT, stated in a note. |
| symbol_currency | Currency shown only as a symbol. |
| inn_variant, strength_variant | Non-canonical spellings. Truth carries the canonical INN alongside. |
| lead_time_weeks | Lead time in weeks in the document, days in truth. |
| mixed_uom, cold_chain, long | Tablets, vials and bottles in one document; a 2-8 C line; twelve or more lines. |

## Cases

| Case | Kind | Variant | Supplier | Currency | Lines | Features | Expect | Notes |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Cross-document structure

- `reconcile_groups`: {len(manifest["reconcile_groups"])} products quoted by two or more root
  documents, with each supplier's currency, pack size and unit price. Reconciliation should
  group these and surface the disagreements.
- `duplicate_sets`: {len(manifest["duplicate_sets"])} root documents that also appear as scans or
  misnamed copies. Extractions from the copies should agree with the root.
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("data/synthetic"))
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    m = build(args.out, args.seed)
    kinds: dict[str, int] = {}
    for c in m["cases"]:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    print(f"built {m['case_count']} cases into {args.out}: {kinds}")
    print(
        f"reconcile groups: {len(m['reconcile_groups'])}, duplicate sets: {len(m['duplicate_sets'])}"
    )


if __name__ == "__main__":
    main()
