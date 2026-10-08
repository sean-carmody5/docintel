"""Loaders. Importing the package registers every loader with the registry."""

from docintel.ingest import (  # noqa: F401  (registration side effect)
    image_loader,
    json_loader,
    pdf_loader,
    text_loader,
)
from docintel.ingest.registry import load, load_bytes, registered
from docintel.ingest.sniff import sniff

__all__ = ["load", "load_bytes", "registered", "sniff"]
