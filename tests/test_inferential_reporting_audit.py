from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/18_worked_inferential_reporting_audit.py"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(path: Path) -> dict[str, str]:
    return {p.name: _sha(p) for p in sorted(path.iterdir()) if p.is_file()}


def test_inferential_reporting_audit_contract(tmp_path: Path) -> None:
    out = tmp_path / "audit"
    cmd = [sys.executable, str(EXAMPLE), "--output-dir", str(out)]
    subprocess.run(cmd, check=True, cwd=ROOT)
    first = _tree(out)
    subprocess.run(cmd, check=True, cwd=ROOT)
    assert _tree(out) == first

    expected = {
        "01_result_registry.csv",
        "02_uncertainty_audit.csv",
        "03_multiplicity_family.csv",
        "04_interpretation_gate.csv",
        "05_reporting_language.csv",
        "06_api_route_map.csv",
        "README.md",
        "inferential_reporting_manifest.json",
    }
    assert {p.name for p in out.iterdir() if p.is_file()} == expected

    results = pd.read_csv(out / "01_result_registry.csv")
    uncertainty = pd.read_csv(out / "02_uncertainty_audit.csv")
    families = pd.read_csv(out / "03_multiplicity_family.csv")
    gate = pd.read_csv(out / "04_interpretation_gate.csv")
    manifest = json.loads((out / "inferential_reporting_manifest.json").read_text())

    assert set(gate.interpretation_gate) == {
        "eligible_confirmatory",
        "eligible_exploratory",
        "blocked_missing_uncertainty_identity",
        "blocked_multiplicity_incomplete",
        "blocked_scale_or_unit_mismatch",
        "blocked_diagnostic_failure",
    }
    assert uncertainty.interval_bounds_ordered.all()
    assert {"p_value_raw", "p_value_adjusted"} <= set(results.columns)
    assert "significant" not in " ".join(results.columns).lower()

    f1 = families.loc[families.multiplicity_family_id == "F1"].iloc[0]
    f2 = families.loc[families.multiplicity_family_id == "F2"].iloc[0]
    assert bool(f1.family_record_complete)
    assert not bool(f2.family_record_complete)

    r03 = gate.loc[gate.result_id == "R03"].iloc[0]
    r04 = gate.loc[gate.result_id == "R04"].iloc[0]
    r05 = gate.loc[gate.result_id == "R05"].iloc[0]
    r06 = gate.loc[gate.result_id == "R06"].iloc[0]
    r07 = gate.loc[gate.result_id == "R07"].iloc[0]
    assert r03.interpretation_gate == "eligible_exploratory"
    assert r04.interpretation_gate == "blocked_missing_uncertainty_identity"
    assert r05.interpretation_gate == "blocked_multiplicity_incomplete"
    assert r06.interpretation_gate == "blocked_scale_or_unit_mismatch"
    assert r07.interpretation_gate == "blocked_diagnostic_failure"
    blocked = gate.interpretation_gate.str.startswith("blocked_")
    assert not gate.loc[blocked, "interpretation_allowed"].any()

    for key in (
        "inferential_model_fitted_by_example",
        "multiplicity_method_selected_automatically",
        "raw_adjusted_p_values_conflated",
        "exploratory_promoted_to_confirmatory",
        "diagnostic_failure_overridden",
        "scientific_truth_label_created",
        "causal_claim_created",
        "construct_validity_claim_created",
        "device_or_native_rate_validity_claim_created",
    ):
        assert manifest[key] is False

    readme = (out / "README.md").read_text().lower()
    assert "all estimates, intervals, and p-values are teaching values" in readme
    assert "not empirical" in readme


def test_inferential_reporting_clinic_is_discoverable_and_claim_safe() -> None:
    guide = (ROOT / "docs/inferential-reporting-audit.md").read_text(encoding="utf-8")
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    homepage = (ROOT / "docs/index.md").read_text(encoding="utf-8")
    gallery = (ROOT / "docs/runnable-examples.md").read_text(encoding="utf-8")

    lower = guide.lower()
    assert "# Uncertainty, multiplicity & inferential reporting clinic" in guide
    assert "18_worked_inferential_reporting_audit.py" in guide
    assert "p_value_raw" in guide
    assert "p_value_adjusted" in guide
    assert "no universal correction" in lower
    assert "eligible_confirmatory" in guide
    assert "eligible_exploratory" in guide
    assert "blocked_multiplicity_incomplete" in guide
    assert "workflow gates, not scientific truth labels" in lower
    assert "every estimate, interval" in lower
    assert "teaching value" in lower
    assert "Uncertainty, multiplicity & inferential reporting: inferential-reporting-audit.md" in mkdocs
    assert "inferential-reporting-audit.md" in homepage
    assert "twenty deterministic examples" in gallery

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
