from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/16_worked_denominator_exposure_audit.py"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(path: Path) -> dict[str, str]:
    return {p.name: _sha(p) for p in sorted(path.iterdir()) if p.is_file()}


def test_denominator_exposure_audit_contract(tmp_path: Path) -> None:
    out = tmp_path / "audit"
    cmd = [sys.executable, str(EXAMPLE), "--output-dir", str(out)]
    subprocess.run(cmd, check=True, cwd=ROOT)
    first = _tree(out)
    subprocess.run(cmd, check=True, cwd=ROOT)
    assert _tree(out) == first

    expected = {
        "01_observation_status_registry.csv",
        "02_denominator_exposure_ledger.csv",
        "03_count_rate_audit.csv",
        "04_proportion_dwell_audit.csv",
        "05_latency_censoring_audit.csv",
        "06_reconciliation_flow.csv",
        "07_reporting_language.csv",
        "08_api_route_map.csv",
        "README.md",
        "denominator_exposure_manifest.json",
    }
    assert {p.name for p in out.iterdir() if p.is_file()} == expected

    registry = pd.read_csv(out / "01_observation_status_registry.csv")
    rates = pd.read_csv(out / "03_count_rate_audit.csv")
    props = pd.read_csv(out / "04_proportion_dwell_audit.csv")
    latency = pd.read_csv(out / "05_latency_censoring_audit.csv")
    manifest = json.loads((out / "denominator_exposure_manifest.json").read_text())

    assert len(registry) == 8
    assert set(registry.observation_status) == {
        "observed_positive",
        "observed_zero",
        "partial_observed",
        "missing_trial",
        "absent_by_design",
        "undefined_denominator",
    }
    assert manifest["input_row_count"] == manifest["output_registry_row_count"] == 8

    p01t01 = rates.query("participant_id == 'P01' and trial_id == 'T01'").iloc[0]
    p01t02 = rates.query("participant_id == 'P01' and trial_id == 'T02'").iloc[0]
    assert abs(float(p01t01.fixation_rate_per_s) - 2 / 3) < 1e-12
    assert float(p01t02.fixation_rate_per_s) == 0.0
    undefined_rates = rates.aoi_observable_ms.fillna(0).le(0)
    assert rates.loc[undefined_rates, "fixation_rate_per_s"].isna().all()

    prop = props.query("participant_id == 'P01' and trial_id == 'T01'").iloc[0]
    assert abs(float(prop.dwell_proportion) - 0.3) < 1e-12
    undefined_props = props.aoi_observable_ms.fillna(0).le(0)
    assert props.loc[undefined_props, "dwell_proportion"].isna().all()

    censored = latency.loc[latency.latency_status == "right_censored_no_fixation"]
    assert len(censored) >= 1
    assert censored.right_censored.all()
    assert (censored.analysis_time_ms == censored.censor_time_ms).all()
    blocked = latency.latency_status.isin(
        ["missing_trial", "absent_by_design", "undefined_denominator"]
    )
    assert not latency.loc[blocked, "right_censored"].any()

    for key in (
        "inferential_model_selected",
        "missing_converted_to_zero",
        "absent_by_design_converted_to_zero",
        "undefined_denominator_converted_to_zero",
        "silent_complete_case_filtering",
        "causal_claim_created",
        "construct_validity_claim_created",
        "device_or_native_rate_validity_claim_created",
        "empirical_validation_claim_created",
    ):
        assert manifest[key] is False

    api = pd.read_csv(out / "08_api_route_map.csv")
    assert {
        "api-reference.md#schema-validation",
        "api-reference.md#quality-control",
        "api-reference.md#eye-events",
        "api-reference.md#semantic-aois",
        "api-reference.md#scanpaths",
    } <= set(api.api_route)

    readme = (out / "README.md").read_text().lower()
    assert "fillna(0)" in readme
    assert "right-censored" in readme
    assert "not empirical validation evidence" in readme


def test_denominator_exposure_clinic_is_discoverable_and_claim_safe() -> None:
    guide = (ROOT / "docs/denominator-exposure-censoring.md").read_text(encoding="utf-8")
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    homepage = (ROOT / "docs/index.md").read_text(encoding="utf-8")
    gallery = (ROOT / "docs/runnable-examples.md").read_text(encoding="utf-8")

    lower = guide.lower()
    assert "# Denominator, exposure & censoring clinic" in guide
    assert "16_worked_denominator_exposure_audit.py" in guide
    assert "fillna(0)" in guide
    assert "observed_zero" in guide
    assert "missing_trial" in guide
    assert "absent_by_design" in guide
    assert "undefined_denominator" in guide
    assert "right-censored" in lower
    assert "not empirical validation" in lower
    for route in (
        "api-reference.md#schema-validation",
        "api-reference.md#quality-control",
        "api-reference.md#eye-events",
        "api-reference.md#semantic-aois",
        "api-reference.md#scanpaths",
    ):
        assert route in guide
    assert "Denominator, exposure & censoring clinic: denominator-exposure-censoring.md" in mkdocs
    assert "denominator-exposure-censoring.md" in homepage
    assert "twenty-two deterministic examples" in gallery

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
