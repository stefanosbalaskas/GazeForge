"""Deterministic statistical-handoff example for reviewed GazeForge outputs.

Synthetic/demo only: this script demonstrates row construction, exposure,
missing/zero semantics, censoring, provenance, and descriptive diagnostics.
It does not fit or select an inferential model or establish empirical validity.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from gazeforge import AOI, __version__, aois_to_frame, fingerprint_frame, map_fixations_to_aois

EVIDENCE = "synthetic_demo_not_empirical_evidence"
TRIAL_MS = 3000.0
AOI_NAMES = ("brand", "claim", "disclosure", "product")


def _aois() -> list[AOI]:
    return [
        AOI("brand", "brand", 80, 80, 520, 280, source="researcher_defined"),
        AOI("claim", "claim", 80, 340, 940, 650, source="researcher_defined"),
        AOI("disclosure", "disclosure", 80, 760, 940, 920, source="researcher_defined"),
        AOI("product", "product", 1080, 150, 1840, 930, source="researcher_defined"),
    ]


def _design() -> pd.DataFrame:
    rows = []
    for pi, pid in enumerate(("P001", "P002", "P003", "P004", "P005"), start=1):
        for ti, trial in enumerate(("T01", "T02", "T03", "T04"), start=1):
            condition = "disclosure" if ti % 2 == 0 else "standard"
            observed, status = TRIAL_MS, "complete"
            if (pid, trial) == ("P004", "T03"):
                observed, status = 2200.0, "partial_observation"
            if (pid, trial) == ("P005", "T04"):
                observed, status = 0.0, "missing_trial"
            rows.append(
                {
                    "participant_id": pid,
                    "trial_id": trial,
                    "participant_index": pi,
                    "condition": condition,
                    "trial_duration_ms": TRIAL_MS,
                    "observed_gaze_ms": observed,
                    "coverage_fraction": observed / TRIAL_MS,
                    "coverage_status": status,
                    "trial_retained_after_review": True,
                    "source_sampling_status": "synthetic_demo_60hz_like_not_device_evidence",
                }
            )
    return pd.DataFrame(rows)


def _fixations(design: pd.DataFrame) -> pd.DataFrame:
    centers = {
        "brand": (300.0, 180.0),
        "claim": (500.0, 495.0),
        "disclosure": (500.0, 840.0),
        "product": (1460.0, 540.0),
    }
    durations = {
        "brand": (180.0, 140.0),
        "claim": (300.0, 220.0),
        "disclosure": (280.0,),
        "product": (240.0, 180.0),
    }
    rows, event_index = [], 0
    for trial in design.itertuples(index=False):
        if trial.coverage_status == "missing_trial":
            continue
        sequence = ["brand", "claim", "product"]
        if trial.condition == "disclosure":
            sequence.insert(2, "disclosure")
        time_ms = 220.0
        for label in sequence:
            if (trial.participant_id, trial.trial_id, label) == (
                "P002",
                "T02",
                "disclosure",
            ):
                time_ms += 260.0
                continue
            for j, duration in enumerate(durations[label], start=1):
                if time_ms >= trial.observed_gaze_ms:
                    continue
                duration = min(duration, trial.observed_gaze_ms - time_ms)
                if duration <= 0:
                    continue
                event_index += 1
                x, y = centers[label]
                jitter = float((trial.participant_index - 3) * 2 + j)
                rows.append(
                    {
                        "participant_id": trial.participant_id,
                        "trial_id": trial.trial_id,
                        "condition": trial.condition,
                        "event_index": event_index,
                        "start_ms": time_ms,
                        "end_ms": time_ms + duration,
                        "duration_ms": duration,
                        "x_px": x + jitter,
                        "y_px": y - jitter,
                        "review_status": "reviewed",
                    }
                )
                time_ms += duration + 90.0
            time_ms += 120.0
    return pd.DataFrame(rows)


def _events(assignments: pd.DataFrame, design: pd.DataFrame) -> pd.DataFrame:
    rows, event_index = [], 0
    for trial in design.itertuples(index=False):
        if trial.coverage_status == "missing_trial":
            continue
        group = assignments[
            (assignments["participant_id"] == trial.participant_id)
            & (assignments["trial_id"] == trial.trial_id)
        ].sort_values("start_ms")
        previous_end: float | None = None
        for fixation in group.itertuples(index=False):
            if previous_end is not None and fixation.start_ms > previous_end:
                gap = min(80.0, float(fixation.start_ms - previous_end))
                event_index += 1
                rows.append(
                    {
                        "participant_id": trial.participant_id,
                        "trial_id": trial.trial_id,
                        "condition": trial.condition,
                        "event_index": event_index,
                        "event_label": "saccade",
                        "start_ms": float(fixation.start_ms - gap),
                        "end_ms": float(fixation.start_ms),
                        "duration_ms": gap,
                        "review_status": "reviewed",
                    }
                )
            event_index += 1
            rows.append(
                {
                    "participant_id": trial.participant_id,
                    "trial_id": trial.trial_id,
                    "condition": trial.condition,
                    "event_index": event_index,
                    "event_label": "fixation",
                    "start_ms": float(fixation.start_ms),
                    "end_ms": float(fixation.end_ms),
                    "duration_ms": float(fixation.duration_ms),
                    "review_status": "reviewed",
                }
            )
            previous_end = float(fixation.end_ms)
    return pd.DataFrame(rows)


def _aoi_metrics(
    assignments: pd.DataFrame,
    design: pd.DataFrame,
    aoi_definitions: pd.DataFrame,
) -> pd.DataFrame:
    out = design.merge(
        aoi_definitions[["aoi_id", "label"]].rename(columns={"label": "aoi_label"}),
        how="cross",
    )
    out["aoi_present"] = ~(out["condition"].eq("standard") & out["aoi_id"].eq("disclosure"))
    out["aoi_observable_ms"] = np.where(out["aoi_present"], out["observed_gaze_ms"], 0.0)
    observed = (
        assignments.dropna(subset=["aoi_id"])
        .groupby(["participant_id", "trial_id", "aoi_id"], as_index=False)
        .agg(
            n_fixations=("event_index", "size"),
            dwell_ms=("duration_ms", "sum"),
            first_fixation_latency_ms=("start_ms", "min"),
        )
    )
    out = out.merge(
        observed,
        on=["participant_id", "trial_id", "aoi_id"],
        how="left",
        validate="one_to_one",
    )
    missing = out["coverage_status"].eq("missing_trial")
    absent = ~out["aoi_present"]
    observable = out["aoi_present"] & ~missing
    true_zero = observable & out["n_fixations"].isna()
    out.loc[true_zero, ["n_fixations", "dwell_ms"]] = 0.0
    out.loc[absent | missing, ["n_fixations", "dwell_ms"]] = np.nan
    out["dwell_proportion_observed"] = np.where(
        observable & out["aoi_observable_ms"].gt(0),
        out["dwell_ms"] / out["aoi_observable_ms"],
        np.nan,
    )
    out["metric_status"] = "observed"
    out.loc[true_zero, "metric_status"] = "observed_zero"
    out.loc[absent, "metric_status"] = "not_present_by_design"
    out.loc[missing, "metric_status"] = "missing_trial"
    no_fixation = observable & out["first_fixation_latency_ms"].isna()
    out["latency_status"] = "observed"
    out.loc[no_fixation, "latency_status"] = "right_censored_no_fixation"
    out.loc[absent, "latency_status"] = "not_present_by_design"
    out.loc[missing, "latency_status"] = "missing_trial"
    out["latency_censor_time_ms"] = np.where(no_fixation, out["aoi_observable_ms"], np.nan)
    out["analysis_role"] = "model_ready_trial_aoi_measure"
    out["zero_policy"] = "zero only when AOI present + trial observed; missing/absent stay NA"
    return out.drop(columns=["participant_index", "trial_retained_after_review"])


def _event_metrics(events: pd.DataFrame, design: pd.DataFrame) -> pd.DataFrame:
    out = design.merge(pd.DataFrame({"event_label": ["fixation", "saccade"]}), how="cross")
    observed = events.groupby(["participant_id", "trial_id", "event_label"], as_index=False).agg(
        n_events=("event_index", "size"),
        total_event_ms=("duration_ms", "sum"),
        mean_event_ms=("duration_ms", "mean"),
    )
    out = out.merge(
        observed,
        on=["participant_id", "trial_id", "event_label"],
        how="left",
        validate="one_to_one",
    )
    missing = out["coverage_status"].eq("missing_trial")
    true_zero = ~missing & out["n_events"].isna()
    out.loc[true_zero, ["n_events", "total_event_ms"]] = 0.0
    out.loc[missing, ["n_events", "total_event_ms", "mean_event_ms"]] = np.nan
    out["events_per_observed_second"] = np.where(
        ~missing & out["observed_gaze_ms"].gt(0),
        out["n_events"] / (out["observed_gaze_ms"] / 1000.0),
        np.nan,
    )
    out["metric_status"] = np.where(
        missing, "missing_trial", np.where(true_zero, "observed_zero", "observed")
    )
    out["analysis_role"] = "model_ready_trial_event_measure"
    return out.drop(columns=["participant_index", "trial_retained_after_review"])


def _descriptive(aoi_metrics: pd.DataFrame) -> pd.DataFrame:
    observed = aoi_metrics[aoi_metrics["metric_status"].isin(["observed", "observed_zero"])]
    out = observed.groupby(
        ["participant_id", "condition", "aoi_id", "aoi_label"], as_index=False
    ).agg(
        n_contributing_trials=("trial_id", "nunique"),
        mean_dwell_ms=("dwell_ms", "mean"),
        mean_dwell_proportion_observed=("dwell_proportion_observed", "mean"),
    )
    out["analysis_role"] = "descriptive_only_not_inferential_input"
    return out


def _dictionary() -> pd.DataFrame:
    rows = [
        ("participant_id", "identity", "participant", "repeated-measures grouping"),
        ("trial_id", "identity", "trial", "repeated observation"),
        ("condition", "design", "trial", "study condition"),
        ("aoi_id", "measurement", "AOI", "reviewed AOI identity"),
        ("observed_gaze_ms", "denominator", "trial", "observed tracking exposure"),
        ("aoi_observable_ms", "denominator", "trial x AOI", "observable AOI exposure"),
        ("n_fixations", "outcome", "trial x AOI", "NA differs from true zero"),
        ("dwell_ms", "outcome", "trial x AOI", "NA differs from zero"),
        ("dwell_proportion_observed", "outcome", "trial x AOI", "dwell / exposure"),
        ("first_fixation_latency_ms", "outcome", "trial x AOI", "see censor status"),
        ("latency_status", "censoring", "trial x AOI", "observed/censored/missing"),
        ("metric_status", "missingness", "row", "zero versus missing/undefined"),
        ("analysis_role", "governance", "row", "model-ready versus descriptive-only"),
    ]
    return pd.DataFrame(rows, columns=["column", "role", "unit", "interpretation"])


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _figures(output_dir: Path, aoi_metrics: pd.DataFrame, design: pd.DataFrame) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "Figures require matplotlib; install the plot/dev extra or use --no-figures."
        ) from exc
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    observed = aoi_metrics[aoi_metrics["metric_status"].isin(["observed", "observed_zero"])]
    dwell = (
        observed.groupby(["aoi_label", "condition"])["dwell_ms"]
        .mean()
        .unstack("condition")
        .reindex(AOI_NAMES)
    )
    ax = dwell.plot(kind="bar")
    ax.set(xlabel="AOI", ylabel="Mean dwell (ms)", title="Synthetic descriptive dwell")
    ax.figure.tight_layout()
    first = figure_dir / "01_aoi_dwell_by_condition.png"
    ax.figure.savefig(first, dpi=140)
    plt.close(ax.figure)
    coverage = design.groupby(["condition", "coverage_status"]).size().unstack(fill_value=0)
    ax = coverage.plot(kind="bar")
    ax.set(xlabel="Condition", ylabel="Trial count", title="Synthetic trial coverage")
    ax.figure.tight_layout()
    second = figure_dir / "02_trial_coverage_status.png"
    ax.figure.savefig(second, dpi=140)
    plt.close(ax.figure)
    return [str(first.relative_to(output_dir)), str(second.relative_to(output_dir))]


def run(output_dir: Path, *, figures: bool = True) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    design = _design()
    fixations = _fixations(design)
    aois = _aois()
    aoi_definitions = aois_to_frame(aois)
    assignments = map_fixations_to_aois(fixations, aois, overlap_rule="first")
    events = _events(assignments, design)
    aoi_metrics = _aoi_metrics(assignments, design, aoi_definitions)
    event_metrics = _event_metrics(events, design)
    descriptive = _descriptive(aoi_metrics)
    dictionary = _dictionary()

    tables = {
        "01_reviewed_fixation_assignments.csv": assignments,
        "02_reviewed_event_intervals.csv": events,
        "03_trial_design_and_coverage.csv": design,
        "04_trial_aoi_metrics.csv": aoi_metrics,
        "05_trial_event_metrics.csv": event_metrics,
        "06_descriptive_participant_condition_summary.csv": descriptive,
        "07_model_handoff_dictionary.csv": dictionary,
        "08_aoi_definitions.csv": aoi_definitions,
    }
    for name, table in tables.items():
        table.to_csv(output_dir / name, index=False)

    _write_json(
        output_dir / "upstream_reference.json",
        {
            "source_identity": "worked_analysis_handoff_v1",
            "source_kind": "reviewed deterministic synthetic/demo records",
            "fixation_fingerprint": fingerprint_frame(fixations),
            "design_fingerprint": fingerprint_frame(design),
            "evidence_classification": EVIDENCE,
        },
    )
    _write_json(
        output_dir / "analysis_handoff_plan.json",
        {
            "inferential_unit_preserved": "participant x trial",
            "repeated_measures_group": "participant_id",
            "primary_model_inputs": [
                "04_trial_aoi_metrics.csv",
                "05_trial_event_metrics.csv",
            ],
            "descriptive_only": "06_descriptive_participant_condition_summary.csv",
            "missing_to_zero_policy": "only explicit observed structural zeros become 0",
            "latency_policy": "no-fixation observed trials are right-censored",
            "estimator_selected": False,
            "statistical_model_fitted": False,
            "evidence_classification": EVIDENCE,
        },
    )
    provenance = [
        {
            "operation": "reviewed_fixations_to_trial_aoi_metrics",
            "input_fingerprint": fingerprint_frame(assignments),
            "output_fingerprint": fingerprint_frame(aoi_metrics),
            "grouping_keys": ["participant_id", "trial_id", "aoi_id"],
            "exposure": "aoi_observable_ms",
            "missing_to_zero": False,
        },
        {
            "operation": "reviewed_events_to_trial_event_metrics",
            "input_fingerprint": fingerprint_frame(events),
            "output_fingerprint": fingerprint_frame(event_metrics),
            "grouping_keys": ["participant_id", "trial_id", "event_label"],
            "exposure": "observed_gaze_ms",
            "missing_to_zero": False,
        },
    ]
    _write_json(output_dir / "provenance.json", provenance)
    figure_files = _figures(output_dir, aoi_metrics, design) if figures else []
    _write_json(
        output_dir / "workflow_manifest.json",
        {
            "gazeforge_version": __version__,
            "evidence_classification": EVIDENCE,
            "n_participants": int(design["participant_id"].nunique()),
            "n_trials_expected": int(len(design)),
            "n_trial_aoi_rows": int(len(aoi_metrics)),
            "n_trial_event_rows": int(len(event_metrics)),
            "missing_values_converted_to_zero": False,
            "unobserved_aoi_exposure_created": False,
            "descriptive_summary_is_model_input": False,
            "statistical_model_fitted": False,
            "automatic_model_selection_performed": False,
            "failed_model_convergence_accepted": False,
            "device_validity_claim_created": False,
            "psychological_state_claim_created": False,
            "causal_claim_created": False,
            "figure_files": figure_files,
        },
    )
    (output_dir / "README.md").write_text(
        "# Worked analysis handoff\n\n"
        "Synthetic/demo only. True observed zeros are `0`; absent-by-design and "
        "missing trials remain `NA`. No statistical estimator is selected or fitted. "
        "Use `07_model_handoff_dictionary.csv` to interpret units and missingness.\n",
        encoding="utf-8",
    )
    print("Worked analysis handoff complete")
    print(f"Output directory: {output_dir}")
    print(f"Trial x AOI rows: {len(aoi_metrics)}")
    print("Missing != zero: preserved")
    print("Statistical model fitted: no")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic model-ready trial tables without model fitting."
    )
    parser.add_argument("--output-dir", type=Path, default=Path("worked-analysis-handoff-demo"))
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()
    run(args.output_dir, figures=not args.no_figures)


if __name__ == "__main__":
    main()
