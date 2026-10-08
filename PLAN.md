# Plan: Document Intelligence Agent

Take-home for Axmed ([brief](docs/brief.md)). Ingest a folder of mixed supplier documents, extract quotation lines into one schema, write a reviewable table, and flag uncertainty. Built to survive the next document, not just these eight.

Status: planning, revision 2. Decisions and who made them are in [docs/agent-log.md](docs/agent-log.md).

## The one idea

Every input becomes the same neutral `Document` (text, optional page images, metadata, security flags). One schema-driven extraction runs over all of them. Format knowledge lives only in loaders. Supplier knowledge lives nowhere. Confidence is computed by code from evidence, not reported by the model.

```mermaid
flowchart LR
  F[(folder)] --> D[discover]
  D -->|one per file| L
  subgraph P[process_document, once per file, in parallel]
    direction LR
    L[load] --> X[extract] --> V[verify]
  end
  V --> R[reconcile]
  R --> W[write<br/>status: pending review]
  W --> T[(CSV + SQLite<br/>+ review report)]
  T -.-> H{{human reviews<br/>and edits the table}}
  H -->|approve| M[promote<br/>stub for systems of record]
```

The table is the review surface, as the brief says. The pipeline writes it and stops. A person reviews and edits it. The `promote` step is the LangGraph interrupt: it resumes only on approval and is a stub here, because what happens after approval is Axmed's systems, not this task.

| Layer | What it is | Why |
|---|---|---|
| Loaders, verify, reconcile, writer, security | Plain Python | Quality lives here. No framework between us and the documents. |
| Graph, fan-out, retries, checkpoint, approval stop | LangGraph | Orchestration, resume after crash, human-in-the-loop as a primitive. |
| Model calls, structured output, provider swap | LangChain | One call shape for text and image inputs, any provider behind a config string. |
| Tracing, eval dataset | LangSmith | Every call recorded with inputs, outputs, tokens, cost. One env var. |

## Code layout

Standard src layout, installable package, one subpackage per concern.

```
pyproject.toml           uv-managed, pinned lockfile
src/docintel/
  config.py              model string, paths, concurrency, thresholds, weights
  documents.py           Document, Evidence, SecurityFlag
  ingest/
    sniff.py             content-based type detection, suffix as fallback
    registry.py          {media type -> loader}, fallback chain, UnsupportedDocument
    json_loader.py  pdf_loader.py  eml_loader.py  image_loader.py  xlsx_loader.py
    generic_loader.py    markitdown fallback for anything else with text
    security.py          hidden text, unicode tricks, injection patterns
  extract/
    schema.py            Pydantic: ExtractionResult, QuotationLine, Evidence
    prompt.py            system prompt, untrusted-data framing
    extractor.py         with_structured_output, text or image messages
  verify/
    grounding.py         is each value present in the source
    checks.py            arithmetic, derivation, plausibility, currency
    confidence.py        composite score and reasons
  reconcile.py           group same product across sources, conflicts
  store/
    writer.py            CSV, SQLite, review_report.md
  graph.py               StateGraph, Send fan-out, checkpointer, interrupt
  cli.py                 run, approve, draw, eval
tests/                   offline by default, fixtures replayed by a fake model
evals/                   synthetic generator, public-sample fetcher, scorer
data/
  provided/              the eight files from Axmed (committed)
  synthetic/             generated, with ground truth (committed, small)
  public/                downloaded samples (git-ignored)
output/                  records.csv, review.sqlite, review_report.md
docs/                    brief, plan, agent log, write-up
```

## Target schema

Extended from the suggested five fields. One row per quotation line. Every field in the Price group is present in at least one of the provided documents, and each changes whether two prices are comparable.

| Group | Fields |
|---|---|
| Provenance | source_document, source_locator (page, line, JSON path), supplier_name, quotation_ref, document_date, valid_until |
| Product | product_name, inn, strength, dosage_form, uom, units_per_pack |
| Price | price_per_pack, price_per_uom, currency, price_basis (stated, derived, list, net, tiered), discount_pct, price_tiers, incoterm, moq, lead_time_days |
| Corrections | superseded (field, old value, new value, reason) |
| Review | per-field confidence and reasons, overall_confidence, needs_review, status (pending, approved, rejected) |

Field glossary, since several are trade terms:

| Field | Meaning | Why it matters |
|---|---|---|
| inn | International Nonproprietary Name, the generic drug name. Paracetamol, not Panadel. | The only key that matches products across suppliers. |
| uom | Unit of measure the price refers to: tablet, vial, ampoule, bottle, pen. | A price per tablet and a price per bottle are not comparable. |
| units_per_pack | How many UOM in the pack the supplier sells. | Converts pack price to unit price. |
| incoterm | Trade term saying who pays freight and insurance and where risk passes. EXW, FCA, FOB, CIF, CIP. | A CIF price includes shipping, an EXW price does not. Same number, different cost. |
| moq | Minimum order quantity. | Whether the price is even available at Axmed's volume. |
| discount_pct | Discount shown on the quotation line. | List price versus net price. The Andina PDF has this column. |
| price_tiers | Volume tiers when a single price is not given. | Ubuntu Health quotes three tiers. |

Separate tables: `flags` (one row per concern, linked to a record) and `conflicts` (one row per product that appears from more than one source with disagreeing values).

## Loading: built for the file type we have not seen

```mermaid
flowchart LR
  A[file] --> S[sniff content<br/>not just suffix]
  S --> R{specific loader<br/>registered?}
  R -->|yes| L[json, pdf, eml,<br/>image, xlsx]
  R -->|no| G{generic text<br/>conversion works?}
  G -->|yes| M[markitdown<br/>docx, pptx, html, csv, ...]
  G -->|no| I{can render<br/>to image?}
  I -->|yes| V[page images<br/>to vision path]
  I -->|no| U[UnsupportedDocument<br/>record, loud flag]
  L --> SEC[security scan]
  M --> SEC
  V --> SEC
  SEC --> DOC[Document]
```

- Type is sniffed from content, so a misnamed `.txt` that is really JSON still loads.
- A specific loader exists where quality needs it. Everything else falls through a generic converter, then a render-to-image path, then a loud unsupported record. Nothing is silently skipped.
- Adding a format with special needs is one file and one registry line. A contract test runs over every registered loader and every sample file.
- `xlsx_loader.py` is the demonstrated extension: the generic path already handles Excel, the specific loader adds sheet and header awareness. A `.docx` dropped in the folder is the demonstration that the fallback works with zero code.

### Formats: built, anticipated, refused

We work from the spec, not from the eight files. The spec names JSON exports, PDFs, email and WhatsApp threads, scans and photos, and "a new file type entirely". This is the coverage we build to.

| Tier | Formats | How | Why this tier |
|---|---|---|---|
| Built, specific loader | JSON (any shape), PDF with a text layer, PDF without one (image-only scan), PDF with a garbled OCR layer, PNG/JPG/TIFF, EML with plain, HTML and attachments, XLSX, CSV in any dialect, DOCX, WhatsApp and other chat exports | One module each. The PDF loader measures text-layer quality and routes bad layers to the vision path. | Named in the spec, or the most common things a supplier actually sends. |
| Handled generically | HTML, XML, Markdown, plain text, PPTX, RTF, legacy .doc and .xls | Content sniffing plus the markitdown converter. No code per format. The extractor reads them as text. | The next file type should cost nothing. |
| Rendered to image | Anything LibreOffice can open that the tiers above cannot read | Optional render-to-page-images path, then the vision path. | Last resort before giving up. |
| Containers | ZIP, email with several attachments | Expanded into their members, each becomes its own Document with a parent reference. | Suppliers bundle. |
| Refused with a reason | Encrypted PDFs, empty files, truncated files, unknown binaries, audio voice notes | An unsupported record carrying the reason. Never a crash, never a guess. | A reviewer needs to know it arrived and why nothing came out. |

### Malformed files

- Every loader either returns a Document or raises a typed `LoaderError` with a reason. The registry turns the error into an unsupported record that appears in the output table and the review report with `status: failed` and the reason.
- Strict parse first, then degrade: a JSON with a trailing comma is retried leniently and flagged `parsed_leniently`; if that fails the bytes are handed to the extractor as text and flagged `parsed_as_text`. A truncated PDF yields the pages it still has, flagged `truncated`.
- Encrypted files are reported as encrypted. No attempt to open them.
- A size cap and a page cap, both flagged when hit, so one 400-page catalogue cannot stall the run.
- The synthetic set carries one case of each: empty, truncated PDF, encrypted PDF, broken JSON, misnamed, random bytes.

## Confidence is computed, not asked for

Models are poor at estimating their own confidence. The extractor is asked for evidence instead: for every field, the verbatim snippet it took the value from. Code then scores each field from independent signals.

```mermaid
flowchart LR
  E[field value<br/>+ evidence snippet] --> G[grounded?<br/>value found in source]
  E --> Q[evidence real?<br/>snippet found in source]
  E --> C[consistent?<br/>arithmetic and relations]
  E --> P[plausible?<br/>ranges, ISO codes, dates]
  E --> A[agreed?<br/>second pass, other source]
  E --> O[OCR quality<br/>images only]
  G & Q & C & P & A & O --> S[score + reasons<br/>high, medium, low]
```

| Signal | How | Applies to |
|---|---|---|
| Grounded | Normalised value searched in the source text or JSON tree. Fuzzy for OCR text. | All |
| Evidence real | The quoted snippet exists in the source and contains the value. | All |
| Consistent | Pack price equals unit price times units. Quantity times unit price less discount equals extended. Dates in order. | Where the inputs exist |
| Plausible | Price ranges per UOM, ISO 4217 currency, integer pack sizes, known incoterms. | All |
| Agreed | Same value from a second extraction pass (optional, doubles cost), from a cross-document duplicate (the Andina scans versus the PDF), or from Tesseract OCR text. | Images, duplicates |
| OCR quality | Tesseract per-word confidence around the evidence region. | Images |

Score starts at 1.0 and each failed signal subtracts a configured weight. Tiers: high, medium, low. Low forces `needs_review`. Every subtraction is recorded as a reason the reviewer can read. Weights live in config and are tuned on the synthetic set, where ground truth is known. The model's own confidence, if given, is a tie-breaker at most. The write-up shows a calibration plot: do low-confidence fields actually turn out wrong more often.

## Vision path

Images, image-only PDFs and PDFs whose text layer fails the quality gate all take the same route.

```mermaid
flowchart LR
  I[page image] --> T[vision model transcribes<br/>the page to markdown,<br/>verbatim, tables kept,<br/>unreadable marked]
  I --> O[Tesseract OCR<br/>with word confidences]
  T --> X[same extraction prompt<br/>as every other format]
  X --> V[verify: grounding against<br/>the transcript, agreement<br/>with OCR, OCR confidence]
```

Why transcribe first rather than extract straight from the image:

- One extraction path for every format. The generalisation argument holds for scans too.
- The transcript is an inspectable artefact. A reviewer can see what the model read, and grounding and evidence checks have a text source to check against.
- Transcription errors are local and visible. A direct image-to-schema call hides them inside the numbers.

Safeguards, because transcription can quietly normalise or invent:

- The transcription prompt demands verbatim text, keeps table structure, and marks anything unreadable as `[illegible]` rather than guessing.
- An independent OCR engine runs on the same page. Numbers present in both the transcript and the OCR text score high; numbers in only one score low. OCR line confidence around the evidence region feeds the score.
- A second extraction pass from a different model family, on the price fields only, when confidence is low. Two unrelated models have to agree before a value scores high. One extra call per flagged page.
- The text-layer quality gate: a PDF whose extracted text has a low ratio of dictionary words, or a high density of odd characters, is treated as having no text layer. The DRAP and Quezon City scans in the public set are exactly this case, and naive text extraction would return garbage with full confidence.

### OCR engine choice

Measured on our degraded synthetic scans and the two provided scans, where the prices are known. Recall is the share of printed prices or product names found anywhere in the OCR output.

| Engine | Price recall | Name recall | Confidence on legible pages | Confidence on unreadable pages |
|---|---|---|---|---|
| RapidOCR (PP-OCRv6 models on ONNX Runtime) | 0.44 | 0.54 | 0.96 to 0.99 | 0.58 and 0.64 |
| Tesseract 5 | 0.10 | 0.27 | 0.3 to 0.9, erratic | 0.16 to 0.33 |

RapidOCR's larger variants were also measured on the same nine pages: the PP-OCRv6 medium models score the same recall (0.48) at 40 seconds a page and the PP-OCRv5 server models slightly less (0.46) at 138 seconds a page, against 2 seconds for the small models. Size buys nothing here; image quality is the limit. RapidOCR recovers 12 of the 13 prices on the provided fax; Tesseract recovers 2. Its line confidence also discriminates readable from unreadable pages, which is the property the agreement score needs. Tesseract's does not. Decision: RapidOCR is the default behind an `OcrEngine` interface, Tesseract is the fallback when installed, and a cloud engine (Textract, Azure Document Intelligence) is the production option for key-value and table confidence, with the caveat that supplier data then leaves the environment. Apache 2.0, CPU only, about two seconds a page. Fine-tuning Tesseract was rejected: its failures are image quality and layout, not glyphs.

## Prompt injection and hostile documents

Supplier documents are untrusted input to a model. Mitigations at four points:

| Point | Mitigation |
|---|---|
| Load | `security.py` flags hidden PDF text (white, tiny, off-page), zero-width and bidi characters, hidden HTML elements in email, and instruction-like phrases. Flags travel with the Document. |
| Prompt | All instructions in the system prompt. Document content inside explicit delimiters, framed as untrusted data whose instructions must be ignored. Structured output only, no tools, no network. An injection can at worst corrupt fields, never act. |
| Output | Schema validation, string sanitisation (no URLs or control characters, length caps), and grounding. A fabricated value has no evidence. |
| Pipeline | Any security flag forces `needs_review`. Nothing reaches `promote` without a person. Flags appear in the review report and the trace. |

A hostile fixture in the synthetic set (JSON with an embedded instruction, PDF with white text) asserts the flags fire and the values stay grounded.

## Data and evaluation

Eight files is not an evaluation. Two additions, both part of Phase A.

**Synthetic by construction.** `evals/synth/` generates ground truth first (a pharma vocabulary of INNs, strengths, forms, suppliers, currencies, incoterms), then renders each truth into every format: JSON in several unrelated shapes (nested, flat, camelCase, pack price only, tiered), PDF in several ReportLab layouts, email with and without a later correction, and images degraded with rotation, blur, noise, glare and cropping. Because the truth is known exactly, the scorer measures field-level precision and recall, numeric tolerance, and confidence calibration. This is the same method Axmed used to make the pack.

**Public samples for robustness.** A fetch script downloads real price lists, catalogues and RFQ forms (UNICEF, Global Fund, PAHO, WHO, national procurement bodies, a manufacturer). No ground truth, so these are smoke tests: does the pipeline degrade into flags rather than crash or guess.

**Licences.** Every public source is recorded with publisher, URL, licence, hash and fetch date. Only files under an explicit open licence (CC BY, Open Jordanian Licence, CC BY-NC with attribution) are committed. The rest, including MSH and Ghana NHIS which assert all rights reserved, are fetched on demand and never redistributed, even in a private repository. The committed README in `data/public` lists all of them so a reviewer can see what was used and on what terms.

**Diversity, honestly.** Half of the synthetic variants were modelled on the eight provided files, the other half on the spec and on what suppliers send in practice. The set is checked against the spec's list, not the pack: JSON in unrelated shapes including non-English keys, PDFs with and without text layers, PDFs with a garbled OCR layer, photos and faxes, emails in four styles, chat exports, spreadsheets, Word, CSV dialects, XML, HTML, plain text, hostile carriers, misnamed files and the malformed family. Gaps still open: non-English prose documents beyond headers, catalogues with no prices at all, and documents mixing several suppliers.

**Model comparison.** The same eval runs across Haiku 4.5, Sonnet 5.5 and Opus 5.5 behind the one config string. The table goes in the write-up with cost per document.

**Generalisation discipline.** The most heavily weighted criterion is surviving documents we have not seen, so the evaluation must not quietly become the specification.

- A held-out set: the same generator with a different seed (`--seed 7` into `data/synthetic_holdout`, built on demand, not committed, not opened while tuning). Prompts, confidence weights and normalisation rules are tuned on the main set only. The held-out score is computed once at the end and reported separately in the write-up. If it is much worse than the main score, that is the finding.
- The extraction prompt never names a supplier, a layout, a dialect or a field name from any export we hold. The loaders never branch on a filename. A reviewer can grep for either.
- Public documents are robustness tests only: no truth, no tuning against them. A fresh handful fetched at the end, not seen before, is run blind.
- Expected-outcome cases are grouped by the behaviour they test, so a gap in coverage is visible as an empty group rather than hidden in a count.

**Expected-outcome backlog.** Built now: expired validity, a scan rotated sideways, a fax with a cover sheet, a reply thread whose quoted RFQ carries the buyer's target prices, a quote that states a price with no unit. Listed for after the pipeline runs end to end: an RFQ with no prices, a purchase order and an invoice that look like quotations, two quotations in one PDF, per-100 pricing, a document with two currencies, a bid tabulation with several suppliers, a spreadsheet with uncached formulas, a password-protected archive member, handwritten corrections on a scan.

**Passing is behaving as expected, not scoring 100%.** Every case carries an `expect` value and the scorer grades against it. A clean JSON must extract every line exactly. A glare-wiped photo or the provided `scan_03` must return what is legible, flag the rest, and never invent a line; a confident wrong price on such a case is a failure, a flagged gap is a pass. An encrypted file must produce a refused record with the reason. Accuracy on the legible cases and calibration on the illegible ones are reported separately, because a pipeline that is right when it is sure and says so when it is not is the product.

## Engineering standard

- uv for environment and lockfile, exact pins.
- ruff for lint and format, mypy on `src/`, pytest offline by default, pre-commit.
- GitHub Actions on every push: lint, type check, offline tests, eval scorer on fixtures.
- Structured logging, `.env.example`, no secrets in git.
- README visual: Mermaid architecture printed from the graph, calibration plot, review report screenshot.

## Model

Default `anthropic:claude-sonnet-5-5` for text and images through one config string. The latest Haiku is 4.5, there is no Haiku 5.5. Compared against Haiku 4.5 and Opus 5.5 in the eval.

## Development strategy

```mermaid
flowchart LR
  subgraph A[Phase A, offline, on the subscription]
    A1[Claude Code writes expected<br/>extractions as fixtures] --> A2[Fake chat model replays<br/>fixtures inside the real graph]
    A2 --> A3[Everything except the prompt<br/>and vision path runs and is tested]
    A3 --> A4[Synthetic generator<br/>and scorer built]
  end
  subgraph B[Phase B, online, Console key]
    B1[Real model, prompt tuning,<br/>vision path, grounding tuned] --> B2[Eval on provided + synthetic,<br/>three models compared]
  end
  A --> B
```

## Build sequence

Priority order. A cut at any line still leaves a complete, honest submission.

```mermaid
gantt
  title Build sequence, realistic estimate 9 to 10 hours of commits
  dateFormat HH:mm
  axisFormat %H:%M
  section Core
  Scaffold, uv, ruff, mypy, CI, CLAUDE.md         :s1, 00:00, 30m
  Document model, sniff, registry, fallback chain :i1, after s1, 40m
  Specific loaders and security scan              :i2, after i1, 60m
  Schema, prompt, fixtures, fake model            :e1, after i2, 60m
  Extract node and grounding                      :e2, after e1, 45m
  Checks, confidence, reasons                     :v1, after e2, 45m
  Reconcile, writer, review report                :w1, after v1, 45m
  Graph, fan-out, checkpoint, approve stop, CLI   :g1, after w1, 45m
  section Prove
  Synthetic generator and scorer                  :p1, after g1, 75m
  Live runs, prompt tuning, model comparison      :p2, after p1, 60m
  Hostile fixtures and docx fallback demo         :p3, after p2, 20m
  section Deliver
  Write-up, agent log, README visuals             :d1, after p3, 60m
  section Stretch
  MCP server over the review table                :x1, after d1, 30m
```

The brief's box is 4 to 6 hours. This plan is nearer 10. Real time spent is stated in the write-up.

## Deliverables

- [ ] Private repo shared with @malber, @albertovpd, @cesar-axmed, granular history, visual README with run instructions
- [ ] Output table with confidence, reasons and source references
- [ ] Agent-generated conversation summary, [docs/agent-log.md](docs/agent-log.md)
- [ ] One-page write-up covering the nine required sections
- [ ] Video walkthrough under five minutes

## Assumptions to state

- `price_per_uom` is the list unit price in the document's currency. Net after discount is a separate field. No FX conversion, cross-currency conflicts are flagged as not directly comparable.
- Tiered price lists produce one row at the lowest-quantity tier, with all tiers in `price_tiers` and a flag.
- A document that corrects itself later wins with the later value, and both are kept.
- Scans of a document also present as a PDF are extracted independently, then cross-checked, because in production the PDF will not always be there.

## Risks

- LangGraph and LangChain version churn. Exact pins, day one.
- Vision extraction on the glared scan will be poor. It must degrade into low confidence and flags, not guesses.
- Scope. The standard is high and the list is long. The sequence above is the cut order.
