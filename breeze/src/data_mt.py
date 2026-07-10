"""Machine-tool private dataset (MechaForge rig): X/Y/Z accel + motor current.

File-based split per class: files 1,2,4,5,10 -> train, files 7,8 -> test.
Windows of 2048 samples, stride 1024, 4 channels.
"""
import glob
import os
import re
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import PROC_DIR

MT_DIR = Path(__file__).parent.parent / "data_mt"
WIN_MT, STRIDE_MT = 2048, 1024
TRAIN_FILES = {"1", "2", "4", "5", "10"}
TEST_FILES = {"7", "8"}
RAW_CLASS_IDS = ["1", "2", "3"]
CLASS_ID_TO_NAME = {
    "1": "normal_machining",
    "2": "lead_screw_anomaly",
    "3": "base_imbalance",
}
CLASS_ID_TO_DISPLAY_NAME = {
    "1": "Normal machining",
    "2": "Lead-screw anomaly",
    "3": "Base imbalance",
}
MT_CLASSES = [CLASS_ID_TO_NAME[c] for c in RAW_CLASS_IDS]
MT_DISPLAY_NAMES = [CLASS_ID_TO_DISPLAY_NAME[c] for c in RAW_CLASS_IDS]
MT_CHANNELS = ["X", "Y", "Z", "Current"]
MT_SAMPLING_RATE_HZ = 4000.0
CLASS_MAPPING_STATUS = "confirmed_by_project_owner_2026-07-10"
CLASS_MAPPING_SOURCE = (
    "Project owner confirmation in BREEZE private machine-tool preflight "
    "request, 2026-07-10; not present in the published MechaForge PDF text."
)
CLASS_MAPPING_CONFIRMED_DATE = "2026-07-10"
FILENAME_RE = re.compile(r"^(?P<class_id>[123])_(?P<file_id>\d+)(?:_pre)?\.csv$")


def parse_mt_filename(path: str | Path) -> dict[str, str | bool]:
    """Parse private machine-tool CSV names without using the class as a feature."""
    name = Path(path).name
    match = FILENAME_RE.match(name)
    if not match:
        return {"parse_ok": False, "file_name": name}
    class_id = match.group("class_id")
    file_id = match.group("file_id")
    return {
        "parse_ok": True,
        "file_name": name,
        "raw_class_id": class_id,
        "file_id": file_id,
        "class_name": CLASS_ID_TO_NAME[class_id],
        "display_name": CLASS_ID_TO_DISPLAY_NAME[class_id],
    }


def normalize_mt_class(label: str | int) -> str:
    """Return the canonical class name for raw IDs, formal names, or displays."""
    key = str(label)
    if key in CLASS_ID_TO_NAME:
        return CLASS_ID_TO_NAME[key]
    if key in MT_CLASSES:
        return key
    for raw_id, display in CLASS_ID_TO_DISPLAY_NAME.items():
        if key == display:
            return CLASS_ID_TO_NAME[raw_id]
    legacy = {"MT-1": "1", "MT-2": "2", "MT-3": "3"}
    if key in legacy:
        return CLASS_ID_TO_NAME[legacy[key]]
    raise KeyError(f"unknown private machine-tool class label: {label!r}")


def class_name_to_raw_id(class_name: str) -> str:
    cls = normalize_mt_class(class_name)
    for raw_id, name in CLASS_ID_TO_NAME.items():
        if cls == name:
            return raw_id
    raise KeyError(class_name)


def _windows(arr):
    n = (len(arr) - WIN_MT) // STRIDE_MT + 1
    if n < 1:
        return np.empty((0, len(MT_CHANNELS), WIN_MT), dtype=np.float32)
    return np.stack([arr[i * STRIDE_MT:i * STRIDE_MT + WIN_MT].T
                     for i in range(n)]).astype(np.float32)


def build():
    out = {}
    for f in sorted(glob.glob(str(MT_DIR / "*.csv"))):
        parsed = parse_mt_filename(f)
        if not parsed["parse_ok"]:
            raise ValueError(f"invalid private machine-tool filename: {f}")
        cls, fid = str(parsed["raw_class_id"]), str(parsed["file_id"])
        d = np.genfromtxt(f, delimiter=",", skip_header=1)
        split = "train" if fid in TRAIN_FILES else "test"
        out.setdefault((split, cls), []).append(_windows(d))
    for (split, cls), ws in out.items():
        W = np.concatenate(ws).astype(np.float32)
        np.savez_compressed(PROC_DIR / f"mt_{split}_{cls}.npz", windows=W)
        print(split, cls, W.shape)


def load_mt(split):
    Xs, ys = [], []
    for ci, cls in enumerate(RAW_CLASS_IDS):
        d = np.load(PROC_DIR / f"mt_{split}_{cls}.npz")
        Xs.append(d["windows"])
        ys.append(np.full(len(d["windows"]), ci))
    return np.concatenate(Xs), np.concatenate(ys)


if __name__ == "__main__":
    build()
