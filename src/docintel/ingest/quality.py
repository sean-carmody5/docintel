"""How much to trust a text layer.

A scanner's OCR layer, a broken font encoding or a repaired file can all yield text
that looks fine to a byte count and is garbage to a reader. This scores raw text
without a dictionary: odd characters, digits inside words, vowel-less words and
stray marks. Tuned on the synthetic set, where clean and deliberately garbled PDFs
share a truth, and checked against real scanned PDFs in the public set.
"""

from __future__ import annotations

import re

_ALLOWED = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    " \n\t\r.,;:/()%&+-*#'\"=_|[]<>@€£$"
)
_SPLIT = re.compile(r"[\s|/\-]+")
_WORD = re.compile(r"[A-Za-z]{2,}")
_DIGIT_IN_WORD = re.compile(r"[A-Za-z]\d[A-Za-z]|^[A-Za-z]{2,}\d+[A-Za-z]{2,}$")
_UNIT_LIKE = re.compile(
    r"^\d+(\.\d+)?(mg|mcg|g|kg|ml|l|iu|x|mm|cm|%|h|d)s?$"  # 500mg, 10x, 20ml
    r"|^[A-Z]{1,5}\d{1,8}[A-Z]?$"  # J01CR02 is handled below; HA742, S1300008
    r"|^\d+[A-Za-z]{1,3}$"  # 30s, 1st
    r"|^[A-Z]\d{2}[A-Z]{2}\d{2}$",  # ATC codes like J01CR02
    re.I,
)
_STRAY = re.compile(r"[~`^]|\w'\w'")
_VOWEL = re.compile(r"[aeiouyAEIOUY]")
_MARKUP = re.compile(r"\*\*|<br>|</?sup>|</?sub>|</?b>|</?i>")


def text_quality(text: str) -> float:
    """0 is certainly garbage, 1 is clean. Below QUALITY_THRESHOLD the layer is not trusted."""
    if not text or not text.strip():
        return 0.0
    text = _MARKUP.sub(" ", text)
    tokens = [t.strip(".,;:()[]\"'") for t in _SPLIT.split(text) if t]
    words = [t for t in tokens if _WORD.search(t)]
    if not words:
        return 0.5
    odd_chars = sum(1 for ch in text if ch not in _ALLOWED and not ch.isalpha()) / len(text)
    bad = 0
    for w in words:
        if _UNIT_LIKE.match(w):
            continue
        if (
            _DIGIT_IN_WORD.search(w)
            or _STRAY.search(w)
            or (len(w) >= 4 and w.isalpha() and not _VOWEL.search(w))
        ):
            bad += 1
    bad_ratio = bad / len(words)
    score = 1.0 - min(1.0, odd_chars * 20) * 0.4 - min(1.0, bad_ratio * 6) * 0.6
    return round(max(0.0, score), 3)


QUALITY_THRESHOLD = 0.75
