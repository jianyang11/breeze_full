"""Run PU leave-one-condition-out downstream evaluations.

This scheduler is checkpointed at the CSV row level by eval_npz_downstream.py.
It consumes fold-specific PU LOCO synthetic pools built from the training
conditions only. Running this downstream scheduler adds no LLM calls.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


CONDITIONS = ["N09_M07_F10", "N15_M01_F10", "N15_M07_F04", "N15_M07_F10"]
METHODS = {
    "llm": {"baseline": "custom_pool"},
    "rule": {"baseline": "custom_pool"},
    "random_open_loop": {"baseline": "custom_pool"},
    "noise_aug": {"baseline": "noise_aug"},
    "real_only": {"baseline": "real_only"},
}


def command_for(
    cond: str,
    method: str,
    seeds: int,
    n_real: list[int],
    n_syn: int,
    epochs: int,
    out_dir: Path,
    llm_pool_root: Path,
    nonllm_pool_root: Path,
    train_template: str,
    test_template: str,
    split_prefix: str,
    normalize: str,
) -> list[str]:
    spec = METHODS[method]
    split = f"{split_prefix}_{cond}" if split_prefix else f"loco_{cond}"
    cmd = [
        sys.executable,
        "breeze/src/eval_npz_downstream.py",
        "--dataset",
        "PU",
        "--split",
        split,
        "--train-npz",
        train_template.format(cond=cond),
        "--test-npz",
        test_template.format(cond=cond),
        "--baseline",
        spec["baseline"],
        "--seeds",
        str(seeds),
        "--n-real",
        *[str(x) for x in n_real],
        "--epochs",
        str(epochs),
        "--normalize",
        normalize,
        "--out",
        str(out_dir / f"{split}_{method}_nsyn{n_syn}.csv"),
    ]
    if spec["baseline"] != "real_only":
        cmd.extend(["--n-syn", str(n_syn)])
    if spec["baseline"] == "custom_pool":
        pool_root = llm_pool_root if method == "llm" else nonllm_pool_root
        cmd.extend(["--pool", str(pool_root / split / method / "pool.npz")])
    return cmd


def run_condition(
    cond: str,
    seeds: int,
    n_real: list[int],
    n_syn: int,
    epochs: int,
    out_dir: Path,
    llm_pool_root: Path,
    nonllm_pool_root: Path,
    max_parallel: int,
    methods: list[str],
    train_template: str,
    test_template: str,
    split_prefix: str,
    normalize: str,
) -> None:
    pending = [
        (
            f"loco_{cond}_{method}_nsyn{n_syn}.csv",
            command_for(
                cond,
                method,
                seeds,
                n_real,
                n_syn,
                epochs,
                out_dir,
                llm_pool_root,
                nonllm_pool_root,
                train_template,
                test_template,
                split_prefix,
                normalize,
            ),
        )
        for method in methods
    ]
    running: list[tuple[str, subprocess.Popen[str]]] = []
    while pending or running:
        while pending and len(running) < max_parallel:
            label, cmd = pending.pop(0)
            print(f"[launch] {label}", flush=True)
            running.append((label, subprocess.Popen(cmd, text=True)))
        still_running: list[tuple[str, subprocess.Popen[str]]] = []
        for label, proc in running:
            ret = proc.poll()
            if ret is None:
                still_running.append((label, proc))
                continue
            if ret != 0:
                raise SystemExit(f"{label} failed with exit code {ret}")
            print(f"[done] {label}", flush=True)
        running = still_running
        if running:
            time.sleep(5)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="breeze/results/pu_loco_2026-07-07/downstream")
    parser.add_argument("--conditions", nargs="+", default=CONDITIONS)
    parser.add_argument("--methods", nargs="+", default=list(METHODS))
    parser.add_argument("--seeds", type=int, default=40)
    parser.add_argument("--n-real", type=int, nargs="+", default=[5, 10, 25])
    parser.add_argument("--n-syn", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--max-parallel", type=int, default=4)
    parser.add_argument("--llm-pool-root", default="breeze/runs/pu_loco_llm_smoke_2026-07-07_v3")
    parser.add_argument("--nonllm-pool-root", default="breeze/runs/pu_loco_nonllm_pools_2026-07-07")
    parser.add_argument("--train-template", default="proc/pu_loco_{cond}_train.npz")
    parser.add_argument("--test-template", default="proc/pu_loco_{cond}_test.npz")
    parser.add_argument("--split-prefix", default="loco")
    parser.add_argument("--normalize", choices=["none", "per-window-rms"], default="none")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for cond in args.conditions:
        if cond not in CONDITIONS:
            raise SystemExit(f"unknown condition: {cond}")
        for method in args.methods:
            if method not in METHODS:
                raise SystemExit(f"unknown method: {method}")
        print(f"[condition] {cond}", flush=True)
        run_condition(
            cond=cond,
            seeds=args.seeds,
            n_real=args.n_real,
            n_syn=args.n_syn,
            epochs=args.epochs,
            out_dir=out_dir,
            llm_pool_root=Path(args.llm_pool_root),
            nonllm_pool_root=Path(args.nonllm_pool_root),
            max_parallel=args.max_parallel,
            methods=args.methods,
            train_template=args.train_template,
            test_template=args.test_template,
            split_prefix=args.split_prefix,
            normalize=args.normalize,
        )


if __name__ == "__main__":
    main()
