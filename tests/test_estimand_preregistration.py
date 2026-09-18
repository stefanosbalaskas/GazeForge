from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/13_worked_estimand_preregistration.py"


def _hashes(path: Path) -> dict[str, str]:
    return {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.iterdir())
        if item.is_file()
    }


def _run(path: Path) -> None:
    subprocess.run(
        [sys.executable, str(EXAMPLE), "--output-dir", str(path)],
        check=True,
        cwd=ROOT,
    )


def test_estimand_preregistration_is_deterministic_and_result_free(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _run(first)
    _run(second)

    expected = {
        "01_outcome_registry.csv",
        "02_estimand_registry.csv",
        "03_contrast_registry.csv",
        "04_sensitivity_registry.csv",
        "05_deviation_registry.csv",
        "06_reporting_plan.csv",
        "preregistration_manifest.json",
        "README.md",
    }
    assert {p.name for p in first.iterdir() if p.is_file()} == expected
    assert _hashes(first) == _hashes(second)

    outcomes = pd.read_csv(first / "01_outcome_registry.csv")
    assert set(outcomes["analysis_status"]) <= {"primary", "secondary", "exploratory"}
    assert outcomes["row_unit"].notna().all()
    assert outcomes["exposure_denominator_policy"].notna().all()
    latency = outcomes.loc[outcomes["outcome_id"] == "O03"].iloc[0]
    assert "right-censored" in latency["missing_zero_censoring_policy"]
    assert "latency=0" in latency["missing_zero_censoring_policy"]

    estimands = pd.read_csv(first / "02_estimand_registry.csv")
    assert not estimands["estimator_selected"].astype(bool).any()
    assert not estimands["model_family_selected"].astype(bool).any()

    sensitivity = pd.read_csv(first / "04_sensitivity_registry.csv")
    assert (sensitivity["status"] == "prespecified").any()

    deviations = pd.read_csv(first / "05_deviation_registry.csv")
    assert deviations.empty
    assert list(deviations.columns) == [
        "deviation_id",
        "registered_at",
        "affected_registry",
        "affected_id",
        "change",
        "reason",
        "status_after_change",
    ]

    manifest = json.loads((first / "preregistration_manifest.json").read_text(encoding="utf-8"))
    for key in (
        "model_fit_performed",
        "estimator_selected",
        "model_family_selected",
        "inferential_statistics_created",
        "p_values_created",
        "effect_sizes_created",
        "result_dependent_outcome_selection_performed",
        "missing_converted_to_zero",
        "censored_observations_dropped",
        "construct_validity_claim_created",
        "causal_validity_claim_created",
    ):
        assert manifest[key] is False
