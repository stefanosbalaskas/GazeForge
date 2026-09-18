"""Regression coverage for the worked QC review and exclusion-ledger path."""

from __future__ import annotations

import json
import pathlib
import runpy
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_worked_qc_review_ledger_runs_and_reconciles(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    output_dir = tmp_path / "worked-qc-review-ledger-demo"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "08_worked_qc_review_ledger.py",
            "--output-dir",
            str(output_dir),
        ],
    )

    runpy.run_path(
        str(ROOT / "examples" / "08_worked_qc_review_ledger.py"),
        run_name="__main__",
    )
    captured = capsys.readouterr()

    expected_csv = {
        "01_canonical_source.csv",
        "02_pre_review_qc_samples.csv",
        "03_trial_quality.csv",
        "04_decision_criteria.csv",
        "05_sample_review_ledger.csv",
        "06_trial_review_ledger.csv",
        "07_participant_review_ledger.csv",
        "08_exclusion_flow.csv",
        "09_reviewed_sample_status.csv",
        "10_primary_analysis_rows.csv",
        "11_exploratory_sensitivity.csv",
    }
    expected_json = {
        "analysis_plan.json",
        "provenance.json",
        "workflow_manifest.json",
    }
    assert {path.name for path in output_dir.glob("*.csv")} == expected_csv
    assert {path.name for path in output_dir.glob("*.json")} == expected_json

    canonical = pd.read_csv(output_dir / "01_canonical_source.csv")
    qc = pd.read_csv(output_dir / "02_pre_review_qc_samples.csv")
    criteria = pd.read_csv(output_dir / "04_decision_criteria.csv")
    sample_ledger = pd.read_csv(output_dir / "05_sample_review_ledger.csv")
    trial_ledger = pd.read_csv(output_dir / "06_trial_review_ledger.csv")
    participant_ledger = pd.read_csv(
        output_dir / "07_participant_review_ledger.csv"
    )
    flow = pd.read_csv(output_dir / "08_exclusion_flow.csv")
    status = pd.read_csv(output_dir / "09_reviewed_sample_status.csv")
    primary = pd.read_csv(output_dir / "10_primary_analysis_rows.csv")
    exploratory = pd.read_csv(output_dir / "11_exploratory_sensitivity.csv")
    manifest = json.loads(
        (output_dir / "workflow_manifest.json").read_text(encoding="utf-8")
    )
    plan = json.loads(
        (output_dir / "analysis_plan.json").read_text(encoding="utf-8")
    )

    assert len(canonical) == len(qc) == len(status) == 270
    assert len(primary) == 210
    assert manifest["canonical_source_unchanged"] is True
    assert manifest["pre_review_qc_unchanged"] is True
    assert manifest["trial_denominator"] == 9
    assert manifest["excluded_trials"] == 2
    assert manifest["retained_trials"] == 7
    assert manifest["participant_denominator"] == 3
    assert manifest["retained_participants"] == 3
    assert manifest["qc_flag_reviewed_and_retained"] is True
    assert manifest["qc_flag_is_automatic_exclusion"] is False
    assert manifest["exploratory_rule_applied_to_primary_analysis"] is False
    assert manifest["device_validity_claim_created"] is False
    assert manifest["event_model_validity_claim_created"] is False
    assert manifest["measurement_validity_claim_created"] is False

    assert set(criteria["status"]) == {"prespecified", "exploratory"}
    assert set(
        criteria.loc[criteria["purpose"] == "primary_analysis", "criterion_id"]
    ) == {"C01", "C02"}
    assert plan["sample_qc_flag_is_automatic_exclusion"] is False
    assert plan["exploratory_criterion_applied_to_primary_analysis"] is False

    assert len(sample_ledger) == 1
    assert bool(sample_ledger.loc[0, "qc_flag"]) is True
    assert sample_ledger.loc[0, "decision"] == "retained"
    assert sample_ledger.loc[0, "criterion_id"] == "C03"

    excluded = trial_ledger.loc[trial_ledger["decision"] == "excluded"]
    assert {
        (row.participant_id, row.trial_id, row.triggered_criteria)
        for row in excluded.itertuples()
    } == {
        ("P001", "T02", "C01"),
        ("P002", "T03", "C02"),
    }
    assert trial_ledger["decision_order"].tolist() == list(range(1, 10))

    assert set(participant_ledger["decision"]) == {"retained"}
    p001 = participant_ledger.loc[
        participant_ledger["participant_id"] == "P001"
    ].iloc[0]
    assert int(p001["n_trials_excluded"]) == 1
    assert int(p001["n_trials_retained"]) == 2

    assert not exploratory["applied_to_primary_analysis"].any()
    assert set(exploratory["criterion_status"]) == {"exploratory"}

    primary_flow = flow.loc[flow["stage"] == "primary_analysis_rows"].iloc[0]
    assert int(primary_flow["denominator"]) == 270
    assert int(primary_flow["excluded"]) == 60
    assert int(primary_flow["retained"]) == 210

    assert set(status["analysis_status"]) == {"retained", "excluded_trial"}
    assert "Pre-review QC unchanged: yes" in captured.out
    assert "anomaly flags prompt review; they are not automatic exclusions" in captured.out
    assert "reproducible review rules are not validation evidence" in captured.out


def test_qc_review_ledger_learning_path_is_discoverable_and_claim_safe() -> None:
    script = _read("examples/08_worked_qc_review_ledger.py")
    guide = _read("docs/qc-review-exclusion-ledger.md")
    gallery = _read("docs/runnable-examples.md")
    examples_readme = _read("examples/README.md")
    homepage = _read("docs/index.md")
    mkdocs = _read("mkdocs.yml")

    for token in (
        "qc_flag_is_automatic_exclusion",
        "exploratory_rule_applied_to_primary_analysis",
        "apply_reviewed_primary_exclusions",
        "sample_qc_flag_is_exclusion_rule",
        "synthetic_demo_not_empirical_evidence",
    ):
        assert token in script

    lower = guide.lower()
    assert "qc evidence ≠ automatic invalidity" in lower
    assert "flagged and retained" in lower
    assert "prespecified and exploratory" in lower
    assert "denominator accounting" in lower
    assert "do not by themselves prove" in lower
    assert "reproducibility does not make it externally validated" in lower
    assert "sample, trial, participant" in lower

    assert "fourteen deterministic examples" in gallery.lower()
    assert "08_worked_qc_review_ledger.py" in gallery
    assert "qc-review-exclusion-ledger.md" in gallery
    assert "08_worked_qc_review_ledger.py" in examples_readme

    for page in (gallery, examples_readme, mkdocs):
        assert "qc-review-exclusion-ledger.md" in page

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
