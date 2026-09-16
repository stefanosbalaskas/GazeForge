"""Smoke tests for the public learning examples."""

from __future__ import annotations

import json
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


def test_end_to_end_research_workflow_runs(tmp_path, monkeypatch, capsys) -> None:
    output_dir = tmp_path / "end-to-end-demo"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "end_to_end_research_workflow.py",
            "--output-dir",
            str(output_dir),
            "--no-figures",
        ],
    )
    runpy.run_path(
        str(_REPO_ROOT / "examples" / "end_to_end_research_workflow.py"),
        run_name="__main__",
    )
    captured = capsys.readouterr()

    assert len(list(output_dir.glob("*.csv"))) == 10
    assert (output_dir / "provenance.json").is_file()
    manifest_path = output_dir / "workflow_manifest.json"
    assert manifest_path.is_file()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["evidence_classification"] == "synthetic_demo_not_empirical_evidence"
    assert manifest["source_unchanged"] is True
    assert manifest["figure_outputs"] == []
    assert "Source table unchanged: yes" in captured.out
