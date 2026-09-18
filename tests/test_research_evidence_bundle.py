from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/09_worked_research_evidence_bundle.py"


def test_worked_research_evidence_bundle_is_archive_shaped_and_claim_safe(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    subprocess.run(
        [sys.executable, str(EXAMPLE), "--output-dir", str(output)],
        check=True,
        cwd=ROOT,
    )

    expected = {
        "README.md",
        "source_contract.json",
        "01_source_tracker_export.csv",
        "02_canonical_gaze.csv",
        "03_pre_review_qc_samples.csv",
        "04_decision_criteria.csv",
        "05_trial_quality.csv",
        "06_trial_review_ledger.csv",
        "07_primary_analysis_rows.csv",
        "08_event_samples.csv",
        "09_event_intervals.csv",
        "10_fixation_centroids.csv",
        "11_aoi_definitions.csv",
        "12_fixation_aoi_assignments.csv",
        "13_semantic_scanpaths.csv",
        "artifact_index.csv",
        "analysis_plan.json",
        "provenance.json",
        "workflow_manifest.json",
    }
    assert expected == {path.name for path in output.iterdir() if path.is_file()}

    manifest = json.loads((output / "workflow_manifest.json").read_text(encoding="utf-8"))
    assert manifest["evidence_classification"] == "synthetic_demo_not_empirical_evidence"
    assert manifest["source_unchanged"] is True
    assert manifest["canonical_pre_review_unchanged"] is True
    assert manifest["pre_review_qc_unchanged"] is True
    assert manifest["qc_flag_is_automatic_exclusion"] is False
    assert manifest["excluded_trials"] == 2
    assert manifest["device_validity_claim_created"] is False
    assert manifest["event_model_validity_claim_created"] is False
    assert manifest["measurement_validity_claim_created"] is False
    assert manifest["psychological_state_claim_created"] is False

    index = pd.read_csv(output / "artifact_index.csv")
    assert {"source", "canonical", "qc", "review", "analysis", "provenance", "reporting"} <= set(index["layer"])
    assert index["archive_recommended"].astype(bool).all()
    assert index["filename"].is_unique
    assert {"artifact_index.csv", "workflow_manifest.json"} <= set(index["filename"])

    source = pd.read_csv(output / "01_source_tracker_export.csv")
    canonical = pd.read_csv(output / "02_canonical_gaze.csv")
    qc = pd.read_csv(output / "03_pre_review_qc_samples.csv")
    primary = pd.read_csv(output / "07_primary_analysis_rows.csv")
    ledger = pd.read_csv(output / "06_trial_review_ledger.csv")

    assert len(source) == len(canonical) == len(qc)
    assert len(primary) < len(qc)
    assert (ledger["decision"] == "excluded").sum() == 2


def test_evidence_bundle_docs_are_discoverable_and_homepage_keeps_three_hero_buttons() -> None:
    guide = (ROOT / "docs/research-evidence-bundle.md").read_text(encoding="utf-8")
    chooser = (ROOT / "docs/method-chooser.md").read_text(encoding="utf-8")
    dictionary = (ROOT / "docs/artifact-dictionary.md").read_text(encoding="utf-8")
    runnable = (ROOT / "docs/runnable-examples.md").read_text(encoding="utf-8")
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    homepage = (ROOT / "docs/index.md").read_text(encoding="utf-8")

    for text in (guide, chooser, dictionary, runnable, mkdocs, homepage):
        assert "research-evidence-bundle.md" in text or text is guide

    assert "09_worked_research_evidence_bundle.py" in guide
    assert "09_worked_research_evidence_bundle.py" in runnable
    assert "artifact_index.csv" in guide
    assert "qc flags are not automatic exclusions" in guide.lower()
    assert "not empirical validation evidence" in guide.lower()

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
