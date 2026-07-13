"""Generic checkpointed downstream evaluation for NPZ train/test splits.

This runner is used for Phase-B smoke tests before dataset-specific synthetic
pools are trusted. It supports arbitrary channel counts and class counts.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import confusion_matrix, f1_score

from models import SimpleCNN


def load_npz(path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    data = np.load(path, allow_pickle=True)
    key = "X" if "X" in data.files else "windows"
    X = data[key].astype(np.float32)
    y = data["y"].astype(np.int64)
    if "class_names" in data.files:
        class_names = [str(x) for x in data["class_names"]]
    elif "metadata" in data.files:
        labels = []
        for item in data["metadata"]:
            rec = json.loads(str(item))
            labels.append(str(rec.get("label", rec.get("class", ""))))
        by_id = {}
        for yi, label in zip(y, labels):
            by_id.setdefault(int(yi), label)
        class_names = [by_id[i] for i in sorted(by_id)]
    else:
        class_names = [f"class_{i}" for i in sorted(set(int(v) for v in y))]
    return X, y, class_names


NORMALIZATION_MODES = ("none", "per-window-rms")


def normalize_per_window_rms(X: np.ndarray) -> np.ndarray:
    """Normalize each window and channel by its own finite, nonzero RMS.

    This is a representation transform, not an augmentation: it is applied
    only after a baseline has formed its complete training set, and the same
    transform is applied independently to every evaluation window.
    """
    if X.ndim != 3:
        raise ValueError(f"expected (windows, channels, samples), got {X.shape}")
    if not np.isfinite(X).all():
        raise ValueError("per-window-rms normalization requires finite windows")
    X64 = X.astype(np.float64, copy=False)
    rms = np.sqrt(np.mean(X64 * X64, axis=2, keepdims=True))
    if not np.isfinite(rms).all() or np.any(rms <= 0.0):
        raise ValueError("per-window-rms normalization requires nonzero finite channel RMS")
    return (X64 / rms).astype(np.float32)


def apply_normalization(X: np.ndarray, mode: str) -> np.ndarray:
    if mode == "none":
        return X
    if mode == "per-window-rms":
        return normalize_per_window_rms(X)
    raise ValueError(f"unknown normalization mode: {mode}")


def done_keys(path: Path) -> set[tuple[str, str, str, str, int, int]]:
    if not path.exists():
        return set()
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "normalization" not in reader.fieldnames:
            raise RuntimeError(
                f"{path} uses the legacy downstream schema without normalization; "
                "write normalized results to a new CSV"
            )
        return {
            (
                r["dataset"],
                r["split"],
                r["baseline"],
                r["normalization"],
                int(r["n_real"]),
                int(r["seed"]),
            )
            for r in reader
        }


def few_shot_subset(X: np.ndarray, y: np.ndarray, n_per_class: int, n_classes: int, rng: np.random.Generator):
    idx = []
    actual = {}
    for ci in range(n_classes):
        c = np.where(y == ci)[0]
        take = min(n_per_class, len(c))
        idx.extend(rng.choice(c, take, replace=False))
        actual[str(ci)] = int(take)
    idx = np.asarray(idx, dtype=int)
    return X[idx], y[idx], actual


def noise_aug(Xr: np.ndarray, yr: np.ndarray, n_per_class: int, n_classes: int, rng: np.random.Generator):
    xs, ys = [], []
    channel_std = Xr.std(axis=(0, 2), keepdims=True) + 1e-8
    for ci in range(n_classes):
        idx = np.where(yr == ci)[0]
        if len(idx) == 0:
            continue
        chosen = rng.choice(idx, n_per_class, replace=True)
        base = Xr[chosen]
        scale = rng.normal(1.0, 0.04, size=(len(chosen), 1, 1)).astype(np.float32)
        jitter = rng.normal(0.0, 0.03, size=base.shape).astype(np.float32) * channel_std
        xs.append(base * scale + jitter)
        ys.append(np.full(len(chosen), ci, dtype=np.int64))
    if not xs:
        return np.zeros((0,) + Xr.shape[1:], dtype=np.float32), np.zeros((0,), dtype=np.int64)
    return np.concatenate(xs).astype(np.float32), np.concatenate(ys)


def sample_pool(pool_path: Path, n_per_class: int, n_classes: int, rng: np.random.Generator):
    data = np.load(pool_path, allow_pickle=True)
    X = data["X"].astype(np.float32)
    y = data["y"].astype(np.int64)
    keep = []
    for ci in range(n_classes):
        idx = np.where(y == ci)[0]
        if len(idx):
            keep.extend(rng.choice(idx, min(n_per_class, len(idx)), replace=False))
    keep = np.asarray(keep, dtype=int)
    return X[keep], y[keep]


def fit(Xtr: np.ndarray, ytr: np.ndarray, seed: int, epochs: int, n_classes: int):
    torch.manual_seed(seed)
    mean = Xtr.mean(axis=(0, 2), keepdims=True)
    std = Xtr.std(axis=(0, 2), keepdims=True) + 1e-8
    Xn = (Xtr - mean) / std
    model = SimpleCNN(in_ch=Xtr.shape[1], num_classes=n_classes)
    opt = torch.optim.Adam(model.parameters(), lr=3e-4, weight_decay=1e-4)
    crit = nn.CrossEntropyLoss()
    Xt = torch.tensor(Xn, dtype=torch.float32)
    yt = torch.tensor(ytr, dtype=torch.long)
    gen = torch.Generator().manual_seed(seed)
    n = len(Xt)
    for _ in range(epochs):
        perm = torch.randperm(n, generator=gen)
        for start in range(0, n, 32):
            idx = perm[start : start + 32]
            opt.zero_grad()
            loss = crit(model(Xt[idx]), yt[idx])
            loss.backward()
            opt.step()
    model.eval()
    return model, mean, std


def evaluate(model, mean: np.ndarray, std: np.ndarray, Xte: np.ndarray, yte: np.ndarray):
    Xn = (Xte - mean) / std
    preds = []
    with torch.no_grad():
        Xt = torch.tensor(Xn, dtype=torch.float32)
        for start in range(0, len(Xt), 256):
            preds.append(model(Xt[start : start + 256]).argmax(1).numpy())
    pred = np.concatenate(preds)
    acc = float((pred == yte).mean())
    macro = float(f1_score(yte, pred, average="macro", zero_division=0))
    return acc, macro, pred


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--train-npz", required=True)
    parser.add_argument("--test-npz", required=True)
    parser.add_argument("--baseline", required=True, choices=["real_only", "noise_aug", "custom_pool"])
    parser.add_argument("--pool")
    parser.add_argument("--seeds", type=int, default=2)
    parser.add_argument("--n-real", type=int, nargs="+", default=[5, 10])
    parser.add_argument("--n-syn", type=int, default=150)
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--normalize", choices=NORMALIZATION_MODES, default="none")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    train_path = Path(args.train_npz)
    test_path = Path(args.test_npz)
    Xtr, ytr, class_names = load_npz(train_path)
    Xte, yte, test_class_names = load_npz(test_path)
    if class_names != test_class_names:
        raise RuntimeError(f"class names differ: train={class_names}, test={test_class_names}")
    n_classes = len(class_names)
    if args.baseline == "custom_pool" and not args.pool:
        raise SystemExit("--pool is required for custom_pool")
    Xte_eval = apply_normalization(Xte, args.normalize)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    new_file = not out.exists()
    done = done_keys(out)
    with out.open("a", newline="") as fh:
        writer = csv.writer(fh)
        if new_file:
            writer.writerow(
                [
                    "dataset",
                    "split",
                    "baseline",
                    "normalization",
                    "n_real",
                    "seed",
                    "actual_real_per_class",
                    "n_syn",
                    "acc",
                    "macro_f1",
                    "per_class_f1_json",
                    "confusion_json",
                    "class_names_json",
                ]
            )
        for n_real in args.n_real:
            for seed in range(args.seeds):
                key = (args.dataset, args.split, args.baseline, args.normalize, n_real, seed)
                if key in done:
                    continue
                rng = np.random.default_rng(1000 * n_real + seed)
                Xr, yr, actual = few_shot_subset(Xtr, ytr, n_real, n_classes, rng)
                if args.baseline == "real_only":
                    Xa, ya, n_syn = Xr, yr, 0
                elif args.baseline == "noise_aug":
                    Xs, ys = noise_aug(Xr, yr, args.n_syn, n_classes, rng)
                    Xa, ya, n_syn = np.concatenate([Xr, Xs]), np.concatenate([yr, ys]), len(ys)
                else:
                    Xs, ys = sample_pool(Path(args.pool), args.n_syn, n_classes, rng)
                    Xa, ya, n_syn = np.concatenate([Xr, Xs]), np.concatenate([yr, ys]), len(ys)
                Xa_eval = apply_normalization(Xa, args.normalize)
                model, mean, std = fit(Xa_eval, ya, seed, args.epochs, n_classes)
                acc, macro, pred = evaluate(model, mean, std, Xte_eval, yte)
                per = f1_score(yte, pred, average=None, labels=list(range(n_classes)), zero_division=0)
                cm = confusion_matrix(yte, pred, labels=list(range(n_classes)))
                writer.writerow(
                    [
                        args.dataset,
                        args.split,
                        args.baseline,
                        args.normalize,
                        n_real,
                        seed,
                        json.dumps(actual, sort_keys=True, separators=(",", ":")),
                        n_syn,
                        f"{acc:.4f}",
                        f"{macro:.4f}",
                        json.dumps({class_names[i]: float(per[i]) for i in range(n_classes)}, separators=(",", ":")),
                        json.dumps(cm.tolist(), separators=(",", ":")),
                        json.dumps(class_names, separators=(",", ":")),
                    ]
                )
                fh.flush()
                print(
                    f"{args.dataset}/{args.split} {args.baseline} normalize={args.normalize} n_real={n_real} "
                    f"seed={seed} n_syn={n_syn} acc={acc:.4f} macro_f1={macro:.4f}",
                    flush=True,
                )


if __name__ == "__main__":
    main()
