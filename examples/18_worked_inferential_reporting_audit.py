"""Deterministic uncertainty, multiplicity, and inferential-reporting teaching audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

EVIDENCE = "synthetic_demo_not_empirical_evidence"
GATE_STATUSES = {
    "eligible_confirmatory",
    "eligible_exploratory",
    "blocked_missing_uncertainty_identity",
    "blocked_multiplicity_incomplete",
    "blocked_scale_or_unit_mismatch",
    "blocked_diagnostic_failure",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _results() -> pd.DataFrame:
    rows = [
        (
            "R01", "E01", "POP_PRIMARY", "primary", "confirmatory", "F1",
            "difference_ms", "difference_ms", "ms", "ms", 120.0, 30.0, 210.0,
            0.95, "wald_confidence_interval", 0.012, 0.024, "holm", True,
        ),
        (
            "R02", "E02", "POP_PRIMARY", "secondary", "confirmatory", "F1",
            "rate_difference_per_s", "rate_difference_per_s", "fixations/s",
            "fixations/s", 0.18, 0.03, 0.33, 0.95,
            "wald_confidence_interval", 0.031, 0.031, "holm", True,
        ),
        (
            "R03", "E03", "POP_PRIMARY", "exploratory", "exploratory", "",
            "transition_probability_difference", "transition_probability_difference",
            "probability", "probability", 0.07, -0.01, 0.15, 0.95,
            "bootstrap_confidence_interval", 0.080, None,
            "not_applicable_exploratory", True,
        ),
        (
            "R04", "E04", "POP_PRIMARY", "secondary", "confirmatory", "F2",
            "difference_ms", "difference_ms", "ms", "ms", 75.0, 10.0, 140.0,
            None, "", 0.041, 0.082, "holm", True,
        ),
        (
            "R05", "E05", "POP_PRIMARY", "secondary", "confirmatory", "F2",
            "difference_ms", "difference_ms", "ms", "ms", 55.0, 5.0, 105.0,
            0.95, "wald_confidence_interval", 0.049, None, "", True,
        ),
        (
            "R06", "E06", "POP_PRIMARY", "secondary", "confirmatory", "F3",
            "difference_ms", "ratio", "ms", "ratio", 1.20, 1.02, 1.41, 0.95,
            "profile_confidence_interval", 0.018, 0.018, "none_single_member", True,
        ),
        (
            "R07", "E07", "POP_PRIMARY", "secondary", "confirmatory", "F4",
            "difference_ms", "difference_ms", "ms", "ms", 95.0, 20.0, 170.0,
            0.95, "wald_confidence_interval", 0.022, 0.022,
            "none_single_member", False,
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "result_id",
            "estimand_id",
            "analysis_population_id",
            "result_role",
            "inference_role",
            "multiplicity_family_id",
            "registered_effect_scale",
            "reported_effect_scale",
            "registered_unit",
            "reported_unit",
            "estimate",
            "interval_lower",
            "interval_upper",
            "interval_level",
            "uncertainty_method",
            "p_value_raw",
            "p_value_adjusted",
            "multiplicity_method",
            "diagnostic_gate_passed",
        ],
    )


def _uncertainty_audit(results: pd.DataFrame) -> pd.DataFrame:
    out = results[
        [
            "result_id",
            "estimate",
            "interval_lower",
            "interval_upper",
            "interval_level",
            "uncertainty_method",
            "registered_effect_scale",
            "reported_effect_scale",
            "registered_unit",
            "reported_unit",
        ]
    ].copy()
    out["interval_bounds_ordered"] = (
        out.interval_lower.le(out.estimate) & out.estimate.le(out.interval_upper)
    )
    out["uncertainty_identity_complete"] = (
        out.interval_level.notna() & out.uncertainty_method.astype(str).str.len().gt(0)
    )
    out["scale_unit_match"] = (
        out.registered_effect_scale.eq(out.reported_effect_scale)
        & out.registered_unit.eq(out.reported_unit)
    )
    return out


def _multiplicity(results: pd.DataFrame) -> pd.DataFrame:
    confirmatory = results.loc[results.inference_role.eq("confirmatory")].copy()
    rows: list[dict[str, object]] = []
    for family_id, group in confirmatory.groupby("multiplicity_family_id", sort=True):
        method_values = [x for x in group.multiplicity_method.astype(str) if x]
        declared_method = method_values[0] if method_values else ""
        complete = (
            bool(family_id)
            and bool(declared_method)
            and group.p_value_raw.notna().all()
            and group.p_value_adjusted.notna().all()
            and group.multiplicity_method.astype(str).str.len().gt(0).all()
        )
        rows.append(
            {
                "multiplicity_family_id": family_id,
                "member_count": len(group),
                "declared_method": declared_method,
                "family_record_complete": bool(complete),
                "automatic_method_selection": False,
            }
        )
    return pd.DataFrame(rows)


def _interpretation_gate(
    results: pd.DataFrame,
    uncertainty: pd.DataFrame,
    families: pd.DataFrame,
) -> pd.DataFrame:
    family_complete = dict(
        zip(families.multiplicity_family_id, families.family_record_complete, strict=True)
    )
    audit = results.merge(
        uncertainty[
            [
                "result_id",
                "interval_bounds_ordered",
                "uncertainty_identity_complete",
                "scale_unit_match",
            ]
        ],
        on="result_id",
        validate="one_to_one",
    )
    rows: list[dict[str, object]] = []
    for row in audit.itertuples(index=False):
        if not bool(row.diagnostic_gate_passed):
            status = "blocked_diagnostic_failure"
        elif not bool(row.scale_unit_match):
            status = "blocked_scale_or_unit_mismatch"
        elif not bool(row.interval_bounds_ordered) or not bool(row.uncertainty_identity_complete):
            status = "blocked_missing_uncertainty_identity"
        elif row.inference_role == "confirmatory" and not bool(
            family_complete.get(row.multiplicity_family_id, False)
        ):
            status = "blocked_multiplicity_incomplete"
        elif row.inference_role == "exploratory":
            status = "eligible_exploratory"
        else:
            status = "eligible_confirmatory"
        rows.append(
            {
                "result_id": row.result_id,
                "estimand_id": row.estimand_id,
                "analysis_population_id": row.analysis_population_id,
                "inference_role": row.inference_role,
                "interpretation_gate": status,
                "interpretation_allowed": status.startswith("eligible_"),
                "confirmatory_language_allowed": status == "eligible_confirmatory",
            }
        )
    return pd.DataFrame(rows)


def _reporting_language() -> pd.DataFrame:
    return pd.DataFrame(
        [
            (
                "effect_scale",
                "Condition B increased the outcome by 1.2 without stating the scale.",
                "Report the estimate on the declared effect scale with its unit.",
            ),
            (
                "uncertainty",
                "The effect was precise.",
                (
                    "Report the interval bounds, level, and interval method; precision "
                    "is interpreted in that context."
                ),
            ),
            (
                "multiplicity",
                "The raw p-value was below .05, so the confirmatory result was positive.",
                (
                    "Report raw and adjusted p-values distinctly and name the "
                    "prespecified multiplicity family/method."
                ),
            ),
            (
                "exploratory",
                "The exploratory result confirmed the primary hypothesis.",
                (
                    "Label exploratory results as exploratory and keep them outside "
                    "the confirmatory family."
                ),
            ),
        ],
        columns=["topic", "avoid", "prefer"],
    )


def _api_routes() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("estimand preregistration", "estimand-preregistration.md"),
            ("model diagnostics", "model-diagnostics-convergence.md"),
            ("sensitivity/robustness", "sensitivity-robustness-clinic.md"),
            ("reporting", "reporting-clinic.md"),
            ("publication readiness", "publication-readiness.md"),
        ],
        columns=["layer", "route"],
    )


def _readme() -> str:
    return """# Worked uncertainty & multiplicity audit

This bundle is `synthetic_demo_not_empirical_evidence` and is **not empirical
validation evidence**. All estimates, intervals, and p-values are teaching values.

The audit does not fit a model, choose a multiplicity method, or decide whether a
scientific hypothesis is true. It keeps effect scale/unit, interval method/level,
raw versus adjusted p-value identity, multiplicity family, diagnostic eligibility,
and confirmatory versus exploratory status explicit before manuscript reporting.
"""


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = _results()
    uncertainty = _uncertainty_audit(results)
    families = _multiplicity(results)
    gate = _interpretation_gate(results, uncertainty, families)

    tables = {
        "01_result_registry.csv": results,
        "02_uncertainty_audit.csv": uncertainty,
        "03_multiplicity_family.csv": families,
        "04_interpretation_gate.csv": gate,
        "05_reporting_language.csv": _reporting_language(),
        "06_api_route_map.csv": _api_routes(),
    }
    for name, table in tables.items():
        table.to_csv(output_dir / name, index=False)
    (output_dir / "README.md").write_text(_readme(), encoding="utf-8")

    if set(gate.interpretation_gate) != GATE_STATUSES:
        raise RuntimeError("Teaching interpretation-gate coverage changed.")
    if (results.p_value_raw.dropna() < 0).any() or (results.p_value_raw.dropna() > 1).any():
        raise RuntimeError("Raw p-values must remain in [0, 1].")
    if (
        (results.p_value_adjusted.dropna() < 0).any()
        or (results.p_value_adjusted.dropna() > 1).any()
    ):
        raise RuntimeError("Adjusted p-values must remain in [0, 1].")
    blocked = gate.interpretation_gate.str.startswith("blocked_")
    if gate.loc[blocked, "interpretation_allowed"].any():
        raise RuntimeError("A blocked result was marked interpretation-eligible.")

    manifest = {
        "example": "18_worked_inferential_reporting_audit",
        "evidence_classification": EVIDENCE,
        "result_count": len(results),
        "interpretation_gate_statuses": sorted(GATE_STATUSES),
        "artifact_hashes_sha256": {
            p.name: _sha256(p)
            for p in sorted(output_dir.iterdir())
            if p.is_file() and p.name != "inferential_reporting_manifest.json"
        },
        "inferential_model_fitted_by_example": False,
        "multiplicity_method_selected_automatically": False,
        "raw_adjusted_p_values_conflated": False,
        "exploratory_promoted_to_confirmatory": False,
        "diagnostic_failure_overridden": False,
        "scientific_truth_label_created": False,
        "causal_claim_created": False,
        "construct_validity_claim_created": False,
        "device_or_native_rate_validity_claim_created": False,
    }
    _write_json(output_dir / "inferential_reporting_manifest.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an inferential reporting audit bundle.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-inferential-reporting-audit"),
    )
    run(parser.parse_args().output_dir)


if __name__ == "__main__":
    main()
