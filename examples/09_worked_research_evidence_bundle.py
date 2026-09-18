"""Build a deterministic, archive-facing GazeForge research evidence bundle.

The example composes existing public GazeForge APIs into one reviewable bundle:
tracker-shaped source -> canonical data -> non-destructive QC -> reviewed trial
decisions -> primary-analysis derivative -> transparent events -> researcher-defined
AOIs -> fixation assignments -> semantic scanpaths -> provenance and manifest.

All inputs are synthetic/demo data. The bundle demonstrates software composition and
research bookkeeping only; it is not empirical validation evidence and does not
establish tracker, native-60-Hz, Gazepoint, GP3, event-model, AOI, or measurement
validity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from gazeforge import (
    AOI,
    AuditTrail,
    __version__,
    adapt_gazepoint_samples,
    ai_flag_anomalies,
    aois_to_frame,
    fingerprint_frame,
    infer_sampling_rate_hz,
    ivt_classify_events,
    map_fixations_to_aois,
    samples_to_event_intervals,
    score_trial_quality,
    to_semantic_scanpaths,
)

SAMPLING_RATE_HZ = 60.0
SCREEN_SIZE_PX = (1920, 1080)
EVIDENCE_CLASSIFICATION = "synthetic_demo_not_empirical_evidence"
REVIEWER_ID = "demo_reviewer"
REVIEWED_AT_UTC = "2026-01-15T12:00:00Z"


def _build_tracker_source() -> pd.DataFrame:
    centers = {
        "brand": (300.0, 180.0),
        "claim": (500.0, 495.0),
        "disclosure": (500.0, 840.0),
        "product": (1460.0, 540.0),
    }
    sequences = {
        "ad_a": ("brand", "claim", "product", "disclosure"),
        "ad_b": ("product", "claim", "disclosure", "brand"),
    }
    jitter = ((0.0, 0.0), (3.0, -2.0), (-2.0, 2.0), (2.0, 1.0), (-3.0, -1.0))
    dt_s = 1.0 / SAMPLING_RATE_HZ
    rows: list[dict[str, Any]] = []

    for participant_index, participant in enumerate(("P001", "P002", "P003"), start=1):
        offset_x = float((participant_index - 1) * 2)
        offset_y = float(participant_index - 2)
        for trial, sequence in sequences.items():
            time_s = 0.0
            previous: tuple[float, float] | None = None
            for label in sequence:
                center = centers[label]
                if previous is not None:
                    for step in range(1, 5):
                        fraction = step / 5.0
                        x_px = previous[0] + fraction * (center[0] - previous[0])
                        y_px = previous[1] + fraction * (center[1] - previous[1])
                        rows.append(
                            {
                                "USER_FILE": participant,
                                "MEDIA_ID": trial,
                                "TIME": round(time_s, 9),
                                "BPOGX": x_px / SCREEN_SIZE_PX[0],
                                "BPOGY": y_px / SCREEN_SIZE_PX[1],
                                "PUPIL": 3.2,
                                "VALIDITY": 1,
                            }
                        )
                        time_s += dt_s
                for sample_index in range(24):
                    dx, dy = jitter[sample_index % len(jitter)]
                    x_px = center[0] + dx + offset_x
                    y_px = center[1] + dy + offset_y
                    rows.append(
                        {
                            "USER_FILE": participant,
                            "MEDIA_ID": trial,
                            "TIME": round(time_s, 9),
                            "BPOGX": x_px / SCREEN_SIZE_PX[0],
                            "BPOGY": y_px / SCREEN_SIZE_PX[1],
                            "PUPIL": float(3.2 + 0.05 * np.sin(sample_index / 4.0)),
                            "VALIDITY": 1,
                        }
                    )
                    time_s += dt_s
                previous = center

    source = pd.DataFrame(rows)

    # Two deliberate trial-level review cases. They stay in source/canonical/QC.
    p1b = source.index[
        (source["USER_FILE"] == "P001") & (source["MEDIA_ID"] == "ad_b")
    ][:26]
    source.loc[p1b, ["BPOGX", "BPOGY"]] = np.nan

    p2b = source.index[
        (source["USER_FILE"] == "P002") & (source["MEDIA_ID"] == "ad_b")
    ][:20]
    source.loc[p2b, "BPOGX"] = 1.08

    return source


def _aois() -> list[AOI]:
    return [
        AOI("brand", "brand", 80, 80, 520, 280, source="researcher_defined"),
        AOI("claim", "claim", 80, 340, 940, 650, source="researcher_defined"),
        AOI("disclosure", "disclosure", 80, 760, 940, 920, source="researcher_defined"),
        AOI("product", "product", 1080, 150, 1840, 930, source="researcher_defined"),
    ]


def _fixation_centroids(
    event_samples: pd.DataFrame,
    event_intervals: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    fixations = event_intervals.loc[event_intervals["event_label"] == "fixation"]
    for event in fixations.itertuples(index=False):
        samples = event_samples.loc[
            (event_samples["participant_id"] == event.participant_id)
            & (event_samples["trial_id"] == event.trial_id)
            & (event_samples["timestamp_ms"] >= event.start_ms)
            & (event_samples["timestamp_ms"] < event.end_ms)
        ]
        x = pd.to_numeric(samples["x_px"], errors="coerce")
        y = pd.to_numeric(samples["y_px"], errors="coerce")
        valid = x.notna() & y.notna()
        if not valid.any():
            continue
        rows.append(
            {
                "participant_id": event.participant_id,
                "trial_id": event.trial_id,
                "event_index": int(event.event_index),
                "start_ms": float(event.start_ms),
                "end_ms": float(event.end_ms),
                "duration_ms": float(event.duration_ms),
                "n_samples": int(event.n_samples),
                "x_px": float(x[valid].mean()),
                "y_px": float(y[valid].mean()),
            }
        )
    return pd.DataFrame(rows)


def _criteria() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "criterion_id": "C01",
                "scope": "trial",
                "status": "prespecified_for_demo",
                "metric": "missing_rate",
                "operator": ">=",
                "threshold": 0.20,
                "action": "exclude_trial_after_review",
                "rationale": "Teaching threshold for the deterministic bundle; not a validated universal rule.",
            },
            {
                "criterion_id": "C02",
                "scope": "trial",
                "status": "prespecified_for_demo",
                "metric": "offscreen_rate",
                "operator": ">=",
                "threshold": 0.15,
                "action": "exclude_trial_after_review",
                "rationale": "Teaching threshold for the deterministic bundle; not a validated universal rule.",
            },
            {
                "criterion_id": "C03",
                "scope": "sample",
                "status": "review_only",
                "metric": "qc_flag",
                "operator": "==",
                "threshold": True,
                "action": "review_not_automatic_exclusion",
                "rationale": "Automated anomaly flags are evidence for review, not invalidity labels.",
            },
        ]
    )


def _review_trials(quality: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for order, trial in enumerate(
        quality.sort_values(["participant_id", "trial_id"]).itertuples(index=False),
        start=1,
    ):
        triggers: list[str] = []
        if float(trial.missing_rate) >= 0.20:
            triggers.append("C01")
        if float(trial.offscreen_rate) >= 0.15:
            triggers.append("C02")
        rows.append(
            {
                "decision_order": order,
                "reviewed_at_utc": REVIEWED_AT_UTC,
                "reviewer_id": REVIEWER_ID,
                "participant_id": trial.participant_id,
                "trial_id": trial.trial_id,
                "triggered_criteria": ";".join(triggers),
                "review_status": "reviewed",
                "decision": "excluded" if triggers else "retained",
                "n_samples": int(trial.n_samples),
                "missing_rate": float(trial.missing_rate),
                "offscreen_rate": float(trial.offscreen_rate),
                "anomaly_rate": float(trial.anomaly_rate),
                "quality_score": float(trial.quality_score),
                "rationale": (
                    "Reviewed demo criterion met."
                    if triggers
                    else "No prespecified demo trial-exclusion criterion met."
                ),
            }
        )
    return pd.DataFrame(rows)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bundle_readme() -> str:
    return """# GazeForge worked research evidence bundle

This directory is a deterministic **synthetic/demo** archive showing how to keep
source data, QC evidence, reviewed decisions, analysis derivatives, event/AOI/
scanpath outputs, and reporting metadata separate.

## Read in this order

1. `source_contract.json` — what the tracker-shaped columns and units mean.
2. `01_source_tracker_export.csv` — immutable source-shaped input.
3. `02_canonical_gaze.csv` and `03_pre_review_qc_samples.csv` — derived but
   pre-review records; neither silently applies exclusions.
4. `04_decision_criteria.csv` and `06_trial_review_ledger.csv` — explicit
   teaching criteria and reviewed decisions.
5. `07_primary_analysis_rows.csv` — the separate derivative used downstream.
6. `08_event_samples.csv` through `13_semantic_scanpaths.csv` — transparent
   event/AOI/scanpath analysis products.
7. `artifact_index.csv`, `analysis_plan.json`, `provenance.json`, and
   `workflow_manifest.json` — archive/reporting metadata.

## Evidence boundary

Successful execution demonstrates software composition and auditable bookkeeping.
It does **not** establish tracker validity, native-60-Hz validity, Gazepoint/GP3
validity, event-model validity, AOI construct validity, calibration validity,
measurement validity, or a substantive psychological effect. QC flags are not
automatic exclusions, and the demonstration thresholds are not universal rules.
"""


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    source = _build_tracker_source()
    source_snapshot = source.copy(deep=True)
    source_fingerprint = fingerprint_frame(source)
    source.to_csv(output_dir / "01_source_tracker_export.csv", index=False)

    gaze = adapt_gazepoint_samples(
        source,
        screen_size_px=SCREEN_SIZE_PX,
        participant_col="USER_FILE",
        trial_col="MEDIA_ID",
        timestamp_col="TIME",
        x_col="BPOGX",
        y_col="BPOGY",
        pupil_col="PUPIL",
        validity_col="VALIDITY",
        time_unit="seconds",
        coordinates="normalized",
        sampling_rate_hz=SAMPLING_RATE_HZ,
    )
    canonical = gaze.data
    canonical_snapshot = canonical.copy(deep=True)
    canonical_fingerprint = fingerprint_frame(canonical)
    observed_cadence_hz = infer_sampling_rate_hz(canonical)
    canonical.to_csv(output_dir / "02_canonical_gaze.csv", index=False)

    trail = AuditTrail()
    trail.add(
        operation="adapt_gazepoint_samples",
        input_data=source,
        output_data=canonical,
        parameters={
            "time_unit": "seconds",
            "coordinates": "normalized",
            "screen_size_px": SCREEN_SIZE_PX,
            "sampling_rate_hz": SAMPLING_RATE_HZ,
        },
        warnings=[
            "Adapter compatibility is not Gazepoint/GP3 or native-60-Hz validation.",
            "Observed timestamp cadence is a stream diagnostic, not proof of hardware rate.",
        ],
    )

    qc = ai_flag_anomalies(
        canonical,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        random_state=42,
        trail=trail,
    )
    qc_snapshot = qc.copy(deep=True)
    qc_fingerprint = fingerprint_frame(qc)
    qc.to_csv(output_dir / "03_pre_review_qc_samples.csv", index=False)

    quality = score_trial_quality(qc, screen_size_px=SCREEN_SIZE_PX)
    quality.to_csv(output_dir / "05_trial_quality.csv", index=False)

    criteria = _criteria()
    criteria.to_csv(output_dir / "04_decision_criteria.csv", index=False)
    trial_ledger = _review_trials(quality)
    trial_ledger.to_csv(output_dir / "06_trial_review_ledger.csv", index=False)

    excluded = set(
        zip(
            trial_ledger.loc[trial_ledger["decision"] == "excluded", "participant_id"],
            trial_ledger.loc[trial_ledger["decision"] == "excluded", "trial_id"],
            strict=True,
        )
    )
    reviewed = qc.copy()
    reviewed["analysis_status"] = [
        "excluded_trial" if key in excluded else "retained"
        for key in zip(reviewed["participant_id"], reviewed["trial_id"], strict=True)
    ]
    primary = reviewed.loc[reviewed["analysis_status"] == "retained"].copy()
    primary.to_csv(output_dir / "07_primary_analysis_rows.csv", index=False)

    trail.add(
        operation="apply_reviewed_trial_decisions",
        input_data=qc,
        output_data=primary,
        parameters={
            "decision_source": "06_trial_review_ledger.csv",
            "qc_flag_is_automatic_exclusion": False,
            "criteria": ["C01", "C02"],
        },
        warnings=[
            "The demo criteria are teaching thresholds, not validated universal exclusion rules."
        ],
    )

    event_samples = ivt_classify_events(
        primary,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        velocity_threshold_px_s=1000.0,
    )
    event_samples.to_csv(output_dir / "08_event_samples.csv", index=False)
    event_intervals = samples_to_event_intervals(
        event_samples,
        label_col="predicted_event",
        sampling_rate_hz=SAMPLING_RATE_HZ,
    )
    event_intervals.to_csv(output_dir / "09_event_intervals.csv", index=False)

    fixation_centroids = _fixation_centroids(event_samples, event_intervals)
    fixation_centroids.to_csv(output_dir / "10_fixation_centroids.csv", index=False)

    aois = _aois()
    aoi_definitions = aois_to_frame(aois)
    aoi_definitions.to_csv(output_dir / "11_aoi_definitions.csv", index=False)
    assignments = map_fixations_to_aois(
        fixation_centroids,
        aois,
        overlap_rule="first",
        trail=trail,
    )
    assignments.to_csv(output_dir / "12_fixation_aoi_assignments.csv", index=False)
    scanpaths = to_semantic_scanpaths(assignments)
    scanpaths.to_csv(output_dir / "13_semantic_scanpaths.csv", index=False)

    trail.add(
        operation="build_semantic_scanpaths",
        input_data=assignments,
        output_data=scanpaths,
        parameters={"collapse_repeats": True, "drop_unassigned": True},
        warnings=["Semantic scanpaths describe sequence structure, not latent mental states."],
    )

    source_contract = {
        "source_format": "deterministic Gazepoint-style synthetic export",
        "participant_col": "USER_FILE",
        "trial_col": "MEDIA_ID",
        "timestamp_col": "TIME",
        "timestamp_unit": "seconds",
        "x_col": "BPOGX",
        "y_col": "BPOGY",
        "coordinate_basis": "normalized_screen_fraction",
        "screen_size_px": list(SCREEN_SIZE_PX),
        "nominal_rate_hz": SAMPLING_RATE_HZ,
        "observed_cadence_hz": float(observed_cadence_hz),
        "observed_cadence_is_hardware_rate_proof": False,
        "repair_policy": "review-first; no silent clipping, row deletion, or unit guessing",
        "evidence_classification": EVIDENCE_CLASSIFICATION,
    }
    _write_json(output_dir / "source_contract.json", source_contract)

    analysis_plan = {
        "purpose": "worked archive-facing research evidence bundle",
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "primary_analysis_input": "07_primary_analysis_rows.csv",
        "reviewed_trial_decisions": "06_trial_review_ledger.csv",
        "qc_flag_is_automatic_exclusion": False,
        "source_mutation_allowed": False,
        "canonical_pre_review_mutation_allowed": False,
        "pre_review_qc_mutation_allowed": False,
        "event_method": {
            "algorithm": "I-VT",
            "velocity_threshold_px_s": 1000.0,
            "status": "transparent demonstration baseline",
        },
        "aoi_source": "researcher_defined",
        "aoi_labels": ["brand", "claim", "disclosure", "product"],
        "substantive_boundary": (
            "Gaze/AOI/scanpath outputs describe observable attention structure only; "
            "they do not establish trust, persuasion, comprehension, intent, diagnosis, "
            "or another latent psychological state."
        ),
    }
    _write_json(output_dir / "analysis_plan.json", analysis_plan)

    # The worked archive is advertised as deterministic. Freeze demo provenance
    # timestamps so repeated runs have byte-identical reporting identities.
    for record in trail.records:
        record.timestamp_utc = REVIEWED_AT_UTC

    (output_dir / "provenance.json").write_text(
        trail.to_json(indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "README.md").write_text(_bundle_readme(), encoding="utf-8")

    artifact_rows = [
        ("README.md", "reporting", "bundle", True, "human-readable archive map"),
        ("source_contract.json", "source", "source contract", True, "declared import semantics"),
        ("01_source_tracker_export.csv", "source", "sample", True, "immutable tracker-shaped source"),
        ("02_canonical_gaze.csv", "canonical", "sample", True, "vendor-neutral canonical derivative"),
        ("03_pre_review_qc_samples.csv", "qc", "sample", True, "non-destructive pre-review QC evidence"),
        ("04_decision_criteria.csv", "review", "criterion", True, "review policy registry"),
        ("05_trial_quality.csv", "qc", "trial", True, "trial-quality evidence"),
        ("06_trial_review_ledger.csv", "review", "trial decision", True, "reviewed exclusion decisions"),
        ("07_primary_analysis_rows.csv", "analysis", "sample", False, "reviewed primary-analysis derivative"),
        ("08_event_samples.csv", "analysis", "sample", False, "transparent event labels"),
        ("09_event_intervals.csv", "analysis", "event", False, "event intervals"),
        ("10_fixation_centroids.csv", "analysis", "fixation", False, "fixation-level coordinates"),
        ("11_aoi_definitions.csv", "analysis", "AOI", True, "researcher-defined geometry"),
        ("12_fixation_aoi_assignments.csv", "analysis", "fixation", False, "AOI assignments"),
        ("13_semantic_scanpaths.csv", "analysis", "trial sequence", False, "semantic sequence representation"),
        ("artifact_index.csv", "reporting", "artifact", True, "bundle table of contents"),
        ("analysis_plan.json", "reporting", "plan", True, "frozen analysis intent and boundaries"),
        ("provenance.json", "provenance", "operation", True, "operation lineage"),
        ("workflow_manifest.json", "reporting", "bundle", True, "bundle identity, hashes, denominators, and boundaries"),
    ]
    artifact_index = pd.DataFrame(
        [
            {
                "filename": filename,
                "layer": layer,
                "unit": unit,
                "immutable_or_frozen": immutable,
                "archive_recommended": True,
                "purpose": purpose,
                "evidence_classification": EVIDENCE_CLASSIFICATION,
                "cannot_establish": (
                    "empirical validity, native-device validity, native-60-Hz validity, "
                    "Gazepoint/GP3 validity, or a substantive psychological effect"
                ),
            }
            for filename, layer, unit, immutable, purpose in artifact_rows
        ]
    )
    artifact_index.to_csv(output_dir / "artifact_index.csv", index=False)

    pd.testing.assert_frame_equal(source, source_snapshot, check_exact=True)
    pd.testing.assert_frame_equal(canonical, canonical_snapshot, check_exact=True)
    pd.testing.assert_frame_equal(qc, qc_snapshot, check_exact=True)

    source_unchanged = fingerprint_frame(source) == source_fingerprint
    canonical_pre_review_unchanged = fingerprint_frame(canonical) == canonical_fingerprint
    pre_review_qc_unchanged = fingerprint_frame(qc) == qc_fingerprint

    assert source_unchanged
    assert canonical_pre_review_unchanged
    assert pre_review_qc_unchanged
    assert len(excluded) == 2
    assert len(primary) < len(qc)
    assert set(assignments["aoi_label"].dropna().astype(str)) == {
        "brand",
        "claim",
        "disclosure",
        "product",
    }

    files_for_hash = sorted(
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.name != "workflow_manifest.json"
    )
    file_hashes = {path.name: _sha256_file(path) for path in files_for_hash}

    manifest = {
        "example": "09_worked_research_evidence_bundle",
        "gazeforge_version": __version__,
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "source_unchanged": source_unchanged,
        "canonical_pre_review_unchanged": canonical_pre_review_unchanged,
        "pre_review_qc_unchanged": pre_review_qc_unchanged,
        "source_fingerprint": source_fingerprint,
        "canonical_fingerprint": canonical_fingerprint,
        "pre_review_qc_fingerprint": qc_fingerprint,
        "primary_analysis_fingerprint": fingerprint_frame(primary),
        "source_rows": int(len(source)),
        "pre_review_qc_rows": int(len(qc)),
        "primary_analysis_rows": int(len(primary)),
        "trial_denominator": int(len(trial_ledger)),
        "excluded_trials": int((trial_ledger["decision"] == "excluded").sum()),
        "retained_trials": int((trial_ledger["decision"] == "retained").sum()),
        "artifact_index": "artifact_index.csv",
        "artifact_hashes_sha256": file_hashes,
        "qc_flag_is_automatic_exclusion": False,
        "device_validity_claim_created": False,
        "event_model_validity_claim_created": False,
        "measurement_validity_claim_created": False,
        "psychological_state_claim_created": False,
        "scientific_boundary": (
            "Synthetic/demo archive showing auditable software composition only. "
            "It does not establish empirical, tracker/device, native-60-Hz, Gazepoint/GP3, "
            "event-model, AOI construct, calibration, or measurement validity."
        ),
    }
    _write_json(output_dir / "workflow_manifest.json", manifest)

    print("Worked research evidence bundle complete")
    print(f"Output directory: {output_dir}")
    print(f"Source unchanged: {'yes' if source_unchanged else 'no'}")
    print(f"Pre-review QC unchanged: {'yes' if pre_review_qc_unchanged else 'no'}")
    print(f"Reviewed trials: {len(trial_ledger)}; excluded: {len(excluded)}")
    print(f"Primary-analysis rows: {len(primary)}/{len(qc)}")
    print("Evidence boundary: synthetic/demo archive only; no empirical validity claim created.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the deterministic worked GazeForge research evidence bundle."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-research-evidence-bundle"),
        help="Directory for the archive-facing evidence bundle.",
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
