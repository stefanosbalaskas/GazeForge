"""Smoke tests for the public learning examples."""

from __future__ import annotations

import pathlib
import runpy
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_synthetic_qc_example_runs(capsys) -> None:
    runpy.run_path(str(_REPO_ROOT / "examples" / "01_synthetic_qc.py"), run_name="__main__")
    captured = capsys.readouterr()
    assert "quality_score" in captured.out


def test_ivt_baseline_example_runs(capsys) -> None:
    runpy.run_path(str(_REPO_ROOT / "examples" / "02_ivt_baseline.py"), run_name="__main__")
    captured = capsys.readouterr()
    assert "First-trial event transitions:" in captured.out


def test_visual_diagnostics_example_runs(tmp_path, monkeypatch, capsys) -> None:
    output_dir = tmp_path / "visual-demo"
    monkeypatch.setattr(
        sys,
        "argv",
        ["03_visual_diagnostics.py", "--output-dir", str(output_dir)],
    )
    runpy.run_path(
        str(_REPO_ROOT / "examples" / "03_visual_diagnostics.py"),
        run_name="__main__",
    )
    captured = capsys.readouterr()
    assert len(list(output_dir.glob("*.png"))) == 6
    assert "not empirical validation evidence" in captured.out
