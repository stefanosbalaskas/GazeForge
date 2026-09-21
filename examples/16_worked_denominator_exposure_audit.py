"""Deterministic denominator/exposure/missingness/censoring teaching audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

EVIDENCE = "synthetic_demo_not_empirical_evidence"
OBS_STATUSES = {
    "observed_positive",
    "observed_zero",
    "partial_observed",
    "missing_trial",
    "absent_by_design",
    "undefined_denominator",
}
LAT_STATUSES = {
    "event_observed",
    "right_censored_no_fixation",
    "missing_trial",
    "absent_by_design",
    "undefined_denominator",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _source() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("P01", "T01", "A", "claim", 3000, 3000, 3000, 2, 900, 420),
            ("P01", "T02", "B", "claim", 3000, 3000, 3000, 0, 0, None),
            ("P02", "T01", "A", "claim", 3000, 2250, 2250, 1, 500, 1100),
            ("P02", "T02", "B", "claim", 3000, None, None, None, None, None),
            ("P03", "T01", "A", "disclosure", 3000, 3000, 0, None, None, None),
            ("P03", "T02", "B", "disclosure", 3000, 1800, 1800, 0, 0, None),
            ("P04", "T01", "A", "claim", 3000, 0, 0, None, None, None),
            ("P04", "T02", "B", "claim", 3000, 3000, 3000, 3, 1200, 250),
        ],
        columns=(
            "participant_id",
            "trial_id",
            "condition",
            "aoi_label",
            "expected_trial_ms",
            "observed_gaze_ms",
            "aoi_observable_ms",
            "fixation_count",
            "dwell_ms",
            "first_fixation_ms",
        ),
    )


def _status(row: pd.Series) -> str:
    if pd.isna(row.observed_gaze_ms):
        return "missing_trial"
    if row.observed_gaze_ms == 0:
        return "undefined_denominator"
    if row.aoi_observable_ms == 0:
        return "absent_by_design"
    if pd.isna(row.fixation_count):
        return "undefined_denominator"
    partial = row.observed_gaze_ms < row.expected_trial_ms
    if row.fixation_count == 0:
        return "partial_observed" if partial else "observed_zero"
    return "partial_observed" if partial else "observed_positive"


def _registry(source: pd.DataFrame) -> pd.DataFrame:
    out = source.copy()
    out["observation_status"] = out.apply(_status, axis=1)
    out["coverage_fraction"] = out.observed_gaze_ms / out.expected_trial_ms
    out["eligible_for_rate_or_proportion"] = (
        out.aoi_observable_ms.fillna(0).gt(0) & out.fixation_count.notna()
    )
    out["observed_zero_is_valid"] = out.fixation_count.fillna(-1).eq(
        0
    ) & out.aoi_observable_ms.fillna(0).gt(0)
    return out


def _exposure(registry: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "participant_id",
        "trial_id",
        "condition",
        "aoi_label",
        "expected_trial_ms",
        "observed_gaze_ms",
        "aoi_observable_ms",
        "coverage_fraction",
        "observation_status",
    ]
    out = registry[cols].copy()
    out["trial_in_expected_denominator"] = True
    out["trial_in_observed_denominator"] = out.observed_gaze_ms.notna()
    out["aoi_in_observable_denominator"] = out.aoi_observable_ms.fillna(0).gt(0)
    out["coverage_75pct_or_more"] = out.coverage_fraction.fillna(-1).ge(0.75)
    return out


def _rates(registry: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "participant_id",
        "trial_id",
        "aoi_label",
        "fixation_count",
        "aoi_observable_ms",
        "observation_status",
    ]
    out = registry[cols].copy()
    valid = out.fixation_count.notna() & out.aoi_observable_ms.fillna(0).gt(0)
    out["fixation_rate_per_s"] = float("nan")
    out.loc[valid, "fixation_rate_per_s"] = (
        out.loc[valid, "fixation_count"] / out.loc[valid, "aoi_observable_ms"] * 1000
    )
    out["rate_defined"] = valid
    return out


def _proportions(registry: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "participant_id",
        "trial_id",
        "aoi_label",
        "dwell_ms",
        "aoi_observable_ms",
        "observation_status",
    ]
    out = registry[cols].copy()
    valid = out.dwell_ms.notna() & out.aoi_observable_ms.fillna(0).gt(0)
    out["dwell_proportion"] = float("nan")
    out.loc[valid, "dwell_proportion"] = (
        out.loc[valid, "dwell_ms"] / out.loc[valid, "aoi_observable_ms"]
    )
    out["proportion_defined"] = valid
    out["numerator_le_denominator"] = pd.Series(pd.NA, index=out.index, dtype="boolean")
    out.loc[valid, "numerator_le_denominator"] = (
        out.loc[valid, "dwell_ms"] <= out.loc[valid, "aoi_observable_ms"]
    )
    return out


def _latency(registry: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in registry.itertuples(index=False):
        blocked = row.observation_status in {
            "missing_trial",
            "absent_by_design",
            "undefined_denominator",
        }
        observed = not blocked and pd.notna(row.first_fixation_ms)
        censored = not blocked and not observed
        status = (
            row.observation_status
            if blocked
            else ("event_observed" if observed else "right_censored_no_fixation")
        )
        time_ms = (
            float(row.first_fixation_ms)
            if observed
            else float(row.aoi_observable_ms)
            if censored
            else None
        )
        rows.append(
            {
                "participant_id": row.participant_id,
                "trial_id": row.trial_id,
                "aoi_label": row.aoi_label,
                "latency_status": status,
                "event_observed": observed,
                "right_censored": censored,
                "analysis_time_ms": time_ms,
                "censor_time_ms": time_ms if censored else None,
            }
        )
    return pd.DataFrame(rows)


def _flow(registry: pd.DataFrame, latency: pd.DataFrame) -> pd.DataFrame:
    counts = [
        ("expected participant-trial-AOI rows", len(registry)),
        ("rows with observed gaze", registry.observed_gaze_ms.notna().sum()),
        ("rows with observable AOI exposure", registry.aoi_observable_ms.fillna(0).gt(0).sum()),
        ("rate/proportion eligible rows", registry.eligible_for_rate_or_proportion.sum()),
        ("observed-zero rows", registry.observed_zero_is_valid.sum()),
        ("right-censored latency rows", latency.right_censored.sum()),
        ("missing-trial rows", registry.observation_status.eq("missing_trial").sum()),
        ("absent-by-design rows", registry.observation_status.eq("absent_by_design").sum()),
        (
            "undefined-denominator rows",
            registry.observation_status.eq("undefined_denominator").sum(),
        ),
    ]
    return pd.DataFrame(counts, columns=["stage_or_status", "row_count"])


def _reporting() -> pd.DataFrame:
    return pd.DataFrame(
        [
            (
                "methods",
                "Missing and no-fixation observations were coded as zero.",
                (
                    "Observed zero, missing, absent-by-design, undefined, and "
                    "censored states were retained separately."
                ),
            ),
            (
                "rate",
                "Fixation counts were compared across trials.",
                (
                    "Counts were retained with exposure; rates were computed only "
                    "for positive defined exposure."
                ),
            ),
            (
                "proportion",
                "Dwell percentage was set to zero when the AOI was unavailable.",
                "Dwell proportion remained undefined when AOI exposure was absent or undefined.",
            ),
            (
                "latency",
                "No fixation was assigned latency zero or the trial maximum.",
                "No-fixation latency was right-censored only when the AOI was observable.",
            ),
        ],
        columns=["section", "avoid", "prefer"],
    )


def _api() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("schema/import", "api-reference.md#schema-validation"),
            ("quality control", "api-reference.md#quality-control"),
            ("eye events", "api-reference.md#eye-events"),
            ("semantic AOIs", "api-reference.md#semantic-aois"),
            ("scanpaths", "api-reference.md#scanpaths"),
        ],
        columns=["layer", "api_route"],
    )


def _readme() -> str:
    return """# Worked denominator & exposure audit

This bundle is `synthetic_demo_not_empirical_evidence`.
It is **not empirical validation evidence** and performs no inferential modelling.

Observed positive, observed zero, partial observation, missing trial,
absent-by-design, undefined denominator, and right-censored latency remain distinct.
Missing or absent-by-design observations are never converted to zero. Rates and
proportions remain undefined when their denominator is unavailable or zero.
No-fixation latency is right-censored only when the target was observable.

Retain numerator, denominator/exposure, observation status, and censoring status
beside derived metrics. Do not use `fillna(0)` or silent complete-case filtering.
"""


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    source = _source()
    registry = _registry(source)
    latency = _latency(registry)
    tables = {
        "01_observation_status_registry.csv": registry,
        "02_denominator_exposure_ledger.csv": _exposure(registry),
        "03_count_rate_audit.csv": _rates(registry),
        "04_proportion_dwell_audit.csv": _proportions(registry),
        "05_latency_censoring_audit.csv": latency,
        "06_reconciliation_flow.csv": _flow(registry, latency),
        "07_reporting_language.csv": _reporting(),
        "08_api_route_map.csv": _api(),
    }
    for name, table in tables.items():
        table.to_csv(output_dir / name, index=False)
    (output_dir / "README.md").write_text(_readme(), encoding="utf-8")

    if set(registry.observation_status) != OBS_STATUSES:
        raise RuntimeError("Observation-status teaching coverage changed.")
    if not set(latency.latency_status) <= LAT_STATUSES:
        raise RuntimeError("Unexpected latency status.")
    if len(registry) != len(source):
        raise RuntimeError("The audit silently changed the row denominator.")

    blocked = registry.observation_status.isin(
        ["missing_trial", "absent_by_design", "undefined_denominator"]
    )
    if registry.loc[blocked, "fixation_count"].fillna(-1).eq(0).any():
        raise RuntimeError("Missing/absent/undefined rows were converted to zero.")
    latency_blocked = latency.latency_status.isin(
        ["missing_trial", "absent_by_design", "undefined_denominator"]
    )
    if latency.loc[latency_blocked, "right_censored"].any():
        raise RuntimeError("Blocked observations were misclassified as censored.")

    manifest = {
        "example": "16_worked_denominator_exposure_audit",
        "evidence_classification": EVIDENCE,
        "input_row_count": len(source),
        "output_registry_row_count": len(registry),
        "observation_statuses": sorted(OBS_STATUSES),
        "latency_statuses": sorted(LAT_STATUSES),
        "artifact_hashes_sha256": {
            p.name: _sha256(p)
            for p in sorted(output_dir.iterdir())
            if p.is_file() and p.name != "denominator_exposure_manifest.json"
        },
        "inferential_model_selected": False,
        "missing_converted_to_zero": False,
        "absent_by_design_converted_to_zero": False,
        "undefined_denominator_converted_to_zero": False,
        "silent_complete_case_filtering": False,
        "causal_claim_created": False,
        "construct_validity_claim_created": False,
        "device_or_native_rate_validity_claim_created": False,
        "empirical_validation_claim_created": False,
    }
    _write_json(output_dir / "denominator_exposure_manifest.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a denominator/exposure audit bundle.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-denominator-exposure-audit"),
    )
    run(parser.parse_args().output_dir)


if __name__ == "__main__":
    main()
