"""Excel and Word: tables become markdown tables, everything else becomes lines."""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import openpyxl
from docx import Document as WordDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from docintel.documents import Document, Kind, LoaderError, Severity, document_id
from docintel.ingest.registry import register

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_ROWS_PER_SHEET = 2000


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime | date):
        return (
            value.isoformat()[:10]
            if isinstance(value, date) and not isinstance(value, datetime)
            else value.isoformat()
        )
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def markdown_table(rows: list[list[str]]) -> str:
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    head, *body = rows
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * width]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def rows_to_markdown(rows: list[list[str]]) -> str:
    """Sparse rows (one or two values) read as lines; dense runs read as a table."""
    out: list[str] = []
    table: list[list[str]] = []

    def flush() -> None:
        if table:
            out.append(markdown_table(table) if len(table) > 1 else " | ".join(table[0]))
            table.clear()

    for row in rows:
        values = [c for c in row if c]
        if not values:
            flush()
            continue
        if len(values) <= 2:
            flush()
            out.append(": ".join(values) if len(values) == 2 else values[0])
        else:
            last = max(i for i, c in enumerate(row) if c) + 1
            table.append(row[:last])
    flush()
    return "\n\n".join(out)


@register(XLSX)
def load_xlsx(path: Path, data: bytes, media_type: str) -> Document:
    try:
        wb = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
    except Exception as err:
        raise LoaderError("unreadable", f"not a readable workbook: {err}") from err
    doc = Document(
        id=document_id(data), source_path=path, kind=Kind.SPREADSHEET, media_type=media_type
    )
    sections: list[str] = []
    sheet_rows: dict[str, int] = {}
    for ws in wb.worksheets:
        rows: list[list[str]] = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= MAX_ROWS_PER_SHEET:
                doc.flag(
                    "row_cap",
                    Severity.WARNING,
                    f"sheet {ws.title}: only {MAX_ROWS_PER_SHEET} rows read",
                )
                break
            rows.append([_cell(v) for v in row])
        sheet_rows[ws.title] = len(rows)
        body = rows_to_markdown(rows)
        if body:
            sections.append(f"## Sheet: {ws.title}\n\n{body}")
    wb.close()
    doc.metadata["sheets"] = sheet_rows
    doc.text = "\n\n".join(sections)
    doc.text_quality = 1.0 if doc.text else 0.0
    if not doc.text:
        doc.flag("empty_workbook", Severity.WARNING, "no non-empty cells")
    return doc


def _iter_body(word: Any) -> list[Paragraph | Table]:
    items: list[Paragraph | Table] = []
    for child in word.element.body.iterchildren():
        if child.tag == qn("w:p"):
            items.append(Paragraph(child, word))
        elif child.tag == qn("w:tbl"):
            items.append(Table(child, word))
    return items


@register(DOCX)
def load_docx(path: Path, data: bytes, media_type: str) -> Document:
    try:
        word = WordDocument(BytesIO(data))
    except Exception as err:
        raise LoaderError("unreadable", f"not a readable Word document: {err}") from err
    doc = Document(id=document_id(data), source_path=path, kind=Kind.WORD, media_type=media_type)
    parts: list[str] = []
    tables = 0
    for item in _iter_body(word):
        if isinstance(item, Paragraph):
            text = item.text.strip()
            if not text:
                continue
            style = (item.style.name if item.style is not None else "") or ""
            if style.startswith("Heading"):
                parts.append(f"## {text}")
            elif style.startswith("List"):
                parts.append(f"- {text}")
            else:
                parts.append(text)
        else:
            tables += 1
            rows = [[_cell(c.text) for c in r.cells] for r in item.rows]
            if rows:
                parts.append(markdown_table(rows))
    doc.metadata.update({"tables": tables, "paragraphs": len(word.paragraphs)})
    props = word.core_properties
    for key in ("author", "title", "subject"):
        value = getattr(props, key, None)
        if value:
            doc.metadata[key] = value
    doc.text = "\n\n".join(parts)
    doc.text_quality = 1.0 if doc.text else 0.0
    return doc
