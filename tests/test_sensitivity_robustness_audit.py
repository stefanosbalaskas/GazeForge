from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/15_worked_sensitivity_robustness_audit.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(path: Path) -> dict[str, str]:
    return {p.name: _sha256(p) for p in sorted(path.iterdir()) if p.is_file()}


def test_sensitivity_audit_is_deterministic_and_preserves_primary_contract(
    tmp_path: Path,
) -> None:
    out = tmp_path / "audit"
    cmd = [sys.executable, str(EXAMPLE), "--output-dir", str(out)]
    subprocess.run(cmd, check=True, cwd=ROOT)
    first = _tree(out)
    subprocess.run(cmd, check=True, cwd=ROOT)
    assert _tree(out) == first

    expected = {
        "01_sensitivity_registry.csv",
        "02_executed_conditions.csv",
        "03_result_comparison.csv",
        "04_deviation_ledger.csv",
        "05_interpretation_matrix.csv",
        "06_reporting_language.csv",
        "README.md",
        "sensitivity_manifest.json",
    }
    assert {p.name for p in out.iterdir() if p.is_file()} == expected

    registry = pd.read_csv(out / "01_sensitivity_registry.csv")
    executed = pd.read_csv(out / "02_executed_conditions.csv")
    comparison = pd.read_csv(out / "03_result_comparison.csv")
    manifest = json.loads((out / "sensitivity_manifest.json").read_text())

    assert set(registry["analysis_status"]) <= {
        "primary",
        "prespecified_sensitivity",
        "exploratory_sensitivity",
    }
    assert set(executed["analysis_status"]) <= {
        "primary",
        "prespecified_sensitivity",
        "exploratory_sensitivity",
        "deviation",
    }
    assert set(executed["execution_status"]) == {
        "completed",
        "not_evaluable",
        "non_converged",
    }
    assert "not_evaluable" in set(comparison["comparison_status"])
    assert "non_converged" in set(comparison["comparison_status"])
    assert "changed_estimand_not_comparable" in set(comparison["comparison_status"])

    same_ids = set(registry.loc[registry["same_estimand_required"], "condition_id"])
    assert set(executed.loc[executed["condition_id"].isin(same_ids), "estimand_id"]) == {"E01"}
    registered = set(registry.loc[registry["condition_id"] != "B00", "condition_id"])
    assert registered <= set(executed["condition_id"])

    assert not any("p_value" in col or "significant" in col for col in comparison.columns)
    assert set(comparison["automatic_robustness_verdict"]) == {"not_created"}

    assert manifest["primary_estimand_id"] == "E01"
    assert manifest["registered_sensitivities_all_represented"] is True
    assert manifest["not_evaluable_condition_count"] >= 1
    assert manifest["non_converged_condition_count"] >= 1
    for key in (
        "statistical_significance_claim_created",
        "automatic_robustness_verdict_created",
        "causal_claim_created",
        "construct_validity_claim_created",
        "native_device_validity_claim_created",
        "primary_estimand_redefined",
        "non_evaluable_or_nonconverged_silently_dropped",
        "synthetic_values_are_empirical_results",
    ):
        assert manifest[key] is False

    api = pd.read_csv(out / "05_interpretation_matrix.csv")
    assert {
        "api-reference.md#quality-control",
        "api-reference.md#eye-events",
        "api-reference.md#sampling-sensitivity",
        "api-reference.md#semantic-aois",
        "api-reference.md#scanpaths",
        "api-reference.md#model-comparison",
        "api-reference.md#matched-fold-model-differences",
    } <= set(api["api_route"])

    readme = (out / "README.md").read_text().lower()
    assert "not_evaluable" in readme
    assert "non_converged" in readme
    assert "favourable sensitivity result never replaces" in readme
    assert "not native-device validation" in readme
    assert "not empirical" in readme
