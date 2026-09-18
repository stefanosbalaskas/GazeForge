"""Build deterministic manuscript/reporting derivatives from the evidence-bundle example.

Synthetic/demo only. This script reuses the existing archive-facing evidence-bundle
example, verifies that its source/QC/review/analysis artifacts remain byte-identical,
and writes reporting derivatives only. It does not fit models, invent inferential
statistics, or upgrade software-demo output into empirical validation evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

EVIDENCE = "synthetic_demo_not_empirical_evidence"
ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_EXAMPLE = ROOT / "examples/09_worked_research_evidence_bundle.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_bundle(directory: Path) -> dict[str, str]:
    return {
        str(path.relative_to(directory)).replace("\\", "/"): _sha256(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _run_upstream(directory: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(UPSTREAM_EXAMPLE),
            "--output-dir",
            str(directory),
        ],
        check=True,
        cwd=ROOT,
    )


def _denominator_flow(manifest: dict[str, Any]) -> pd.DataFrame:
    rows = [
        ("source_sample_rows", int(manifest["source_rows"]), "sample", "source"),
        ("pre_review_qc_rows", int(manifest["pre_review_qc_rows"]), "sample", "qc"),
        ("trial_denominator", int(manifest["trial_denominator"]), "trial", "review"),
        ("excluded_trials", int(manifest["excluded_trials"]), "trial", "review"),
        ("retained_trials", int(manifest["retained_trials"]), "trial", "review"),
        ("primary_analysis_rows", int(manifest["primary_analysis_rows"]), "sample", "analysis"),
    ]
    out = pd.DataFrame(rows, columns=["stage", "n", "unit", "layer"])
    out["evidence_classification"] = EVIDENCE
    return out


def _artifact_citation_table(
    artifact_index: pd.DataFrame,
    hashes: dict[str, str],
) -> pd.DataFrame:
    out = artifact_index[
        [
            "filename",
            "layer",
            "unit",
            "purpose",
            "evidence_classification",
            "cannot_establish",
        ]
    ].copy()
    out["upstream_sha256"] = out["filename"].map(hashes)
    out["citation_role"] = (
        out["layer"].astype(str)
        + " artifact; cite exact filename/hash when material to the reported claim"
    )
    return out


def _methods_example(
    manifest: dict[str, Any],
    source_contract: dict[str, Any],
    analysis_plan: dict[str, Any],
) -> str:
    return f"""# Synthetic reporting example: Methods

This text is generated from a deterministic **software demonstration** and must be
adapted to the actual study record.

## Acquisition and import

The worked source used an explicitly mapped tracker-shaped export and preserved the
source separately from the canonical derivative. The declared nominal rate was
{source_contract["nominal_rate_hz"]:.1f} Hz and the timestamp-derived observed cadence
was {source_contract["observed_cadence_hz"]:.1f} Hz. Coordinates were interpreted as
{source_contract["coordinate_basis"]}. Agreement between nominal rate and observed
cadence in this demo is not proof of tracker or native-rate validity.

## Quality control and review

Automated quality-control output was retained as review evidence rather than treated
as an automatic exclusion oracle. The worked ledger contained
{manifest["trial_denominator"]} reviewed trials, of which
{manifest["excluded_trials"]} met the demonstration review criteria and
{manifest["retained_trials"]} were retained. The teaching thresholds are not universal
exclusion recommendations.

## Event, AOI, and scanpath derivation

The demonstration used {analysis_plan["event_method"]["algorithm"]} with the teaching
threshold {analysis_plan["event_method"]["velocity_threshold_px_s"]:.1f} px/s, followed
by {analysis_plan["aoi_source"]} AOIs and semantic scanpath derivation. Event labels,
AOI membership, and scanpath structure describe observable representations; they do
not directly establish
trust, persuasion, comprehension, emotion, diagnosis, preference, or intent.

## Software and evidence identity

The upstream bundle reports GazeForge version
`{manifest["gazeforge_version"]}`. A real manuscript should additionally report the
exact development commit when unreleased code is used. The complete worked record is
classified `{EVIDENCE}`.

## Evidence boundary

Successful deterministic execution demonstrates software composition and reporting
traceability. It does not establish device validity, native-60-Hz validity,
Gazepoint/GP3 validity, event-model validity, AOI construct validity, measurement
validity, causal effects, or psychological states.
"""


def _results_example(manifest: dict[str, Any]) -> str:
    return f"""# Synthetic reporting example: Results

This file contains **bookkeeping results from a software demonstration**, not empirical
study findings.

The worked archive preserved {manifest["source_rows"]} source-shaped sample rows and
{manifest["pre_review_qc_rows"]} pre-review QC rows. The review ledger contained
{manifest["trial_denominator"]} trials: {manifest["retained_trials"]} retained and
{manifest["excluded_trials"]} excluded under the demonstration criteria. The separate
primary-analysis derivative contained {manifest["primary_analysis_rows"]} sample rows.

These counts document the deterministic example workflow only. They are not estimates
of a substantive effect and do not support claims about persuasion, trust, emotion,
comprehension, diagnosis, preference, intent, tracker validity, or universal event/QC
thresholds.
"""


def _archive_readme() -> str:
    return """# Worked manuscript/reporting bundle

Read the files in this order:

1. `software_identity.json` — software/evidence identity.
2. `denominator_flow.csv` — source/QC/review/analysis counts.
3. `artifact_citation_table.csv` — exact upstream artifact names and SHA-256 hashes.
4. `methods_record.json` — structured reporting facts.
5. `reporting_boundaries.json` — claims the demo does not support.
6. `methods_example.md` and `results_example.md` — claim-safe teaching prose.
7. `reporting_manifest.json` — reporting-file hashes and upstream immutability check.

This directory contains reporting derivatives only. The upstream evidence bundle is
generated in a temporary directory, fingerprinted before and after reporting extraction,
and discarded. Reporting does not rewrite source, QC, review, or analysis artifacts.

All contents are `synthetic_demo_not_empirical_evidence`.
"""


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="gazeforge-reporting-upstream-") as temp:
        upstream = Path(temp) / "evidence-bundle"
        _run_upstream(upstream)
        hashes_before = _hash_bundle(upstream)

        manifest = json.loads(
            (upstream / "workflow_manifest.json").read_text(encoding="utf-8")
        )
        source_contract = json.loads(
            (upstream / "source_contract.json").read_text(encoding="utf-8")
        )
        analysis_plan = json.loads(
            (upstream / "analysis_plan.json").read_text(encoding="utf-8")
        )
        artifact_index = pd.read_csv(upstream / "artifact_index.csv")
        denominator_flow = _denominator_flow(manifest)
        citation_table = _artifact_citation_table(artifact_index, hashes_before)

        denominator_flow.to_csv(output_dir / "denominator_flow.csv", index=False)
        citation_table.to_csv(output_dir / "artifact_citation_table.csv", index=False)

        methods_record = {
            "evidence_classification": EVIDENCE,
            "source_rows": int(manifest["source_rows"]),
            "pre_review_qc_rows": int(manifest["pre_review_qc_rows"]),
            "trial_denominator": int(manifest["trial_denominator"]),
            "excluded_trials": int(manifest["excluded_trials"]),
            "retained_trials": int(manifest["retained_trials"]),
            "primary_analysis_rows": int(manifest["primary_analysis_rows"]),
            "qc_flags_are_automatic_exclusions": False,
            "nominal_rate_hz": float(source_contract["nominal_rate_hz"]),
            "observed_cadence_hz": float(source_contract["observed_cadence_hz"]),
            "coordinate_basis": source_contract["coordinate_basis"],
            "event_method": analysis_plan["event_method"],
            "aoi_source": analysis_plan["aoi_source"],
            "aoi_labels": analysis_plan["aoi_labels"],
            "scanpath_status": "descriptive_sequence_representation",
            "native_rate_claim_created": False,
            "inferential_statistics_created": False,
        }
        _write_json(output_dir / "methods_record.json", methods_record)

        software_identity = {
            "gazeforge_version": manifest["gazeforge_version"],
            "upstream_example": "09_worked_research_evidence_bundle.py",
            "upstream_example_identity": "09_worked_research_evidence_bundle",
            "development_commit_required_for_real_study": True,
            "development_commit_embedded_in_demo": False,
            "evidence_classification": EVIDENCE,
        }
        _write_json(output_dir / "software_identity.json", software_identity)

        reporting_boundaries = {
            "evidence_classification": EVIDENCE,
            "empirical_validation_claim_created": False,
            "device_validity_claim_created": False,
            "native_60hz_validity_claim_created": False,
            "gazepoint_gp3_validity_claim_created": False,
            "event_model_validity_claim_created": False,
            "aoi_construct_validity_claim_created": False,
            "measurement_validity_claim_created": False,
            "causal_claim_created": False,
            "psychological_state_claim_created": False,
            "universal_qc_threshold_claim_created": False,
            "universal_ivt_threshold_claim_created": False,
            "unsafe_examples_rejected": [
                "Successful import validated the tracker.",
                "QC automatically removed invalid observations.",
                "The demo validates GazeForge at native 60 Hz.",
                "The scanpath proves persuasion, trust, or comprehension.",
            ],
        }
        _write_json(output_dir / "reporting_boundaries.json", reporting_boundaries)

        (output_dir / "methods_example.md").write_text(
            _methods_example(manifest, source_contract, analysis_plan),
            encoding="utf-8",
        )
        (output_dir / "results_example.md").write_text(
            _results_example(manifest),
            encoding="utf-8",
        )
        (output_dir / "archive_readme.md").write_text(
            _archive_readme(),
            encoding="utf-8",
        )

        hashes_after = _hash_bundle(upstream)
        if hashes_before != hashes_after:
            raise RuntimeError("Reporting extraction modified the upstream evidence bundle.")

    reporting_files = sorted(
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.name != "reporting_manifest.json"
    )
    reporting_hashes = {path.name: _sha256(path) for path in reporting_files}
    _write_json(
        output_dir / "reporting_manifest.json",
        {
            "example": "11_worked_manuscript_reporting_bundle",
            "evidence_classification": EVIDENCE,
            "upstream_example": "09_worked_research_evidence_bundle.py",
            "upstream_artifacts_unchanged": True,
            "upstream_file_count": len(hashes_before),
            "upstream_hashes_sha256": hashes_before,
            "reporting_hashes_sha256": reporting_hashes,
            "source_artifact_modified": False,
            "qc_artifact_modified": False,
            "review_artifact_modified": False,
            "analysis_artifact_modified": False,
            "inferential_statistics_invented": False,
            "empirical_validity_claim_created": False,
            "psychological_state_claim_created": False,
        },
    )

    print("Worked manuscript/reporting bundle complete")
    print(f"Output directory: {output_dir}")
    print("Upstream source/QC/review/analysis artifacts unchanged: yes")
    print("Inferential statistics invented: no")
    print("Evidence boundary: synthetic/demo reporting derivatives only")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic reporting derivatives from the evidence-bundle demo."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-manuscript-reporting-bundle"),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
