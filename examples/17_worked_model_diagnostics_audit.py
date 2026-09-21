"""Deterministic vendor-neutral model-diagnostics teaching audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

EVIDENCE = "synthetic_demo_not_empirical_evidence"
DIAGNOSTIC_STATUS = {
    "pass",
    "blocked_non_converged",
    "blocked_singular_or_boundary",
    "blocked_missing_diagnostics",
    "blocked_separation_or_covariance",
}
GATE_STATUS = {
    "eligible_for_interpretation",
    "blocked_diagnostic_failure",
    "exploratory_changed_estimand",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fits() -> pd.DataFrame:
    rows = [
        ("M01", "E01", "POP_PRIMARY", "GLMM", "primary", None, False),
        ("M02", "E01", "POP_PRIMARY", "GLMM", "prespecified_sensitivity", "M01", False),
        ("M03", "E01", "POP_PRIMARY", "GLMM", "prespecified_sensitivity", "M01", False),
        ("M04", "E01", "POP_PRIMARY", "GLMM", "diagnostic_review", "M01", False),
        ("M05", "E01", "POP_PRIMARY", "GLMM", "diagnostic_review", "M01", False),
        ("M06", "E01_CC", "POP_COMPLETE_CASE", "GLMM", "deviation", "M01", True),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "model_id",
            "estimand_id",
            "analysis_population_id",
            "model_family",
            "analysis_status",
            "replacement_for",
            "changed_estimand_or_population",
        ],
    ).assign(
        specialist_software="teaching_specialist_backend",
        specialist_software_version="DEMO_VERSION",
        automatic_model_selection=False,
    )


def _diagnostics() -> pd.DataFrame:
    rows = [
        ("M01", "converged", False, False, True, True),
        ("M02", "non_converged", False, False, None, True),
        ("M03", "converged", True, False, True, True),
        ("M04", "unknown", None, None, None, False),
        ("M05", "converged", False, True, False, True),
        ("M06", "converged", False, False, True, True),
    ]
    out = pd.DataFrame(
        rows,
        columns=[
            "model_id",
            "convergence_status",
            "singular_or_boundary",
            "separation_problem",
            "covariance_or_hessian_valid",
            "diagnostics_complete",
        ],
    )
    out["diagnostic_status"] = out.apply(_diagnostic_status, axis=1)
    return out


def _diagnostic_status(row: pd.Series) -> str:
    if not bool(row.diagnostics_complete):
        return "blocked_missing_diagnostics"
    if row.convergence_status != "converged":
        return "blocked_non_converged"
    if bool(row.singular_or_boundary):
        return "blocked_singular_or_boundary"
    if bool(row.separation_problem) or row.covariance_or_hessian_valid is False:
        return "blocked_separation_or_covariance"
    return "pass"


def _gate(fits: pd.DataFrame, diagnostics: pd.DataFrame) -> pd.DataFrame:
    out = fits.merge(diagnostics[["model_id", "diagnostic_status"]], on="model_id")
    out["interpretation_gate"] = "blocked_diagnostic_failure"
    passed = out.diagnostic_status.eq("pass")
    same_target = ~out.changed_estimand_or_population
    out.loc[passed & same_target, "interpretation_gate"] = "eligible_for_interpretation"
    out.loc[passed & ~same_target, "interpretation_gate"] = "exploratory_changed_estimand"
    out["interpretation_allowed"] = out.interpretation_gate.eq("eligible_for_interpretation")
    out["may_replace_primary_automatically"] = False
    return out[
        [
            "model_id",
            "estimand_id",
            "analysis_population_id",
            "diagnostic_status",
            "interpretation_gate",
            "interpretation_allowed",
            "may_replace_primary_automatically",
        ]
    ]


def _sensitivity_linkage(fits: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in fits.itertuples(index=False):
        relation = "primary_reference"
        if row.model_id != "M01":
            relation = (
                "changed_estimand_deviation"
                if row.changed_estimand_or_population
                else "same_estimand_variant"
            )
        rows.append(
            {
                "model_id": row.model_id,
                "replacement_for": row.replacement_for,
                "relation_to_primary": relation,
                "estimand_id": row.estimand_id,
                "analysis_population_id": row.analysis_population_id,
                "automatic_replacement_selected": False,
            }
        )
    return pd.DataFrame(rows)


def _reporting() -> pd.DataFrame:
    return pd.DataFrame(
        [
            (
                "methods",
                "All fitted models were interpreted because coefficients were returned.",
                (
                    "Model identity, software, convergence, and required diagnostics "
                    "were audited before interpretation."
                ),
            ),
            (
                "non_convergence",
                "The model nearly converged, so estimates were retained.",
                (
                    "The non-converged fit was retained in the audit but blocked "
                    "from inferential interpretation."
                ),
            ),
            (
                "singularity",
                "The singular fit was accepted as a robustness result.",
                (
                    "The singular/boundary fit was flagged for review and not treated "
                    "as a valid confirmatory result."
                ),
            ),
            (
                "replacement",
                "A complete-case replacement confirmed the primary model.",
                (
                    "The complete-case candidate changed the estimand/population and "
                    "was reported as an exploratory deviation."
                ),
            ),
        ],
        columns=["section", "avoid", "prefer"],
    )


def _api_routes() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("analysis handoff", "analysis-handoff.md"),
            ("denominator/exposure", "denominator-exposure-censoring.md"),
            ("sensitivity", "sensitivity-robustness-clinic.md"),
            ("reporting", "reporting-clinic.md"),
            ("publication readiness", "publication-readiness.md"),
        ],
        columns=["layer", "route"],
    )


def _readme() -> str:
    return """# Worked model diagnostics audit

This bundle is `synthetic_demo_not_empirical_evidence` and is **not empirical
validation evidence**. It does not fit a real model or create p-values/effect sizes.

A coefficient table is not enough to establish an interpretable fit. Non-convergence,
singular/boundary fits, separation/invalid covariance states, and missing diagnostics
block interpretation. GazeForge does not choose a replacement estimator automatically.
A diagnostically clean replacement that changes the estimand or analysis population is
reported as an exploratory deviation rather than silently replacing the primary model.
"""


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fits = _fits()
    diagnostics = _diagnostics()
    gate = _gate(fits, diagnostics)
    tables = {
        "01_model_fit_registry.csv": fits,
        "02_diagnostic_status.csv": diagnostics,
        "03_interpretation_gate.csv": gate,
        "04_sensitivity_linkage.csv": _sensitivity_linkage(fits),
        "05_reporting_language.csv": _reporting(),
        "06_api_route_map.csv": _api_routes(),
    }
    for name, table in tables.items():
        table.to_csv(output_dir / name, index=False)
    (output_dir / "README.md").write_text(_readme(), encoding="utf-8")

    if set(diagnostics.diagnostic_status) != DIAGNOSTIC_STATUS:
        raise RuntimeError("Teaching diagnostic-status coverage changed.")
    if not set(gate.interpretation_gate) <= GATE_STATUS:
        raise RuntimeError("Unexpected interpretation-gate status.")
    failed = gate.diagnostic_status.ne("pass")
    if gate.loc[failed, "interpretation_allowed"].any():
        raise RuntimeError("A failed diagnostic state was marked interpretation-eligible.")
    changed = gate.estimand_id.ne("E01") | gate.analysis_population_id.ne("POP_PRIMARY")
    if gate.loc[changed, "interpretation_allowed"].any():
        raise RuntimeError("A changed-estimand replacement was silently promoted.")

    manifest = {
        "example": "17_worked_model_diagnostics_audit",
        "evidence_classification": EVIDENCE,
        "model_count": len(fits),
        "diagnostic_statuses": sorted(DIAGNOSTIC_STATUS),
        "interpretation_gate_statuses": sorted(GATE_STATUS),
        "artifact_hashes_sha256": {
            p.name: _sha(p)
            for p in sorted(output_dir.iterdir())
            if p.is_file() and p.name != "model_diagnostics_manifest.json"
        },
        "inferential_model_fitted_by_example": False,
        "automatic_replacement_model_selected": False,
        "failed_fit_accepted_for_inference": False,
        "p_value_or_effect_claim_created": False,
        "causal_claim_created": False,
        "construct_validity_claim_created": False,
        "device_validity_claim_created": False,
    }
    _write_json(output_dir / "model_diagnostics_manifest.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a model diagnostics audit bundle.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-model-diagnostics-audit"),
    )
    run(parser.parse_args().output_dir)


if __name__ == "__main__":
    main()
