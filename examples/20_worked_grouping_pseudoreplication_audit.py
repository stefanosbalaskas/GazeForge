"""Build a deterministic grouping and pseudoreplication audit bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

EVIDENCE = "synthetic_demo_not_empirical_evidence"
UNIT_ROLES = {
    "observation_row",
    "measurement_unit",
    "inferential_unit",
    "generalisation_unit",
}
GROUPING_RELATIONS = {
    "repeated_within_unit",
    "nested",
    "crossed",
    "descriptive_only",
}
RISK_STATUSES = {
    "acceptable_with_grouping_preserved",
    "pseudoreplication_risk",
    "aggregation_changes_inferential_unit",
    "descriptive_only_not_inferential_input",
}


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _unit_registry() -> pd.DataFrame:
    rows = [
        (
            "U01",
            "fixation_x_aoi_row",
            "fixation",
            "participant_trial",
            "participant",
            True,
            True,
            True,
            True,
        ),
        (
            "U02",
            "trial_x_aoi_row",
            "participant_trial_aoi",
            "participant_trial",
            "participant",
            True,
            True,
            True,
            True,
        ),
        (
            "U03",
            "trial_event_row",
            "participant_trial_event_type",
            "participant_trial",
            "participant",
            True,
            True,
            True,
            False,
        ),
        (
            "U04",
            "participant_condition_mean",
            "participant_condition_summary",
            "participant",
            "participant",
            True,
            False,
            False,
            False,
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=(
            "unit_id",
            "row_unit",
            "measurement_unit",
            "inferential_unit",
            "generalisation_unit",
            "participant_id_retained",
            "trial_id_retained",
            "stimulus_id_retained",
            "aoi_or_event_id_retained",
        ),
    )


def _grouping_structure() -> pd.DataFrame:
    rows = [
        (
            "G01",
            "participant_id",
            "trial_id",
            "nested",
            "trials indexed within participant in this teaching design",
            False,
        ),
        (
            "G02",
            "participant_id",
            "stimulus_id",
            "crossed",
            "the same stimuli are viewed by multiple participants",
            False,
        ),
        (
            "G03",
            "participant_id",
            "aoi_label",
            "repeated_within_unit",
            "multiple AOI outcomes are recorded within participant-trial records",
            False,
        ),
        (
            "G04",
            "participant_condition_mean",
            "trial_id",
            "descriptive_only",
            "trial identity has been aggregated away for plotting/reporting",
            False,
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=(
            "grouping_id",
            "factor_a",
            "factor_b",
            "relation",
            "design_reason",
            "model_term_selected_automatically",
        ),
    )


def _independence_audit() -> pd.DataFrame:
    rows = [
        (
            "R01",
            "fixations treated as independent participants",
            "fixation_x_aoi_row",
            "participant",
            "pseudoreplication_risk",
            True,
            "many rows share participant/trial identity",
        ),
        (
            "R02",
            "trial x AOI rows with participant/trial/stimulus retained",
            "trial_x_aoi_row",
            "participant_trial",
            "acceptable_with_grouping_preserved",
            False,
            "dependence remains visible for specialist modelling",
        ),
        (
            "R03",
            "participant-condition means substituted for trial-level model input",
            "participant_condition_mean",
            "participant",
            "aggregation_changes_inferential_unit",
            True,
            "trial/stimulus variation is no longer represented",
        ),
        (
            "R04",
            "participant-condition means used only for descriptive plot",
            "participant_condition_mean",
            "participant",
            "descriptive_only_not_inferential_input",
            False,
            "descriptive summary remains separate from inferential input",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=(
            "audit_id",
            "scenario",
            "row_unit",
            "declared_inferential_unit",
            "risk_status",
            "blocks_unqualified_independence_claim",
            "reason",
        ),
    )


def _aggregation_risk() -> pd.DataFrame:
    rows = [
        (
            "A01",
            "trial_x_aoi",
            "participant_condition_mean",
            "trial_id;stimulus_id;aoi_label",
            True,
            False,
            "descriptive_summary_only",
        ),
        (
            "A02",
            "fixation_rows",
            "trial_x_aoi",
            "fixation_id",
            False,
            False,
            "measurement_construction_if_prespecified",
        ),
        (
            "A03",
            "trial_event_rows",
            "participant_condition_mean",
            "trial_id;stimulus_id;event_type",
            True,
            False,
            "changes_analysis_unit",
        ),
        (
            "A04",
            "trial_x_aoi",
            "trial_x_aoi",
            "",
            False,
            False,
            "identity_preserving_handoff",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=(
            "aggregation_id",
            "source_granularity",
            "target_granularity",
            "grouping_keys_lost",
            "changes_inferential_unit_or_estimand",
            "performed_automatically",
            "interpretation",
        ),
    )


def _crossed_nested_handoff() -> pd.DataFrame:
    rows = [
        (
            "participant_id",
            "grouping_identity",
            "repeated observations share participants",
            "not_selected_by_gazeforge",
        ),
        (
            "trial_id",
            "nested_identity_candidate",
            "trial numbering/identity is interpreted from study design",
            "not_selected_by_gazeforge",
        ),
        (
            "stimulus_id",
            "crossed_identity_candidate",
            "stimuli recur across participants in this teaching design",
            "not_selected_by_gazeforge",
        ),
        (
            "session_id",
            "grouping_identity_if_present",
            "session dependence is study-specific",
            "not_selected_by_gazeforge",
        ),
        (
            "aoi_label",
            "repeated_measure_identity",
            "AOI rows are repeated measurement rows, not participants",
            "not_selected_by_gazeforge",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=(
            "identity",
            "handoff_role",
            "design_statement",
            "statistical_term_selection",
        ),
    )


def _reporting_language() -> pd.DataFrame:
    rows = [
        (
            "inferential_unit",
            "The inferential input retained participant, trial, and stimulus identity.",
            "Each fixation was treated as an independent participant.",
        ),
        (
            "crossed_stimuli",
            "Stimulus identity was retained because materials recurred across participants.",
            "Stimulus dependence was ignored after averaging.",
        ),
        (
            "aggregation",
            "Participant-condition means were used for description only.",
            "Participant-condition means silently replaced the trial-level analysis.",
        ),
        (
            "model_structure",
            (
                "Grouping identities were handed to specialist software without "
                "automatic model-term selection."
            ),
            "The package selected the correct random-effects structure.",
        ),
        (
            "small_variance",
            (
                "A small or unavailable variance component did not by itself "
                "remove a grouping identity."
            ),
            "The stimulus effect was negligible because its variance estimate was small.",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=("topic", "claim_safe_wording", "avoid_wording"),
    )


def _api_routes() -> pd.DataFrame:
    rows = [
        ("schema", "api-reference.md#schema"),
        ("quality control", "api-reference.md#quality-control"),
        ("eye events", "api-reference.md#eye-events"),
        ("semantic AOIs", "api-reference.md#semantic-aois"),
        ("dynamic AOIs", "api-reference.md#dynamic-aois"),
        ("scanpaths", "api-reference.md#scanpaths"),
        ("hierarchical location-scale", "api-reference.md#hierarchical-location-scale-models"),
    ]
    return pd.DataFrame(rows, columns=("layer", "api_route"))


def _readme() -> str:
    return """# Grouping, repeated-measures, and pseudoreplication audit

This deterministic teaching bundle is `synthetic_demo_not_empirical_evidence`.

It distinguishes observation rows, measurement units, inferential units, and
generalisation units; preserves participant/trial/stimulus identities; and flags
obvious pseudoreplication or aggregation risks.

It does not select fixed effects, random intercepts/slopes, covariance structures,
cluster-robust standard errors, GEE, LMM/GLMM, Bayesian hierarchical models, or any
other statistical estimator.
"""


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    units = _unit_registry()
    grouping = _grouping_structure()
    independence = _independence_audit()
    aggregation = _aggregation_risk()
    handoff = _crossed_nested_handoff()
    reporting = _reporting_language()
    api = _api_routes()

    tables = {
        "01_unit_registry.csv": units,
        "02_grouping_structure.csv": grouping,
        "03_row_independence_audit.csv": independence,
        "04_aggregation_risk_register.csv": aggregation,
        "05_crossed_nested_handoff.csv": handoff,
        "06_reporting_language.csv": reporting,
        "07_api_route_map.csv": api,
    }
    for name, table in tables.items():
        table.to_csv(output_dir / name, index=False)

    if set(grouping["relation"]) != GROUPING_RELATIONS:
        raise RuntimeError("Grouping relation teaching coverage changed.")
    if not set(independence["risk_status"]) <= RISK_STATUSES:
        raise RuntimeError("Unexpected pseudoreplication risk status.")
    if grouping["model_term_selected_automatically"].astype(bool).any():
        raise RuntimeError("Grouping audit must not select model terms.")
    if aggregation["performed_automatically"].astype(bool).any():
        raise RuntimeError("Aggregation audit must not perform automatic aggregation.")
    if handoff["statistical_term_selection"].ne("not_selected_by_gazeforge").any():
        raise RuntimeError("Specialist model structure must remain unselected.")

    risky = independence["risk_status"].isin(
        {"pseudoreplication_risk", "aggregation_changes_inferential_unit"}
    )
    if not independence.loc[risky, "blocks_unqualified_independence_claim"].all():
        raise RuntimeError("Pseudoreplication risk must fail closed.")

    required_identity = units["unit_id"].isin(["U01", "U02"])
    for col in ("participant_id_retained", "trial_id_retained", "stimulus_id_retained"):
        if not units.loc[required_identity, col].astype(bool).all():
            raise RuntimeError(f"Required grouping identity lost: {col}")

    (output_dir / "README.md").write_text(_readme(), encoding="utf-8")
    _write_json(
        output_dir / "grouping_pseudoreplication_manifest.json",
        {
            "example": "20_worked_grouping_pseudoreplication_audit",
            "evidence_classification": EVIDENCE,
            "unit_roles": sorted(UNIT_ROLES),
            "grouping_relations": sorted(GROUPING_RELATIONS),
            "pseudoreplication_risk_count": int(
                independence["risk_status"].eq("pseudoreplication_risk").sum()
            ),
            "aggregation_change_risk_count": int(
                independence["risk_status"].eq("aggregation_changes_inferential_unit").sum()
            ),
            "automatic_aggregation_performed": False,
            "fixed_effect_selected": False,
            "random_intercept_selected": False,
            "random_slope_selected": False,
            "covariance_structure_selected": False,
            "cluster_robust_se_selected": False,
            "gee_selected": False,
            "lmm_glmm_selected": False,
            "bayesian_hierarchical_model_selected": False,
            "statistical_estimator_selected": False,
            "small_variance_used_to_drop_grouping_identity": False,
            "stimulus_identity_discarded": False,
            "participant_identity_discarded": False,
            "device_validity_claim_created": False,
            "construct_validity_claim_created": False,
            "causal_validity_claim_created": False,
            "psychological_state_claim_created": False,
        },
    )

    print("Worked grouping/pseudoreplication audit complete")
    print(f"Output directory: {output_dir}")
    print(f"Pseudoreplication risk rows: {int(risky.sum())}")
    print("Statistical model structure selected: no")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a deterministic grouping/pseudoreplication audit bundle."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-grouping-pseudoreplication-audit"),
    )
    run(parser.parse_args().output_dir)


if __name__ == "__main__":
    main()
