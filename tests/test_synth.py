"""Invariants of the synthetic set: truth is internally consistent and every case has a file."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from evals.synth.build import CASES, build

SYNTH = Path("data/synthetic")


@pytest.fixture(scope="module")
def manifest(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("synthetic")
    return build(out, seed=7) | {"_out": out}


def test_every_case_builds_a_file(manifest: dict) -> None:
    out: Path = manifest["_out"]
    for case in manifest["cases"]:
        assert case["files"], case["id"]
        for name in case["files"]:
            size = (out / case["id"] / name).stat().st_size
            if case["variant"] == "empty":
                assert size == 0
            else:
                assert size > 0, f"{case['id']}/{name}"


def test_truth_prices_are_consistent(manifest: dict) -> None:
    out: Path = manifest["_out"]
    for case in manifest["cases"]:
        if "truth" not in case:
            continue
        truth = json.loads((out / case["truth"]).read_text(encoding="utf-8"))
        for ln in truth["quotation"]["lines"]:
            unit, pack, units = ln["price_per_uom"], ln["price_per_pack"], ln["units_per_pack"]
            assert units >= 1
            assert abs(unit * units - pack) <= max(0.01, pack * 0.01), (case["id"], ln["line_no"])
            if ln["superseded"]:
                assert ln["superseded"]["old"] != ln["superseded"]["new"]
                assert ln["superseded"]["new"] == ln[ln["superseded"]["field"]]
            if ln["price_basis"] == "tiered":
                tiers = ln["price_tiers"]
                assert tiers and tiers[0]["price_per_pack"] == pack
                assert [t["price_per_pack"] for t in tiers] == sorted(
                    (t["price_per_pack"] for t in tiers), reverse=True
                )
            if ln["quantity"] is not None:
                net = unit * (1 - (ln["discount_pct"] or 0) / 100)
                assert abs(ln["quantity"] * net - ln["extended_amount"]) < 0.02


def test_corrections_appear_in_documents(manifest: dict) -> None:
    out: Path = manifest["_out"]
    for case in manifest["cases"]:
        if "correction" not in case.get("features", []) or case["kind"] not in (
            "eml",
            "csv",
            "chat",
            "xml",
            "html",
            "txt",
        ):
            continue
        truth = json.loads((out / case["truth"]).read_text(encoding="utf-8"))
        corrected = [ln for ln in truth["quotation"]["lines"] if ln["superseded"]]
        assert corrected, case["id"]
        text = (out / case["id"] / case["files"][0]).read_text(encoding="utf-8", errors="replace")
        # quoted-printable can wrap a number across lines; strip soft breaks before searching
        text = text.replace("=\n", "")
        for ln in corrected:
            new = ln["superseded"]["new"]
            assert str(new) in text or f"{new:.4f}" in text or f"{new:.3f}" in text, (
                case["id"],
                new,
            )


def test_duplicate_sets_share_truth(manifest: dict) -> None:
    out: Path = manifest["_out"]
    for root, copies in manifest["duplicate_sets"].items():
        root_truth = json.loads((out / root / "truth.json").read_text(encoding="utf-8"))[
            "quotation"
        ]
        for copy in copies:
            copy_truth = json.loads((out / copy / "truth.json").read_text(encoding="utf-8"))[
                "quotation"
            ]
            assert copy_truth == root_truth, (root, copy)


def test_case_ids_are_unique() -> None:
    ids = [c.id for c in CASES]
    assert len(ids) == len(set(ids))


def test_committed_set_matches_manifest() -> None:
    if not SYNTH.exists():
        pytest.skip("committed synthetic set not present")
    manifest = json.loads((SYNTH / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["case_count"] == len(CASES)
    for case in manifest["cases"]:
        for name in case["files"]:
            assert (SYNTH / case["id"] / name).exists(), f"{case['id']}/{name}"
