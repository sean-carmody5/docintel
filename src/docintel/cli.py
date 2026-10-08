"""Command line: run a folder, approve a run, draw the graph.

docintel run data/provided --out output
docintel approve --thread-id <id> --out output
docintel draw
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from docintel.config import Settings
from docintel.graph import Pipeline, mermaid, resume, run, sqlite_checkpointer


def _settings(args: argparse.Namespace) -> Settings:
    return Settings.from_env(
        extractor=getattr(args, "extractor", None),
        model=getattr(args, "model", None),
        output_dir=Path(args.out) if getattr(args, "out", None) else None,
        ocr=False if getattr(args, "no_ocr", False) else None,
        as_of=date.fromisoformat(args.as_of) if getattr(args, "as_of", None) else None,
    )


def cmd_run(args: argparse.Namespace) -> int:
    settings = _settings(args)
    thread_id = args.thread_id or datetime.now(UTC).strftime("run-%Y%m%d-%H%M%S")
    pipeline = Pipeline(settings)
    checkpointer = sqlite_checkpointer(settings.output_dir / "checkpoints.sqlite")
    result = run(pipeline, Path(args.input_dir), thread_id=thread_id, checkpointer=checkpointer)
    values = result["values"]
    review = values.get("review", {})
    print(f"thread:        {thread_id}")
    print(f"documents:     {len(values.get('documents', []))}")
    print(
        f"records:       {review.get('records', 0)} ({review.get('needs_review', 0)} need review)"
    )
    for name, path in values.get("outputs", {}).items():
        print(f"{name + ':':14} {path}")
    if result["interrupted"]:
        print("\nStopped for review. Edit the table, then:")
        print(f"  docintel approve --thread-id {thread_id} --out {settings.output_dir}")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    settings = _settings(args)
    pipeline = Pipeline(settings)
    checkpointer = sqlite_checkpointer(settings.output_dir / "checkpoints.sqlite")
    decisions: dict[str, str] = {}
    if args.decisions:
        payload = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
        decisions = payload.get("decisions", payload) if isinstance(payload, dict) else {}
    state = resume(
        pipeline,
        thread_id=args.thread_id,
        approved=not args.reject,
        checkpointer=checkpointer,
        decisions=decisions,
    )
    print(f"approved:  {state.get('approved')}")
    print(f"promoted:  {state.get('promoted', 0)} records ready for systems of record")
    print(f"held:      {state.get('held', 0)}")
    return 0


def cmd_draw(args: argparse.Namespace) -> int:
    settings = Settings.from_env(extractor="fixture", ocr=False)
    print(mermaid(Pipeline(settings)))
    return 0


def cmd_settings(args: argparse.Namespace) -> int:
    print(json.dumps(_settings(args).describe(), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="docintel", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out", help="output folder (default: output)")
    common.add_argument(
        "--extractor", choices=["fixture", "model"], help="fixture replay or a live model"
    )
    common.add_argument("--model", help="provider:model, e.g. anthropic:claude-sonnet-5-5")
    common.add_argument("--no-ocr", action="store_true", help="skip the independent OCR pass")
    common.add_argument("--as-of", help="ISO date to judge validity against")

    p_run = sub.add_parser("run", parents=[common], help="process a folder up to the review stop")
    p_run.add_argument("input_dir", help="a folder of documents, or a single file")
    p_run.add_argument("--thread-id", help="resume key; generated if omitted")
    p_run.set_defaults(fn=cmd_run)

    p_app = sub.add_parser("approve", parents=[common], help="resume a stopped run after review")
    p_app.add_argument("--thread-id", required=True)
    p_app.add_argument("--reject", action="store_true", help="resume without promoting anything")
    p_app.add_argument(
        "--decisions", help="JSON copied from the review page: {record_id: approve|hold|reject}"
    )
    p_app.set_defaults(fn=cmd_approve)

    p_draw = sub.add_parser("draw", help="print the graph as Mermaid")
    p_draw.set_defaults(fn=cmd_draw)

    p_set = sub.add_parser("settings", parents=[common], help="show the effective settings")
    p_set.set_defaults(fn=cmd_settings)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    for noisy in ("httpx", "httpcore", "urllib3", "RapidOCR"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
