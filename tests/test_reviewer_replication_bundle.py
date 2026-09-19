from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/14_worked_reviewer_replication_bundle.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hashes(path: Path) -> dict[str, str]:
    return {p.name: _sha256(p) for p in sorted(path.iterdir()) if p.is_file()}


def test_bundle_is_deterministic_and_claim_safe(tmp_path: Path) -> None:
    out = tmp_path / "bundle"
    cmd = [sys.executable, str(EXAMPLE), "--output-dir", str(out)]
    subprocess.run(cmd, check=True, cwd=ROOT)
    first = _tree_hashes(out)
    subprocess.run(cmd, check=True, cwd=ROOT)
    assert _tree_hashes(out) == first

    expected = {
        "01_claim_artifact_matrix.csv",
        "02_rerun_plan.csv",
        "03_reproducibility_checklist.csv",
        "04_limitations_register.csv",
        "05_api_route_map.csv",
        "software_environment.json",
        "reviewer_start_here.md",
        "artifact_hash_ledger.csv",
        "replication_manifest.json",
    }
    assert {p.name for p in out.iterdir() if p.is_file()} == expected

    manifest = json.loads((out / "replication_manifest.json").read_text())
    assert manifest["evidence_classification"] == "synthetic_demo_not_empirical_evidence"
    assert manifest["scientific_analysis_performed"] is False
    assert manifest["private_or_restricted_source_bundled"] is False
    for key in (
        "empirical_validation_claim_created",
        "device_validity_claim_created",
        "native_rate_validity_claim_created",
        "model_validity_claim_created",
        "measurement_or_construct_validity_claim_created",
        "source_artifact_modified",
        "qc_artifact_modified",
        "review_artifact_modified",
        "analysis_artifact_modified",
        "missing_converted_to_zero",
        "causal_claim_created",
        "external_validity_claim_created",
        "psychological_state_claim_created",
        "reproducibility_equals_validity_claim_created",
    ):
        assert manifest[key] is False

    classes = {
        "fully_rerunnable_demo",
        "rerunnable_with_private_input",
        "inspectable_only",
    }
    claim_matrix = pd.read_csv(out / "01_claim_artifact_matrix.csv")
    rerun = pd.read_csv(out / "02_rerun_plan.csv")
    assert set(claim_matrix["reproducibility_class"]) <= classes
    assert claim_matrix["evidence_classification"].eq(
        "synthetic_demo_not_empirical_evidence"
    ).all()
    assert claim_matrix["interpretation_boundary"].notna().all()
    private_claims = claim_matrix["artifact_access"] == "study_archive_required"
    assert not claim_matrix.loc[private_claims, "bundled_by_default"].astype(bool).any()
    assert set(rerun["reproducibility_class"]) == classes
    private_row = rerun.loc[rerun["purpose"] == "private study rerun"].iloc[0]
    assert bool(private_row["external_or_private_input_required"]) is True

    ledger = pd.read_csv(out / "artifact_hash_ledger.csv")
    for row in ledger.itertuples():
        assert row.sha256 == _sha256(out / row.filename)
        assert bool(row.scientific_validity_created) is False

    api = pd.read_csv(out / "05_api_route_map.csv")
    assert {
        "api-reference.md#schema",
        "api-reference.md#quality-control",
        "api-reference.md#eye-events",
        "api-reference.md#semantic-aois",
        "api-reference.md#dynamic-aois",
        "api-reference.md#scanpaths",
        "api-reference.md#visual-diagnostics",
        "api-reference.md#structural-validation-scope",
        "api-reference.md#sampling-sensitivity",
    } <= set(api["api_route"])

    start = (out / "reviewer_start_here.md").read_text().lower()
    assert "reproducibility" in start
    assert "not empirical validation evidence" in start
    assert "private/restricted" in start
    assert "latent state" in start


def test_reviewer_handoff_is_discoverable_and_claim_safe() -> None:
    guide = (ROOT / "docs/reviewer-replication-handoff.md").read_text(encoding="utf-8")
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    homepage = (ROOT / "docs/index.md").read_text(encoding="utf-8")
    gallery = (ROOT / "docs/runnable-examples.md").read_text(encoding="utf-8")

    lower = guide.lower()
    assert "# Reviewer & replication handoff" in guide
    assert "14_worked_reviewer_replication_bundle.py" in guide
    assert "fully_rerunnable_demo" in guide
    assert "rerunnable_with_private_input" in guide
    assert "inspectable_only" in guide
    assert "not empirical validation evidence" in lower
    assert "privacy and licensing" in lower
    assert "fillna(0)" in guide
    assert "full git commit sha" in lower
    assert "api-reference.md#schema" in guide
    assert "api-reference.md#quality-control" in guide
    assert "api-reference.md#eye-events" in guide
    assert "api-reference.md#semantic-aois" in guide
    assert "api-reference.md#dynamic-aois" in guide
    assert "api-reference.md#scanpaths" in guide
    assert "api-reference.md#visual-diagnostics" in guide
    assert "api-reference.md#structural-validation-scope" in guide
    assert "api-reference.md#sampling-sensitivity" in guide
    assert "Reviewer & replication handoff: reviewer-replication-handoff.md" in mkdocs
    assert "reviewer-replication-handoff.md" in homepage
    assert "twenty-two deterministic examples" in gallery

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
