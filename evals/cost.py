"""Cost per document from the tokens a run actually sent.

    uv run python -m evals.cost output/live-synth output/live-haiku-synth

Reads extractions/usage.jsonl in each folder. Prices are USD per million tokens and
are ASSUMPTIONS to verify against the provider's price page before quoting them.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

# input, output; USD per million tokens. Verify before quoting.
PRICES = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-5-5": (3.0, 15.0),
    "claude-opus-5-5": (5.0, 25.0),
}


def price_for(model: str) -> tuple[float, float] | None:
    for key, rates in PRICES.items():
        if key in model:
            return rates
    return None


def summarise(folder: Path) -> dict[str, object]:
    path = folder / "extractions" / "usage.jsonl"
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    per_doc: dict[str, dict[str, float]] = defaultdict(lambda: {"in": 0.0, "out": 0.0, "usd": 0.0})
    models: set[str] = set()
    for r in rows:
        rates = price_for(r["model"])
        models.add(r["model"])
        d = per_doc[r["doc_id"]]
        d["in"] += r["input_tokens"]
        d["out"] += r["output_tokens"]
        if rates:
            d["usd"] += r["input_tokens"] / 1e6 * rates[0] + r["output_tokens"] / 1e6 * rates[1]
    n = len(per_doc) or 1
    total_in = sum(d["in"] for d in per_doc.values())
    total_out = sum(d["out"] for d in per_doc.values())
    total_usd = sum(d["usd"] for d in per_doc.values())
    return {
        "folder": str(folder),
        "models": sorted(models),
        "documents": len(per_doc),
        "calls": len(rows),
        "input_tokens": int(total_in),
        "output_tokens": int(total_out),
        "usd_total": round(total_usd, 3),
        "usd_per_document": round(total_usd / n, 4),
        "tokens_per_document": int((total_in + total_out) / n),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folders", nargs="+", type=Path)
    args = ap.parse_args()
    print(
        "| Run | Model | Documents | Calls | Input tokens | Output tokens "
        "| USD total | USD per document |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for folder in args.folders:
        s = summarise(folder)
        print(
            f"| {folder.name} | {', '.join(s['models'])} | {s['documents']} | {s['calls']} | "
            f"{s['input_tokens']:,} | {s['output_tokens']:,} | {s['usd_total']:.2f} "
            f"| {s['usd_per_document']:.4f} |"
        )
    print("\nPrices are assumptions in evals/cost.py; verify against the provider's price page.")


if __name__ == "__main__":
    main()
