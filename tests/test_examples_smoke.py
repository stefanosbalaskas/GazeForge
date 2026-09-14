"""Smoke tests for the public learning examples."""

from __future__ import annotations

import runpy
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_qc_example_runs(capsys) -> None:
    runpy.run_path(str(_REPO_ROOT / "examples" / "01_synthetic_qc.py"), run_name="__main__")
    captured = capsys.readouterr()
    assert "quality_score" in captured.out


def test_ivt_baseline_example_runs(capsys) -> None:
    runpy.run_path(str(_REPO_ROOT / "examples" / "02_ivt_baseline.py"), run_name="__main__")
    captured = capsys.readouterr()
    assert "First-trial event transitions:" in captured.out
