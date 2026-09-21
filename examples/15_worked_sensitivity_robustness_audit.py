"""Build a deterministic sensitivity/robustness audit teaching bundle.

The example uses synthetic teaching values only. It does not fit a statistical model,
create p-values/significance decisions, redefine the primary estimand, or turn
sensitivity consistency into scientific validity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

EVIDENCE = "synthetic_demo_not_empirical_evidence"
ANALYSIS_STATUS = {
    "primary",
    "prespecified_sensitivity",
    "exploratory_sensitivity",
    "deviation",
}
EXECUTION_STATUS = {"completed", "not_evaluable", "non_converged"}
COMPARISON_STATUS = {
    "primary_reference",
    "same_estimand_comparable",
    "changed_estimand_not_comparable",
    "not_evaluable",
    "non_converged",
}
PRIMARY_ESTIMAND = "E01"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _registry() -> pd.DataFrame:
    rows = [
        (
            "B00",
            "primary",
            "primary specification",
            "registered primary claim-AOI dwell estimand",
            True,
            "api-reference.md#semantic-aois",
            "primary result remains the reference; no sensitivity replaces it",
        ),
        (
            "S01",
            "prespecified_sensitivity",
            "coverage threshold",
            "repeat E01 with minimum observable exposure = 80%",
            True,
            "api-reference.md#quality-control",
            "coverage sensitivity does not validate the exclusion threshold",
        ),
        (
            "S02",
            "prespecified_sensitivity",
            "event detector threshold",
            "repeat E01 under the prespecified alternate event threshold",
            True,
            "api-reference.md#eye-events",
            "detector sensitivity does not establish physiological event truth",
        ),
        (
            "S03",
            "prespecified_sensitivity",
            "sampling condition",
            "repeat E01 on a declared derived lower-rate condition",
            True,
            "api-reference.md#sampling-sensitivity",
            "derived-rate sensitivity is not native-device validation",
        ),
        (
            "S04",
            "prespecified_sensitivity",
            "model family",
            "repeat E01 with a prespecified alternative specialist model family",
            True,
            "api-reference.md#model-comparison",
            "failed convergence remains visible and is not a valid result",
        ),
        (
            "S05",
            "prespecified_sensitivity",
            "strict coverage threshold",
            "repeat E01 with minimum observable exposure = 95%",
            True,
            "api-reference.md#quality-control",
            "an unevaluable condition is reported rather than silently dropped",
        ),
        (
            "S06",
            "exploratory_sensitivity",
            "AOI boundary",
            "repeat E01 using a documented exploratory AOI-boundary variant",
            True,
            "api-reference.md#semantic-aois",
            "AOI sensitivity is not construct validation",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "condition_id",
            "analysis_status",
            "sensitivity_dimension",
            "specification",
            "same_estimand_required",
            "api_route",
            "interpretation_boundary",
        ],
    )


def _executed() -> pd.DataFrame:
    rows = [
        ("B00", "primary", "completed", "E01", 180, 97200, 120.0, 30.0),
        ("S01", "prespecified_sensitivity", "completed", "E01", 170, 91800, 116.0, 32.0),
        ("S02", "prespecified_sensitivity", "completed", "E01", 180, 97200, 124.0, 31.0),
        ("S03", "prespecified_sensitivity", "completed", "E01", 180, 97200, 118.0, 33.0),
        ("S04", "prespecified_sensitivity", "non_converged", "E01", 180, 97200, None, None),
        ("S05", "prespecified_sensitivity", "not_evaluable", "E01", 22, 11880, None, None),
        ("S06", "exploratory_sensitivity", "completed", "E01", 180, 97200, 109.0, 35.0),
        ("D01", "deviation", "completed", "E01_CC", 152, 82080, 131.0, 29.0),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "condition_id",
            "analysis_status",
            "execution_status",
            "estimand_id",
            "analysis_denominator",
            "exposure_ms",
            "synthetic_estimate_ms",
            "synthetic_uncertainty_width_ms",
        ],
    )


def _comparison(executed: pd.DataFrame) -> pd.DataFrame:
    primary = executed.loc[executed["condition_id"] == "B00"].iloc[0]
    rows: list[dict[str, object]] = []
    for row in executed.itertuples(index=False):
        same_estimand = row.estimand_id == PRIMARY_ESTIMAND
        if row.condition_id == "B00":
            status = "primary_reference"
        elif row.execution_status == "not_evaluable":
            status = "not_evaluable"
        elif row.execution_status == "non_converged":
            status = "non_converged"
        elif not same_estimand:
            status = "changed_estimand_not_comparable"
        else:
            status = "same_estimand_comparable"

        comparable = status == "same_estimand_comparable"
        estimate_delta = None
        relative_delta_pct = None
        direction_consistent = None
        if comparable:
            estimate_delta = float(row.synthetic_estimate_ms - primary.synthetic_estimate_ms)
            relative_delta_pct = float(100.0 * estimate_delta / primary.synthetic_estimate_ms)
            direction_consistent = bool(
                row.synthetic_estimate_ms * primary.synthetic_estimate_ms >= 0
            )

        rows.append(
            {
                "condition_id": row.condition_id,
                "analysis_status": row.analysis_status,
                "comparison_status": status,
                "same_estimand": same_estimand,
                "comparable_to_primary": comparable,
                "denominator_delta": int(row.analysis_denominator - primary.analysis_denominator),
                "exposure_delta_ms": int(row.exposure_ms - primary.exposure_ms),
                "estimate_delta_ms": estimate_delta,
                "relative_delta_pct": relative_delta_pct,
                "direction_consistent_with_primary": direction_consistent,
                "automatic_robustness_verdict": "not_created",
            }
        )
    return pd.DataFrame(rows)


def _deviations() -> pd.DataFrame:
    rows = [
        (
            "D01",
            "post-result diagnostic review",
            "complete-case restriction added after primary analysis",
            "changes target population from registered E01 to E01_CC",
            "exploratory deviation; cannot replace the primary result",
        )
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "deviation_id",
            "timing",
            "change",
            "estimand_effect",
            "reporting_status",
        ],
    )


def _interpretation() -> pd.DataFrame:
    rows = [
        (
            "QC/coverage",
            "sensitivity to usable-exposure rules",
            "estimand, outcome, contrast, missing/zero semantics",
            "exclusion-rule validity",
            "api-reference.md#quality-control",
        ),
        (
            "event detector",
            "sensitivity to detector definition/threshold",
            "estimand and participant/trial denominator",
            "physiological truth of one detector",
            "api-reference.md#eye-events",
        ),
        (
            "sampling",
            "sensitivity to declared derived-rate analysis conditions",
            "derivation rule and source provenance",
            "native-device validity",
            "api-reference.md#sampling-sensitivity",
        ),
        (
            "AOI boundary",
            "sensitivity to a documented region-definition variant",
            "construct label and exposure rule",
            "construct validity",
            "api-reference.md#semantic-aois",
        ),
        (
            "scanpath preprocessing",
            "sensitivity to repeat/unassigned-state rules",
            "sequence estimand identity",
            "latent strategy or intent",
            "api-reference.md#scanpaths",
        ),
        (
            "model family",
            "sensitivity to prespecified estimator/model family",
            "same scientific estimand and analysis population",
            "universal model superiority",
            "api-reference.md#model-comparison",
        ),
        (
            "held-out model comparison",
            "matched-fold sensitivity of model differences",
            "held-out identity and matched observations",
            "population generalisation beyond the stated split",
            "api-reference.md#matched-fold-model-differences",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "dimension",
            "addresses",
            "must_hold_fixed",
            "does_not_establish",
            "api_route",
        ],
    )


def _reporting_language() -> pd.DataFrame:
    rows = [
        (
            "methods",
            "We tried several analyses to see what worked.",
            (
                "We executed the complete prespecified sensitivity set and labelled "
                "later deviations separately."
            ),
        ),
        (
            "results",
            "The result was robust across all analyses.",
            (
                "Same-estimand completed variants had the reported estimate/denominator "
                "changes; one model variant did not converge and one strict-coverage "
                "condition was not evaluable."
            ),
        ),
        (
            "sampling",
            "The 60 Hz sensitivity confirms native 60 Hz validity.",
            (
                "The declared derived-rate condition was a sensitivity analysis and does "
                "not establish native-device validity."
            ),
        ),
        (
            "exploratory",
            "The complete-case analysis confirms the primary effect.",
            (
                "The complete-case deviation changed the target population and is reported "
                "as exploratory rather than as a direct robustness check of E01."
            ),
        ),
        (
            "limitations",
            "All reasonable specifications produced the same conclusion.",
            (
                "Sensitivity coverage is limited to the registered/executed specifications; "
                "untested choices and non-evaluable/non-converged variants remain explicit "
                "limitations."
            ),
        ),
    ]
    return pd.DataFrame(rows, columns=["section", "avoid", "prefer"])


def _readme() -> str:
    return """# Worked sensitivity & robustness audit

This deterministic teaching bundle is `synthetic_demo_not_empirical_evidence`. It is
**not empirical validation evidence**. It uses fixed synthetic summary values and does
not fit a statistical model,
create p-values, significance decisions, causal claims, construct-validity claims,
or a universal `robust`/`not robust` verdict.

Read the registry first, then executed conditions and the result-comparison table.
The comparison table keeps same-estimand variants separate from a deviation that
changes the target population. `not_evaluable` and `non_converged` conditions remain
present rather than being silently dropped.

A favourable sensitivity result never replaces the registered primary result.
Derived-rate sensitivity is not native-device validation. Detector/AOI/sequence
sensitivity does not establish physiological or construct validity.
"""


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    registry = _registry()
    executed = _executed()
    comparison = _comparison(executed)
    deviations = _deviations()
    interpretation = _interpretation()
    reporting = _reporting_language()

    tables = {
        "01_sensitivity_registry.csv": registry,
        "02_executed_conditions.csv": executed,
        "03_result_comparison.csv": comparison,
        "04_deviation_ledger.csv": deviations,
        "05_interpretation_matrix.csv": interpretation,
        "06_reporting_language.csv": reporting,
    }
    for name, table in tables.items():
        table.to_csv(output_dir / name, index=False)
    (output_dir / "README.md").write_text(_readme(), encoding="utf-8")

    if not set(registry["analysis_status"]) <= ANALYSIS_STATUS:
        raise RuntimeError("Unexpected registered analysis status.")
    if not set(executed["analysis_status"]) <= ANALYSIS_STATUS:
        raise RuntimeError("Unexpected executed analysis status.")
    if not set(executed["execution_status"]) <= EXECUTION_STATUS:
        raise RuntimeError("Unexpected execution status.")
    if not set(comparison["comparison_status"]) <= COMPARISON_STATUS:
        raise RuntimeError("Unexpected comparison status.")

    registered_sensitivity_ids = set(
        registry.loc[registry["condition_id"] != "B00", "condition_id"]
    )
    executed_ids = set(executed["condition_id"])
    if not registered_sensitivity_ids <= executed_ids:
        raise RuntimeError("A registered sensitivity condition is missing from execution.")

    same_estimand_ids = set(registry.loc[registry["same_estimand_required"], "condition_id"])
    executed_same = executed.loc[executed["condition_id"].isin(same_estimand_ids)]
    if set(executed_same["estimand_id"]) != {PRIMARY_ESTIMAND}:
        raise RuntimeError("A same-estimand sensitivity silently changed estimand identity.")

    if "not_evaluable" not in set(executed["execution_status"]):
        raise RuntimeError("At least one not-evaluable teaching condition is required.")
    if "non_converged" not in set(executed["execution_status"]):
        raise RuntimeError("At least one non-converged teaching condition is required.")

    manifest = {
        "example": "15_worked_sensitivity_robustness_audit",
        "evidence_classification": EVIDENCE,
        "primary_estimand_id": PRIMARY_ESTIMAND,
        "registered_sensitivity_count": int(len(registered_sensitivity_ids)),
        "registered_sensitivities_all_represented": True,
        "not_evaluable_condition_count": int(
            (executed["execution_status"] == "not_evaluable").sum()
        ),
        "non_converged_condition_count": int(
            (executed["execution_status"] == "non_converged").sum()
        ),
        "artifact_hashes_sha256": {
            path.name: _sha256(path)
            for path in sorted(output_dir.iterdir())
            if path.is_file() and path.name != "sensitivity_manifest.json"
        },
        "statistical_significance_claim_created": False,
        "automatic_robustness_verdict_created": False,
        "causal_claim_created": False,
        "construct_validity_claim_created": False,
        "native_device_validity_claim_created": False,
        "primary_estimand_redefined": False,
        "non_evaluable_or_nonconverged_silently_dropped": False,
        "synthetic_values_are_empirical_results": False,
    }
    _write_json(output_dir / "sensitivity_manifest.json", manifest)

    print("Worked sensitivity/robustness audit complete")
    print(f"Output directory: {output_dir}")
    print("Evidence classification: synthetic_demo_not_empirical_evidence")
    print("Automatic robustness verdict: not created")
    print("Primary estimand redefined: no")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a deterministic sensitivity/robustness audit bundle."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-sensitivity-robustness-audit"),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
