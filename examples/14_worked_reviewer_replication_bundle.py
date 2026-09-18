"""Build a deterministic reviewer/replication handoff bundle.

Reviewer-facing metadata only: no new scientific analysis, private data,
validity claim, or latent-state inference is created.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

EVIDENCE = "synthetic_demo_not_empirical_evidence"
REPRO_CLASSES = {
    "fully_rerunnable_demo",
    "rerunnable_with_private_input",
    "inspectable_only",
}
OUTPUTS = (
    "01_claim_artifact_matrix.csv",
    "02_rerun_plan.csv",
    "03_reproducibility_checklist.csv",
    "04_limitations_register.csv",
    "05_api_route_map.csv",
    "software_environment.json",
    "reviewer_start_here.md",
    "artifact_hash_ledger.csv",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _claims() -> pd.DataFrame:
    rows = [
        (
            "C01",
            "QC flags remained review evidence rather than automatic exclusions.",
            "03_pre_review_qc_samples.csv; 06_trial_review_ledger.csv",
            "rerunnable_with_private_input",
            "api-reference.md#quality-control",
            EVIDENCE,
            "study_archive_required",
            False,
            "reproducible review rule != validated review rule",
        ),
        (
            "C02",
            "AOI/scanpath outputs describe observable gaze structure.",
            "12_fixation_aoi_assignments.csv; 13_semantic_scanpaths.csv",
            "rerunnable_with_private_input",
            "api-reference.md#semantic-aois; api-reference.md#scanpaths",
            EVIDENCE,
            "study_archive_required",
            False,
            "observable gaze != trust, persuasion, comprehension, or intent",
        ),
        (
            "C03",
            "Reporting references frozen evidence without rewriting analysis artifacts.",
            "artifact_citation_table.csv; reporting_manifest.json",
            "fully_rerunnable_demo",
            "reporting-clinic.md",
            EVIDENCE,
            "bundled_teaching_derivative",
            True,
            "clearer prose or hashes do not strengthen the evidence class",
        ),
        (
            "C04",
            "This reviewer bundle is a deterministic software-demonstration handoff.",
            "artifact_hash_ledger.csv; replication_manifest.json",
            "fully_rerunnable_demo",
            "reviewer-replication-handoff.md",
            EVIDENCE,
            "bundled_teaching_derivative",
            True,
            "reproducible software behaviour is not empirical validation evidence",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "claim_id",
            "statement",
            "supporting_artifact",
            "reproducibility_class",
            "api_or_guide_route",
            "evidence_classification",
            "artifact_access",
            "bundled_by_default",
            "interpretation_boundary",
        ],
    )

def _rerun_plan() -> pd.DataFrame:
    rows = [
        (
            1,
            "evidence",
            "python examples/09_worked_research_evidence_bundle.py",
            "fully_rerunnable_demo",
            False,
        ),
        (
            2,
            "analysis handoff",
            "python examples/10_worked_analysis_handoff.py --no-figures",
            "fully_rerunnable_demo",
            False,
        ),
        (
            3,
            "reporting",
            "python examples/11_worked_manuscript_reporting_bundle.py",
            "fully_rerunnable_demo",
            False,
        ),
        (
            4,
            "interpretation",
            "python examples/12_worked_measurement_interpretation_audit.py",
            "fully_rerunnable_demo",
            False,
        ),
        (
            5,
            "private study rerun",
            "python <study-script> --source <authorized-input>",
            "rerunnable_with_private_input",
            True,
        ),
        (
            6,
            "restricted archive review",
            "inspect permitted artifacts and manifests",
            "inspectable_only",
            True,
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "step",
            "purpose",
            "command_or_action",
            "reproducibility_class",
            "external_or_private_input_required",
        ],
    )


def _checklist() -> pd.DataFrame:
    rows = [
        ("R01", "software/version/commit identity recorded", "demonstrated_in_worked_example"),
        ("R02", "source access/licensing declared", "requires_study_specific_evidence"),
        ("R03", "claim-supporting artifacts and hashes named", "demonstrated_in_worked_example"),
        ("R04", "denominators/exclusions reconcile", "requires_study_specific_evidence"),
        ("R05", "missing/zero/censored states remain distinct", "requires_study_specific_evidence"),
        (
            "R06",
            "reproducibility separated from scientific validity",
            "demonstrated_in_worked_example",
        ),
    ]
    return pd.DataFrame(rows, columns=["check_id", "check", "status"])


def _limitations() -> pd.DataFrame:
    rows = [
        ("synthetic demo", "not empirical performance or validation evidence"),
        ("reproducibility", "matching hashes do not establish scientific validity"),
        ("restricted inputs", "technical packagability does not override privacy/licensing"),
        ("measurement", "gaze observables do not automatically measure latent constructs"),
        ("sampling", "observed/derived rate does not prove native-device validity"),
    ]
    return pd.DataFrame(rows, columns=["limitation", "reporting_implication"])


def _api_routes() -> pd.DataFrame:
    rows = [
        ("schema", "api-reference.md#schema"),
        ("quality control", "api-reference.md#quality-control"),
        ("eye events", "api-reference.md#eye-events"),
        ("semantic AOIs", "api-reference.md#semantic-aois"),
        ("dynamic AOIs", "api-reference.md#dynamic-aois"),
        ("scanpaths", "api-reference.md#scanpaths"),
        ("visual diagnostics", "api-reference.md#visual-diagnostics"),
        ("structural validation", "api-reference.md#structural-validation-scope"),
        ("sampling sensitivity", "api-reference.md#sampling-sensitivity"),
    ]
    return pd.DataFrame(rows, columns=["layer", "api_route"])

def _readme() -> str:
    return """# Reviewer / replicator start here

This is a deterministic reviewer-facing software demonstration. It is
`synthetic_demo_not_empirical_evidence`. It is **not empirical validation evidence**
and does not contain private/restricted study data.

Read `replication_manifest.json` first, then the claim-artifact matrix, rerun plan,
reproducibility checklist, limitations register, API route map, and hash ledger.

Reproducibility classes are `fully_rerunnable_demo`,
`rerunnable_with_private_input`, and `inspectable_only`. Do not treat matching
hashes, deterministic reruns, or a complete archive as device/model/measurement/
construct/causal/external validity. Do not infer a latent state or other latent
psychological construct from gaze-derived observables. Privacy and licensing remain
separate from technical ability to package a file.
"""


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = {
        "01_claim_artifact_matrix.csv": _claims(),
        "02_rerun_plan.csv": _rerun_plan(),
        "03_reproducibility_checklist.csv": _checklist(),
        "04_limitations_register.csv": _limitations(),
        "05_api_route_map.csv": _api_routes(),
    }
    for name, table in tables.items():
        table.to_csv(output_dir / name, index=False)

    env = {
        "example": "14_worked_reviewer_replication_bundle",
        "evidence_classification": EVIDENCE,
        "gazeforge_release_identity": "0.1.0a1",
        "development_analysis_requires_full_commit_sha": True,
        "supported_python_matrix": ["3.10", "3.12", "3.14"],
        "private_or_restricted_source_bundled": False,
    }
    _write_json(output_dir / "software_environment.json", env)
    (output_dir / "reviewer_start_here.md").write_text(_readme(), encoding="utf-8")

    claims = tables["01_claim_artifact_matrix.csv"]
    rerun = tables["02_rerun_plan.csv"]
    if not set(claims["reproducibility_class"]) <= REPRO_CLASSES:
        raise RuntimeError("Unexpected reproducibility class in claim matrix.")
    if set(rerun["reproducibility_class"]) != REPRO_CLASSES:
        raise RuntimeError("Rerun plan must demonstrate all reproducibility classes.")
    private = rerun.loc[rerun["purpose"] == "private study rerun"].iloc[0]
    if not bool(private["external_or_private_input_required"]):
        raise RuntimeError("Private study rerun must require authorized external input.")
    if claims["evidence_classification"].ne(EVIDENCE).any():
        raise RuntimeError("Every claim row must retain the demo evidence classification.")
    if claims["interpretation_boundary"].astype(str).str.strip().eq("").any():
        raise RuntimeError("Every claim row must retain an interpretation boundary.")
    private_claims = claims["artifact_access"] == "study_archive_required"
    if claims.loc[private_claims, "bundled_by_default"].astype(bool).any():
        raise RuntimeError("Study/private artifacts must not be bundled by default.")

    targets = [output_dir / name for name in OUTPUTS if name != "artifact_hash_ledger.csv"]
    ledger = pd.DataFrame(
        [
            {
                "filename": path.name,
                "sha256": _sha256(path),
                "verification_scope": "reviewer_bundle_file_identity_only",
                "scientific_validity_created": False,
            }
            for path in targets
        ]
    )
    ledger.to_csv(output_dir / "artifact_hash_ledger.csv", index=False)

    manifest_targets = [output_dir / name for name in OUTPUTS]
    manifest = {
        "example": "14_worked_reviewer_replication_bundle",
        "evidence_classification": EVIDENCE,
        "reproducibility_classes": sorted(REPRO_CLASSES),
        "bundle_file_hashes_sha256": {p.name: _sha256(p) for p in manifest_targets},
        "scientific_analysis_performed": False,
        "private_or_restricted_source_bundled": False,
        "source_artifact_modified": False,
        "qc_artifact_modified": False,
        "review_artifact_modified": False,
        "analysis_artifact_modified": False,
        "missing_converted_to_zero": False,
        "empirical_validation_claim_created": False,
        "device_validity_claim_created": False,
        "native_rate_validity_claim_created": False,
        "model_validity_claim_created": False,
        "measurement_or_construct_validity_claim_created": False,
        "causal_claim_created": False,
        "external_validity_claim_created": False,
        "psychological_state_claim_created": False,
        "reproducibility_equals_validity_claim_created": False,
    }
    _write_json(output_dir / "replication_manifest.json", manifest)

    print("Worked reviewer/replication bundle complete")
    print(f"Output directory: {output_dir}")
    print("Evidence classification: synthetic_demo_not_empirical_evidence")
    print("Private/restricted source bundled: no")
    print("Scientific analysis performed: no")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a deterministic reviewer/replication handoff bundle."
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
