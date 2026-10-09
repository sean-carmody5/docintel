# Agent log

Agent-generated summary of the planning and build conversation between Seán and Claude Code (Claude Fable 5.1). Kept current from the first commit. Entries note who steered each decision.


## The short version

- Seán set the bar: generalise to documents we have not seen, confidence computed from evidence rather than asked of the model, best practices, visual docs, small commits that say why.
- The agent proposed one neutral document shape, loaders chosen by content, one extraction schema with quoted evidence, and a computed confidence; Seán accepted it and moved human review to after the table is written.
- Evaluation was built before the pipeline: 66 synthetic cases from exact truth, a held-out seed, 37 public documents, hand-written fixtures for the provided pack. Seán's rule: pass means behaving as expected, not scoring 100%.
- OCR was measured, not assumed: RapidOCR over Tesseract, with the larger variants checked and rejected.
- The pipeline runs end to end offline. Live runs wait on an API key.
- Three blind model sets (Haiku 4.5, Sonnet 5.5, Opus 5.5) replayed through the pipeline found a crash on a malformed recording and three defects in the synthetic truth; both fixed, nothing in the pipeline tuned.
- The review page went through three designs. Seán rejected a card page as "AI generated" and a dense workstation as "20 year old software"; the third is one calm list with the source beside the fields, and every control is checked by script.
- Seán's notes for the write-up: data residency may force open-weight models in the organisation's own environment, with Qwen VL the first candidate for scans; OCR word boxes to point at where a price was read.

## Session 1, 6 to 7 October 2026: vetting and planning

**Vetting the pack (Seán's request).** Before reading the brief in detail Seán asked for every provided file to be checked for embedded content or prompt injection. The agent inspected zip structure, PDF objects and content streams, hidden and white text, image chunks, EXIF and trailing bytes, contrast-stretched scans, the email's HTML part, and JSON for duplicate keys and unicode tricks. Nothing was found. White text in both PDFs is table headers on dark fills.

**What the pack contains (agent finding).** Eight synthetic files. Planted difficulties: a price corrected in an email P.S., a JSON with pack prices only, a JSON with tiered ZAR pricing, a PDF with a discount column, one quotation present three times (PDF plus two degraded scans), and products that overlap across suppliers in different currencies and pack sizes, including salbutamol as a syrup and as an inhaler.

**Architecture (agent proposed, Seán accepted).** Neutral Document representation, one schema-driven extraction, format knowledge only in loaders, deterministic validation layer, per-field confidence, reconciliation with a conflicts table, LangGraph for orchestration with a review interrupt, LangSmith tracing.

**Framework (Seán challenged, agent explained, Seán accepted).** Seán questioned whether LangChain and LangGraph add anything he could not write himself. The agent's position: technically little for eight files, but the brief lists a framework as a constraint and scores fluency second, so use it thinly for orchestration and tracing, keep the document handling in plain Python, and say so in the write-up. The agent produced a visual primer to explain state, interrupts, checkpoints and Mermaid output.

**Model billing (Seán asked, agent verified).** Seán wanted to run the pipeline's model calls on his Claude subscription. The agent checked current Anthropic documentation: subscription logins are for Claude Code and claude.ai only and the Agent SDK requires an API key. Decision: develop offline against recorded fixtures and a fake chat model, which Claude Code authors from the documents on the subscription, and use a Console key with a minimum top-up for real runs at the end. The fixtures double as the golden evaluation set.

**Time-box (Seán asked).** Treated as guidance, not a stopwatch, but commit timestamps are visible, so the build is planned as one or two sittings of roughly six hours with real time stated in the write-up.

**Repository (Seán's call).** First push is the provided materials plus the plan. Docs are to be visual throughout, with a final pass at the end.

## Session 2, 7 October 2026: plan revision

Seán reviewed the first plan and steered the following. Each is now in PLAN.md revision 2.

**Review placement (Seán corrected, agent agreed).** The brief says the table must be suitable for human review, which means the table is the review surface. The agent had placed the LangGraph stop before writing. Reordered: write first with status pending, a person reviews and edits the table, and the approval stop gates a stub promote step.

**Model (Seán's call).** Sonnet 5.5 default. Seán asked whether Haiku 5.5 exists. It does not, the latest Haiku is 4.5. Eval will compare Haiku 4.5, Sonnet 5.5 and Opus 5.5.

**Layout (Seán questioned, agent proposed).** Seán asked whether a flat package of ten modules is normal. Moved to a src layout with one subpackage per concern, and a real package name.

**Schema (Seán asked for a glossary).** Trade terms explained in the plan. Agreed to keep the wider field set and evaluate.

**Confidence (Seán's requirement).** Not to be left to the model. Agent proposed evidence-based scoring: the model cites a snippet per field, code checks grounding, evidence validity, arithmetic consistency, plausibility, agreement with a second pass or a duplicate source or OCR, and OCR word confidence for images. Weights tuned on synthetic data, calibration reported.

**New file types (Seán's requirement).** Build in anticipation, not one Excel loader. Agent proposed content sniffing, a specific-loader registry, a generic text converter fallback, a render-to-image fallback, and a loud unsupported record. Contract tests over every loader.

**Dataset (Seán's requirement).** Bulk out with synthetic data generated from known ground truth, rendered into every format and degraded for the image cases, plus public price lists as robustness smoke tests.

**Prompt injection (Seán's requirement).** Mitigations at load, prompt, output and pipeline level, with hostile fixtures in the test set.

**MCP (Seán asked).** Agent's view: overkill for the core, a possible stretch as a reviewer-facing server over the review table.

**Standard (Seán's direction).** No room for mediocrity. Plan now includes uv, ruff, mypy, pytest, pre-commit and GitHub Actions. Realistic estimate revised from 6 to about 10 hours, to be stated honestly in the write-up.

## Session 3, 7 October 2026: repository and evaluation data

**Repository (Seán's go-ahead).** Local git init, private GitHub repository created through the API with the credential Git Credential Manager already held, first push of the provided materials, brief, plan, CLAUDE.md and agent log. Git on this machine would have rewritten the provided PDFs as text on checkout, so a gitattributes file pinning binaries and LF went in as the second commit. Package scaffold with uv, exact lockfile, ruff, mypy and a src layout.

**Dataset (Seán's direction, agent built).** Seán asked for plenty of time on a synthetic plus real dataset with manual review and iteration. The agent built a generator that writes ground truth first and renders it into six JSON dialects, three PDF layouts, four email styles, Excel, Word, two CSV conventions, four image degradations, three injection carriers, misnamed files and an unsupported blob: 45 cases. Review found packaging types that did not fit pack sizes, a heavy scan that was too readable, table columns that wrapped or overflowed, Spanish taglines on Indian suppliers and email timezones that did not match the sender. All fixed and rechecked. Invariant tests cover price arithmetic, corrections, tiers and duplicate sets.

**Public data (agent researched, Seán to review).** A research agent searched about 45 sources and verified 36 downloadable documents. Thirty-seven are now listed in evals/public/sources.json with publisher, licence and tags, and fetched into a git-ignored folder by a script that checks magic bytes and records hashes. Three hosts need relaxed TLS because of broken certificate chains. Licence note: MSH and Ghana NHIS assert all rights reserved, so nothing in that folder is redistributed.

**Determinism (agent).** Regeneration must be byte-identical for the commit history to stay honest, so PDFs are rendered invariant, email message IDs come from the seeded generator, Office packages are rewritten with fixed timestamps, and all text outputs are LF.

## Session 4, 8 October 2026: diversity, malformed files, vision, licences

**Diversity audit (Seán asked whether the evaluation leaned on the eight files).** The agent's honest count: three of six JSON dialects, two of three PDF layouts and one of six email styles were modelled on the pack. Gaps against the spec were image-only scanned PDFs, PDFs with a garbled OCR layer, XML, HTML, plain text, non-English field names and the malformed family. All added as separate commits: a French-keyed JSON dialect with a Moroccan supplier, XML, HTML and fixed-width text, scanned PDFs with and without a garbage text layer, empty, truncated, encrypted and broken-JSON cases, and a forty-line spreadsheet.

**Formats and malformed files (Seán's requirement, now in the plan).** A tiered table built from the spec: specific loaders for the named and common formats, a generic text path for the rest, render-to-image as a last resort, containers expanded, and encrypted or empty files refused with a reason. Malformed policy: typed loader errors become records, strict parse then lenient then as-text, each step flagged.

**Vision (Seán's assumption, agent agreed with caveats).** Transcribe pages to markdown with a vision model, then run the same extraction as every other format. Safeguards: verbatim transcription with illegible markers, independent Tesseract OCR as an agreement signal, an optional direct second pass on low-confidence price fields, and a text-layer quality gate so garbage OCR layers in PDFs are not trusted.

**Licences (Seán questioned git-ignoring in a private repo).** Decision: commit only files under an explicit open licence, commit a README listing all public sources with publisher and licence, fetch the rest on demand. A private repository is still redistribution.

**Commit practice (Seán asked).** Messages were judged adequate, granularity was not: the generator landed as one large commit with review fixes folded in. CLAUDE.md now requires one module per commit and one review finding per commit, and this session followed it.

## Session 5, 8 October 2026: OCR decision and the ingest layer

**OCR engine (Seán challenged Tesseract, asked for verification, agent measured).** Web benchmarks favoured PaddleOCR's models; the agent then measured RapidOCR (PP-OCRv6 on ONNX) against Tesseract on our degraded synthetic scans and the two provided scans, where prices are known. RapidOCR recovered four times the prices and its line confidence separated legible pages from unreadable ones, which Tesseract's did not. Decision: RapidOCR behind an engine interface, Tesseract as fallback, cloud OCR named for production. Seán also approved a second extraction pass from a different model family on low-confidence price fields. Side finding: the synthetic fax was harsher than the real one and was softened.

**Ingest layer (agent built, in nineteen commits).** Document model with content-hash ids and failed-load records; content sniffing with the extension only as a tie-breaker; a registry with exact, family, generic-text and failed fallbacks; loaders for JSON (strict, lenient, as-text), the text family, PDF with a structural scanned-page check and a text-layer quality score, images, email with attachments as children, Excel and Word as markdown, markitdown for the long tail, and ZIP archives. Every loader is exercised against all 59 synthetic cases, the provided pack and the public scanned PDFs.

**Findings during build.** pymupdf4llm runs its own OCR on image-only pages unless told not to, which would have hijacked routing. Real scanner OCR layers score 0.95 to 0.99 on the quality heuristic, so structure, not text quality, decides that a PDF is a scan. csv.Sniffer fails on exports with key/value rows above the table. Wrapped PDF table cells arrive as <br> with bold runs per fragment and split product names. One commit went in with a failing test because a pipe hid pytest's exit code; pipefail is now on in every command and the fix was its own commit.

**Security (agent built).** Hidden PDF spans (tiny, off-page, or white with no dark fill beneath), hidden HTML elements via a tag-balanced scan, invisible and bidirectional unicode, and injection phrases. All four hostile cases flag; none of the 55 clean cases or the provided files do.

## Session 6, 8 October 2026: OCR variants, CI, expected failures, verification

**Other OCR models (Seán asked).** Measured rather than argued: RapidOCR's medium and server model variants on the same nine pages recover the same prices as the small default at 20 to 70 times the time per page. Decision unchanged. Image quality, not model size, is the limit; the independent second signal comes from a different model family, not a bigger OCR.

**CI (Seán asked).** GitHub Actions on every push: lint, format, types, a rebuild of the synthetic set compared against the commit, and the offline tests. The first run failed because zlib writes different bytes on Linux for identical PNG and Office content, so the check now compares images by pixels and Office files by zip members. The second failed because uv run pytest does not put the repo root on the path; fixed in pytest config. Green since.

**Expected failures (Seán's point).** Passing means behaving as the case expects, not 100% accuracy. Two glare-wipe photo cases added that erase table rows like the provided scan_03. The plan states the rule.

**Branches and merge requests (Seán asked).** Agent's view, accepted: overkill for a solo take-home; trunk with small commits is what the brief weighs. Not adopted.

**Verification layer (agent built).** Records model; conservative INN, strength and form normalisation; grounding of every value and evidence quote in the source; deterministic arithmetic, code and plausibility checks; confidence per field computed from those signals with every deduction recorded; derived prices inherit confidence from their inputs. Two grounding bugs found by the synthetic set and fixed: a number after a CSV comma, and an INN truncated by a fixed-width column. Hand-written expected extractions for the eight provided documents, with the two scans marking illegible fields honestly.

## Session 7, 8 October 2026: the pipeline runs end to end

**Eval design (Seán's direction).** Seán asked for more expected-failure cases and, more importantly, for an evaluation that represents the wider world without becoming the thing the pipeline is tuned to. The plan now has a generalisation discipline: a held-out set from a different seed that is never opened while tuning, no supplier or layout names in prompts, public documents as blind robustness tests, and cases grouped by behaviour. Five expected-outcome cases were built (expired validity, rotated scan, fax cover sheet, buyer target prices in a quoted RFQ, a price with no unit) and a backlog lists the rest. On other OCR engines: RapidOCR is PaddleOCR's models, measured; EasyOCR and the rest sit below it and the ceiling is image quality, so no more time was spent there.

**Pipeline (agent built, eleven commits).** Reconciliation that reports cross-supplier conflicts and cross-checks duplicate copies of a quotation; the writer producing CSV, SQLite and a Markdown report that leads with what to look at first; settings from the environment; the vision path with a transcriber and an OCR engine interface; the LangGraph state graph with fan-out, retries, SQLite checkpoints and the review interrupt; a CLI with run, approve and draw; and the scorer. The offline run on the provided pack gives 37 records, 16 flagged for review once OCR and the duplicate cross-check are on. On the synthetic set, fixture replay passes all 66 cases with no invented lines and no wrong values, which proves the plumbing, not the model.

**Findings during build.** The pack has 37 lines, not the 27 first assumed. A duplicate match must only lift fields whose values agree in both copies, and a lifted field must clear its stale review reason. Attachment records carry the attachment's name, so the scorer follows the parent to find the case.

**Blocked on Seán.** Live runs need a Console API key with a small top-up. Everything up to that point runs offline.

## Session 8, 8 October 2026: the review workstation, three model sets, and what they found

**Single-file input (Seán asked).** `docintel run` takes one file as well as a folder.

**Review page (Seán asked for a dry run, then rejected the first cut as "a classic AI generated UI").** The agent listed the tells it was reproducing: a row of metric tiles, pill badges on everything, uniform rounded cards with drop shadows, gradient blues, Inter, emoji markers, everything centred. Rebuilt as a three-pane workstation: documents on the left, records in the middle with a six-cell confidence strip per row so the weak field is visible before the number is read, and the selected record's fields with score bars, reasons and evidence quotes on the right. Hairlines, tabular numerals, one accent colour, keyboard navigation, decisions kept in the browser and copied out as JSON that `approve --decisions` applies. Screenshotted with Playwright in both themes and at a narrow width; a table overflow and a stacked-layout defect were fixed before showing it. Inspecting the first cut also found three logic faults: a record missing an essential field scored 0.85 overall because missing fields were skipped (now zero); absent fields rendered as red failures (now muted); the weeks conversion was penalised twice.

**Three model sets (Seán's idea).** Three Claude Code subagents, Haiku 4.5, Sonnet 5.5 and Opus 5.5, each extracted the same 33 documents (the eight provided plus 25 synthetic) by hand from the same brief, with the truth files off limits. Replayed through the pipeline with `--fixtures` and scored against truth:

| Set | Synthetic cases passed | Line recall | Invented lines | Wrong at high confidence |
|---|---|---|---|---|
| Haiku 4.5 | 3 of 25 | 0.07 | 0 | 1 |
| Sonnet 5.5 | 24 of 24 | 1.00 | 0 | 0 |
| Opus 5.5 | 24 of 24 | 1.00 | 0 | 0 |

Haiku declined most of the work: it marked xlsx, docx, html and csv as needing special parsing, every image as unreadable, and wrote integers where the schema wants evidence strings in seven files. Sonnet and Opus both caught both planted injections and left unreadable digits as illegible rather than guessing. On the provided pack neither contradicted the hand-written reference on any key field; every difference was a value the agent left blank, mostly units per pack on bottle lines where the reference had assumed one per bottle. Caveat, to repeat in the write-up: this is the Claude Code harness reading files with tools, not the API's structured-output path with the pipeline's prompt, so it measures the models' reading more than the extractor. Reports are in evals/reports.

**Haiku's malformed recordings found a pipeline defect (agent fixed).** One schema-invalid recording raised inside the graph node, LangGraph retried, and the whole batch died on one document. A failed extraction is now that document's flagged empty record, like a failed load, and the run finishes.

**Two independent readers found three eval defects (agent fixed, truth regenerated).** Sonnet and Opus failed the same three cases with identical output, which points at the answer key. The fixed-width print-out cuts two cells at the column width, and truth now holds the text as printed. The photo case is page 1 of a three-page quotation, and truth now holds only the ten lines on that page; the generator trims any one-page image of a longer source the same way. The garbled-OCR-layer cases demanded a review flag, but a pipeline that ignores the layer and reads the image correctly has nothing to flag, so the expectation is plain extract. Fixture replay still passes 66 of 66. No prompt or threshold changed: the pipeline was not tuned to the eval, the eval was corrected by evidence from outside it.

**Review page, second rejection (Seán).** The three-pane workstation was "far too noisy, way too much going on, looks like 20 year old software". Agent's reading of the gap: density and chrome, not just the tells of the first cut. Rebuilt a third time as a single list in the style of current product software: one row per line with product, price and at most one short note, least certain first; open a row for the fields; colour only on fields the pipeline flagged; reasons, evidence and scores behind "Show details". Comparisons moved to their own tab. Decisions export as before.

**Source beside the fields (Seán chose it from three options).** Opening a row now shows the document on the right: the page image for scans and PDFs (born-digital PDFs are rendered for this), or the loader's text with the evidence quotes highlighted and scrolled to the line's own product and price. Previews are JPEGs in a sources folder next to the page, so it still opens from disk; text goes in the page. Seán also asked for the legend to be a help button rather than a permanent panel, opening on first use, and for the mark meanings and keys to be explained plainly; both done. Noted for the write-up: outline on the scan the exact spot a price was read from, using the OCR engine's word boxes.

**One row per line, not per document (Seán asked).** The page lists quotation lines because that is what the table, the reconciliation and the systems of record work on: a document holds several products, and one line can be unreadable while its neighbours are fine. Sorted least certain first, the top rows were five lines of the same glare photo, which is why the sort looked like a repeat. Grouping by document with a header row is the obvious next step if a reviewer prefers to work file by file.

**Data residency (Seán's note for the write-up).** Cloud models now; a medical deployment may be bound by confidentiality to open-weight models hosted in the organisation's own environment, or to the cloud provider's inference service under agreement. Recorded in the plan with what the swap costs: a local vision model and open-model structured-output quality are the two unknowns, and the eval set is how a candidate earns the slot.

**Zoom (Seán asked).** The full-size page viewer zooms with the scroll wheel or keys around the cursor, pans by dragging, fits or shows actual size, and steps through pages; previews are rendered at 170 dpi and capped at 2400 px wide so a price cell on a phone photo survives a 2x zoom. Seán's note for the write-up on the open-weight path: the larger Qwen VL models are the first candidates for the scan path because of their OCR-grade reading.

**Documentation pass (Seán's priority: clarity over volume).** README rebuilt around what a reader needs, with the page in it and mock and live runs spelled out; a walkthrough of one real run; a two-page how-it-works; the plan rewritten as the design as built with an honest list of what was planned and not built; the log given a short version. Seán asked how non-Anthropic models are used: one optional extra each, a key in .env, a different model string; the README says only Anthropic has been exercised.

**Handwriting (Seán's note for the write-up).** From earlier work on documents that often carried handwriting: a strong vision model reads legible handwriting, the OCR engine does not, so the agreement signal would over-flag such pages. The brief names scans and photos, not handwriting, and quotations rarely carry much. Recorded as a known limit with the mitigation path.

**Testing (Seán asked).** Unit tests per module plus end-to-end graph runs on the provided pack; CI now also replays the whole synthetic set through the pipeline and scores it with a require-pass flag, and runs the provided pack to the review stop and through approve, so the "66 of 66" claim is checked on every push rather than asserted.

**Write-up notes (Seán).** Compare the other closed-source families too, not only Claude's. The second vision pass stays future work until a live run shows whether it earns its cost.

**Corrections (Seán asked what a decision means and whether fields should be editable).** Approve sends the line on, reject keeps it out, hold defers it; all per line. Editing was a real gap: a reviewer who can read a price on the zoomed scan had no way to set it except reject and re-key elsewhere. Now any value in an open row is editable in place, a corrected field shows "set by reviewer" with the original beside it and clears its mark, corrections export with the decisions, and approve applies them first: confidence 1.0 with the reason "set by reviewer", a corrected_by_reviewer flag, both values in decisions_applied.json, the corrected value in approved.csv, and records.csv untouched as the pipeline's own output. Invalid corrections (a word in a numeric field, a protected field) are refused and recorded. Seán's remark on the glare photo: he expected it to be a write-off; the pipeline reads the legible half and marks the rest, which is the degrade-honestly behaviour the eval demands.

**Finishing from the page (Seán: "I'd prefer if export did more than copy JSON to my clipboard").** `docintel run --review` and `docintel review` serve the output folder on 127.0.0.1 with the standard library and accept one POST from the page. Apply decisions writes decisions.json, resumes the run, applies corrections then decisions, and shows the counts and approved.csv on the page; the terminal prints the same line. Opened from disk the button saves decisions.json as a download and prints the exact approve command with the thread id, which now travels with the run. Verified by driving the served page with Playwright; the only defect found was the server's own prints being buffered when piped, now flushed.

**CLI `--fixtures` (agent).** Any recorded set replays without code changes, and the run metadata names the roots it used.

## Session 9, 8 October 2026: the first live runs

**Key (Seán).** Seán put an Anthropic key in `.env`, git-ignored, and said to have a run. The agent started with one JSON file so the first money spent was cents.

**First call found a bug.** claude-sonnet-5-5 rejects any temperature other than its default and the pipeline sent 0.0 on every call; the failure surfaced cleanly as an extraction_failed record. Temperature is now unset unless configured, and max_tokens is explicit. Second attempt: 4 lines, every value grounded, zero differences from the hand-written fixture.

**Provided pack, live.** 37 lines in 76 seconds, 19 flagged. Key values agreed with the fixtures on 193 of 199; the differences were the model being more careful than the fixture writer (blank where a bottle has no pack count) and one real miss: the fax copy read "Losardina" for "Losandina" and the duplicate cross-check let it through because it assumed names agreed once the product key matched. Names, strengths and units are now compared across copies with punctuation ignored. Every live extraction and page transcript is now recorded and replays exactly with `--fixtures`, so no run is paid for twice.

**Synthetic set, live (agent ran it; Seán had said to).** 55 of 66, recall 0.87, 2 invented lines, 10 wrong values at high confidence, all on scans. Root cause: on the vision path the model's values were grounded against the model's own transcript, so a misread name scored 1.0. Names, INN and strength are now checked against the independent OCR reading like prices were, which drops an unconfirmed name to medium and flags it. Three smaller fixes: pack prices derived when only a unit price is printed (and the reverse), a concentration written into the INN moved to the strength, fully empty lines dropped and the document flagged. One capacity fix: a 40-line price list returned no lines at an 8k output cap and all 40 at 32k.

**Scorer refinement (agent, under Seán's rule).** Passing means behaving as expected: accuracy is now judged on values the pipeline claims to be sure of, and a wrong value at medium or low confidence is counted and reported as review work rather than a failure. A line whose name the glare cut short but whose price matches is matched, not counted as invented. The fixture replay and both blind agent sets still pass every case under the new rule.

**Result.** The same recorded extractions through the fixed pipeline: 65 of 66, recall 0.986, no invented lines, 2 wrong at high confidence (one cropped photo where the model and the OCR read the same wrong digit; recorded as a known limit), 8 wrong values flagged for a person. The recorded set is committed under tests/fixtures/live/sonnet-5-5 and the reports under evals/reports. Haiku 4.5 and Opus 5.5 comparison and the held-out run are next, after Seán has seen these numbers.

**Evening run (Seán: refine and check for up to an hour, frugally; everything prepped for the morning).** Tokens per call are now recorded beside the extractions, so cost per document is computed from what was sent. Haiku 4.5 on the synthetic set, about $1.30: 58 of 66, 10 wrong values at high confidence, 12 invented lines, one document refused because it sent numbers where the schema wants quote strings. Sonnet 5.5 on the held-out seed, about $4.80: 63 of 66, recall 0.97, the same cropped-photo digit the only silent error. Haiku on the held-out seed, about $1.25: 52 of 66. Two general repairs from Haiku's failures: a quote sent as a number is kept as text, and a dosage form written into the strength moves to the form field. All recordings committed under tests/fixtures/live; reports and the cost table under evals/reports. Opus 5.5 was not run: at roughly five times Sonnet's price per token it would be around $25 for the set, a decision for Seán. Draft write-up and video script written for the morning.

Replayed through the final pipeline, free: Haiku main set 60 of 66 with 4 wrong at high confidence (from 58 and 10); Haiku held-out 54 of 66 with 14 (from 52 and 25); Sonnet held-out unchanged at 63 of 66 with 2. Final reports under evals/reports.

## Session 10, 9 October 2026: the morning

**Seán's live run surfaced four cosmetic faults, fixed:** an HTTP logger under a name the quiet list missed, a LangChain warning about forced tool calling on the newest models (Anthropic's strict JSON-schema mode was tried and rejects a schema this size, so tool calling stays and the warning is silenced deliberately), no progress indication (one line per document now, streamed from the graph), and no file showing every line's final status (final.csv). Seán asked what happens to held and rejected lines: rejected lines are in final.csv and the audit, never in approved.csv; held lines stay pending for a later Apply.

**Opus 5.5 (Seán said yes).** 60 of 66, recall 0.986, one invented line, five wrong at high confidence, about $8.80. Four of the five are a pack size written into the strength, a convention the schema leaves ambiguous and the data-model section of the write-up now says so. Sonnet stays the default on quality and cost. Recordings committed; cost table updated.

**Repository size (Seán's concern).** 741 files and 12 MB, half of it recordings and fixtures whose job is done. Agent proposed dropping the held-out recordings, the three hand-written agent sets, the committed public documents and the raw reports, about 430 files and 5 MB after; awaiting Seán's yes.
