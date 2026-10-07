# Agent instructions for this repo

Take-home for Axmed: a document intelligence pipeline that extracts quotation lines from mixed supplier documents into a reviewable table. See PLAN.md for architecture and sequence.

## Commits

- Commit after every meaningful step: a working increment or a decision. Not once per session.
- Messages explain why, not what. Name the problem the change solves or the alternative rejected.
- Never squash, never amend a commit that has been pushed, never rewrite history.
- Record decisions and who made them (Seán or the agent) in docs/agent-log.md as they happen.

## Code

- Python 3.12, PEP 8, type hints, minimal. Basic meaningful error handling, no over-engineering.
- Plain Python for loaders, validation, reconciliation and writing. LangGraph only for orchestration. LangChain only for model calls.
- Never branch on filenames, supplier names or known field names. New formats go in loaders, nothing else changes.
- Tests run offline by default using recorded fixtures and a fake chat model. Real model calls only when `PIPELINE_LIVE=1`.
- Pin exact dependency versions.
- Secrets live in `.env`, which is git-ignored. Never commit keys.

## Style

- UK English in docs and comments. No em dashes.
- Docs and README stay visual: Mermaid diagrams over prose where a diagram shows the mechanism.
