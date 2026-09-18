"""Build a deterministic outcome/estimand preregistration teaching bundle.

This example freezes outcome definitions, estimands, contrasts, and sensitivity plans
before model fitting. It performs no inferential analysis and does not choose a
statistical estimator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

EVIDENCE_CLASSIFICATION = "synthetic_demo_not_empirical_evidence"
ALLOWED_ANALYSIS_STATUS = ("primary", "secondary", "exploratory")
DEVIATION_COLUMNS = (
    "deviation_id",
    "registered_at",
    "affected_registry",
    "affected_id",
    "change",
    "reason",
    "status_after_change",
)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _outcomes() -> pd.DataFrame:
    rows = [
        {
            "outcome_id": "O01",
            "analysis_status": "primary",
            "name": "claim_aoi_dwell_ms",
            "observable_definition": "sum of reviewed fixation duration assigned to the claim AOI",
            "measurement_unit": "milliseconds",
            "row_unit": "participant × trial × AOI",
            "grouping": "participant repeated across trials",
            "time_window": "full declared trial exposure",
            "exposure_denominator_policy": "retain aoi_observable_ms and observed_gaze_ms",
            "missing_zero_censoring_policy": "zero only when the AOI was observable and no dwell occurred; missing remains missing",
            "transformation": "none preregistered",
            "event_source": "declared fixation detector/version frozen before analysis",
            "aoi_source": "researcher-defined reviewed claim AOI",
            "multiplicity_family": "primary_attention_allocation",
            "api_reference": "api-reference.md#semantic-aois",
        },
        {
            "outcome_id": "O02",
            "analysis_status": "secondary",
            "name": "claim_aoi_fixation_count",
            "observable_definition": "count of reviewed fixation events assigned to the claim AOI",
            "measurement_unit": "count",
            "row_unit": "participant × trial × AOI",
            "grouping": "participant repeated across trials",
            "time_window": "full declared trial exposure",
            "exposure_denominator_policy": "retain observable trial/AOI exposure; do not invent zero for unavailable trials",
            "missing_zero_censoring_policy": "observed zero distinct from missing or absent-by-design",
            "transformation": "none preregistered",
            "event_source": "same frozen fixation detector as O01",
            "aoi_source": "same reviewed claim AOI as O01",
            "multiplicity_family": "secondary_attention_frequency",
            "api_reference": "api-reference.md#eye-events; api-reference.md#semantic-aois",
        },
        {
            "outcome_id": "O03",
            "analysis_status": "secondary",
            "name": "disclosure_first_fixation_latency_ms",
            "observable_definition": "time from declared trial origin to first reviewed fixation in the disclosure AOI",
            "measurement_unit": "milliseconds",
            "row_unit": "participant × trial × AOI",
            "grouping": "participant repeated across trials",
            "time_window": "from trial origin through available disclosure exposure",
            "exposure_denominator_policy": "retain event_observed and latency_censor_time_ms",
            "missing_zero_censoring_policy": "no fixation is right-censored at observable exposure; never encode no fixation as latency=0",
            "transformation": "none preregistered",
            "event_source": "same frozen fixation detector as O01",
            "aoi_source": "researcher-defined reviewed disclosure AOI",
            "multiplicity_family": "secondary_attention_timing",
            "api_reference": "api-reference.md#eye-events; api-reference.md#semantic-aois",
        },
        {
            "outcome_id": "O04",
            "analysis_status": "exploratory",
            "name": "claim_to_product_transition_count",
            "observable_definition": "count of declared claim→product semantic AOI transitions within trial",
            "measurement_unit": "count",
            "row_unit": "participant × trial sequence",
            "grouping": "participant repeated across trials",
            "time_window": "full declared trial exposure",
            "exposure_denominator_policy": "retain analysed sequence length and unassigned-state policy",
            "missing_zero_censoring_policy": "zero only when a valid sequence was observed with no target transition; missing sequence remains missing",
            "transformation": "collapse immediate repeated AOI labels before transition counting",
            "event_source": "reviewed fixation sequence",
            "aoi_source": "frozen reviewed AOI set",
            "multiplicity_family": "exploratory_sequence",
            "api_reference": "api-reference.md#scanpaths",
        },
    ]
    return pd.DataFrame(rows)


def _estimands() -> pd.DataFrame:
    rows = [
        {
            "estimand_id": "E01",
            "outcome_id": "O01",
            "analysis_status": "primary",
            "target_population": "participants meeting the prespecified reviewed inclusion criteria",
            "condition_contrast_id": "C01",
            "summary_target": "condition difference in expected participant-trial claim dwell",
            "inferential_unit": "participant with repeated trial observations",
            "aggregation_before_model": "none beyond fixation→trial×AOI measurement construction",
            "missingness_policy": "do not impute or coerce unavailable outcomes to zero without a separately justified plan",
            "censoring_policy": "not applicable to dwell; preserve missing exposure",
            "estimator_selected": False,
            "model_family_selected": False,
        },
        {
            "estimand_id": "E02",
            "outcome_id": "O02",
            "analysis_status": "secondary",
            "target_population": "same reviewed population as E01",
            "condition_contrast_id": "C01",
            "summary_target": "condition difference in expected claim fixation-event frequency under observed exposure",
            "inferential_unit": "participant with repeated trial observations",
            "aggregation_before_model": "fixations counted within participant×trial×AOI only",
            "missingness_policy": "retain exposure and distinguish observed zero from missing",
            "censoring_policy": "not applicable to count outcome",
            "estimator_selected": False,
            "model_family_selected": False,
        },
        {
            "estimand_id": "E03",
            "outcome_id": "O03",
            "analysis_status": "secondary",
            "target_population": "same reviewed population as E01",
            "condition_contrast_id": "C01",
            "summary_target": "condition contrast in time to first observed disclosure fixation",
            "inferential_unit": "participant with repeated trial observations",
            "aggregation_before_model": "none",
            "missingness_policy": "distinguish missing trial/exposure from no observed fixation",
            "censoring_policy": "right-censor no-fixation trials at latency_censor_time_ms",
            "estimator_selected": False,
            "model_family_selected": False,
        },
        {
            "estimand_id": "E04",
            "outcome_id": "O04",
            "analysis_status": "exploratory",
            "target_population": "same reviewed population as E01",
            "condition_contrast_id": "C01",
            "summary_target": "exploratory condition difference in claim→product transition frequency",
            "inferential_unit": "participant with repeated trial sequences",
            "aggregation_before_model": "within-trial transition counting only",
            "missingness_policy": "retain missing sequences and analysed sequence length",
            "censoring_policy": "not applicable to sequence count",
            "estimator_selected": False,
            "model_family_selected": False,
        },
    ]
    return pd.DataFrame(rows)


def _contrasts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "contrast_id": "C01",
                "name": "disclosure_B_minus_disclosure_A",
                "factor": "condition",
                "level_a": "disclosure_A",
                "level_b": "disclosure_B",
                "direction": "B - A",
                "analysis_status": "primary",
                "population_scope": "reviewed eligible participants/trials",
                "posthoc_level_selection_allowed": False,
            }
        ]
    )


def _sensitivities() -> pd.DataFrame:
    rows = [
        ("S01", "O01", "prespecified", "AOI boundary perturbation", "repeat O01 under a small justified reviewed claim-AOI perturbation"),
        ("S02", "O01;O02;O03", "prespecified", "event detector threshold", "repeat affected measurements under one prespecified detector sensitivity setting"),
        ("S03", "O01;O02", "prespecified", "coverage threshold", "repeat with the prespecified minimum observable-exposure sensitivity rule"),
        ("S04", "O03", "prespecified", "latency censoring", "retain all no-fixation cases and vary only a justified administrative exposure definition"),
        ("S05", "O04", "exploratory", "sequence preprocessing", "compare repeat-collapse versus preserved-repeat sequence coding"),
    ]
    return pd.DataFrame(
        rows,
        columns=("sensitivity_id", "outcome_ids", "status", "check", "procedure"),
    )


def _deviations() -> pd.DataFrame:
    return pd.DataFrame(columns=DEVIATION_COLUMNS)


def _reporting_plan() -> pd.DataFrame:
    rows = [
        ("O01", "primary", "report effect/uncertainty only after specialist modelling; always report observed exposure and analysis population", "AOI dwell is visual inspection and not a direct trust/persuasion measure"),
        ("O02", "secondary", "report count outcome with exposure/denominator and multiplicity-family status", "fixation count is not automatically interest or cognitive effort"),
        ("O03", "secondary", "report no-fixation censoring and exposure alongside latency inference", "no observed fixation is not latency zero or proof of no awareness"),
        ("O04", "exploratory", "label exploratory in tables/text and report the sequence-construction rule", "transition structure is not a direct persuasion-strategy measure"),
    ]
    return pd.DataFrame(
        rows,
        columns=("outcome_id", "analysis_status", "reporting_rule", "interpretation_boundary"),
    )


def _readme() -> str:
    return """# Worked outcome & estimand preregistration bundle

This deterministic teaching bundle freezes measurement/outcome definitions before
model fitting. It contains **no observed study results**, p-values, effect sizes,
model coefficients, inferential estimates, or automatically selected estimators.

The registry distinguishes `primary`, `secondary`, and `exploratory` outcomes;
preserves exposure, missing/zero, and right-censoring semantics; and starts with an
empty but schema-valid deviation registry. Any later deviation should be appended
rather than rewriting the original registration.

Evidence class: `synthetic_demo_not_empirical_evidence`.
"""


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    outcomes = _outcomes()
    estimands = _estimands()
    contrasts = _contrasts()
    sensitivities = _sensitivities()
    deviations = _deviations()
    reporting = _reporting_plan()

    tables = {
        "01_outcome_registry.csv": outcomes,
        "02_estimand_registry.csv": estimands,
        "03_contrast_registry.csv": contrasts,
        "04_sensitivity_registry.csv": sensitivities,
        "05_deviation_registry.csv": deviations,
        "06_reporting_plan.csv": reporting,
    }
    for name, table in tables.items():
        table.to_csv(output_dir / name, index=False)
    (output_dir / "README.md").write_text(_readme(), encoding="utf-8")

    statuses = set(outcomes["analysis_status"]) | set(estimands["analysis_status"])
    if not statuses <= set(ALLOWED_ANALYSIS_STATUS):
        raise RuntimeError("Unexpected analysis status in preregistration registry.")
    if outcomes["row_unit"].astype(str).str.strip().eq("").any():
        raise RuntimeError("Every outcome must declare its analysis row unit.")
    if outcomes["exposure_denominator_policy"].astype(str).str.strip().eq("").any():
        raise RuntimeError("Every outcome must declare exposure/denominator semantics.")
    latency = outcomes.loc[outcomes["outcome_id"] == "O03"].iloc[0]
    if "right-censored" not in latency["missing_zero_censoring_policy"]:
        raise RuntimeError("Latency preregistration must preserve right-censoring.")
    if estimands[["estimator_selected", "model_family_selected"]].any().any():
        raise RuntimeError("The preregistration example must not select an estimator/model family.")
    if not (sensitivities.loc[sensitivities["status"] == "prespecified"].shape[0] >= 1):
        raise RuntimeError("At least one sensitivity check must be prespecified.")
    if list(deviations.columns) != list(DEVIATION_COLUMNS):
        raise RuntimeError("Deviation registry schema changed unexpectedly.")

    data_files = [output_dir / name for name in tables] + [output_dir / "README.md"]
    _write_json(
        output_dir / "preregistration_manifest.json",
        {
            "example": "13_worked_estimand_preregistration",
            "evidence_classification": EVIDENCE_CLASSIFICATION,
            "allowed_analysis_status": list(ALLOWED_ANALYSIS_STATUS),
            "outcome_count": int(len(outcomes)),
            "estimand_count": int(len(estimands)),
            "contrast_count": int(len(contrasts)),
            "sensitivity_count": int(len(sensitivities)),
            "initial_deviation_count": int(len(deviations)),
            "artifact_hashes_sha256": {path.name: _sha256(path) for path in data_files},
            "model_fit_performed": False,
            "estimator_selected": False,
            "model_family_selected": False,
            "inferential_statistics_created": False,
            "p_values_created": False,
            "effect_sizes_created": False,
            "result_dependent_outcome_selection_performed": False,
            "missing_converted_to_zero": False,
            "censored_observations_dropped": False,
            "construct_validity_claim_created": False,
            "causal_validity_claim_created": False,
            "scientific_boundary": (
                "Preregistration makes planned measurement and estimand choices auditable; "
                "it does not establish construct validity, causal validity, or estimator suitability."
            ),
        },
    )

    print("Worked outcome/estimand preregistration complete")
    print(f"Output directory: {output_dir}")
    print(f"Registered outcomes: {len(outcomes)}")
    print("Model fit performed: no")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a deterministic outcome/estimand preregistration teaching bundle."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-estimand-preregistration"),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
