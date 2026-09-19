from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/18_worked_missing_data_assumptions_audit.py"


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


def test_missing_data_assumptions_audit_is_deterministic_and_nonselecting(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _run(first)
    _run(second)

    expected = {
        "01_missing_data_source_registry.csv",
        "02_mechanism_assumption_questions.csv",
        "03_analysis_treatment_registry.csv",
        "04_exclusion_missingness_separation.csv",
        "05_sensitivity_handoff.csv",
        "06_reporting_language.csv",
        "missing_data_assumptions_manifest.json",
        "README.md",
    }
    assert {path.name for path in first.iterdir() if path.is_file()} == expected
    assert _hashes(first) == _hashes(second)

    source = pd.read_csv(first / "01_missing_data_source_registry.csv")
    assert set(source["source_class"]) == {
        "observed",
        "acquisition_unavailable",
        "partial_observation",
        "design_absence",
        "undefined_derived_metric",
        "right_censored_event",
    }

    questions = pd.read_csv(first / "02_mechanism_assumption_questions.csv")
    assert questions["mcar_mar_mnar_conclusion"].eq("not_inferred_by_gazeforge").all()

    treatments = pd.read_csv(first / "03_analysis_treatment_registry.csv")
    assert treatments["selection_status"].eq("not_selected_by_gazeforge").all()
    assert not treatments["selected_automatically"].astype(bool).any()

    separation = pd.read_csv(first / "04_exclusion_missingness_separation.csv")
    missing = separation["source_class"].eq("acquisition_unavailable")
    assert not separation.loc[missing, "review_decision"].eq("excluded_after_review").any()
    censored = separation["source_class"].eq("right_censored_event")
    assert separation.loc[censored, "review_decision"].eq("retained_censored").all()

    manifest = json.loads(
        (first / "missing_data_assumptions_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["evidence_classification"] == "synthetic_demo_not_empirical_evidence"
    assert manifest["denominator_exposure_clinic"] == "denominator-exposure-censoring.md"
    for key in (
        "missingness_mechanism_inferred",
        "mcar_classification_created",
        "mar_classification_created",
        "mnar_classification_created",
        "automatic_complete_case_filtering_performed",
        "single_imputation_selected",
        "multiple_imputation_selected",
        "weighting_method_selected",
        "joint_model_selected",
        "pattern_mixture_model_selected",
        "selection_model_selected",
        "survival_estimator_selected",
        "glm_glmm_selected",
        "sem_selected",
        "bayesian_model_selected",
        "statistical_model_selected",
        "qc_flag_converted_to_exclusion",
        "censoring_reclassified_as_missing",
        "design_absence_reclassified_as_missing",
        "undefined_metric_reclassified_as_missing",
        "device_validity_claim_created",
        "measurement_validity_claim_created",
        "construct_validity_claim_created",
        "causal_validity_claim_created",
        "psychological_state_claim_created",
    ):
        assert manifest[key] is False
