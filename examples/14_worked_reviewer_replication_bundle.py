"""Build a deterministic reviewer/replicator handoff teaching bundle.

The bundle maps reported statements to study artifacts, access requirements,
reproducibility classes, limitations, rerun routes, software identity, and public
GazeForge API documentation. It does not claim that reproducibility equals validity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

EVIDENCE_CLASSIFICATION = "synthetic_demo_not_empirical_evidence"
REPRODUCIBILITY_CLASSES = (
    "fully_rerunnable",
    "rerunnable_with_private_input",
    "inspectable_only",
)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _claim_artifact_matrix() -> pd.DataFrame:
    rows = [
        (
            "C01",
            "The retained trial denominator follows the reviewed exclusion ledger.",
            "08_exclusion_flow.csv",
            "denominator/review evidence",
            "study_archive_required",
            False,
            "rerunnable_with_private_input",
            "synthetic_demo_not_empirical_evidence",
            "Reproducible denominator accounting does not establish that the exclusion rule is scientifically valid.",
            "API02",
        ),
        (
            "C02",
            "The primary analysis rows were derived from reviewed retained units.",
            "07_primary_analysis_rows.csv",
            "analysis derivative",
            "study_archive_required",
            False,
            "rerunnable_with_private_input",
            "synthetic_demo_not_empirical_evidence",
            "A reconstructable derivative does not establish measurement, construct, or causal validity.",
            "API01",
        ),
        (
            "C03",
            "Claim-AOI dwell is defined from reviewed fixation-to-AOI assignments.",
            "04_trial_aoi_metrics.csv",
            "measurement derivative",
            "study_archive_required",
            False,
            "rerunnable_with_private_input",
            "synthetic_demo_not_empirical_evidence",
            "AOI dwell is observed visual inspection under declared event/AOI definitions, not a direct trust or persuasion measure.",
            "API04",
        ),
        (
            "C04",
            "No-fixation latency cases remain censored rather than encoded as zero.",
            "04_trial_aoi_metrics.csv",
            "measurement derivative",
            "study_archive_required",
            False,
            "rerunnable_with_private_input",
            "synthetic_demo_not_empirical_evidence",
            "Censoring semantics improve auditability but do not choose or validate a downstream statistical estimator.",
            "API03",
        ),
        (
            "C05",
            "The analysis software/environment identity is explicitly recorded.",
            "software_environment.json",
            "reviewer handoff metadata",
            "bundled_teaching_derivative",
            True,
            "fully_rerunnable",
            "synthetic_demo_not_empirical_evidence",
            "Software identity supports reproducibility; it is not scientific validation evidence.",
            "API01",
        ),
        (
            "C06",
            "Archive limitations and evidence boundaries are visible to the reviewer.",
            "04_limitations_register.csv",
            "reviewer handoff metadata",
            "bundled_teaching_derivative",
            True,
            "fully_rerunnable",
            "synthetic_demo_not_empirical_evidence",
            "A complete limitations register does not remove the limitations it records.",
            "API08",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=(
            "claim_id",
            "reported_statement_template",
            "artifact_reference",
            "artifact_role",
            "artifact_access",
            "bundled_by_default",
            "reproducibility_class",
            "evidence_classification",
            "interpretation_boundary",
            "api_route_id",
        ),
    )


def _rerun_plan() -> pd.DataFrame:
    rows = [
        (
            "R01",
            "reviewer handoff teaching bundle",
            "fully_rerunnable",
            "python examples/14_worked_reviewer_replication_bundle.py --output-dir worked-reviewer-replication-bundle",
            "base Python environment with pandas; no external study data",
            "none",
            "API01;API08",
        ),
        (
            "R02",
            "synthetic research evidence bundle",
            "fully_rerunnable",
            "python examples/09_worked_research_evidence_bundle.py --output-dir worked-research-evidence-bundle",
            "GazeForge checkout matching the recorded software identity",
            "none; demonstration inputs are synthetic",
            "API01;API02;API03;API04;API06",
        ),
        (
            "R03",
            "empirical source import and reviewed analysis derivative",
            "rerunnable_with_private_input",
            "python <archived-study-script> --stage source-to-analysis",
            "exact private/restricted source files + study configuration + environment lock",
            "source data are not bundled by this teaching example",
            "API01;API02;API03;API04",
        ),
        (
            "R04",
            "restricted benchmark/source-dependent validation",
            "inspectable_only",
            "inspect archived report/certificate/fingerprints and obtain source independently if authorised",
            "verified report/certificate + source rights/access documentation",
            "technical packaging ability does not override licence/privacy restrictions",
            "API08;API09",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=(
            "rerun_id",
            "stage",
            "reproducibility_class",
            "command_or_action",
            "prerequisites",
            "data_access_note",
            "api_route_ids",
        ),
    )


def _checklist() -> pd.DataFrame:
    rows = [
        ("Q01", "reading_order", "Start-here file names the recommended review order.", "pass_for_demo"),
        ("Q02", "claim_traceability", "Every claim row names an artifact reference and interpretation boundary.", "pass_for_demo"),
        ("Q03", "software_identity", "Software/environment requirements are explicit.", "pass_for_demo"),
        ("Q04", "data_access", "Private/restricted inputs are marked as prerequisites rather than bundled.", "pass_for_demo"),
        ("Q05", "denominators", "Study archives should expose retained/excluded denominator flow.", "study_archive_required"),
        ("Q06", "hashes", "Bundled reviewer derivatives have SHA-256 identities.", "pass_for_demo"),
        ("Q07", "limitations", "Limitations and scientific boundaries travel with the handoff.", "pass_for_demo"),
        ("Q08", "independent_validation", "Reproducibility is kept separate from scientific validity.", "pass_for_demo"),
    ]
    return pd.DataFrame(rows, columns=("check_id", "topic", "question", "demo_status"))


def _limitations() -> pd.DataFrame:
    rows = [
        ("L01", "reproducibility_vs_validity", "A deterministic rerun or matching hash does not establish device, measurement, model, construct, causal, or external validity.", "always_apply"),
        ("L02", "private_data", "Private participant/source data are not bundled by default; authorised access remains a prerequisite for empirical reruns.", "study_specific"),
        ("L03", "licensing", "Source licensing and redistribution rights are independent from technical ability to copy or package a file.", "study_specific"),
        ("L04", "sampling", "Derived/resampled evidence must not be described as native-device or native-rate validation.", "always_apply"),
        ("L05", "constructs", "Gaze/AOI/scanpath outputs do not by themselves establish trust, persuasion, comprehension, emotion, intent, or diagnosis.", "always_apply"),
        ("L06", "environment", "A development checkout requires an exact commit and dependency/environment record; 'latest' is not a reproducible software identity.", "always_apply"),
        ("L07", "reviewer_access", "An inspectable archive can support audit without being fully rerunnable when lawful source access is unavailable.", "study_specific"),
    ]
    return pd.DataFrame(rows, columns=("limitation_id", "area", "limitation", "scope"))


def _api_routes() -> pd.DataFrame:
    rows = [
        ("API01", "canonical schema and source handoff", "api-reference.md#schema"),
        ("API02", "quality-control evidence", "api-reference.md#quality-control"),
        ("API03", "eye-event construction", "api-reference.md#eye-events"),
        ("API04", "static semantic AOIs", "api-reference.md#semantic-aois"),
        ("API05", "dynamic semantic AOIs", "api-reference.md#dynamic-aois"),
        ("API06", "semantic scanpaths", "api-reference.md#scanpaths"),
        ("API07", "visual diagnostics", "api-reference.md#visual-diagnostics"),
        ("API08", "validation/generalisation identity", "api-reference.md#structural-validation-scope"),
        ("API09", "sampling sensitivity", "api-reference.md#sampling-sensitivity"),
    ]
    return pd.DataFrame(rows, columns=("api_route_id", "purpose", "documentation_anchor"))


def _software_environment() -> dict[str, Any]:
    return {
        "software_name": "GazeForge",
        "immutable_release_reference": "0.1.0a1",
        "immutable_release_doi": "10.5281/zenodo.22650013",
        "development_use_rule": "record the exact full 40-character Git commit",
        "python_requirement": ">=3.10",
        "environment_lock_required_for_empirical_archive": True,
        "demo_runtime_version_embedded": False,
        "reason_demo_runtime_not_embedded": "keep the teaching bundle byte-deterministic across supported runtimes",
        "evidence_classification": EVIDENCE_CLASSIFICATION,
    }


def _start_here() -> str:
    return """# Reviewer start here

This deterministic teaching handoff is **not an empirical study archive**. It shows
how a reviewer/replicator-facing bundle can expose reading order, artifact identity,
rerun prerequisites, data-access constraints, API routes, and limitations without
claiming that reproducibility equals scientific validity.

## Recommended reading order

1. `replication_manifest.json` — scope, safeguards, and output inventory.
2. `01_claim_artifact_matrix.csv` — reported statement → artifact → evidence boundary.
3. `02_rerun_plan.csv` — command/action, prerequisite, and reproducibility class.
4. `artifact_hash_ledger.csv` — SHA-256 identities for bundled teaching derivatives.
5. `03_reproducibility_checklist.csv` — reviewer questions and archive requirements.
6. `04_limitations_register.csv` — limitations that must travel with the archive.
7. `05_api_route_map.csv` — exact public documentation anchors.
8. `software_environment.json` — software/environment identity rules.

## Reproducibility classes

- `fully_rerunnable`: no restricted/private study input is needed.
- `rerunnable_with_private_input`: code/route can be rerun only after authorised input access.
- `inspectable_only`: archived evidence can be audited, but source rights/access prevent a default rerun.

Private/restricted empirical source data are **not bundled by default**. Technical
ability to package a file does not override privacy, consent, licence, or redistribution
constraints. Matching hashes, deterministic reruns, or complete documentation do not
establish device, measurement, model, construct, causal, or external validity.
"""


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    claim_matrix = _claim_artifact_matrix()
    rerun_plan = _rerun_plan()
    checklist = _checklist()
    limitations = _limitations()
    api_routes = _api_routes()

    tables = {
        "01_claim_artifact_matrix.csv": claim_matrix,
        "02_rerun_plan.csv": rerun_plan,
        "03_reproducibility_checklist.csv": checklist,
        "04_limitations_register.csv": limitations,
        "05_api_route_map.csv": api_routes,
    }
    for name, table in tables.items():
        table.to_csv(output_dir / name, index=False)

    _write_json(output_dir / "software_environment.json", _software_environment())
    (output_dir / "reviewer_start_here.md").write_text(_start_here(), encoding="utf-8")

    if not set(claim_matrix["reproducibility_class"]) <= set(REPRODUCIBILITY_CLASSES):
        raise RuntimeError("Unexpected claim reproducibility class.")
    if not set(rerun_plan["reproducibility_class"]) <= set(REPRODUCIBILITY_CLASSES):
        raise RuntimeError("Unexpected rerun-plan reproducibility class.")
    private_rows = rerun_plan["reproducibility_class"] == "rerunnable_with_private_input"
    if rerun_plan.loc[private_rows, "data_access_note"].str.contains("bundled", case=False).eq(False).any():
        raise RuntimeError("Private-input rows must state whether data are bundled.")
    if bool(claim_matrix.loc[claim_matrix["artifact_access"] == "study_archive_required", "bundled_by_default"].any()):
        raise RuntimeError("Study/private artifacts must not be bundled by this teaching example.")
    if claim_matrix["evidence_classification"].ne(EVIDENCE_CLASSIFICATION).any():
        raise RuntimeError("Claim rows must retain the demo evidence classification.")
    if claim_matrix["interpretation_boundary"].astype(str).str.strip().eq("").any():
        raise RuntimeError("Every claim row requires an interpretation boundary.")

    hash_targets = [
        output_dir / "01_claim_artifact_matrix.csv",
        output_dir / "02_rerun_plan.csv",
        output_dir / "03_reproducibility_checklist.csv",
        output_dir / "04_limitations_register.csv",
        output_dir / "05_api_route_map.csv",
        output_dir / "software_environment.json",
        output_dir / "reviewer_start_here.md",
    ]
    hash_ledger = pd.DataFrame(
        [
            {
                "filename": path.name,
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
                "artifact_scope": "bundled_teaching_derivative",
            }
            for path in hash_targets
        ]
    )
    hash_ledger.to_csv(output_dir / "artifact_hash_ledger.csv", index=False)

    _write_json(
        output_dir / "replication_manifest.json",
        {
            "example": "14_worked_reviewer_replication_bundle",
            "evidence_classification": EVIDENCE_CLASSIFICATION,
            "reproducibility_classes": list(REPRODUCIBILITY_CLASSES),
            "claim_count": int(len(claim_matrix)),
            "rerun_route_count": int(len(rerun_plan)),
            "limitation_count": int(len(limitations)),
            "api_route_count": int(len(api_routes)),
            "hash_ledger_sha256": _sha256(output_dir / "artifact_hash_ledger.csv"),
            "private_or_restricted_inputs_bundled": False,
            "source_artifact_modified": False,
            "qc_artifact_modified": False,
            "review_artifact_modified": False,
            "analysis_artifact_modified": False,
            "missing_converted_to_zero": False,
            "device_validity_claim_created": False,
            "native_rate_validity_claim_created": False,
            "measurement_validity_claim_created": False,
            "model_validity_claim_created": False,
            "construct_validity_claim_created": False,
            "causal_validity_claim_created": False,
            "external_validity_claim_created": False,
            "psychological_state_claim_created": False,
            "reproducibility_equated_with_validity": False,
            "scientific_boundary": (
                "Reviewer inspectability, deterministic reruns, and matching hashes support "
                "auditability; they do not establish scientific validity or override data-access rights."
            ),
        },
    )

    print("Worked reviewer/replication bundle complete")
    print(f"Output directory: {output_dir}")
    print(f"Claim routes: {len(claim_matrix)}")
    print("Private/restricted inputs bundled: no")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a deterministic reviewer/replicator handoff teaching bundle."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-reviewer-replication-bundle"),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
