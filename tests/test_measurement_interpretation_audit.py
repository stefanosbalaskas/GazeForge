from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/12_worked_measurement_interpretation_audit.py"


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


def test_measurement_interpretation_audit_is_deterministic_and_claim_safe(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _run(first)
    _run(second)

    expected = {
        "01_claim_registry.csv",
        "02_measurement_interpretation_matrix.csv",
        "03_validity_threats.csv",
        "04_sensitivity_plan.csv",
        "05_reporting_language.csv",
        "interpretation_audit.json",
        "README.md",
    }
    assert {path.name for path in first.iterdir() if path.is_file()} == expected
    assert _hashes(first) == _hashes(second)

    claims = pd.read_csv(first / "01_claim_registry.csv")
    statuses = {value.lower() for value in claims["status"].astype(str)}
    assert not ({"valid", "invalid"} & statuses)
    assert "not_supported_by_gaze_alone" in statuses

    matrix = pd.read_csv(first / "02_measurement_interpretation_matrix.csv")
    latency = matrix.loc[matrix["measure"] == "first_fixation_latency_ms"].iloc[0]
    assert "right-censored" in latency["missing_zero_censoring"]
    assert "not latency=0" in latency["missing_zero_censoring"]
    assert matrix["api_reference"].str.contains("api-reference.md#").all()

    language = pd.read_csv(first / "05_reporting_language.csv")
    assert language["limitation"].str.len().gt(0).all()

    audit = json.loads((first / "interpretation_audit.json").read_text(encoding="utf-8"))
    for key in (
        "automatic_construct_inference_performed",
        "causal_claim_created",
        "psychological_state_claim_created",
        "inferential_statistics_created",
        "estimator_selected",
        "missing_converted_to_zero",
        "no_fixation_latency_converted_to_zero",
        "claim_truth_labels_created",
    ):
        assert audit[key] is False
