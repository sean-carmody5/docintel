# The output table

`records.csv` is deliverable 2 from the brief: the records extracted from the eight provided documents, with confidence flags and source references. One row per quotation line, 37 rows.

| Columns | What they hold |
|---|---|
| `record_id`, `source_document`, `source_path`, `source_locator`, `parent_document` | Where the line came from, down to the line or item on the page |
| `supplier_name` ... `payment_terms` | Header facts shared by every line of a document |
| `product_name`, `inn`, `strength`, `dosage_form`, `uom`, `units_per_pack`, `price_per_uom`, `price_per_pack`, `price_basis`, `currency`, ... | The line itself, values exactly as written |
| `evidence` | The verbatim text each value was taken from, per field |
| `conf_*`, `confidence`, `overall_confidence` | Per-field confidence with the reasons for every deduction, and the line's overall score |
| `needs_review`, `review_reasons`, `flags`, `status` | Whether a person must look, why, and the line's status |

Produced by `uv run docintel run data/provided --out ... --extractor model --model anthropic:claude-sonnet-5-5`. The same records are in `review_report.md` (a report that leads with what to look at first), `conflicts.json` (products quoted by more than one supplier, and duplicate copies cross-checked) and `review.html` (the review page; open it from disk).
