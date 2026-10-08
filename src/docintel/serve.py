"""Serve the review page locally so the reviewer can finish from the page.

A small HTTP server on the loopback interface that serves the output folder and accepts
one POST: the page's decisions and corrections. The callback writes decisions.json,
applies them through the pipeline, and the result goes back to the page. Standard
library only, nothing listens beyond 127.0.0.1.
"""

from __future__ import annotations

import json
import logging
import threading
import webbrowser
from collections.abc import Callable
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

Apply = Callable[[dict[str, Any]], dict[str, Any]]


class ReviewHandler(SimpleHTTPRequestHandler):
    """Static files from the output folder, plus POST /api/decisions."""

    apply: Apply
    out_dir: Path

    def do_POST(self) -> None:  # noqa: N802 - http.server's naming
        if self.path != "/api/decisions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("payload must be a JSON object")
            (self.out_dir / "decisions.json").write_text(
                json.dumps(payload, indent=2), encoding="utf-8", newline="\n"
            )
            result = self.apply(payload)
            body = json.dumps({"ok": True, **result}, default=str).encode("utf-8")
            status = 200
        except Exception as exc:  # noqa: BLE001 - the page shows the message
            log.exception("applying decisions failed")
            body = json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}).encode()
            status = 500
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - base class name
        log.debug("review server: " + format, *args)


def serve_review(
    out_dir: Path, apply: Apply, *, open_browser: bool = True, port: int = 0
) -> ThreadingHTTPServer:
    """Start serving out_dir in a daemon thread. Returns the server; url_of() gives the page."""
    handler = type(
        "BoundReviewHandler", (ReviewHandler,), {"apply": staticmethod(apply), "out_dir": out_dir}
    )
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(handler, directory=str(out_dir)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if open_browser:
        webbrowser.open(url_of(server))
    return server


def url_of(server: ThreadingHTTPServer) -> str:
    return f"http://127.0.0.1:{server.server_address[1]}/review.html"
