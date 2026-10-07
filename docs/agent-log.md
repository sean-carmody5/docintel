# Agent log

Agent-generated summary of the planning and build conversation between Seán and Claude Code (Claude Fable 5.1). Kept current from the first commit. Entries note who steered each decision.

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
