# docintel

Document intelligence pipeline for supplier quotations. Takes a folder of mixed documents (JSON exports, PDFs, emails, scanned images, and whatever arrives next), extracts quotation lines into one schema, writes a table a person can review, and says exactly which values it is unsure of and why.

Built for the Axmed AI Engineer take-home. The [brief](docs/brief.md), the [plan](PLAN.md) and the [agent log](docs/agent-log.md) record what was asked, what was decided, and who decided it.

```mermaid
flowchart LR
  F[(folder)] --> D[discover]
  D -->|one per file| L
  subgraph P[per document, in parallel]
    direction LR
    L[load] --> X[extract] --> V[verify]
  end
  V --> R[reconcile]
  R --> W[write]
  W --> T[(review table)]
  T -.-> H{{person reviews}}
  H -->|approve| M[promote]
```

## Status

Evaluation data in place, pipeline build starting. See [PLAN.md](PLAN.md) for the architecture, the extension points, how confidence is computed, and the build sequence.

## Data

| Set | Where | What | Ground truth |
|---|---|---|---|
| Provided | `data/provided/` | The eight documents supplied with the brief | Hand-checked fixtures |
| Synthetic | `data/synthetic/` | 45 generated cases across JSON, PDF, email, scans, Excel, Word, CSV, hostile and misnamed files ([README](data/synthetic/README.md)) | Exact, by construction |
| Public | `data/public/` (git-ignored) | 37 real price lists, catalogues and RFQ forms from UNICEF, Global Fund, PAHO, national procurement bodies and manufacturers, fetched by `evals/public/fetch.py` | None, robustness only |

## Layout

```
data/provided/    the eight documents supplied with the brief
data/synthetic/   generated documents with known ground truth
data/public/      downloaded real documents, git-ignored
evals/synth/      synthetic generator
evals/public/     public sample sources and fetcher
src/docintel/     the pipeline
docs/             brief, agent log, write-up
```

## Running

Setup and run instructions follow once the pipeline exists.
