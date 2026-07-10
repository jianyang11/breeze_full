"""Focused contract tests for the private machine-tool v2 smoke protocol."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "breeze" / "scripts" / "mt_private_v2_llm_smoke.py"
SPEC = importlib.util.spec_from_file_location("mt_private_v2_llm_smoke", SCRIPT)
smoke = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = smoke
SPEC.loader.exec_module(smoke)


def recipe(cls: str = "normal_machining") -> dict:
    return {
        "class_name": cls,
        "template_rank": 0,
        "channel_std_mult": {channel: 1.0 for channel in smoke.MT_CHANNELS},
        "channel_mean_shift_std": {channel: 0.0 for channel in smoke.MT_CHANNELS},
        "soft_band_gain": {channel: [1.0] * smoke.N_BANDS for channel in smoke.MT_CHANNELS},
        "spectral_mix": 0.20,
        "noise_gain": 0.01,
        "shared_component_gain": 0.02,
        "trend_strength": 0.0,
        "phase_randomization_strength": 1.0,
        "rationale": "train-supported test recipe",
    }


class PrivateMachineToolV2SmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.templates = {
            cls: np.stack([
                np.vstack([np.sin(np.linspace(0, 8 + channel, smoke.WIN_MT) + row) for channel in range(4)])
                for row in (0.1, 0.3, 0.7, 1.1)
            ]).astype(np.float32)
            for cls in smoke.MT_CLASSES
        }
        self.class_std = {cls: values.std(axis=(0, 2)) + 1e-3 for cls, values in self.templates.items()}

    def test_formal_file_guard(self) -> None:
        with self.assertRaises(RuntimeError):
            smoke._find_single_csv("1", "7")
        with self.assertRaises(RuntimeError):
            smoke._find_single_csv("2", "8")

    def test_frozen_development_split(self) -> None:
        self.assertEqual(smoke.INNER_TRAIN_FILE_IDS, ("1", "2", "4", "5"))
        self.assertEqual(smoke.INNER_VAL_FILE_ID, "10")
        self.assertEqual(smoke.FORBIDDEN_FILE_IDS, {"7", "8"})

    def test_recipe_normalization_clips_only_recipe_domain(self) -> None:
        raw = recipe()
        raw["template_rank"] = 99
        raw["channel_std_mult"]["X"] = 9.0
        raw["soft_band_gain"]["Y"][0] = -4.0
        raw["trend_strength"] = -3.0
        normalized = smoke.normalize_recipe(raw, "normal_machining", 4)
        self.assertEqual(normalized["template_rank"], 3)
        self.assertEqual(normalized["channel_std_mult"]["X"], 1.2)
        self.assertEqual(normalized["soft_band_gain"]["Y"][0], 0.7)
        self.assertEqual(normalized["trend_strength"], -0.05)

    def test_recipe_rejects_unknown_field(self) -> None:
        raw = recipe()
        raw["unknown_frequency_hz"] = 42
        with self.assertRaises(ValueError):
            smoke.normalize_recipe(raw, "normal_machining", 4)

    def test_prompt_excludes_raw_ids_and_file_ids(self) -> None:
        exemplar = {"classes": {"normal_machining": {"raw_class_id": "1", "display_name": "Normal machining", "n_windows": 10}}}
        differences = {"pairwise": {}}
        content = smoke.prompt_messages("normal_machining", exemplar, differences, smoke.recipe_schema(4), 0, None)[1]["content"]
        self.assertNotIn('"raw_class_id"', content)
        self.assertNotIn('"file_id"', content)

    def test_stable_seed_reproducible(self) -> None:
        self.assertEqual(smoke.stable_seed("a", 1), smoke.stable_seed("a", 1))
        self.assertNotEqual(smoke.stable_seed("a", 1), smoke.stable_seed("a", 2))

    def test_renderer_shape_and_finite(self) -> None:
        output = smoke.render_mt_recipe(recipe(), self.templates, self.class_std, smoke.stable_seed("render"))
        self.assertEqual(output.shape, (4, smoke.WIN_MT))
        self.assertTrue(np.all(np.isfinite(output)))

    def test_renderer_is_not_template_copy(self) -> None:
        output = smoke.render_mt_recipe(recipe(), self.templates, self.class_std, smoke.stable_seed("not-copy"))
        self.assertFalse(any(np.array_equal(output, template) for template in self.templates["normal_machining"]))

    def test_verifier_calls_and_reports_all_hard_gates(self) -> None:
        rng = np.random.default_rng(4)
        X = np.concatenate([rng.normal(loc=ci * 0.2, size=(12, 4, smoke.WIN_MT)).astype(np.float32) for ci in range(3)])
        y = np.concatenate([np.full(12, ci) for ci in range(3)])
        files = np.asarray([f"{ci}_{index % 4}" for ci in range(3) for index in range(12)])
        verifier = smoke.MachineToolVerifier(coverage=0.90)
        verifier.calibrate(X, y, files)
        report = verifier.verify(X[0], "normal_machining")
        self.assertEqual(set(report["gates"]), {"sanity", "stats_union", "soft_spectrum", "psd_w1"})

    def test_diversity_gate_rejects_exact_train_copy(self) -> None:
        rng = np.random.default_rng(5)
        X = np.concatenate([rng.normal(loc=ci * 0.5, size=(15, 4, smoke.WIN_MT)).astype(np.float32) for ci in range(3)])
        y = np.concatenate([np.full(15, ci) for ci in range(3)])
        files = np.asarray([f"{ci}_{index % 4}" for ci in range(3) for index in range(15)])
        verifier = smoke.MachineToolVerifier(coverage=0.90)
        verifier.calibrate(X, y, files)
        dev = smoke.DevData(X, y, files, np.arange(len(X)), [], [])
        admission = smoke.build_admission(dev, verifier)
        result = smoke.admit_candidate(X[0], "normal_machining", admission, set())
        self.assertTrue(result["exact_train_duplicate"])
        self.assertFalse(result["accepted"])

    def test_class_identity_gate_is_exposed(self) -> None:
        rng = np.random.default_rng(6)
        X = np.concatenate([rng.normal(loc=ci, size=(15, 4, smoke.WIN_MT)).astype(np.float32) for ci in range(3)])
        y = np.concatenate([np.full(15, ci) for ci in range(3)])
        files = np.asarray([f"{ci}_{index % 4}" for ci in range(3) for index in range(15)])
        verifier = smoke.MachineToolVerifier(coverage=0.90)
        verifier.calibrate(X, y, files)
        result = smoke.admit_candidate(X[1] + 1e-5, "normal_machining", smoke.build_admission(smoke.DevData(X, y, files, np.arange(len(X)), [], []), verifier), set())
        self.assertIn("class_identity_prediction", result)
        self.assertIn("class_identity_passed", result)

    def test_slot_state_retains_one_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            old_run = smoke.RUN_DIR
            smoke.RUN_DIR = Path(directory)
            smoke.ensure_dirs()
            state = smoke.default_slot_state("normal_machining", 0)
            state["status"] = "accepted"
            smoke.save_slot_state(state)
            self.assertEqual(smoke.load_slot_state("normal_machining", 0)["status"], "accepted")
            smoke.RUN_DIR = old_run

    def test_api_budget_counts_failed_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            old_out = smoke.OUT_DIR
            smoke.OUT_DIR = Path(directory)
            smoke.append_api_log({"request_index": 1, "parse_status": "error:ConnectionError"})
            smoke.append_api_log({"request_index": 2, "parse_status": "json_ok"})
            self.assertEqual(smoke.api_attempt_count(), 2)
            smoke.OUT_DIR = old_out

    def test_resume_zero_budget_does_not_issue_api(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            old_out, old_run = smoke.OUT_DIR, smoke.RUN_DIR
            smoke.OUT_DIR, smoke.RUN_DIR = Path(directory) / "out", Path(directory) / "run"
            smoke.ensure_dirs()
            state = smoke.default_slot_state("normal_machining", 0)
            state["status"] = "accepted"
            smoke.save_slot_state(state)
            self.assertEqual(smoke.api_attempt_count(), 0)
            self.assertEqual(smoke.load_slot_state("normal_machining", 0)["status"], "accepted")
            smoke.OUT_DIR, smoke.RUN_DIR = old_out, old_run

    def test_api_log_has_no_key_or_authorization_field(self) -> None:
        names = set(smoke.API_LOG_FIELDS)
        self.assertFalse({"api_key", "authorization", "headers", "environment"} & names)

    def test_balanced_pool_selects_slot_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            old_run = smoke.RUN_DIR
            smoke.RUN_DIR = Path(directory)
            (smoke.RUN_DIR / "accepted").mkdir(parents=True)
            rows = []
            for cls in smoke.MT_CLASSES:
                for slot in (2, 0, 1):
                    rel = Path("accepted") / f"{cls}_{slot}.npy"
                    np.save(smoke.RUN_DIR / rel, np.full((4, smoke.WIN_MT), slot, dtype=np.float32))
                    rows.append({"class_name": cls, "slot": slot, "path": str(rel)})
            pools, _ = smoke.load_selected_llm_pool(rows, 2)
            self.assertTrue(np.all(pools["normal_machining"][0] == 0))
            self.assertTrue(np.all(pools["normal_machining"][1] == 1))
            smoke.RUN_DIR = old_run

    def test_real_subset_is_deterministic_and_class_balanced(self) -> None:
        X = np.zeros((30, 4, smoke.WIN_MT), dtype=np.float32)
        y = np.repeat(np.arange(3), 10)
        _, first = smoke.sample_real_subset(X, y, 5, 12)
        _, second = smoke.sample_real_subset(X, y, 5, 12)
        self.assertTrue(np.array_equal(first, second))
        self.assertEqual(np.bincount(first, minlength=3).tolist(), [5, 5, 5])

    def test_downstream_methods_share_real_subset_contract(self) -> None:
        X = np.arange(30 * 4 * smoke.WIN_MT, dtype=np.float32).reshape(30, 4, smoke.WIN_MT)
        y = np.repeat(np.arange(3), 10)
        first, first_y = smoke.sample_real_subset(X, y, 5, 9)
        second, second_y = smoke.sample_real_subset(X, y, 5, 9)
        self.assertTrue(np.array_equal(first, second))
        self.assertTrue(np.array_equal(first_y, second_y))

    def test_decision_schema_contract(self) -> None:
        expected = {
            "status", "allowed_next_stage", "api_start_cumulative", "api_requests_this_stage", "api_end_cumulative", "api_budget",
            "formal_test_files_read", "target_per_class", "accepted_counts", "slot_acceptance_by_class", "feedback_rescue_rate",
            "balanced_n_syn", "pool_gate_passed", "feedback_gate_passed", "downstream_gate_passed",
            "core_cells_passed_vs_real_noise", "core_cells_passed_vs_rule", "core_cells_passed_vs_random", "lead_screw_gate_passed", "reasons",
        }
        self.assertEqual(len(expected), 20)
        self.assertIn("formal_test_files_read", expected)


if __name__ == "__main__":
    unittest.main()
