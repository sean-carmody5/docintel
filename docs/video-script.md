# Video walkthrough script (under 5 minutes)

Screen: terminal on the left, browser on the right. Have `output/demo` from a fresh `--review` run ready before recording so nothing is waited on.

| Time | On screen | Say |
|---|---|---|
| 0:00 | README diagram | Supplier quotations arrive as PDFs, scans, emails, JSON and spreadsheets. This reads a folder of them into one table, works out how sure it is of each value and why, and gives a person a page to finish the job. One idea runs through it: every file becomes the same neutral document, one extraction schema runs over all of them, and confidence is computed by code from evidence, never asked of the model. |
| 0:35 | Terminal: `uv run docintel run data/provided --out output/demo --as-of 2026-08-20 --review` | Eight documents, thirty-seven lines, fourteen flagged, about a minute live. The run stops at the review step and opens the page. Nothing reaches a system of record without a person. |
| 1:05 | Browser: the list | One row per quotation line, least certain first. Red means something you need to price the line could not be read. Amber means the values are there but one was reached in a way worth a look. No mark means every key value is in the document word for word; those can be approved without opening. |
| 1:35 | Open Dolostop 500 from the glare photo, zoom the page | The source sits beside the fields. The unit price is under the glare and the pipeline said so rather than guessing. I can read it on the zoomed page, so I click the field and type it: it shows as set by reviewer with the original kept, and the line can be approved. |
| 2:10 | Open a Novara email line | The supplier corrected a price in a postscript. The later value wins, both are kept, and the line is amber so a person sees it. |
| 2:30 | Comparisons tab | The same product quoted by two suppliers, side by side, with an honest note when the currencies differ. And the Andina proforma arrived as a PDF and two scans: the copies are cross-checked field by field, and a one-letter misread on the fax was caught because the copies disagreed. |
| 2:55 | Press Apply decisions; terminal shows the applied line; open approved.csv | Apply runs the approve step: corrections first, then decisions. Thirty-one lines go on, five rejected, one held, every decision and both values in the audit. |
| 3:20 | Code: `src/docintel/ingest/` listing and `registry.py` | Extensibility is where the brief puts its weight. A new format is one loader registered on a media type; nothing downstream changes. Word and Excel are the built demonstration. A new supplier is nothing to write, because no supplier is named anywhere. A new model is a config string. |
| 3:45 | `evals/reports`, the live score report | Evaluation is 66 synthetic cases generated from exact truth, judged by the behaviour expected of each: extract, flag, degrade honestly, refuse. The first live run found ten wrong values at high confidence, all on scans, because the model's own transcript was vouching for the model. Checking names against the independent OCR reading brought that to two. The fixes replayed for free, because every live extraction is recorded. |
| 4:20 | Git log | Small commits that say why, and an agent log of who decided what. Thank you. |

Cuts if over time: the Comparisons tab (2:30) and the git log (4:20).
