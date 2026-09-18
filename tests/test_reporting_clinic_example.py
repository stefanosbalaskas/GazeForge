from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/11_worked_manuscript_reporting_bundle.py"


def _hashes(directory: Path) -> dict[str, str]:
    return {
        str(path.relative_to(directory)).replace("\\", "/"): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def _run(output: Path) -> None:
    subprocess.run(
        [sys.executable, str(EXAMPLE), "--output-dir", str(output)],
        check=True,
        cwd=ROOT,
    )


def test_worked_reporting_bundle_is_deterministic_and_reporting_only(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _run(first)
    _run(second)

    expected = {
        "methods_record.json",
        "denominator_flow.csv",
        "artifact_citation_table.csv",
        "reporting_boundaries.json",
        "software_identity.json",
        "methods_example.md",
        "results_example.md",
        "archive_readme.md",
        "reporting_manifest.json",
    }
    assert {path.name for path in first.iterdir() if path.is_file()} == expected
    assert _hashes(first) == _hashes(second)

    manifest = json.loads((first / "reporting_manifest.json").read_text(encoding="utf-8"))
    assert manifest["evidence_classification"] == "synthetic_demo_not_empirical_evidence"
    assert manifest["upstream_artifacts_unchanged"] is True
    assert manifest["source_artifact_modified"] is False
    assert manifest["qc_artifact_modified"] is False
    assert manifest["review_artifact_modified"] is False
    assert manifest["analysis_artifact_modified"] is False
    assert manifest["inferential_statistics_invented"] is False
    assert manifest["empirical_validity_claim_created"] is False
    assert manifest["psychological_state_claim_created"] is False

    for upstream in (
        "01_source_tracker_export.csv",
        "03_pre_review_qc_samples.csv",
        "06_trial_review_ledger.csv",
        "07_primary_analysis_rows.csv",
        "13_semantic_scanpaths.csv",
    ):
        assert upstream in manifest["upstream_hashes_sha256"]

    denominator = pd.read_csv(first / "denominator_flow.csv")
    assert denominator.set_index("stage").loc["trial_denominator", "n"] == 6
    assert denominator.set_index("stage").loc["excluded_trials", "n"] == 2
    assert denominator.set_index("stage").loc["retained_trials", "n"] == 4

    citations = pd.read_csv(first / "artifact_citation_table.csv")
    assert citations["upstream_sha256"].notna().all()
    assert citations["upstream_sha256"].str.len().eq(64).all()
    assert "01_source_tracker_export.csv" in set(citations["filename"])
    assert "07_primary_analysis_rows.csv" in set(citations["filename"])

    methods_record = json.loads(
        (first / "methods_record.json").read_text(encoding="utf-8")
    )
    assert methods_record["nominal_rate_hz"] == 60.0
    assert methods_record["observed_cadence_hz"] > 0
    assert methods_record["coordinate_basis"] == "normalized_screen_fraction"
    assert methods_record["event_method"]["algorithm"] == "I-VT"
    assert methods_record["event_method"]["velocity_threshold_px_s"] == 1000.0
    assert methods_record["aoi_source"] == "researcher_defined"

    boundaries = json.loads(
        (first / "reporting_boundaries.json").read_text(encoding="utf-8")
    )
    for key in (
        "empirical_validation_claim_created",
        "device_validity_claim_created",
        "native_60hz_validity_claim_created",
        "gazepoint_gp3_validity_claim_created",
        "event_model_validity_claim_created",
        "aoi_construct_validity_claim_created",
        "measurement_validity_claim_created",
        "causal_claim_created",
        "psychological_state_claim_created",
        "universal_qc_threshold_claim_created",
        "universal_ivt_threshold_claim_created",
    ):
        assert boundaries[key] is False

    methods = (first / "methods_example.md").read_text(encoding="utf-8").lower()
    results = (first / "results_example.md").read_text(encoding="utf-8").lower()
    assert "software demonstration" in methods
    assert "not universal" in methods
    assert "not empirical" in results or "not estimates" in results
    assert "p-value" not in results
    assert "effect size" not in results


def test_reporting_clinic_is_discoverable_and_rejects_inflated_wording() -> None:
    clinic = (ROOT / "docs/reporting-clinic.md").read_text(encoding="utf-8")
    lower = clinic.lower()
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    homepage = (ROOT / "docs/index.md").read_text(encoding="utf-8")
    docmap = (ROOT / "docs/documentation-map.md").read_text(encoding="utf-8")
    chooser = (ROOT / "docs/method-chooser.md").read_text(encoding="utf-8")
    dictionary = (ROOT / "docs/artifact-dictionary.md").read_text(encoding="utf-8")
    evidence = (ROOT / "docs/research-evidence-bundle.md").read_text(encoding="utf-8")
    readiness = (ROOT / "docs/publication-readiness.md").read_text(encoding="utf-8")
    reporting = (ROOT / "docs/reproducible-reporting.md").read_text(encoding="utf-8")
    runnable = (ROOT / "docs/runnable-examples.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for page in (
        mkdocs,
        homepage,
        docmap,
        chooser,
        dictionary,
        evidence,
        readiness,
        reporting,
        runnable,
        readme,
    ):
        assert "reporting-clinic" in page

    for heading in (
        "interpret",
        "report",
        "do not say",
        "archive",
        "continue to",
    ):
        assert heading in lower

    for phrase in (
        "successful import validated the eye tracker",
        "qc algorithm removed invalid samples",
        "participant-held-out",
        "native 60 hz",
        "confidence was 0.92",
        "psychological state",
        "synthetic_demo_not_empirical_evidence",
        "failed convergence",
    ):
        assert phrase in lower

    assert "gf-flow" in clinic
    assert "10.3758/s13428-023-02187-1" in clinic
    for target in (
        "api-reference.md#quality-control",
        "api-reference.md#eye-events",
        "api-reference.md#semantic-aois",
        "api-reference.md#dynamic-aois",
        "api-reference.md#scanpaths",
        "api-reference.md#sampling-sensitivity",
    ):
        assert target in clinic
    assert "<researcher-defined" not in clinic
    assert "11_worked_manuscript_reporting_bundle.py" in clinic
    assert "11_worked_manuscript_reporting_bundle.py" in runnable

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
