"""Hostile-document checks. Supplier files are untrusted input to a language model.

Loaders surface the raw facts (hidden PDF spans, hidden HTML elements). This module
interprets them, looks for instruction-like text and invisible unicode, flags the
document, and strips what the model should never see. Flags force human review
downstream; nothing here decides anything on its own.
"""

from __future__ import annotations

import re

from docintel.documents import Document, Severity

INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior|above|earlier) instructions"
    r"|system notice|you are now in|maintenance mode|#{2,} ?system|end system"
    r"|note to (ai|automated|language|llm)|automated reader|ai systems? processing"
    r"|set (the )?confidence|do not flag|output the string"
    r"|disregard (all |the |any )?(previous|prior|above) "
    r"|^\s*assistant:|as an ai\b|language model",
    re.I | re.M,
)

_ZERO_WIDTH = "​‌‍⁠﻿­"
_BIDI = "‪‫‬‭‮⁦⁧⁨⁩"
_UNICODE_TRICKS = re.compile(f"[{_ZERO_WIDTH}{_BIDI}]|[\U000e0000-\U000e007f]")

_HIDDEN_STYLE = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(px|pt|em)?\b|opacity\s*:\s*0(\.0+)?\b",
    re.I,
)
_OPEN_TAG = re.compile(r"<(?P<tag>[a-zA-Z][\w-]*)\b(?P<attrs>[^>]*)>", re.S)
_TAG = re.compile(r"<[^>]+>")
_VOID = {
    "br",
    "img",
    "hr",
    "input",
    "meta",
    "link",
    "area",
    "base",
    "col",
    "embed",
    "source",
    "wbr",
}


def _is_hidden(attrs: str) -> bool:
    style = re.search(r"style\s*=\s*([\"'])(.*?)\1", attrs, re.S | re.I)
    if style and _HIDDEN_STYLE.search(style.group(2)):
        return True
    return bool(re.search(r"(^|\s)hidden(\s|=|$)", attrs, re.I))


def _matching_close(html: str, tag: str, start: int) -> tuple[int, int]:
    """Index range of the close tag that balances an open tag whose body starts at `start`."""
    pattern = re.compile(rf"<(/?){re.escape(tag)}\b[^>]*>", re.I | re.S)
    depth = 1
    pos = start
    last: re.Match[str] | None = None
    while depth:
        m = pattern.search(html, pos)
        if m is None:
            return len(html), len(html)
        last = m
        depth += -1 if m.group(1) else 1
        pos = m.end()
    assert last is not None
    return last.start(), last.end()


def strip_hidden_html(html: str) -> tuple[str, list[str]]:
    """Remove elements styled invisible, nested or not. Returns cleaned HTML and hidden texts."""
    hidden: list[str] = []
    out: list[str] = []
    pos = 0
    while True:
        m = _OPEN_TAG.search(html, pos)
        if m is None:
            out.append(html[pos:])
            break
        tag = m.group("tag").lower()
        attrs = m.group("attrs")
        if tag in _VOID or attrs.rstrip().endswith("/") or not _is_hidden(attrs):
            out.append(html[pos : m.end()])
            pos = m.end()
            continue
        close_start, close_end = _matching_close(html, tag, m.end())
        text = re.sub(r"\s+", " ", _TAG.sub(" ", html[m.end() : close_start])).strip()
        if text:
            hidden.append(text)
        out.append(html[pos : m.start()])
        out.append(" ")
        pos = close_end
    return "".join(out), hidden


def find_unicode_tricks(text: str) -> list[str]:
    return sorted({f"U+{ord(ch):04X}" for ch in _UNICODE_TRICKS.findall(text)})


def strip_unicode_tricks(text: str) -> str:
    return _UNICODE_TRICKS.sub("", text)


def scan(doc: Document) -> None:
    """Add security flags to a loaded Document."""
    hidden_text: list[str] = list(doc.metadata.get("hidden_text", []))
    hidden_html: list[str] = list(doc.metadata.get("hidden_html", []))
    if hidden_text:
        doc.flag(
            "hidden_text",
            Severity.HIGH,
            f"{len(hidden_text)} invisible text span(s) in the file, e.g. {hidden_text[0][:80]!r}",
        )
    if hidden_html:
        doc.flag(
            "hidden_html",
            Severity.HIGH,
            f"{len(hidden_html)} hidden HTML element(s), e.g. {hidden_html[0][:80]!r}",
        )

    tricks = find_unicode_tricks(doc.text)
    if tricks:
        doc.flag(
            "unicode_hidden", Severity.HIGH, f"invisible or bidi characters: {', '.join(tricks)}"
        )
        doc.text = strip_unicode_tricks(doc.text)

    sources = [
        ("text", doc.text),
        ("hidden text", "\n".join(hidden_text)),
        ("hidden html", "\n".join(hidden_html)),
        ("html part", str(doc.metadata.get("html_part", ""))),
    ]
    for where, body in sources:
        if not body:
            continue
        m = INJECTION.search(body)
        if m:
            start = max(0, m.start() - 40)
            snippet = re.sub(r"\s+", " ", body[start : m.end() + 60]).strip()
            doc.flag("injection_phrase", Severity.HIGH, f"in {where}: ...{snippet}...")
            break
