"""Score a pipeline run over the synthetic set against truth and expectations.

    uv run python -m evals.score --records output/synthetic/records.csv --manifest data/synthetic/manifest.json

Accuracy is measured where truth exists. Behaviour is measured everywhere: every case
says what a correct pipeline does with it (`expect`), and calibration is measured across
all values: a wrong value at high confidence is the failure that matters most.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docintel.verify.normalise import normalise_inn, normalise_strength

KEY_FIELDS = (
    "product_name",
    "inn",
    "strength",
    "units_per_pack",
    "price_per_uom",
    "price_per_pack",
    "currency",
)
NUMERIC = {"units_per_pack", "price_per_uom", "price_per_pack", "moq_packs", "lead_time_days"}
SECURITY = {"hidden_text", "hidden_html", "unicode_hidden", "injection_phrase"}


@dataclass
class CaseScore:
    case_id: str
    kind: str
    expect: str
    truth_lines: int
    extracted_lines: int
    matched: int
    invented: int
    field_correct: Counter = field(default_factory=Counter)
    field_total: Counter = field(default_factory=Counter)
    wrong_high: int = 0
    wrong_total: int = 0
    passed: bool = False
    reason: str = ""

    @property
    def recall(self) -> float:
        return self.matched / self.truth_lines if self.truth_lines else 1.0

    @property
    def precision(self) -> float:
        return (
            (self.extracted_lines - self.invented) / self.extracted_lines
            if self.extracted_lines
            else 1.0
        )

    def accuracy(self, f: str) -> float | None:
        return self.field_correct[f] / self.field_total[f] if self.field_total[f] else None


def _num(x: Any) -> float | None:
    if x in (None, "", "None"):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _close(a: float | None, b: float | None, rel: float = 0.006) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= max(0.0006, rel * max(abs(a), abs(b)))


def _key(name: str | None, inn: str | None, strength: str | None) -> tuple[str, str, str]:
    return (
        re.sub(r"[^a-z0-9]", "", (name or "").lower()),
        normalise_inn(inn) or "",
        normalise_strength(strength) or "",
    )


def _match(record: dict[str, Any], truth_lines: list[dict[str, Any]], used: set[int]) -> int | None:
    rk = _key(record.get("product_name"), record.get("inn"), record.get("strength"))
    for i, t in enumerate(truth_lines):
        if i in used:
            continue
        tk = _key(t["product_name"], t["inn"], t["strength"])
        if rk[0] and rk[0] == tk[0]:
            return i
    for i, t in enumerate(truth_lines):
        if i in used:
            continue
        tk = _key(t["product_name"], t["inn"], t["strength"])
        if rk[1] and rk[1] == tk[1] and rk[2] == tk[2]:
            return i
    return None


def _field_ok(f: str, got: Any, want: Any) -> bool:
    if f in NUMERIC:
        return _close(_num(got), _num(want))
    if f == "inn":
        return normalise_inn(str(got) if got else None) == normalise_inn(want)
    if f == "strength":
        return normalise_strength(str(got) if got else None) == normalise_strength(want)
    if f == "currency":
        return str(got or "").upper() == str(want or "").upper()
    return (
        re.sub(r"\s+", " ", str(got or "")).strip().lower()
        == re.sub(r"\s+", " ", str(want or "")).strip().lower()
    )


def score_case(
    case: dict[str, Any], truth: dict[str, Any] | None, records: list[dict[str, Any]]
) -> CaseScore:
    expect = case["expect"]
    real = [r for r in records if r["status"] not in ("failed", "no_lines")]
    cs = CaseScore(case["id"], case["kind"], expect, 0, len(real), 0, 0)
    flags = {f["code"] for r in records for f in json.loads(r.get("flags") or "[]")}
    reasons = " ".join(r.get("review_reasons", "") for r in records)
    any_review = any(r.get("needs_review") in ("True", True, "1", 1) for r in records)

    if expect == "unsupported":
        cs.passed = bool(records) and all(r["status"] == "failed" for r in records)
        cs.reason = "failed record with reason" if cs.passed else "expected a failed record"
        return cs
    if truth is None:
        cs.passed = bool(records)
        cs.reason = "a record exists" if cs.passed else "no record at all"
        return cs

    truth_lines = truth["quotation"]["lines"]
    cs.truth_lines = len(truth_lines)
    used: set[int] = set()
    for r in real:
        i = _match(r, truth_lines, used)
        if i is None:
            cs.invented += 1
            continue
        used.add(i)
        cs.matched += 1
        t = truth_lines[i]
        conf = json.loads(r.get("confidence") or "{}")
        for f in KEY_FIELDS:
            want = t.get(f) if f != "currency" else truth["quotation"]["currency"]
            got = r.get(f)
            if want in (None, ""):
                continue
            cs.field_total[f] += 1
            ok = _field_ok(f, got, want)
            if ok:
                cs.field_correct[f] += 1
            elif got not in (None, ""):
                cs.wrong_total += 1
                if conf.get(f, {}).get("tier") == "high":
                    cs.wrong_high += 1

    acc = [cs.accuracy(f) for f in KEY_FIELDS if cs.accuracy(f) is not None]
    mean_acc = sum(acc) / len(acc) if acc else 0.0
    if expect == "extract":
        cs.passed = cs.recall >= 0.99 and cs.invented == 0 and mean_acc >= 0.98
        cs.reason = f"recall {cs.recall:.2f}, invented {cs.invented}, field accuracy {mean_acc:.2f}"
    elif expect == "extract_and_flag":
        hostile = bool(case.get("hostile"))
        flagged = bool(flags & SECURITY) if hostile else any_review
        cs.passed = cs.recall >= 0.99 and cs.invented == 0 and mean_acc >= 0.98 and flagged
        cs.reason = f"recall {cs.recall:.2f}, accuracy {mean_acc:.2f}, flagged={flagged}"
    elif expect in ("partial", "low_confidence"):
        cs.passed = cs.invented == 0 and cs.wrong_high == 0
        cs.reason = f"recall {cs.recall:.2f}, invented {cs.invented}, wrong-at-high {cs.wrong_high}"
    elif expect == "malformed":
        cs.passed = bool(records) and cs.invented == 0 and cs.wrong_high == 0
        cs.reason = f"records {len(records)}, invented {cs.invented}, wrong-at-high {cs.wrong_high}"
    else:
        cs.passed = bool(records)
        cs.reason = "unknown expectation; a record exists"
    _ = reasons
    return cs


def load_records(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def score_run(
    records: list[dict[str, Any]], manifest: dict[str, Any], root: Path
) -> dict[str, Any]:
    by_dir: dict[str, list[dict[str, Any]]] = defaultdict(list)
    dir_of_name: dict[str, str] = {}
    children: list[dict[str, Any]] = []
    for r in records:
        if r.get("parent_document"):
            children.append(r)  # an attachment or archive member: follows its parent's case
            continue
        rel = Path(r.get("source_path") or r["source_document"])
        try:
            case_dir = rel.resolve().relative_to(root.resolve()).parts[0]
        except (ValueError, IndexError):
            case_dir = rel.parent.name
        by_dir[case_dir].append(r)
        dir_of_name[r["source_document"]] = case_dir
    for r in children:
        by_dir[dir_of_name.get(r["parent_document"], r["parent_document"])].append(r)

    scores: list[CaseScore] = []
    for case in manifest["cases"]:
        truth = None
        if "truth" in case:
            truth = json.loads((root / case["truth"]).read_text(encoding="utf-8"))
        scores.append(score_case(case, truth, by_dir.get(case["id"], [])))

    calib: Counter = Counter()
    for r in records:
        conf = json.loads(r.get("confidence") or "{}")
        for f, c in conf.items():
            if f in KEY_FIELDS and r.get(f) not in (None, ""):
                calib[(c.get("tier"), "value")] += 1
    field_acc = {
        f: (sum(s.field_correct[f] for s in scores), sum(s.field_total[f] for s in scores))
        for f in KEY_FIELDS
    }
    groups: dict[str, list[CaseScore]] = defaultdict(list)
    for s in scores:
        groups[s.expect].append(s)
    return {
        "cases": len(scores),
        "passed": sum(s.passed for s in scores),
        "by_expect": {
            k: {"cases": len(v), "passed": sum(x.passed for x in v)}
            for k, v in sorted(groups.items())
        },
        "by_kind": {
            k: {"cases": len(v), "passed": sum(x.passed for x in v)}
            for k, v in sorted(_group(scores, "kind").items())
        },
        "field_accuracy": {f: (c / t if t else None) for f, (c, t) in field_acc.items()},
        "wrong_values": sum(s.wrong_total for s in scores),
        "wrong_at_high_confidence": sum(s.wrong_high for s in scores),
        "line_recall": _ratio(sum(s.matched for s in scores), sum(s.truth_lines for s in scores)),
        "invented_lines": sum(s.invented for s in scores),
        "details": [
            {
                "case": s.case_id,
                "kind": s.kind,
                "expect": s.expect,
                "passed": s.passed,
                "recall": round(s.recall, 3),
                "invented": s.invented,
                "wrong_high": s.wrong_high,
                "reason": s.reason,
            }
            for s in scores
        ],
    }


def _group(scores: list[CaseScore], attr: str) -> dict[str, list[CaseScore]]:
    out: dict[str, list[CaseScore]] = defaultdict(list)
    for s in scores:
        out[getattr(s, attr)].append(s)
    return out


def _ratio(a: int, b: int) -> float | None:
    return a / b if b else None


def render(summary: dict[str, Any], title: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"Cases passed: {summary['passed']} of {summary['cases']} | line recall {summary['line_recall']:.3f} | "
        f"invented lines {summary['invented_lines']} | wrong values {summary['wrong_values']} "
        f"(at high confidence: {summary['wrong_at_high_confidence']})",
        "",
        "## By expected outcome",
        "",
        "| Expect | Cases | Passed |",
        "|---|---|---|",
    ]
    lines += [f"| {k} | {v['cases']} | {v['passed']} |" for k, v in summary["by_expect"].items()]
    lines += ["", "## By kind", "", "| Kind | Cases | Passed |", "|---|---|---|"]
    lines += [f"| {k} | {v['cases']} | {v['passed']} |" for k, v in summary["by_kind"].items()]
    lines += ["", "## Field accuracy on matched lines", "", "| Field | Accuracy |", "|---|---|"]
    lines += [
        f"| {f} | {'' if a is None else f'{a:.3f}'} |" for f, a in summary["field_accuracy"].items()
    ]
    lines += [
        "",
        "## Cases",
        "",
        "| Case | Kind | Expect | Passed | Recall | Invented | Wrong at high | Reason |",
        "|---|---|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {d['case']} | {d['kind']} | {d['expect']} | {'yes' if d['passed'] else 'NO'} | {d['recall']:.2f} | "
        f"{d['invented']} | {d['wrong_high']} | {d['reason']} |"
        for d in summary["details"]
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=Path("data/synthetic/manifest.json"))
    ap.add_argument("--out", type=Path, default=None, help="markdown report path")
    ap.add_argument("--title", default="Synthetic set score")
    ap.add_argument(
        "--require-pass", action="store_true", help="exit non-zero if any case fails (for CI)"
    )
    args = ap.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    summary = score_run(load_records(args.records), manifest, args.manifest.parent)
    text = render(summary, args.title)
    out = args.out or args.records.with_name("score.md")
    out.write_text(text, encoding="utf-8", newline="\n")
    (out.with_suffix(".json")).write_text(
        json.dumps(summary, indent=2), encoding="utf-8", newline="\n"
    )
    print(text.split("\n## ")[0])
    print(f"written {out}")
    if args.require_pass and summary["passed"] < summary["cases"]:
        failed = [d["case"] for d in summary["details"] if not d["passed"]]
        raise SystemExit(f"{len(failed)} of {summary['cases']} cases failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
