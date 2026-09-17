"""Worked participant-held-out event-model validation study.

This deterministic synthetic/demo workflow compares a transparent I-VT baseline,
a Random Forest classifier, and a temporal ContextMLP on identical participant-held-out
folds. It writes reviewable predictions, sample/event metrics, calibration diagnostics,
confidence/coverage tables, split identity, provenance, and a manifest.

The output is a software demonstration, not empirical validation evidence.
"""

from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from gazeforge import (
    AuditTrail,
    compare_event_models_grouped,
    evaluate_event_calibration,
    fingerprint_frame,
    selective_accuracy_curve,
)

SAMPLING_RATE_HZ = 60.0
N_SPLITS = 4
RANDOM_STATE = 20260917
EVIDENCE_CLASSIFICATION = "synthetic_demo_not_empirical_evidence"
ABSTENTION_THRESHOLD = 0.80


def _synthetic_labelled_events() -> pd.DataFrame:
    """Construct deterministic participant-labelled fixation/saccade samples."""
    rng = np.random.default_rng(RANDOM_STATE)
    dt_ms = 1000.0 / SAMPLING_RATE_HZ
    base_targets = np.array(
        [
            [360.0, 300.0],
            [820.0, 320.0],
            [1420.0, 360.0],
            [1260.0, 760.0],
            [560.0, 720.0],
        ]
    )
    rows: list[dict[str, object]] = []

    for participant_index in range(8):
        participant_id = f"P{participant_index + 1:03d}"
        participant_shift = np.array(
            [12.0 * (participant_index % 3), 9.0 * (participant_index % 2)]
        )
        for trial_index in range(2):
            trial_id = f"T{trial_index + 1:02d}"
            trial_shift = np.array([18.0 * trial_index, -12.0 * trial_index])
            targets = base_targets + participant_shift + trial_shift
            sample = 0
            current = targets[0].copy()

            for transition_index in range(4):
                for _ in range(18):
                    jitter = rng.normal(0.0, 2.0, size=2)
                    point = current + jitter
                    rows.append(
                        {
                            "participant_id": participant_id,
                            "trial_id": trial_id,
                            "timestamp_ms": sample * dt_ms,
                            "x_px": float(point[0]),
                            "y_px": float(point[1]),
                            "pupil": float(3.2 + rng.normal(0.0, 0.05)),
                            "event_label": "fixation",
                        }
                    )
                    sample += 1

                next_target = targets[transition_index + 1]
                start = current.copy()
                for step in range(1, 6):
                    fraction = step / 5.0
                    point = start + fraction * (next_target - start)
                    point = point + rng.normal(0.0, 1.0, size=2)
                    rows.append(
                        {
                            "participant_id": participant_id,
                            "trial_id": trial_id,
                            "timestamp_ms": sample * dt_ms,
                            "x_px": float(point[0]),
                            "y_px": float(point[1]),
                            "pupil": float(3.2 + rng.normal(0.0, 0.05)),
                            "event_label": "saccade",
                        }
                    )
                    sample += 1
                current = next_target.copy()

            for _ in range(18):
                jitter = rng.normal(0.0, 2.0, size=2)
                point = current + jitter
                rows.append(
                    {
                        "participant_id": participant_id,
                        "trial_id": trial_id,
                        "timestamp_ms": sample * dt_ms,
                        "x_px": float(point[0]),
                        "y_px": float(point[1]),
                        "pupil": float(3.2 + rng.normal(0.0, 0.05)),
                        "event_label": "fixation",
                    }
                )
                sample += 1

    return pd.DataFrame(rows)


def _split_ledger(data: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct and verify the exact GroupKFold participant identity contract."""
    splitter = GroupKFold(n_splits=N_SPLITS)
    groups = data["participant_id"].astype(str)
    rows: list[dict[str, object]] = []

    for fold, (train_idx, test_idx) in enumerate(
        splitter.split(data, y=data["event_label"], groups=groups),
        start=1,
    ):
        train_ids = sorted(
            data.iloc[train_idx]["participant_id"].astype(str).unique()
        )
        test_ids = sorted(
            data.iloc[test_idx]["participant_id"].astype(str).unique()
        )
        overlap = sorted(set(train_ids) & set(test_ids))
        if overlap:
            raise RuntimeError(
                f"Participant leakage detected in fold {fold}: {overlap}"
            )
        for participant_id in train_ids:
            rows.append(
                {
                    "fold": fold,
                    "participant_id": participant_id,
                    "split_role": "train",
                }
            )
        for participant_id in test_ids:
            rows.append(
                {
                    "fold": fold,
                    "participant_id": participant_id,
                    "split_role": "test",
                }
            )
    return pd.DataFrame(rows)


def _validate_prediction_split_identity(
    predictions: pd.DataFrame,
    split_ledger: pd.DataFrame,
) -> None:
    for fold in sorted(predictions["validation_fold"].unique()):
        expected = set(
            split_ledger.loc[
                (split_ledger["fold"] == fold)
                & (split_ledger["split_role"] == "test"),
                "participant_id",
            ].astype(str)
        )
        observed = set(
            predictions.loc[
                predictions["validation_fold"] == fold,
                "participant_id",
            ].astype(str)
        )
        if observed != expected:
            raise RuntimeError(
                f"Prediction/test participant mismatch in fold {fold}: "
                f"expected={sorted(expected)}, observed={sorted(observed)}"
            )


def _calibration_outputs(
    predictions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    calibration_rows: list[dict[str, object]] = []
    selective_parts: list[pd.DataFrame] = []
    policy_rows: list[dict[str, object]] = []
    thresholds = (0.0, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95)

    for model_name in ("RandomForest", "ContextMLP"):
        model_predictions = predictions.loc[
            predictions["comparison_model"] == model_name
        ].copy()
        diagnostics = evaluate_event_calibration(
            model_predictions,
            true_label_col="event_label",
            n_bins=8,
        )
        for row in diagnostics["calibration_table"]:
            calibration_rows.append(
                {
                    "model": model_name,
                    **row,
                    "multiclass_brier_score": diagnostics["multiclass_brier_score"],
                    "expected_calibration_error": diagnostics[
                        "expected_calibration_error"
                    ],
                }
            )

        selective = selective_accuracy_curve(
            model_predictions,
            true_label_col="event_label",
            thresholds=thresholds,
        )
        selective.insert(0, "model", model_name)
        selective_parts.append(selective)

        selected = selective.loc[
            selective["confidence_threshold"] == ABSTENTION_THRESHOLD
        ].iloc[0]
        policy_rows.append(
            {
                "model": model_name,
                "illustrative_confidence_threshold": ABSTENTION_THRESHOLD,
                "n_retained": int(selected["n_retained"]),
                "coverage": float(selected["coverage"]),
                "selective_accuracy": float(selected["accuracy"]),
                "policy_status": "illustrative_not_universal",
            }
        )

    return (
        pd.DataFrame(calibration_rows),
        pd.concat(selective_parts, ignore_index=True),
        pd.DataFrame(policy_rows),
    )


def _write_figures(
    output_dir: Path,
    calibration: pd.DataFrame,
    selective: pd.DataFrame,
) -> list[str]:
    import matplotlib.pyplot as plt

    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []

    fig, ax = plt.subplots(figsize=(7, 5))
    for model_name, part in calibration.groupby("model", sort=False):
        nonempty = part.loc[part["n"] > 0]
        ax.plot(
            nonempty["mean_confidence"],
            nonempty["accuracy"],
            marker="o",
            label=model_name,
        )
    ax.plot([0, 1], [0, 1], linestyle="--", label="perfect calibration")
    ax.set(
        xlabel="Mean predicted confidence",
        ylabel="Empirical accuracy",
        title="Synthetic held-out calibration diagnostic",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    ax.legend()
    fig.tight_layout()
    name = "figures/01_calibration.png"
    fig.savefig(output_dir / name, dpi=160, bbox_inches="tight")
    plt.close(fig)
    outputs.append(name)

    fig, ax = plt.subplots(figsize=(7, 5))
    for model_name, part in selective.groupby("model", sort=False):
        ax.plot(part["coverage"], part["accuracy"], marker="o", label=model_name)
    ax.set(
        xlabel="Coverage retained",
        ylabel="Accuracy on retained samples",
        title="Synthetic confidence/coverage diagnostic",
        xlim=(0, 1.02),
        ylim=(0, 1.02),
    )
    ax.legend()
    fig.tight_layout()
    name = "figures/02_confidence_coverage.png"
    fig.savefig(output_dir / name, dpi=160, bbox_inches="tight")
    plt.close(fig)
    outputs.append(name)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-event-model-validation-demo"),
        help="Directory for the reviewable participant-held-out demo bundle.",
    )
    parser.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip optional Matplotlib figures and write tables/JSON only.",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    source = _synthetic_labelled_events()
    source_snapshot = source.copy(deep=True)
    source_fingerprint = fingerprint_frame(source_snapshot)
    split_ledger = _split_ledger(source_snapshot)

    comparison = compare_event_models_grouped(
        source_snapshot,
        label_col="event_label",
        group_col="participant_id",
        n_splits=N_SPLITS,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        ivt_velocity_threshold_px_s=1000.0,
        min_confidence=0.0,
        random_state=RANDOM_STATE,
        n_estimators=48,
        context_radius_ms=50.0,
        rolling_window_ms=80.0,
        hidden_layer_sizes=(16,),
        temporal_solver="lbfgs",
        temporal_max_iter=100,
        calibration_bins=8,
        include_event_level_metrics=True,
        event_group_cols=("participant_id", "trial_id"),
        event_min_iou=0.50,
    )
    _validate_prediction_split_identity(comparison.predictions, split_ledger)

    sample_metric_columns = [
        "model",
        "fold",
        "n_train_rows",
        "n_test_rows",
        "n_train_groups",
        "n_test_groups",
        "accuracy",
        "balanced_accuracy",
        "macro_f1",
        "multiclass_brier_score",
        "expected_calibration_error",
    ]
    event_metric_columns = [
        "model",
        "fold",
        "event_precision",
        "event_recall",
        "event_f1",
        "event_mean_matched_iou",
        "event_mean_abs_onset_error_ms",
        "event_mean_abs_offset_error_ms",
        "event_mean_abs_duration_error_ms",
    ]
    sample_metrics = comparison.fold_metrics[sample_metric_columns].copy()
    event_metrics = comparison.fold_metrics[event_metric_columns].copy()
    calibration, selective, abstention_policy = _calibration_outputs(
        comparison.predictions
    )

    pd.testing.assert_frame_equal(source, source_snapshot, check_exact=True)
    source_unchanged = fingerprint_frame(source) == source_fingerprint
    if not source_unchanged:
        raise RuntimeError("Source event table changed during the worked example.")

    trail = AuditTrail()
    trail.add(
        operation="compare_event_models_grouped",
        input_data=source_snapshot,
        output_data=comparison.predictions,
        parameters=comparison.design,
        warnings=[
            (
                "Synthetic/demo validation only; do not generalize model ordering "
                "to a real device, task, or population."
            )
        ],
    )

    tables = {
        "01_source_event_samples.csv": source_snapshot,
        "02_participant_split_ledger.csv": split_ledger,
        "03_matched_heldout_predictions.csv": comparison.predictions,
        "04_sample_level_metrics.csv": sample_metrics,
        "05_event_level_metrics.csv": event_metrics,
        "06_model_summary.csv": comparison.summary,
        "07_calibration_bins.csv": calibration,
        "08_confidence_coverage.csv": selective,
        "09_illustrative_abstention_policy.csv": abstention_policy,
    }
    for filename, table in tables.items():
        table.to_csv(args.output_dir / filename, index=False)

    figure_outputs: list[str] = []
    if not args.no_figures:
        figure_outputs = _write_figures(args.output_dir, calibration, selective)

    analysis_plan = {
        "example": "worked_event_model_validation",
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "prediction_target": "synthetic sample-level fixation versus saccade label",
        "reference_label_source": "deterministic synthetic construction",
        "held_out_unit": "participant_id",
        "split_design": "matched participant-disjoint GroupKFold",
        "n_splits": N_SPLITS,
        "models": ["I-VT", "RandomForest", "ContextMLP"],
        "sampling_rate_hz": SAMPLING_RATE_HZ,
        "analysis_rate_status": "synthetic_native_demo_not_device_evidence",
        "sample_level_estimands": [
            "accuracy",
            "balanced_accuracy",
            "macro_f1",
        ],
        "event_level_estimands": [
            "event_f1",
            "matched temporal IoU",
            "onset/offset/duration error",
        ],
        "probability_estimands": [
            "multiclass Brier score",
            "expected calibration error",
            "confidence/coverage",
        ],
        "illustrative_abstention_threshold": ABSTENTION_THRESHOLD,
        "abstention_boundary": (
            "The 0.80 threshold is a teaching policy for this deterministic demo, "
            "not a universal cutoff."
        ),
        "scientific_boundary": (
            "Synthetic model ordering is not evidence that one method is generally superior. "
            "The demo does not establish empirical benchmark performance, native-device validity, "
            "native 60 Hz validity, Gazepoint/GP3 validity, or generalization to a population/task."
        ),
    }
    (args.output_dir / "analysis_plan.json").write_text(
        json.dumps(analysis_plan, indent=2), encoding="utf-8"
    )
    (args.output_dir / "provenance.json").write_text(
        trail.to_json(indent=2), encoding="utf-8"
    )

    manifest = {
        "workflow": "worked_event_model_validation",
        "gazeforge_version": version("gazeforge"),
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "input_mode": "deterministic_synthetic_participant_labelled_event_demo",
        "source_unchanged": source_unchanged,
        "source_fingerprint_sha256": source_fingerprint,
        "held_out_unit": "participant_id",
        "participant_disjoint_verified": True,
        "matched_test_rows_across_models": True,
        "n_splits": N_SPLITS,
        "models": ["I-VT", "RandomForest", "ContextMLP"],
        "sampling_rate_hz": SAMPLING_RATE_HZ,
        "analysis_rate_status": "synthetic_native_demo_not_device_evidence",
        "illustrative_abstention_threshold": ABSTENTION_THRESHOLD,
        "table_outputs": list(tables),
        "supporting_outputs": ["analysis_plan.json", "provenance.json"],
        "figure_outputs": figure_outputs,
        "scientific_boundary": (
            "The bundle demonstrates leakage-safe software composition only. It is not empirical "
            "validation evidence and does not establish benchmark superiority, tracker validity, "
            "native 60 Hz validity, Gazepoint validity, or GP3 validity."
        ),
    }
    (args.output_dir / "workflow_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print(f"Wrote worked event-model validation demo to {args.output_dir.resolve()}")
    print("Participant-disjoint folds verified: yes")
    print("Matched held-out rows across models: yes")
    print("Sample-level and event-level metrics exported separately: yes")
    print("Calibration and confidence/coverage exported for probabilistic models: yes")
    print(f"Evidence boundary: {EVIDENCE_CLASSIFICATION}")
    print("Source table unchanged: yes")


if __name__ == "__main__":
    main()
