"""Regression coverage for the worked manuscript/reporting bundle."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/11_worked_manuscript_reporting_bundle.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _hash_tree(path: Path) -> dict[str, str]:
    return {
        item.relative_to(path).as_posix(): _sha256(item)
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def test_worked_reporting_bundle_is_deterministic_and_preserves_upstream(
    tmp_path: Path,
) -> None:
    output = tmp_path / "reporting"
    evidence = tmp_path / "evidence"
    command = [
        sys.executable,
        str(EXAMPLE),
        "--output-dir",
        str(output),
        "--evidence-dir",
        str(evidence),
        "--analysis-commit",
        "DEMO_COMMIT_SHA",
    ]

    subprocess.run(command, check=True, cwd=ROOT)

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
    assert expected == {path.name for path in output.iterdir() if path.is_file()}

    evidence_before = _hash_tree(evidence)
    reporting_before = _hash_tree(output)
    subprocess.run(command, check=True, cwd=ROOT)
    assert _hash_tree(evidence) == evidence_before
    assert _hash_tree(output) == reporting_before

    manifest = json.loads(
        (output / "reporting_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["evidence_classification"] == "synthetic_demo_not_empirical_evidence"
    assert manifest["upstream_unchanged"] is True
    assert manifest["upstream_before_sha256"] == manifest["upstream_after_sha256"]
    assert manifest["new_scientific_analysis_performed"] is False
    assert manifest["qc_or_exclusion_decisions_changed"] is False
    assert manifest["event_or_aoi_labels_changed"] is False
    assert manifest["inferential_statistics_created"] is False
    assert manifest["empirical_validity_claim_created"] is False
    assert manifest["device_validity_claim_created"] is False
    assert manifest["measurement_validity_claim_created"] is False
    assert manifest["psychological_state_claim_created"] is False
    assert manifest["analysis_commit"] == "DEMO_COMMIT_SHA"

    flow = pd.read_csv(output / "denominator_flow.csv")
    trial = flow.loc[flow["stage"] == "reviewed_trials"].iloc[0]
    samples = flow.loc[flow["stage"] == "primary_analysis_samples"].iloc[0]
    assert int(trial["denominator"]) == 6
    assert int(trial["retained"]) == 4
    assert int(trial["excluded"]) == 2
    assert int(samples["retained"]) < int(samples["denominator"])

    boundaries = json.loads(
        (output / "reporting_boundaries.json").read_text(encoding="utf-8")
    )
    assert boundaries["inferential_effect_claim_created"] is False
    assert boundaries["native_60hz_validity_claim_created"] is False
    assert boundaries["gazepoint_gp3_validity_claim_created"] is False

    methods = (output / "methods_example.md").read_text(encoding="utf-8").lower()
    results = (output / "results_example.md").read_text(encoding="utf-8").lower()
    assert "qc flags were not automatic exclusions" in methods
    assert "not a universal physiological cutoff" in methods
    assert "not empirical validation evidence" in methods
    assert "no inferential statistical test" in results
    assert "trust" in results
    assert "persuasion" in results
    assert "diagnosis" in results


def test_reporting_clinic_is_discoverable_and_study_path_is_accessible() -> None:
    clinic = (ROOT / "docs/reporting-interpretation-clinic.md").read_text(
        encoding="utf-8"
    )
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    homepage = (ROOT / "docs/index.md").read_text(encoding="utf-8")
    css = (ROOT / "docs/stylesheets/extra.css").read_text(encoding="utf-8")

    assert "# Reporting & interpretation clinic" in clinic
    assert "11_worked_manuscript_reporting_bundle.py" in clinic
    assert "Interpret" in clinic
    assert "Do not say" in clinic
    assert "not empirical validation evidence" in clinic.lower()
    assert "no new scientific analysis" in clinic.lower()
    assert (
        "Reporting & interpretation clinic: reporting-interpretation-clinic.md"
        in mkdocs
    )
    assert "reporting-interpretation-clinic.md" in homepage

    assert 'class="gf-study-path"' in clinic
    assert 'aria-current="step"' in clinic
    assert ".gf-study-path" in css
    assert ".gf-study-path a:focus-visible" in css
    assert "prefers-reduced-motion" in css

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
