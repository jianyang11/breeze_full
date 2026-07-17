from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "breeze" / "scripts" / "q1_runs_storage_audit.py"
SPEC = importlib.util.spec_from_file_location("q1_runs_storage_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_primary_release_root_overrides_smoke_name() -> None:
    name = "phaseB_cwru_within_load0_llm_full_v1_combined"
    assert MODULE.classify_root(name, 0) == "PRIMARY_RELEASE_REQUIRED"
    assert MODULE.classify_root("development_smoke", 0) == "DEVELOPMENT_SMOKE_OR_PILOT"


def test_keeper_priority_primary_then_frozen_then_lexicographic() -> None:
    rows = [
        {"scope": "runs", "root": "z_dev", "path": "z"},
        {"scope": "tracked_frozen", "root": "__tracked_frozen__", "path": "frozen"},
        {
            "scope": "runs",
            "root": "rescreen_v2_full",
            "path": "primary",
        },
    ]
    assert MODULE.choose_keeper(rows)["path"] == "primary"
    assert MODULE.choose_keeper(rows[:2])["path"] == "frozen"
    assert MODULE.choose_keeper([rows[0], {"scope": "runs", "root": "a", "path": "a"}])[
        "path"
    ] == "a"


def test_root_mentions_are_boundary_aware_and_not_double_counted() -> None:
    names = ["run_a", "run_a_long"]
    corpus = [
        "breeze/runs/run_a/file.json runs/run_a and breeze/runs/run_a_long/x",
        "notruns/run_a runs/run_a_suffix",
    ]
    assert MODULE.count_root_mentions(names, corpus) == {
        "run_a": 2,
        "run_a_long": 1,
    }
