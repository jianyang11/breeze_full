"""Contract tests for the zero-API private machine-tool v3 protocol."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "breeze" / "scripts" / "mt_private_v3_conditional.py"
SPEC = importlib.util.spec_from_file_location("mt_private_v3_conditional", SCRIPT)
v3 = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = v3
SPEC.loader.exec_module(v3)


def synthetic_context() -> v3.Context:
    rng = np.random.default_rng(42)
    xs, ys, files = [], [], []
    for ci, cls in enumerate(v3.MT_CLASSES):
        for source in range(4):
            for _ in range(3):
                x = rng.normal(loc=ci * 0.7, scale=0.4, size=(len(v3.MT_CHANNELS), v3.WIN_MT)).astype(np.float32)
                x[3] += ci * 0.2
                xs.append(x)
                ys.append(ci)
                files.append(f"{ci + 1}_{source + 1}")
    X = np.stack(xs)
    y = np.asarray(ys, dtype=np.int64)
    sources = np.asarray(files, dtype=object)
    dev = v3.DevData(X, y, sources, np.arange(len(X)), [], [])
    verifier = v3.MachineToolVerifier(coverage=0.90)
    verifier.calibrate(X, y, sources)
    admission = v3.build_admission(dev, verifier)
    templates = {cls: X[y == ci] for ci, cls in enumerate(v3.MT_CLASSES)}
    by_source = {cls: sources[y == ci] for ci, cls in enumerate(v3.MT_CLASSES)}
    return v3.Context(dev, verifier, admission, templates, by_source, v3.directional_profile(dev))


class PrivateMachineToolV3ConditionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = synthetic_context()

    def test_frozen_access_and_control_contract(self) -> None:
        self.assertEqual(v3.INNER_TRAIN_FILE_IDS, ("1", "2", "4", "5"))
        self.assertEqual(v3.INNER_VAL_FILE_ID, "10")
        self.assertEqual(v3.FORBIDDEN_FILE_IDS, {"7", "8"})
        self.assertEqual(v3.CONTROLS_PER_CLASS, 100)
        self.assertEqual(v3.MAX_ATTEMPTS_PER_CLASS, 80)

    def test_directional_profile_is_renderer_bounded(self) -> None:
        for cls in v3.MT_CLASSES:
            profile = self.context.profile[cls]
            self.assertEqual(profile["soft_gain"].shape, (4, v3.N_BANDS))
            self.assertEqual(profile["std_gain"].shape, (4,))
            self.assertGreaterEqual(float(profile["soft_gain"].min()), np.exp(-v3.DIRECTION_GAIN_STRENGTH * v3.DIRECTION_CLIP) - 1e-12)
            self.assertLessEqual(float(profile["soft_gain"].max()), np.exp(v3.DIRECTION_GAIN_STRENGTH * v3.DIRECTION_CLIP) + 1e-12)

    def test_s_a_uses_only_target_carrier_and_is_deterministic(self) -> None:
        first, provenance = v3.render_s_a("lead_screw_anomaly", 3, self.context)
        second, second_provenance = v3.render_s_a("lead_screw_anomaly", 3, self.context)
        self.assertEqual(first.shape, (4, v3.WIN_MT))
        self.assertTrue(np.all(np.isfinite(first)))
        self.assertTrue(np.array_equal(first, second))
        self.assertEqual(provenance, second_provenance)
        self.assertIn(provenance["carrier_a_source"], self.context.sources["lead_screw_anomaly"].tolist())

    def test_s_b_mixes_two_distinct_target_carriers(self) -> None:
        output, provenance = v3.render_s_b("base_imbalance", 2, self.context)
        self.assertEqual(output.shape, (4, v3.WIN_MT))
        self.assertNotEqual(provenance["carrier_a_index"], provenance["carrier_b_index"])
        self.assertIn(provenance["alpha"], v3.MIX_ALPHAS)
        self.assertIn(provenance["carrier_a_source"], self.context.sources["base_imbalance"].tolist())
        self.assertIn(provenance["carrier_b_source"], self.context.sources["base_imbalance"].tolist())

    def test_constant_control_fails_core_sanity(self) -> None:
        constant = np.zeros((4, v3.WIN_MT), dtype=np.float32)
        report = v3.core_admit(constant, "normal_machining", self.context)
        self.assertFalse(report["core_accepted"])
        self.assertIn("sanity", report["failure_reasons"])

    def test_audit_writes_fixed_control_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            old_out, old_run = v3.OUT_DIR, v3.RUN_DIR
            v3.OUT_DIR, v3.RUN_DIR = Path(directory) / "out", Path(directory) / "run"
            v3.ensure_dirs()
            decision = v3.run_admission_audit(self.context)
            rows = v3.read_csv(v3.OUT_DIR / "mt_private_v3_admission_audit_rows.csv")
            self.assertEqual(sum(row["control"] == "white_noise" for row in rows), len(v3.MT_CLASSES) * v3.CONTROLS_PER_CLASS)
            self.assertEqual(sum(row["control"] == "constant" for row in rows), len(v3.MT_CLASSES) * v3.CONTROLS_PER_CLASS)
            self.assertEqual(decision["constant_admitted"], 0)
            v3.OUT_DIR, v3.RUN_DIR = old_out, old_run

    def test_pool_precondition_is_checkpointed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            old_out = v3.OUT_DIR
            v3.OUT_DIR = Path(directory) / "out"
            v3.OUT_DIR.mkdir(parents=True)
            self.assertFalse(v3.pool_is_balanced("s_a_directional", 1))
            path = v3.OUT_DIR / "mt_private_v3_s_a_directional_n1_pool_decision.json"
            path.write_text(json.dumps({"balanced": True}))
            self.assertTrue(v3.pool_is_balanced("s_a_directional", 1))
            v3.OUT_DIR = old_out


if __name__ == "__main__":
    unittest.main()
