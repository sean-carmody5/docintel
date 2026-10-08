"""The review server: serves the output folder, applies what the page posts."""

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from docintel.serve import serve_review, url_of


def test_post_decisions_writes_the_file_and_returns_the_result(tmp_path: Path) -> None:
    (tmp_path / "review.html").write_text("<title>Quotation Review</title>", encoding="utf-8")
    seen: list[dict[str, Any]] = []

    def apply(payload: dict[str, Any]) -> dict[str, Any]:
        seen.append(payload)
        return {"approved": 2, "rejected": 1, "held": 0, "corrected": 1, "approved_csv": "x.csv"}

    server = serve_review(tmp_path, apply, open_browser=False)
    try:
        base = url_of(server).rsplit("/", 1)[0]
        with urllib.request.urlopen(url_of(server)) as resp:
            assert b"Quotation Review" in resp.read()
        body = json.dumps({"decisions": {"a:1": "approve"}, "corrections": {}}).encode()
        req = urllib.request.Request(
            base + "/api/decisions", data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
        assert result["ok"] and result["approved"] == 2 and result["corrected"] == 1
        assert seen == [{"decisions": {"a:1": "approve"}, "corrections": {}}]
        saved = json.loads((tmp_path / "decisions.json").read_text(encoding="utf-8"))
        assert saved["decisions"] == {"a:1": "approve"}

        bad = urllib.request.Request(
            base + "/api/decisions", data=b"[1]", headers={"Content-Type": "application/json"}
        )
        try:
            urllib.request.urlopen(bad)
            raise AssertionError("expected a 500")
        except urllib.error.HTTPError as err:
            assert err.code == 500 and "payload" in json.loads(err.read())["error"]
    finally:
        server.shutdown()
