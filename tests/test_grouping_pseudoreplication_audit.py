from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
EXAMPLE = ROOT / "20_worked_grouping_pseudoreplication_audit.py"


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


def test_grouping_pseudoreplication_audit_is_deterministic_and_nonselecting(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _run(first)
    _run(second)

    expected = {
        "01_unit_registry.csv",
        "02_grouping_structure.csv",
        "03_row_independence_audit.csv",
        "04_aggregation_risk_register.csv",
        "05_crossed_nested_handoff.csv",
        "06_reporting_language.csv",
        "07_api_route_map.csv",
        "grouping_pseudoreplication_manifest.json",
        "README.md",
    }
    assert {path.name for path in first.iterdir() if path.is_file()} == expected
    assert _hashes(first) == _hashes(second)

    units = pd.read_csv(first / "01_unit_registry.csv")
    required = units["unit_id"].isin(["U01", "U02"])
    for col in (
        "participant_id_retained",
        "trial_id_retained",
        "stimulus_id_retained",
    ):
        assert units.loc[required, col].astype(bool).all()

    grouping = pd.read_csv(first / "02_grouping_structure.csv")
    assert set(grouping["relation"]) == {
        "repeated_within_unit",
        "nested",
        "crossed",
        "descriptive_only",
    }
    assert not grouping["model_term_selected_automatically"].astype(bool).any()

    independence = pd.read_csv(first / "03_row_independence_audit.csv")
    risky = independence["risk_status"].isin(
        {"pseudoreplication_risk", "aggregation_changes_inferential_unit"}
    )
    assert risky.sum() >= 2
    assert independence.loc[risky, "blocks_unqualified_independence_claim"].astype(bool).all()

    aggregation = pd.read_csv(first / "04_aggregation_risk_register.csv")
    assert not aggregation["performed_automatically"].astype(bool).any()
    assert aggregation["changes_inferential_unit_or_estimand"].astype(bool).any()

    handoff = pd.read_csv(first / "05_crossed_nested_handoff.csv")
    assert handoff["statistical_term_selection"].eq("not_selected_by_gazeforge").all()

    manifest = json.loads(
        (first / "grouping_pseudoreplication_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["evidence_classification"] == "synthetic_demo_not_empirical_evidence"
    for key in (
        "automatic_aggregation_performed",
        "fixed_effect_selected",
        "random_intercept_selected",
        "random_slope_selected",
        "covariance_structure_selected",
        "cluster_robust_se_selected",
        "gee_selected",
        "lmm_glmm_selected",
        "bayesian_hierarchical_model_selected",
        "statistical_estimator_selected",
        "small_variance_used_to_drop_grouping_identity",
        "stimulus_identity_discarded",
        "participant_identity_discarded",
        "device_validity_claim_created",
        "construct_validity_claim_created",
        "causal_validity_claim_created",
        "psychological_state_claim_created",
    ):
        assert manifest[key] is False

    api = pd.read_csv(first / "07_api_route_map.csv")
    assert {
        "api-reference.md#schema",
        "api-reference.md#quality-control",
        "api-reference.md#eye-events",
        "api-reference.md#semantic-aois",
        "api-reference.md#dynamic-aois",
        "api-reference.md#scanpaths",
        "api-reference.md#hierarchical-location-scale-models",
    } <= set(api["api_route"])
