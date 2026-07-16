from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "breeze" / "paper" / "main_cas.tex"
VERIFIER = ROOT / "breeze" / "src" / "verifier" / "v2.py"
GATE_ABLATION = ROOT / "breeze" / "scripts" / "run_pu_gate_ablation.py"


def _paper_predicate(value: float, direction: str, lower: float, upper: float) -> bool:
    if direction == "two_sided":
        return lower <= value <= upper
    if direction == "upper":
        return value <= upper
    if direction == "lower":
        return value >= lower
    raise ValueError(direction)


@pytest.mark.parametrize(
    ("value", "direction", "expected"),
    [
        (-1.0, "two_sided", False),
        (0.0, "two_sided", True),
        (1.0, "two_sided", True),
        (2.0, "two_sided", True),
        (3.0, "two_sided", False),
        (-1.0, "upper", True),
        (2.0, "upper", True),
        (3.0, "upper", False),
        (-1.0, "lower", False),
        (0.0, "lower", True),
        (3.0, "lower", True),
    ],
)
def test_direction_specific_predicate_truth_table(value: float, direction: str, expected: bool):
    assert _paper_predicate(value, direction, lower=0.0, upper=2.0) is expected


def test_paper_uses_disjoint_direction_specific_relations_and_empty_set_clause():
    text = PAPER.read_text()
    assert r"j\in\mathcal{J}_{\mathrm{int}}" in text
    assert r"j\in\mathcal{J}_{\mathrm{up}}" in text
    assert r"j\in\mathcal{J}_{\mathrm{low}}" in text
    assert r"\mathcal{S}_y=\varnothing" in text
    assert r"f_j(x)\leq u_{j,y,m}\ \text{or}\ f_j(x)\geq l_{j,y,m}" not in text


def test_v2_source_relations_match_the_paper_partition():
    text = VERIFIER.read_text()
    assert 'axis_passed = axis_dist <= float(st_cal["axis_threshold"])' in text
    assert "bad = np.where((vals < lo) | (vals > hi))[0]" in text
    assert "passed = dist <= thr" in text
    assert 'passed = mc["sideband_prominence"] >= mc_cal["fault_min"]' in text
    assert (
        'ok = sc["fund_prominence"] >= rec["prom_min"] '
        'and rec["energy_lo"] <= er <= rec["energy_hi"]'
    ) in text
    assert 'if sc["fund_prominence"] > rec["prom_max"]:' in text


def test_empty_selected_set_passes_only_the_pool_diversity_stage():
    text = GATE_ABLATION.read_text()
    assert "if active_delta is None or not selected_z:" in text
    assert "nearest >= active_delta" in text
