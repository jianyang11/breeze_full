"""Few-shot real-only diagnosis on the private machine-tool dataset.

This script is isolated from the PU downstream table because the machine-tool
schema has four input channels. It writes checkpoint-resumable CSV rows with
per-class F1 and confusion matrices.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import confusion_matrix, f1_score

sys.path.insert(0, str(Path(__file__).parent))
from config import RESULTS_DIR
from data_mt import MT_CLASSES, load_mt
from models import SimpleCNN


def few_shot_subset(X: np.ndarray, y: np.ndarray, n_per_class: int, rng: np.random.Generator):
    idx = []
    for ci in range(len(MT_CLASSES)):
        c = np.where(y == ci)[0]
        idx.extend(rng.choice(c, min(n_per_class, len(c)), replace=False))
    idx = np.asarray(idx, dtype=int)
    return X[idx], y[idx]


def fit_mt(Xtr: np.ndarray, ytr: np.ndarray, seed: int, epochs: int):
    torch.manual_seed(seed)
    mean = Xtr.mean(axis=(0, 2), keepdims=True)
    std = Xtr.std(axis=(0, 2), keepdims=True) + 1e-8
    Xn = (Xtr - mean) / std
    model = SimpleCNN(in_ch=Xtr.shape[1], num_classes=len(MT_CLASSES))
    opt = torch.optim.Adam(model.parameters(), lr=3e-4, weight_decay=1e-4)
    crit = nn.CrossEntropyLoss()
    Xt = torch.tensor(Xn, dtype=torch.float32)
    yt = torch.tensor(ytr, dtype=torch.long)
    generator = torch.Generator().manual_seed(seed)
    for _ in range(epochs):
        perm = torch.randperm(len(Xt), generator=generator)
        for start in range(0, len(Xt), 32):
            idx = perm[start:start + 32]
            opt.zero_grad()
            loss = crit(model(Xt[idx]), yt[idx])
            loss.backward()
            opt.step()
    model.eval()
    return model, mean, std


def evaluate_mt(model, mean, std, Xte: np.ndarray, yte: np.ndarray):
    Xn = (Xte - mean) / std
    preds = []
    with torch.no_grad():
        Xt = torch.tensor(Xn, dtype=torch.float32)
        for start in range(0, len(Xt), 256):
            preds.append(model(Xt[start:start + 256]).argmax(1).numpy())
    pred = np.concatenate(preds)
    acc = float((pred == yte).mean())
    macro = float(f1_score(yte, pred, average="macro", labels=list(range(len(MT_CLASSES))), zero_division=0))
    per = f1_score(yte, pred, average=None, labels=list(range(len(MT_CLASSES))), zero_division=0)
    cm = confusion_matrix(yte, pred, labels=list(range(len(MT_CLASSES)))
                          )
    return acc, macro, per, cm


def done_keys(path: Path) -> set[tuple[int, int, int]]:
    if not path.exists():
        return set()
    with path.open() as fh:
        return {(int(r["n_real"]), int(r["seed"]), int(r["epochs"])) for r in csv.DictReader(fh)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--n-real", type=int, nargs="+", default=[10, 25, 50])
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--out", default=str(RESULTS_DIR / "mt_real_only_eval.csv"))
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Xtr, ytr = load_mt("train")
    Xte, yte = load_mt("test")
    Xtr = Xtr.astype(np.float32)
    Xte = Xte.astype(np.float32)

    done = done_keys(out)
    new_file = not out.exists()
    with out.open("a", newline="") as fh:
        writer = csv.writer(fh)
        if new_file:
            writer.writerow([
                "dataset",
                "baseline",
                "n_real",
                "seed",
                "epochs",
                "n_train",
                "acc",
                "macro_f1",
                *[f"f1_{c}" for c in MT_CLASSES],
                "confusion",
            ])
        for n_real in args.n_real:
            for seed in range(args.seeds):
                key = (n_real, seed, args.epochs)
                if key in done:
                    continue
                rng = np.random.default_rng(1000 * n_real + seed)
                Xfew, yfew = few_shot_subset(Xtr, ytr, n_real, rng)
                model, mean, std = fit_mt(Xfew, yfew, seed=seed, epochs=args.epochs)
                acc, macro, per, cm = evaluate_mt(model, mean, std, Xte, yte)
                writer.writerow([
                    "machine_tool_private",
                    "real_only",
                    n_real,
                    seed,
                    args.epochs,
                    len(Xfew),
                    f"{acc:.4f}",
                    f"{macro:.4f}",
                    *[f"{v:.4f}" for v in per],
                    json.dumps(cm.tolist(), separators=(",", ":")),
                ])
                fh.flush()
                print(
                    f"mt real_only n_real={n_real} seed={seed} epochs={args.epochs} "
                    f"acc={acc:.4f} macro_f1={macro:.4f}",
                    flush=True,
                )


if __name__ == "__main__":
    main()
