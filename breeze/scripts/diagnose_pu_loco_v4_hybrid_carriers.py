"""Audit BREEZE-H healthy carrier admission on train-only PU windows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "breeze" / "src"))
sys.path.insert(0, str(ROOT / "breeze" / "scripts"))

from build_pu_loco_v3_internal_candidates import load_train_condition  # noqa: E402
from config import CLASSES, CONDITIONS  # noqa: E402
from verifier.v2 import BreezeVerifierV2  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--heldout", required=True, choices=CONDITIONS)
    parser.add_argument("--verifier", required=True)
    parser.add_argument("--n-per-condition", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260713)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    verifier = BreezeVerifierV2.load(Path(args.verifier))
    rng = np.random.default_rng(args.seed)
    healthy_index = CLASSES.index("healthy")
    rows: list[dict[str, object]] = []
    for condition in CONDITIONS:
        if condition == args.heldout:
            continue
        X, y, _ = load_train_condition(condition)
        W = X[y == healthy_index]
        n = min(args.n_per_condition, len(W))
        chosen = rng.choice(len(W), n, replace=False)
        channel_std = float(np.std(W[:, 0, :]))
        raw_pass = 0
        perturbed_pass = 0
        for index in chosen:
            raw = W[int(index)]
            raw_pass += int(bool(verifier.verify(raw, "healthy").get("feasible")))
            perturbed = raw.copy()
            perturbed[0] = perturbed[0] * rng.normal(1.0, 0.04) + rng.normal(
                0.0, 0.03 * channel_std, size=perturbed[0].shape
            )
            perturbed_pass += int(bool(verifier.verify(perturbed, "healthy").get("feasible")))
        rows.append(
            {
                "source_condition": condition,
                "n": n,
                "raw_healthy_pass": raw_pass,
                "noise_aug_scale_jitter_pass": perturbed_pass,
            }
        )
    result = {
        "heldout": args.heldout,
        "boundary": "only config.SPLIT train healthy windows are sampled; pseudo-held-out and formal held-out windows are not read",
        "rows": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
