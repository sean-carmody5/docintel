# Evaluation reports

Every run below is scored by `evals/score.py` against the synthetic truth, judged by the behaviour each case expects. "Silent errors" are wrong values at high confidence, the number that matters most; "flagged" are wrong values at medium or low confidence, which the review page surfaces.

| Report | Set | Model | Passed | Silent errors | Notes |
|---|---|---|---|---|---|
| `live_sonnet-5-5_synthetic_final.md` | Synthetic, 66 cases | Sonnet 5.5 | 65 of 66 | 2 | One cropped photo where the model and the OCR read the same digit. Recall 0.986, no invented lines. |
| `holdout_sonnet-5-5_final.md` | Held-out seed, 66 cases, never opened while tuning | Sonnet 5.5 | 63 of 66 | 2 | The generalisation result. Same cropped-photo case. |
| `live_haiku-4-5_synthetic_final.md` | Synthetic | Haiku 4.5 | 60 of 66 | 4 | 12 invented lines on scans. A quarter of Sonnet's cost. |
| `holdout_haiku-4-5_final.md` | Held-out seed | Haiku 4.5 | 54 of 66 | 14 | |
| `live_opus-5-5_synthetic_final.md` | Synthetic | Opus 5.5 | 60 of 66 | 5 | Four of the five are a pack size written into the strength. Nearly twice Sonnet's cost. |
| `agents_sonnet_synthetic.md`, `agents_opus_synthetic.md`, `agents_haiku_synthetic.md` | 24 to 25 covered cases | Claude Code subagents reading the documents by hand, before any live run | 24, 24, 3 | 0, 0, 1 | The two strong readers agreeing against the answer key found three defects in the truth, which were corrected. Haiku declined most formats. |
| `cost.md` | | | | | Tokens recorded per call; prices in `evals/cost.py` are assumptions to verify. |

The recorded extractions behind the live runs are under `tests/fixtures/live/<model>/synthetic` and replay with `docintel run data/synthetic --fixtures <that folder>`. The held-out set is rebuilt with `python -m evals.synth.build --out data/synthetic_holdout --seed 7`; its recordings are not kept, so its numbers come from the reports here.

On the provided pack, every live model agreed with the hand-written fixtures on the key fields except where it left a value blank that the fixture writer had assumed (units per pack on bottle lines).
