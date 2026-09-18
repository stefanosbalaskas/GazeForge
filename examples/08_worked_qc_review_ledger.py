"""Worked QC review and exclusion-ledger example.

This deterministic demo separates automated QC evidence from human-reviewed
analysis decisions. It preserves the canonical and pre-review QC tables,
records prespecified and exploratory criteria separately, and writes an
auditable exclusion ledger. It is not empirical validation evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from gazeforge import (
    AuditTrail,
    __version__,
    ai_flag_anomalies,
    fingerprint_frame,
    score_trial_quality,
)

SCREEN_SIZE_PX = (1920, 1080)
SAMPLING_RATE_HZ = 60.0
EVIDENCE_CLASSIFICATION = "synthetic_demo_not_empirical_evidence"
DEMO_REVIEWER = "demo_reviewer"
DEMO_REVIEW_DATE = "2026-01-15T12:00:00Z"


def _build_canonical_demo() -> pd.DataFrame:
    """Return deterministic canonical gaze with reviewable QC cases."""
    rows: list[dict[str, Any]] = []
    n_samples = 30
    dt_ms = 1000.0 / SAMPLING_RATE_HZ

    for p_idx, participant in enumerate(("P001", "P002", "P003"), start=1):
        for t_idx, trial in enumerate(("T01", "T02", "T03"), start=1):
            for sample_idx in range(n_samples):
                phase = 0.23 * sample_idx + 0.41 * t_idx + 0.13 * p_idx
                rows.append(
                    {
                        "participant_id": participant,
                        "trial_id": trial,
                        "timestamp_ms": round(sample_idx * dt_ms, 6),
                        "x_px": float(960 + 230 * np.sin(phase)),
                        "y_px": float(540 + 150 * np.cos(phase * 0.91)),
                        "pupil": float(3.2 + 0.1 * np.sin(phase * 0.63)),
                    }
                )

    data = pd.DataFrame(rows)

    # Prespecified trial-level review case: 12/30 missing gaze samples.
    missing_mask = (
        (data["participant_id"] == "P001")
        & (data["trial_id"] == "T02")
        & (data.groupby(["participant_id", "trial_id"]).cumcount() < 12)
    )
    data.loc[missing_mask, ["x_px", "y_px"]] = np.nan

    # Prespecified trial-level review case: 9/30 off-screen samples.
    offscreen_mask = (
        (data["participant_id"] == "P002")
        & (data["trial_id"] == "T03")
        & (data.groupby(["participant_id", "trial_id"]).cumcount() < 9)
    )
    data.loc[offscreen_mask, "x_px"] = 2035.0

    # Isolated within-screen jump used only to create review evidence.
    isolated = (
        (data["participant_id"] == "P003")
        & (data["trial_id"] == "T01")
        & (data.groupby(["participant_id", "trial_id"]).cumcount() == 14)
    )
    data.loc[isolated, ["x_px", "y_px"]] = [75.0, 975.0]

    return data


def _criterion_registry() -> pd.DataFrame:
    """Return the deterministic review policy used by the teaching example."""
    return pd.DataFrame(
        [
            {
                "criterion_id": "C01",
                "scope": "trial",
                "status": "prespecified",
                "metric": "missing_rate",
                "operator": ">=",
                "threshold": 0.30,
                "action": "exclude_trial_after_review",
                "purpose": "primary_analysis",
                "rationale": "Trial missing-gaze proportion at or above 30%.",
            },
            {
                "criterion_id": "C02",
                "scope": "trial",
                "status": "prespecified",
                "metric": "offscreen_rate",
                "operator": ">=",
                "threshold": 0.20,
                "action": "exclude_trial_after_review",
                "purpose": "primary_analysis",
                "rationale": "Trial off-screen proportion at or above 20%.",
            },
            {
                "criterion_id": "C03",
                "scope": "sample",
                "status": "prespecified",
                "metric": "qc_flag",
                "operator": "==",
                "threshold": True,
                "action": "review_only",
                "purpose": "quality_review",
                "rationale": "Automated anomaly flag prompts review but is not an exclusion rule.",
            },
            {
                "criterion_id": "S01",
                "scope": "trial",
                "status": "exploratory",
                "metric": "anomaly_rate",
                "operator": ">=",
                "threshold": 1.0 / 30.0,
                "action": "sensitivity_only",
                "purpose": "exploratory_sensitivity",
                "rationale": (
                    "Illustrative post-hoc sensitivity rule; never applied to primary rows."
                ),
            },
        ]
    )


def _trial_review_ledger(quality: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    order = 1
    for _, trial in quality.sort_values(["participant_id", "trial_id"]).iterrows():
        triggers: list[str] = []
        if float(trial["missing_rate"]) >= 0.30:
            triggers.append("C01")
        if float(trial["offscreen_rate"]) >= 0.20:
            triggers.append("C02")

        decision = "excluded" if triggers else "retained"
        rows.append(
            {
                "decision_order": order,
                "reviewed_at_utc": DEMO_REVIEW_DATE,
                "reviewer_id": DEMO_REVIEWER,
                "participant_id": trial["participant_id"],
                "trial_id": trial["trial_id"],
                "scope": "trial",
                "triggered_criteria": ";".join(triggers),
                "review_status": "reviewed",
                "decision": decision,
                "denominator_n_samples": int(trial["n_samples"]),
                "missing_rate": float(trial["missing_rate"]),
                "offscreen_rate": float(trial["offscreen_rate"]),
                "anomaly_rate": float(trial["anomaly_rate"]),
                "quality_score": float(trial["quality_score"]),
                "rationale": (
                    "Prespecified threshold met and reviewed."
                    if triggers
                    else "No prespecified primary exclusion threshold met."
                ),
            }
        )
        order += 1
    return pd.DataFrame(rows)


def _sample_review_ledger(
    qc: pd.DataFrame,
    excluded_trial_keys: set[tuple[str, str]],
) -> pd.DataFrame:
    candidate = qc.loc[qc["qc_flag"].astype(bool)].copy()
    candidate["trial_key"] = list(
        zip(candidate["participant_id"], candidate["trial_id"], strict=True)
    )
    candidate = candidate.loc[~candidate["trial_key"].isin(excluded_trial_keys)]
    if candidate.empty:
        raise RuntimeError(
            "The deterministic demo expected at least one anomaly-flagged sample "
            "inside a retained trial."
        )

    sample = candidate.sort_values(
        ["qc_anomaly_score", "participant_id", "trial_id", "timestamp_ms"],
        ascending=[False, True, True, True],
    ).iloc[0]
    return pd.DataFrame(
        [
            {
                "decision_order": 1,
                "reviewed_at_utc": DEMO_REVIEW_DATE,
                "reviewer_id": DEMO_REVIEWER,
                "participant_id": sample["participant_id"],
                "trial_id": sample["trial_id"],
                "timestamp_ms": float(sample["timestamp_ms"]),
                "scope": "sample",
                "criterion_id": "C03",
                "qc_flag": bool(sample["qc_flag"]),
                "qc_anomaly_score": float(sample["qc_anomaly_score"]),
                "review_status": "reviewed",
                "decision": "retained",
                "denominator_n_samples": int(len(qc)),
                "rationale": (
                    "Isolated automated anomaly flag reviewed; no prespecified "
                    "sample-level exclusion rule was met."
                ),
            }
        ]
    )


def _participant_review_ledger(
    trial_ledger: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for participant, part in trial_ledger.groupby("participant_id", sort=True):
        n_total = int(len(part))
        n_excluded = int((part["decision"] == "excluded").sum())
        n_retained = n_total - n_excluded
        rows.append(
            {
                "participant_id": participant,
                "scope": "participant",
                "review_status": "reviewed",
                "n_trials_total": n_total,
                "n_trials_excluded": n_excluded,
                "n_trials_retained": n_retained,
                "decision": "retained" if n_retained >= 2 else "review_required",
                "denominator_n_trials": n_total,
                "rationale": (
                    "Participant retained because at least two reviewed trials remain."
                    if n_retained >= 2
                    else "Participant requires separate review; no automatic exclusion applied."
                ),
            }
        )
    return pd.DataFrame(rows)


def _build_exclusion_flow(
    qc: pd.DataFrame,
    trial_ledger: pd.DataFrame,
    participant_ledger: pd.DataFrame,
    primary_rows: pd.DataFrame,
) -> pd.DataFrame:
    total_trials = int(len(trial_ledger))
    excluded_trials = int((trial_ledger["decision"] == "excluded").sum())
    return pd.DataFrame(
        [
            {
                "stage": "pre_review_qc",
                "unit": "sample",
                "denominator": int(len(qc)),
                "excluded": 0,
                "retained": int(len(qc)),
                "note": "QC evidence only; no rows removed.",
            },
            {
                "stage": "trial_review",
                "unit": "trial",
                "denominator": total_trials,
                "excluded": excluded_trials,
                "retained": total_trials - excluded_trials,
                "note": "Human-reviewed prespecified trial criteria.",
            },
            {
                "stage": "participant_review",
                "unit": "participant",
                "denominator": int(len(participant_ledger)),
                "excluded": int((participant_ledger["decision"] == "excluded").sum()),
                "retained": int((participant_ledger["decision"] == "retained").sum()),
                "note": "No participant is excluded by a sample-level anomaly.",
            },
            {
                "stage": "primary_analysis_rows",
                "unit": "sample",
                "denominator": int(len(qc)),
                "excluded": int(len(qc) - len(primary_rows)),
                "retained": int(len(primary_rows)),
                "note": "Separate derivative created from reviewed trial decisions.",
            },
        ]
    )


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    canonical = _build_canonical_demo()
    canonical_snapshot = canonical.copy(deep=True)
    canonical_fingerprint = fingerprint_frame(canonical)

    trail = AuditTrail()
    qc = ai_flag_anomalies(
        canonical,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        contamination=0.04,
        random_state=42,
        trail=trail,
    )
    qc_snapshot = qc.copy(deep=True)
    qc_fingerprint = fingerprint_frame(qc)

    quality = score_trial_quality(qc, screen_size_px=SCREEN_SIZE_PX)
    criteria = _criterion_registry()
    trial_ledger = _trial_review_ledger(quality)

    excluded_trials = trial_ledger.loc[
        trial_ledger["decision"] == "excluded",
        ["participant_id", "trial_id"],
    ]
    excluded_trial_keys = set(
        zip(
            excluded_trials["participant_id"],
            excluded_trials["trial_id"],
            strict=True,
        )
    )

    sample_ledger = _sample_review_ledger(qc, excluded_trial_keys)
    participant_ledger = _participant_review_ledger(trial_ledger)

    status = qc.copy()
    status["analysis_status"] = [
        "excluded_trial"
        if (participant, trial) in excluded_trial_keys
        else "retained"
        for participant, trial in zip(
            status["participant_id"], status["trial_id"], strict=True
        )
    ]
    primary_rows = status.loc[status["analysis_status"] == "retained"].copy()

    exploratory = quality.copy()
    exploratory["criterion_id"] = "S01"
    exploratory["criterion_status"] = "exploratory"
    exploratory["triggered"] = exploratory["anomaly_rate"] >= (1.0 / 30.0)
    exploratory["applied_to_primary_analysis"] = False
    exploratory["note"] = (
        "Sensitivity-only teaching rule; primary analysis rows are unchanged."
    )

    exclusion_flow = _build_exclusion_flow(
        qc,
        trial_ledger,
        participant_ledger,
        primary_rows,
    )

    trail.add(
        operation="apply_reviewed_primary_exclusions",
        input_data=qc,
        output_data=primary_rows,
        parameters={
            "decision_source": "human_reviewed_trial_ledger",
            "prespecified_criteria": ["C01", "C02"],
            "sample_qc_flag_is_exclusion_rule": False,
            "exploratory_criterion_applied": False,
        },
        warnings=[
            "QC flags are review evidence, not automatic invalidity labels.",
            "Reproducible exclusion rules are not evidence that the rules are validated.",
        ],
    )

    outputs = {
        "01_canonical_source.csv": canonical,
        "02_pre_review_qc_samples.csv": qc,
        "03_trial_quality.csv": quality,
        "04_decision_criteria.csv": criteria,
        "05_sample_review_ledger.csv": sample_ledger,
        "06_trial_review_ledger.csv": trial_ledger,
        "07_participant_review_ledger.csv": participant_ledger,
        "08_exclusion_flow.csv": exclusion_flow,
        "09_reviewed_sample_status.csv": status,
        "10_primary_analysis_rows.csv": primary_rows,
        "11_exploratory_sensitivity.csv": exploratory,
    }
    for filename, frame in outputs.items():
        frame.to_csv(output_dir / filename, index=False)

    analysis_plan = {
        "purpose": "worked QC review and exclusion-ledger demonstration",
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "primary_exclusion_scope": "trial",
        "primary_criteria": ["C01", "C02"],
        "sample_qc_flag_is_automatic_exclusion": False,
        "exploratory_criterion": "S01",
        "exploratory_criterion_applied_to_primary_analysis": False,
        "participant_exclusion_from_single_bad_trial": False,
        "source_mutation_allowed": False,
        "pre_review_qc_mutation_allowed": False,
    }
    _write_json(output_dir / "analysis_plan.json", analysis_plan)
    (output_dir / "provenance.json").write_text(
        trail.to_json(indent=2) + "\n",
        encoding="utf-8",
    )

    canonical_unchanged = canonical.equals(canonical_snapshot)
    qc_unchanged = qc.equals(qc_snapshot)
    n_excluded_trials = int((trial_ledger["decision"] == "excluded").sum())
    n_retained_participants = int(
        (participant_ledger["decision"] == "retained").sum()
    )
    anomaly_review_retained = bool(
        sample_ledger.iloc[0]["qc_flag"]
        and sample_ledger.iloc[0]["decision"] == "retained"
    )

    assert canonical_unchanged
    assert qc_unchanged
    assert n_excluded_trials == 2
    assert n_retained_participants == 3
    assert anomaly_review_retained
    assert len(primary_rows) == len(qc) - 60
    assert not exploratory["applied_to_primary_analysis"].any()

    manifest = {
        "example": "08_worked_qc_review_ledger",
        "gazeforge_version": __version__,
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "canonical_source_unchanged": canonical_unchanged,
        "pre_review_qc_unchanged": qc_unchanged,
        "canonical_fingerprint": canonical_fingerprint,
        "pre_review_qc_fingerprint": qc_fingerprint,
        "reviewed_status_fingerprint": fingerprint_frame(status),
        "primary_analysis_fingerprint": fingerprint_frame(primary_rows),
        "source_rows": int(len(canonical)),
        "pre_review_qc_rows": int(len(qc)),
        "primary_analysis_rows": int(len(primary_rows)),
        "trial_denominator": int(len(trial_ledger)),
        "excluded_trials": n_excluded_trials,
        "retained_trials": int(len(trial_ledger) - n_excluded_trials),
        "participant_denominator": int(len(participant_ledger)),
        "retained_participants": n_retained_participants,
        "qc_flag_reviewed_and_retained": anomaly_review_retained,
        "qc_flag_is_automatic_exclusion": False,
        "exploratory_rule_applied_to_primary_analysis": False,
        "device_validity_claim_created": False,
        "event_model_validity_claim_created": False,
        "measurement_validity_claim_created": False,
        "csv_outputs": list(outputs),
        "json_outputs": [
            "analysis_plan.json",
            "provenance.json",
            "workflow_manifest.json",
        ],
        "scientific_boundary": (
            "This deterministic synthetic workflow demonstrates auditable review "
            "and exclusion bookkeeping. It does not establish that an anomaly, "
            "threshold, tracker, event model, calibration, or measurement is valid."
        ),
    }
    _write_json(output_dir / "workflow_manifest.json", manifest)

    print("Worked QC review + exclusion ledger complete")
    print(f"Output directory: {output_dir}")
    print(f"Pre-review QC unchanged: {'yes' if qc_unchanged else 'no'}")
    print(f"Reviewed trial denominator: {len(trial_ledger)}")
    print(f"Excluded trials: {n_excluded_trials}")
    print(f"Retained participants: {n_retained_participants}/{len(participant_ledger)}")
    print(
        "QC-flag boundary: anomaly flags prompt review; they are not automatic exclusions."
    )
    print(
        "Evidence boundary: synthetic workflow demo only; reproducible review rules "
        "are not validation evidence."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the deterministic QC review and exclusion-ledger example."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-qc-review-ledger-demo"),
        help="Directory for reviewable CSV/JSON outputs.",
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
