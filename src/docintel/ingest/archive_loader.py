"""ZIP archives: each member becomes a child Document. Suppliers bundle."""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

from docintel.documents import Document, Kind, LoaderError, Severity, document_id
from docintel.ingest.registry import load_bytes, register

MAX_MEMBERS = 50
MAX_MEMBER_BYTES = 50 * 1024 * 1024


@register("application/zip")
def load_zip(path: Path, data: bytes, media_type: str) -> Document:
    try:
        zf = zipfile.ZipFile(BytesIO(data))
    except zipfile.BadZipFile as err:
        raise LoaderError("unreadable", f"corrupt zip: {err}") from err
    doc = Document(id=document_id(data), source_path=path, kind=Kind.ARCHIVE, media_type=media_type)
    with zf:
        members = [
            m
            for m in zf.infolist()
            if not m.is_dir()
            and not m.filename.startswith("__MACOSX/")
            and not Path(m.filename).name.startswith(".")
        ]
        if len(members) > MAX_MEMBERS:
            doc.flag(
                "member_cap",
                Severity.WARNING,
                f"{len(members)} members, first {MAX_MEMBERS} loaded",
            )
        listing: list[str] = []
        for m in members[:MAX_MEMBERS]:
            listing.append(f"- {m.filename} ({m.file_size} bytes)")
            if m.file_size > MAX_MEMBER_BYTES:
                doc.flag(
                    "member_too_large",
                    Severity.WARNING,
                    f"{m.filename} skipped: {m.file_size} bytes",
                )
                continue
            if m.flag_bits & 0x1:
                doc.flag(
                    "member_encrypted", Severity.WARNING, f"{m.filename} is password protected"
                )
                continue
            child = load_bytes(Path(m.filename), zf.read(m))
            child.parent_id = doc.id
            child.metadata["member_of"] = path.name
            doc.children.append(child)
    doc.text = "Archive members:\n" + "\n".join(listing)
    doc.text_quality = 1.0
    doc.metadata["members"] = [m.filename for m in members]
    return doc
