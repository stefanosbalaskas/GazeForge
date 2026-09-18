"""Build a deterministic manuscript/reporting bundle from the worked evidence bundle.

This example deliberately performs no new scientific analysis. It reuses
examples/09_worked_research_evidence_bundle.py, fingerprints the upstream evidence
before and after reporting, and writes only reporting derivatives.

The complete workflow is synthetic/demo material. It is not empirical validation
evidence and does not establish tracker/device validity, native-60-Hz validity,
Gazepoint/GP3 validity, event-model validity, AOI construct validity, measurement
validity, or latent psychological states.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
from pathlib import Path
from typing import Any

import pandas as pd

from gazeforge import __version__

EVIDENCE_CLASSIFICATION = "synthetic_demo_not_empirical_evidence"
UPSTREAM_EXAMPLE = Path(__file__).with_name("09_worked_research_evidence_bundle.py")
REPORTING_FILES = (
    "methods_record.json",
    "denominator_flow.csv",
    "artifact_citation_table.csv",
    "reporting_boundaries.json",
    "software_identity.json",
    "methods_example.md",
    "results_example.md",
    "archive_readme.md",
)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_directory(path: Path) -> dict[str, str]:
    return {
        item.relative_to(path).as_posix(): _sha256_file(item)
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def _ensure_evidence_bundle(evidence_dir: Path) -> None:
    manifest = evidence_dir / "workflow_manifest.json"
    if manifest.is_file():
        existing = _read_json(manifest)
        if existing.get("evidence_classification") != EVIDENCE_CLASSIFICATION:
            raise ValueError(
                "The supplied evidence bundle is not the worked synthetic/demo bundle."
            )
        return

    if evidence_dir.exists() and any(evidence_dir.iterdir()):
        raise ValueError(
            "Evidence directory is non-empty but has no workflow_manifest.json; "
            "refusing to overwrite an ambiguous upstream directory."
        )

    namespace = runpy.run_path(str(UPSTREAM_EXAMPLE))
    run_upstream = namespace.get("run")
    if not callable(run_upstream):
        raise RuntimeError("Could not load run() from the worked evidence-bundle example.")
    run_upstream(evidence_dir)


def _denominator_flow(manifest: dict[str, Any]) -> pd.DataFrame:
    source_rows = int(manifest["source_rows"])
    qc_rows = int(manifest["pre_review_qc_rows"])
    primary_rows = int(manifest["primary_analysis_rows"])
    trial_denominator = int(manifest["trial_denominator"])
    retained_trials = int(manifest["retained_trials"])
    excluded_trials = int(manifest["excluded_trials"])

    return pd.DataFrame(
        [
            {
                "stage": "source_samples",
                "unit": "sample",
                "denominator": source_rows,
                "retained": source_rows,
                "excluded": 0,
                "source_artifact": "01_source_tracker_export.csv",
                "interpretation": "immutable tracker-shaped demo source",
            },
            {
                "stage": "pre_review_qc_samples",
                "unit": "sample",
                "denominator": qc_rows,
                "retained": qc_rows,
                "excluded": 0,
                "source_artifact": "03_pre_review_qc_samples.csv",
                "interpretation": "QC evidence before reviewed exclusions",
            },
            {
                "stage": "primary_analysis_samples",
                "unit": "sample",
                "denominator": qc_rows,
                "retained": primary_rows,
                "excluded": qc_rows - primary_rows,
                "source_artifact": "07_primary_analysis_rows.csv",
                "interpretation": "separate derivative after reviewed trial decisions",
            },
            {
                "stage": "reviewed_trials",
                "unit": "trial",
                "denominator": trial_denominator,
                "retained": retained_trials,
                "excluded": excluded_trials,
                "source_artifact": "06_trial_review_ledger.csv",
                "interpretation": "review decisions under teaching criteria",
            },
        ]
    )


def _artifact_citation_table(
    artifact_index: pd.DataFrame,
    upstream_hashes: dict[str, str],
) -> pd.DataFrame:
    section_by_layer = {
        "source": "Methods: data/source",
        "canonical": "Methods: canonicalisation",
        "qc": "Methods: QC",
        "review": "Methods: review/exclusions",
        "analysis": "Methods/results: observable analysis outputs",
        "provenance": "Supplement/archive: provenance",
        "reporting": "Supplement/archive: reporting metadata",
    }
    table = artifact_index.copy()
    table["sha256"] = table["filename"].map(upstream_hashes)
    table["manuscript_or_archive_location"] = table["layer"].map(section_by_layer)
    table["citation_note"] = (
        "Cite/report only for the role and evidence class recorded in this row."
    )
    return table[
        [
            "filename",
            "layer",
            "unit",
            "sha256",
            "manuscript_or_archive_location",
            "purpose",
            "evidence_classification",
            "cannot_establish",
            "citation_note",
        ]
    ]


def _methods_markdown(
    source_contract: dict[str, Any],
    plan: dict[str, Any],
    manifest: dict[str, Any],
    analysis_commit: str,
) -> str:
    labels = ", ".join(plan["aoi_labels"])
    return f"""# Worked Methods example

> **Evidence boundary:** this is deterministic synthetic/demo reporting material and
> is **not empirical validation evidence**. Replace every study-specific detail with
> the actual acquisition, protocol, review, and analysis record before manuscript use.

A tracker-shaped synthetic source was adapted to the canonical GazeForge schema
using explicitly declared participant, trial, timestamp, gaze-coordinate, pupil,
and validity fields. Source timestamps were expressed in
{source_contract["timestamp_unit"]}, coordinates were
{source_contract["coordinate_basis"]}, and the demonstration display geometry
was {source_contract["screen_size_px"][0]} × {source_contract["screen_size_px"][1]}
pixels. The nominal demonstration rate was {source_contract["nominal_rate_hz"]:.1f}
Hz. The observed timestamp cadence was retained as a stream diagnostic and was not
treated as proof of native hardware sampling rate.

Quality-control outputs were preserved before review.
**QC flags were not automatic exclusions.**
Trial-level review used the explicitly recorded demonstration
criteria in 04_decision_criteria.csv; {manifest["excluded_trials"]} of
{manifest["trial_denominator"]} trials were excluded after review, leaving
{manifest["retained_trials"]} retained trials. Reviewed decisions were applied to a
separate 07_primary_analysis_rows.csv derivative containing
{manifest["primary_analysis_rows"]} of {manifest["pre_review_qc_rows"]} pre-review
sample rows.

Eye events were generated using the transparent
{plan["event_method"]["algorithm"]} demonstration baseline with a
{plan["event_method"]["velocity_threshold_px_s"]:.1f} px/s velocity threshold. This
value is an example setting, **not a universal physiological cutoff**. AOIs were
{plan["aoi_source"]} and labelled {labels}. Semantic scanpaths summarized
observable AOI sequences; they were not interpreted as diagnoses, emotions,
trust, persuasion, comprehension, intent, or other latent psychological states.

The reporting bundle records GazeForge version {__version__} and development
analysis commit {analysis_commit}. For real development-checkout analyses, a
full commit SHA should replace any demonstration placeholder.
"""


def _results_markdown(manifest: dict[str, Any]) -> str:
    return f"""# Worked Results example

This reporting example contains **descriptive workflow accounting only**. No
inferential statistical test, effect estimate, causal contrast, or psychological
state inference is created.

The synthetic/demo workflow reviewed {manifest["trial_denominator"]} trials.
{manifest["excluded_trials"]} trials met the recorded teaching exclusion criteria
after review and {manifest["retained_trials"]} were retained. The pre-review QC
table contained {manifest["pre_review_qc_rows"]} sample rows; the separate
primary-analysis derivative contained {manifest["primary_analysis_rows"]} rows.

Transparent event, AOI-assignment, and semantic-scanpath artifacts were generated
for the reviewed analysis derivative. These outputs demonstrate an auditable
software workflow and **are not empirical validation evidence**. They do not
establish tracker/device validity, native-60-Hz validity, Gazepoint/GP3 validity,
event-model validity, AOI construct validity, measurement validity, or an effect on
trust, persuasion, emotion, comprehension, diagnosis, or intent.
"""


def _archive_readme(evidence_dir_name: str) -> str:
    return f"""# Worked manuscript/reporting bundle

This directory contains reporting derivatives generated from the deterministic
GazeForge research evidence bundle in {evidence_dir_name}.

## Read in this order

1. reporting_manifest.json — upstream identity, invariants, and reporting hashes.
2. methods_record.json — structured Methods facts.
3. denominator_flow.csv — sample/trial denominator reconciliation.
4. artifact_citation_table.csv — upstream file identity and manuscript/archive role.
5. reporting_boundaries.json — safe/unsafe interpretation boundaries.
6. software_identity.json — software and development-commit identity.
7. methods_example.md and results_example.md — worked wording examples.

## Invariant

The reporting step does not edit, filter, relabel, exclude, or otherwise modify
the upstream evidence bundle. The manifest records SHA-256 hashes before and after
report generation and requires exact equality.

## Evidence boundary

This is synthetic/demo material and is **not empirical validation evidence**.
Reporting quality cannot upgrade the strength of the underlying scientific
evidence.
"""


def run(
    output_dir: Path,
    *,
    evidence_dir: Path,
    analysis_commit: str,
) -> None:
    _ensure_evidence_bundle(evidence_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    upstream_before = _hash_directory(evidence_dir)
    manifest = _read_json(evidence_dir / "workflow_manifest.json")
    source_contract = _read_json(evidence_dir / "source_contract.json")
    plan = _read_json(evidence_dir / "analysis_plan.json")
    artifact_index = pd.read_csv(evidence_dir / "artifact_index.csv")

    if manifest["evidence_classification"] != EVIDENCE_CLASSIFICATION:
        raise ValueError("Unexpected upstream evidence classification.")

    denominator_flow = _denominator_flow(manifest)
    denominator_flow.to_csv(output_dir / "denominator_flow.csv", index=False)

    citation_table = _artifact_citation_table(artifact_index, upstream_before)
    citation_table.to_csv(output_dir / "artifact_citation_table.csv", index=False)

    methods_record = {
        "purpose": "worked manuscript/reporting bundle",
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "upstream_manifest": "workflow_manifest.json",
        "upstream_evidence_directory": evidence_dir.name,
        "source": {
            "source_format": source_contract["source_format"],
            "timestamp_unit": source_contract["timestamp_unit"],
            "coordinate_basis": source_contract["coordinate_basis"],
            "screen_size_px": source_contract["screen_size_px"],
            "nominal_rate_hz": source_contract["nominal_rate_hz"],
            "observed_cadence_hz": source_contract["observed_cadence_hz"],
            "observed_cadence_is_hardware_rate_proof": False,
        },
        "qc_and_review": {
            "qc_flags_are_automatic_exclusions": False,
            "criteria_artifact": "04_decision_criteria.csv",
            "review_ledger": "06_trial_review_ledger.csv",
            "trial_denominator": manifest["trial_denominator"],
            "excluded_trials": manifest["excluded_trials"],
            "retained_trials": manifest["retained_trials"],
            "pre_review_sample_rows": manifest["pre_review_qc_rows"],
            "primary_analysis_sample_rows": manifest["primary_analysis_rows"],
        },
        "event_method": plan["event_method"],
        "event_threshold_is_universal_physiological_cutoff": False,
        "aoi_source": plan["aoi_source"],
        "aoi_labels": plan["aoi_labels"],
        "scanpath_interpretation": (
            "observable AOI sequence structure; not a latent psychological state"
        ),
        "analysis_commit": analysis_commit,
    }
    _write_json(output_dir / "methods_record.json", methods_record)

    reporting_boundaries = {
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "safe_statements": [
            "QC flags were treated as review evidence rather than automatic exclusions.",
            "Observed timestamp cadence was reported separately from native hardware rate.",
            "I-VT was used as a transparent demonstration baseline with an explicit threshold.",
            "AOIs were researcher-defined and semantic scanpaths represented observable sequences.",
            "The reporting bundle preserves exact upstream file hashes.",
        ],
        "do_not_claim": [
            "successful import validates the eye tracker",
            "the demonstration proves native 60 Hz validity",
            "the example validates Gazepoint or GP3",
            "the I-VT teaching threshold is a universal physiological cutoff",
            "AOI membership proves a psychological construct",
            "scanpaths reveal trust, persuasion, emotion, comprehension, diagnosis, or intent",
            "synthetic/demo execution is empirical validation evidence",
        ],
        "device_validity_claim_created": False,
        "native_60hz_validity_claim_created": False,
        "gazepoint_gp3_validity_claim_created": False,
        "event_model_validity_claim_created": False,
        "measurement_validity_claim_created": False,
        "psychological_state_claim_created": False,
        "inferential_effect_claim_created": False,
    }
    _write_json(output_dir / "reporting_boundaries.json", reporting_boundaries)

    software_identity = {
        "gazeforge_version": __version__,
        "analysis_commit": analysis_commit,
        "development_commit_required_for_real_development_analysis": True,
        "example_script": "10_worked_manuscript_reporting_bundle.py",
        "upstream_example": "09_worked_research_evidence_bundle.py",
        "evidence_classification": EVIDENCE_CLASSIFICATION,
    }
    _write_json(output_dir / "software_identity.json", software_identity)

    (output_dir / "methods_example.md").write_text(
        _methods_markdown(source_contract, plan, manifest, analysis_commit),
        encoding="utf-8",
    )
    (output_dir / "results_example.md").write_text(
        _results_markdown(manifest),
        encoding="utf-8",
    )
    (output_dir / "archive_readme.md").write_text(
        _archive_readme(evidence_dir.name),
        encoding="utf-8",
    )

    upstream_after = _hash_directory(evidence_dir)
    if upstream_before != upstream_after:
        raise RuntimeError("Upstream evidence bundle changed during reporting.")

    reporting_hashes = {
        name: _sha256_file(output_dir / name)
        for name in REPORTING_FILES
    }
    reporting_manifest = {
        "example": "10_worked_manuscript_reporting_bundle",
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "gazeforge_version": __version__,
        "analysis_commit": analysis_commit,
        "upstream_evidence_directory": evidence_dir.name,
        "upstream_before_sha256": upstream_before,
        "upstream_after_sha256": upstream_after,
        "upstream_unchanged": True,
        "reporting_artifact_hashes_sha256": reporting_hashes,
        "trial_denominator": manifest["trial_denominator"],
        "excluded_trials": manifest["excluded_trials"],
        "retained_trials": manifest["retained_trials"],
        "pre_review_sample_rows": manifest["pre_review_qc_rows"],
        "primary_analysis_sample_rows": manifest["primary_analysis_rows"],
        "new_scientific_analysis_performed": False,
        "qc_or_exclusion_decisions_changed": False,
        "event_or_aoi_labels_changed": False,
        "inferential_statistics_created": False,
        "empirical_validity_claim_created": False,
        "device_validity_claim_created": False,
        "measurement_validity_claim_created": False,
        "psychological_state_claim_created": False,
        "scientific_boundary": (
            "Reporting derivatives preserve upstream evidence identity and cannot "
            "upgrade synthetic/demo evidence into empirical validation."
        ),
    }
    _write_json(output_dir / "reporting_manifest.json", reporting_manifest)

    print("Worked manuscript/reporting bundle complete")
    print(f"Evidence directory: {evidence_dir}")
    print(f"Reporting directory: {output_dir}")
    print("Upstream evidence unchanged: yes")
    print(
        "Evidence boundary: synthetic/demo reporting only; "
        "no new scientific analysis or empirical validity claim created."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a reporting bundle without modifying upstream evidence."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-manuscript-reporting-bundle"),
        help="Directory for reporting-only derivatives.",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=None,
        help=(
            "Existing worked evidence bundle. If omitted, a sibling "
            "'<output-dir>-evidence' bundle is created using example 09."
        ),
    )
    parser.add_argument(
        "--analysis-commit",
        default="DEMO_UNSPECIFIED_COMMIT",
        help=(
            "Exact development commit SHA for manuscript-facing use. "
            "The deterministic demo placeholder is intentionally not a real identity."
        ),
    )
    args = parser.parse_args()

    evidence_dir = (
        args.evidence_dir
        if args.evidence_dir is not None
        else args.output_dir.with_name(args.output_dir.name + "-evidence")
    )
    run(
        args.output_dir,
        evidence_dir=evidence_dir,
        analysis_commit=args.analysis_commit,
    )


if __name__ == "__main__":
    main()
