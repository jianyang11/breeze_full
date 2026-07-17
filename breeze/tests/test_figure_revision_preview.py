from __future__ import annotations

import sys
from pathlib import Path
import json

import numpy as np
from PIL import Image


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import figure_revision_data as frd  # noqa: E402


def test_baseline_and_sources_are_restricted() -> None:
    paths = frd.all_formal_source_paths()
    frd.assert_allowed_sources(paths)
    assert paths
    names = "\n".join(str(path).lower() for path in paths)
    assert "trained_baselines" not in names
    assert "mt_private" not in names
    assert "/smoke/" not in names


def test_fig3_complete_paired_effects_and_deterministic_ci() -> None:
    summary, seeds, sources = frd.build_fig3_data()
    assert len(summary) == 36
    assert len(seeds) == 1200
    expected = {"PU": 20, "CWRU": 40, "Berkeley": 40}
    assert summary.groupby("dataset")["n_pairs"].unique().map(list).to_dict() == {
        dataset: [count] for dataset, count in expected.items()
    }
    for dataset, shots in {
        "PU": {5, 10, 25},
        "CWRU": {5, 10, 25},
        "Berkeley": {2, 5, 10},
    }.items():
        subset = summary[summary["dataset"].eq(dataset)]
        assert set(subset["shot"]) == shots
        assert set(subset["metric"]) == {"acc", "macro_f1"}
        assert set(subset["comparison"]) == (
            {"rule", "random_open_loop"} if dataset == "PU" else {"rule", "noise_aug"}
        )
    duplicate_keys = seeds.duplicated(
        ["dataset", "comparison", "shot", "metric", "seed"]
    )
    assert not duplicate_keys.any()
    first = summary.sort_values(["dataset", "comparison", "shot", "metric"]).reset_index(drop=True)
    second, _, _ = frd.build_fig3_data()
    second = second.sort_values(["dataset", "comparison", "shot", "metric"]).reset_index(drop=True)
    np.testing.assert_array_equal(
        first[["ci_low_pp", "ci_high_pp"]].to_numpy(),
        second[["ci_low_pp", "ci_high_pp"]].to_numpy(),
    )
    assert all(path.exists() for path in sources)


def test_medoid_selection_is_train_only_and_deterministic() -> None:
    sources = frd.load_pu_sources()
    first, _ = frd.select_pu_medoids(sources, ("healthy", "OR", "IR"))
    second, _ = frd.select_pu_medoids(sources, ("healthy", "OR", "IR"))
    first = first.sort_values(["class_index", "source"]).reset_index(drop=True)
    second = second.sort_values(["class_index", "source"]).reset_index(drop=True)
    assert len(first) == 12
    assert set(first["reference_split"]) == {"PU outer-training only"}
    assert first["source_index"].tolist() == second["source_index"].tolist()
    np.testing.assert_array_equal(
        first["distance_to_source_robust_center"].to_numpy(),
        second["distance_to_source_robust_center"].to_numpy(),
    )
    assert (first["n_features_retained"] > 1).all()


def test_fixed_envelope_configuration_and_absolute_values() -> None:
    medoids, waveforms, envelope, _ = frd.build_fig4_data(("OR", "IR"))
    assert len(medoids) == 8
    assert set(envelope["demodulation_hz"]) == {"500-2000"}
    assert set(envelope["class"]) == {"OR", "IR"}
    assert set(envelope["source"]) == {"real", "llm", "rule", "random_open_loop"}
    sources = frd.load_pu_sources()
    for _, row in medoids.iterrows():
        expected = sources[row["source"]][0][int(row["source_index"]), 0, : int(0.05 * frd.FS)]
        observed = waveforms[
            waveforms["class"].eq(row["class"])
            & waveforms["source"].eq(row["source"])
        ].sort_values("sample")["amplitude"].to_numpy()
        np.testing.assert_array_equal(observed, expected)
    group_peaks = waveforms.groupby(["class", "source"])["amplitude"].apply(
        lambda values: values.abs().max()
    )
    assert not np.allclose(group_peaks.to_numpy(), 1.0)
    assert (envelope[["q25", "median", "q75"]].to_numpy() >= 0).all()
    assert (envelope["q25"] <= envelope["median"]).all()
    assert (envelope["median"] <= envelope["q75"]).all()


def test_fig5_na_and_ratio_contract() -> None:
    ratios, diversity, sources = frd.build_fig5_data()
    assert set(ratios["dataset"]) == {"pu", "cwru", "berkeley"}
    berkeley = ratios[ratios["dataset"].eq("berkeley")]
    for metric in ("kurtosis_w1", "envelope_frequency_alignment_error_hz"):
        cells = berkeley[berkeley["metric"].eq(metric)]
        assert len(cells) > 0
        assert cells["log2_ratio"].isna().all()
    available = ratios[ratios["status"].eq("available")]
    recomputed = np.log2(
        available["method_distance"].to_numpy()
        / available["rule_distance"].to_numpy()
    )
    np.testing.assert_allclose(recomputed, available["log2_ratio"].to_numpy())
    assert (available[["method_distance", "rule_distance"]].to_numpy() > 0).all()
    assert set(diversity["direction"]) == {"no universal optimum"}
    assert "log2_ratio" not in diversity.columns
    assert all(path.exists() for path in sources)


def test_fig6_round_freeze_is_complete_and_monotone() -> None:
    cumulative, slots, sources = frd.build_fig6_data()
    assert len(slots) == 450
    assert slots.groupby("class").size().to_dict() == {
        "IR": 150,
        "OR": 150,
        "healthy": 150,
    }
    assert int(slots["final_admitted"].sum()) == 286
    assert set(slots.loc[slots["final_admitted"], "first_pass_round"]) == {
        0.0,
        1.0,
        2.0,
        3.0,
    }
    expected = {
        0: (205, 205),
        1: (36, 241),
        2: (27, 268),
        3: (18, 286),
    }
    pooled = cumulative[cumulative["class"].eq("all")]
    assert {
        int(row.feedback_round_k): (
            int(row.newly_admitted),
            int(row.cumulative_admitted),
        )
        for row in pooled.itertuples(index=False)
    } == expected
    for _, rows in cumulative.groupby("class"):
        rows = rows.sort_values("feedback_round_k")
        assert rows["cumulative_admitted"].is_monotonic_increasing
    assert all(path.exists() for path in sources)


def test_fig7_excludes_load0_and_preserves_discrete_states() -> None:
    cwru, pu, chain, sources = frd.build_fig7_data()
    assert len(cwru) == 18
    assert set(cwru["heldout_load"]) == {1, 2, 3}
    assert "lolo_load0" not in set(cwru["split"])
    assert set(cwru["metric"]) == {"acc", "macro_f1"}
    assert len(pu) == 48
    assert set(pu["version"]) == {"v1", "v2"}
    assert pu["passed_count"].between(0, 4).all()
    assert set(pu["registered_comparisons"]) == {4}
    assert chain["stage"].tolist() == ["v1", "v2", "v3", "v4", "v5", "v6"]
    assert chain["formal"].tolist() == [True, True, False, False, False, False]
    assert all(path.exists() for path in sources)


def test_preview_exports_and_manifests_are_complete() -> None:
    expected = {
        "fig3_downstream_effects": "fig3_downstream_effects",
        "fig4_waveform_envelope": "fig4_waveform_envelope",
        "fig5_physical_error": "fig5_physical_error",
        "fig6_admission_mechanism": "fig6_admission_mechanism",
        "fig7_cross_condition": "fig7_cross_condition",
        "figS1_pu_distributions": "figS1_pu_distributions",
        "figS2_healthy_waveform_envelope": "figS2_healthy_waveform_envelope",
        "figS3_pu_failure_chain": "figS3_pu_failure_chain",
    }
    for directory, stem in expected.items():
        root = frd.PREVIEW / directory
        for suffix in ("pdf", "svg", "png", "tiff"):
            assert (root / f"{stem}.{suffix}").exists()
        svg = (root / f"{stem}.svg").read_text()
        assert "<text" in svg
        with Image.open(root / f"{stem}.png") as image:
            assert abs(image.width - round(183 / 25.4 * 300)) <= 2
        with Image.open(root / f"{stem}.tiff") as image:
            assert abs(image.width - round(183 / 25.4 * 600)) <= 2
            dpi = image.info["dpi"]
            assert np.isclose(dpi[0], 600, atol=0.1)
            assert np.isclose(dpi[1], 600, atol=0.1)
        manifest = json.loads((root / "source-manifest.json").read_text())
        assert manifest["status"] == "complete"
        assert {item["path"] for item in manifest["code"]} == {
            "breeze/src/figure_revision_data.py",
            "breeze/src/figures_revision_preview.py",
        }
        for key in ("code", "sources", "outputs"):
            for item in manifest[key]:
                path = frd.REPO / item["path"]
                assert path.exists()
                assert frd.sha256(path) == item["sha256"]


def test_fig3_axis_contract_and_fig6_has_no_blocker() -> None:
    axes = np.genfromtxt(
        frd.PREVIEW / "fig3_downstream_effects" / "axis_limits.csv",
        delimiter=",",
        names=True,
        dtype=None,
        encoding="utf-8",
    )
    first_row = axes[axes["row"] == 1]
    assert len(set(first_row["x_min_pp"])) == 1
    assert len(set(first_row["x_max_pp"])) == 1
    blocker = frd.PREVIEW / "fig6_admission_mechanism_BLOCKED"
    assert not any(blocker.glob("*"))
    figure = frd.PREVIEW / "fig6_admission_mechanism"
    assert (figure / "fig6_admission_mechanism.pdf").exists()
    assert (figure / "source_data.csv").exists()
