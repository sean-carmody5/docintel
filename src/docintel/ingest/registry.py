"""Media type to loader. Adding a format is one function and one decorator.

Resolution order for a file: exact media type, then the type's family wildcard
(`text/*`), then the generic text loader for anything that decodes as text, then
a failed Document with the reason. Nothing is silently skipped.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from docintel.documents import Document, LoaderError, failed_document
from docintel.ingest import sniff as _sniff
from docintel.ingest.security import scan

log = logging.getLogger(__name__)

Loader = Callable[[Path, bytes, str], Document]

_LOADERS: dict[str, Loader] = {}
MAX_BYTES = 50 * 1024 * 1024


def register(*media_types: str) -> Callable[[Loader], Loader]:
    def deco(fn: Loader) -> Loader:
        for m in media_types:
            if m in _LOADERS:
                raise ValueError(f"loader already registered for {m}: {_LOADERS[m].__name__}")
            _LOADERS[m] = fn
        return fn

    return deco


def registered() -> dict[str, str]:
    return {m: fn.__name__ for m, fn in sorted(_LOADERS.items())}


def resolve(media_type: str) -> Loader | None:
    if media_type in _LOADERS:
        return _LOADERS[media_type]
    family = media_type.split("/")[0] + "/*"
    if family in _LOADERS:
        return _LOADERS[family]
    if media_type.startswith("text/") or media_type in ("application/json", "application/xml"):
        return _LOADERS.get("text/*")
    return None


def load_bytes(path: Path, data: bytes) -> Document:
    media = _sniff.sniff(data, path.suffix)
    if media == _sniff.EMPTY:
        return failed_document(path, media, LoaderError("empty", "zero bytes"))
    if len(data) > MAX_BYTES:
        return failed_document(
            path, media, LoaderError("too_large", f"{len(data)} bytes exceeds {MAX_BYTES}"), data
        )
    loader = resolve(media)
    if loader is None:
        return failed_document(
            path, media, LoaderError("unsupported", f"no loader for {media}"), data
        )
    try:
        doc = loader(path, data, media)
    except LoaderError as err:
        return failed_document(path, media, err, data)
    except Exception as err:  # a loader bug must surface as a record, not a crashed run
        log.exception("loader %s failed on %s", loader.__name__, path)
        return failed_document(
            path, media, LoaderError("unreadable", f"{type(err).__name__}: {err}"), data
        )
    scan(doc)
    return doc


def load(path: Path) -> Document:
    return load_bytes(path, path.read_bytes())
