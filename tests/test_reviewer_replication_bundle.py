from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/14_worked_reviewer_replication_bundle.py"


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


def test_reviewer_replication_bundle_is_deterministic_and_claim_safe(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _run(first)
    _run(second)

    expected = {
        "01_claim_artifact_matrix.csv",
        "02_rerun_plan.csv",
        "03_reproducibility_checklist.csv",
        "04_limitations_register.csv",
        "05_api_route_map.csv",
        "artifact_hash_ledger.csv",
        "software_environment.json",
        "reviewer_start_here.md",
        "replication_manifest.json",
    }
    assert {path.name for path in first.iterdir() if path.is_file()} == expected
    assert _hashes(first) == _hashes(second)

    claims = pd.read_csv(first / "01_claim_artifact_matrix.csv")
    allowed = {"fully_rerunnable", "rerunnable_with_private_input", "inspectable_only"}
    assert set(claims["reproducibility_class"]) <= allowed
    assert claims["evidence_classification"].eq("synthetic_demo_not_empirical_evidence").all()
    assert claims["interpretation_boundary"].notna().all()
    private_claims = claims["artifact_access"] == "study_archive_required"
    assert not claims.loc[private_claims, "bundled_by_default"].astype(bool).any()

    rerun = pd.read_csv(first / "02_rerun_plan.csv")
    assert set(rerun["reproducibility_class"]) <= allowed
    private = rerun["reproducibility_class"] == "rerunnable_with_private_input"
    assert rerun.loc[private, "data_access_note"].str.contains("not bundled", case=False).all()

    routes = pd.read_csv(first / "05_api_route_map.csv")
    assert routes["documentation_anchor"].str.startswith("api-reference.md#").all()

    ledger = pd.read_csv(first / "artifact_hash_ledger.csv")
    assert len(ledger) == 7
    for row in ledger.itertuples(index=False):
        path = first / row.filename
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row.sha256
        assert path.stat().st_size == row.bytes

    manifest = json.loads((first / "replication_manifest.json").read_text(encoding="utf-8"))
    assert manifest["reproducibility_classes"] == [
        "fully_rerunnable",
        "rerunnable_with_private_input",
        "inspectable_only",
    ]
    assert manifest["private_or_restricted_inputs_bundled"] is False
    assert manifest["hash_ledger_sha256"] == hashlib.sha256(
        (first / "artifact_hash_ledger.csv").read_bytes()
    ).hexdigest()
    for key in (
        "source_artifact_modified",
        "qc_artifact_modified",
        "review_artifact_modified",
        "analysis_artifact_modified",
        "missing_converted_to_zero",
        "device_validity_claim_created",
        "native_rate_validity_claim_created",
        "measurement_validity_claim_created",
        "model_validity_claim_created",
        "construct_validity_claim_created",
        "causal_validity_claim_created",
        "external_validity_claim_created",
        "psychological_state_claim_created",
        "reproducibility_equated_with_validity",
    ):
        assert manifest[key] is False
