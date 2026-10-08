"""Is each extracted value actually in the source? Is the evidence quote real?

The model is asked to quote its source. Code checks the quote exists and contains
the value, and separately searches the whole text for the value itself. A value
with no trace in the source is the single strongest sign of a hallucination.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Grounding:
    value_found: bool
    evidence_found: bool
    evidence_has_value: bool
    method: str


_NUMERIC = re.compile(r"^[\s$€£]*[\d.,\s]+$")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def number_forms(value: float | int) -> set[str]:
    """Ways a document might print this number: separators, comma decimals, trailing zeros."""
    forms: set[str] = set()
    if isinstance(value, bool):
        return forms
    if float(value).is_integer():
        n = int(value)
        forms.update({str(n), f"{n:,}", f"{n:,}".replace(",", "."), f"{n:,}".replace(",", " ")})
        forms.update({f"{n}.0", f"{n}.00", f"{n}.000", f"{n},00", f"{n:,}.00"})
        return forms
    for decimals in range(2, 7):
        s = f"{value:.{decimals}f}"
        forms.add(s)
        forms.add(s.replace(".", ","))
        forms.add(f"{value:,.{decimals}f}")
        stripped = s.rstrip("0")
        forms.add(stripped)
        forms.add(stripped.replace(".", ","))
    return {f for f in forms if f}


def _contains_number(text: str, form: str) -> bool:
    # Not inside a longer digit run, and not the head of a thousands group (12 in 12,345).
    # A plain comma before the number is allowed: CSV delimiters sit there.
    pattern = r"(?<![\d.])" + re.escape(form) + r"(?!\d)(?!,\d{3}(?!\d))"
    return re.search(pattern, text) is not None


def value_in_text(value: object, text: str) -> bool:
    if value is None or text == "":
        return False
    if isinstance(value, bool):
        return True
    low = _norm(text)
    if isinstance(value, int | float):
        return any(_contains_number(low, f.lower()) for f in number_forms(value))
    needle = _norm(str(value))
    if not needle:
        return False
    if needle in low:
        return True
    # Tolerate OCR noise and column truncation: three quarters of the words is a match.
    words = [w for w in re.split(r"[^\w.]+", needle) if len(w) >= 3]
    if not words:
        return False
    hits = sum(w in low for w in words)
    return hits >= max(1, -(-len(words) * 3 // 4))


def ground(value: object, evidence: str | None, text: str) -> Grounding:
    found = value_in_text(value, text)
    if not evidence:
        return Grounding(found, False, False, "no_evidence")
    if isinstance(value, int | float) and _NUMERIC.match(evidence):
        # Evidence for a number is the number; how it was formatted is not a disagreement.
        return Grounding(found, found, True, "numeric")
    ev = _norm(evidence)
    low = _norm(text)
    evidence_found = ev in low
    if not evidence_found:
        words = [w for w in re.split(r"[^\w.]+", ev) if len(w) >= 3]
        evidence_found = bool(words) and sum(w in low for w in words) >= max(
            1, int(len(words) * 0.7)
        )
    has_value = value_in_text(value, evidence)
    return Grounding(found, evidence_found, has_value, "evidence")
