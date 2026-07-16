from breeze.scripts.compute_global_bh_sensitivity import bh_adjust, core_rows


def test_bh_adjust_known_family_and_monotonicity() -> None:
    adjusted = bh_adjust([0.01, 0.04, 0.03, 0.002])
    assert adjusted == [0.02, 0.04, 0.04, 0.008]
    ordered = sorted(zip([0.01, 0.04, 0.03, 0.002], adjusted))
    assert [value for _, value in ordered] == sorted(value for _, value in ordered)


def test_frozen_core_family_definition() -> None:
    rows = core_rows()
    assert len(rows) == 102
    assert sum(row["dataset"] == "PU" for row in rows) == 12
    assert sum(row["dataset"] == "CWRU" for row in rows) == 72
    assert sum(row["dataset"] == "Berkeley" for row in rows) == 18
