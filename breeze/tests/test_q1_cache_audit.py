from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "breeze" / "scripts" / "q1_cache_audit.py"
SPEC = importlib.util.spec_from_file_location("q1_cache_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_latex_bibliography_is_not_classified_as_transient() -> None:
    category, action, _evidence = MODULE.latex_category(Path("main.bbl"))
    assert category == "BIBLIOGRAPHY_BUILD_EVIDENCE"
    assert action == "PRESERVE"


def test_latex_auxiliary_is_rebuildable_but_requires_authorization() -> None:
    category, action, _evidence = MODULE.latex_category(Path("main.aux"))
    assert category == "LATEX_TRANSIENT_CACHE"
    assert action == "REBUILDABLE_PENDING_AUTHORIZATION"


def test_path_size_does_not_follow_directory_symlink(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "large.bin").write_bytes(b"x" * 100)
    selected = tmp_path / "selected"
    selected.mkdir()
    (selected / "small.bin").write_bytes(b"abc")
    (selected / "linked").symlink_to(outside, target_is_directory=True)
    byte_count, file_count = MODULE.path_size(selected)
    assert byte_count == 3
    assert file_count == 1
