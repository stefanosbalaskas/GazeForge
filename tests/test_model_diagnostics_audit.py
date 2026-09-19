from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/17_worked_model_diagnostics_audit.py"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(path: Path) -> dict[str, str]:
    return {p.name: _sha(p) for p in sorted(path.iterdir()) if p.is_file()}


def test_model_diagnostics_audit_contract(tmp_path: Path) -> None:
    out = tmp_path / "audit"
    cmd = [sys.executable, str(EXAMPLE), "--output-dir", str(out)]
    subprocess.run(cmd, check=True, cwd=ROOT)
    first = _tree(out)
    subprocess.run(cmd, check=True, cwd=ROOT)
    assert _tree(out) == first

    expected = {
        "01_model_fit_registry.csv",
        "02_diagnostic_status.csv",
        "03_interpretation_gate.csv",
        "04_sensitivity_linkage.csv",
        "05_reporting_language.csv",
        "06_api_route_map.csv",
        "README.md",
        "model_diagnostics_manifest.json",
    }
    assert {p.name for p in out.iterdir() if p.is_file()} == expected

    fits = pd.read_csv(out / "01_model_fit_registry.csv")
    diag = pd.read_csv(out / "02_diagnostic_status.csv")
    gate = pd.read_csv(out / "03_interpretation_gate.csv")
    manifest = json.loads((out / "model_diagnostics_manifest.json").read_text())

    assert set(diag.diagnostic_status) == {
        "pass",
        "blocked_non_converged",
        "blocked_singular_or_boundary",
        "blocked_missing_diagnostics",
        "blocked_separation_or_covariance",
    }
    assert set(gate.interpretation_gate) == {
        "eligible_for_interpretation",
        "blocked_diagnostic_failure",
        "exploratory_changed_estimand",
    }
    failed = gate.diagnostic_status.ne("pass")
    assert not gate.loc[failed, "interpretation_allowed"].any()
    assert not gate.may_replace_primary_automatically.any()

    changed = fits.changed_estimand_or_population
    changed_ids = set(fits.loc[changed, "model_id"])
    assert changed_ids == {"M06"}
    m06 = gate.loc[gate.model_id == "M06"].iloc[0]
    assert m06.interpretation_gate == "exploratory_changed_estimand"
    assert not bool(m06.interpretation_allowed)

    assert not any("p_value" in c or "effect_size" in c for c in gate.columns)
    for key in (
        "inferential_model_fitted_by_example",
        "automatic_replacement_model_selected",
        "failed_fit_accepted_for_inference",
        "p_value_or_effect_claim_created",
        "causal_claim_created",
        "construct_validity_claim_created",
        "device_validity_claim_created",
    ):
        assert manifest[key] is False

    readme = (out / "README.md").read_text().lower()
    assert "non-convergence" in readme
    assert "singular/boundary" in readme
    assert "missing diagnostics" in readme
    assert "not empirical" in readme
