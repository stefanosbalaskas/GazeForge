"""Validation for frozen Gaze-in-the-Wild secondary recovery-lead evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

PROBE_RECORD_TYPE = "gaze-in-wild-secondary-recovery-lead-provenance-probe-v1"
EVIDENCE_RECORD_TYPE = "gaze-in-wild-secondary-recovery-lead-evidence-v1"
EXPECTED_PROBE_FINGERPRINT = "89714d8ab6dee18385f27cf609e99bd857048898aee699cc38ee3c7a195ad9dd"
AWESOME_REPOSITORY = "https://github.com/Morris88826/awesome-eye-data"
AWESOME_COMMIT = "4c6a58ef5be5693e08adac33e8768a3b88ddf8ac"
EDIT_REPOSITORY = "https://github.com/George614/edit_distance_gpu"
EDIT_COMMIT = "01711b11556c271a7a15e566935089bb2775121b"
LABELLER_FILENAMES = [
    "LabellerIdx_7_PrIdx_1_TrIdx_1.mat",
    "LabellerIdx_8_PrIdx_1_TrIdx_1.mat",
]
_FALSE_BOUNDARY_KEYS = (
    "authoritative_original_dataset_copy_obtained",
    "original_distribution_identity_verified_from_secondary_leads",
    "dataset_file_rights_resolved",
    "analysis_use_authorized",
    "redistribution_authorized",
    "participant_mapping_verified",
    "complete_trial_task_mapping_verified",
    "sampling_cadence_verified",
    "independent_labeller_recoverability_verified",
    "empirical_evidence_eligible",
    "human_human_agreement_created",
    "participant_disjoint_model_validation_created",
    "cross_dataset_performance_created",
    "gp3_validity_created",
    "frozen_evidence_performance_claim_created",
)


@dataclass(frozen=True, slots=True)
class GazeInWildSecondaryLeadEvidence:
    """Validated binding between a live immutable-source probe and frozen review."""

    probe_fingerprint_sha256: str
    evidence_fingerprint_sha256: str


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _fingerprint(value: Mapping[str, Any], key: str) -> str:
    body = dict(value)
    body.pop(key, None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(value: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    path = Path(value)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"Could not load GIW secondary-lead evidence: {exc}") from exc
    if not isinstance(loaded, dict):
        raise BenchmarkIntegrityError("GIW secondary-lead evidence must be a JSON object.")
    return loaded


def validate_gaze_in_wild_secondary_lead_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the immutable-source probe while preserving a closed scientific gate."""

    probe = _load(probe_or_path)
    if probe.get("record_type") != PROBE_RECORD_TYPE or probe.get("dataset") != "Gaze-in-the-Wild":
        raise BenchmarkIntegrityError("GIW secondary-lead probe identity drifted.")
    observed = _fingerprint(probe, "probe_fingerprint_sha256")
    if probe.get("probe_fingerprint_sha256") != observed:
        raise BenchmarkIntegrityError("GIW secondary-lead probe fingerprint drifted.")
    if observed != EXPECTED_PROBE_FINGERPRINT:
        raise BenchmarkIntegrityError("GIW secondary-lead reviewed probe contract drifted.")

    sources = probe.get("sources")
    if not isinstance(sources, Mapping):
        raise BenchmarkIntegrityError("GIW secondary-lead sources are missing.")
    transformed = sources.get("transformed_collection_lead")
    labeller = sources.get("labeller_filename_lead")
    if not isinstance(transformed, Mapping) or not isinstance(labeller, Mapping):
        raise BenchmarkIntegrityError("GIW secondary-lead source records are incomplete.")

    if transformed.get("repository") != AWESOME_REPOSITORY or transformed.get("pinned_commit_sha1") != AWESOME_COMMIT:
        raise BenchmarkIntegrityError("GIW transformed-collection source identity drifted.")
    if transformed.get("classification") != "external_transformed_collection_advertisement":
        raise BenchmarkIntegrityError("GIW transformed-collection lead was misclassified.")
    for key in (
        "external_collection_contents_obtained_by_this_probe",
        "external_collection_contents_audited_by_this_probe",
        "authoritative_original_distribution_equivalence_verified",
    ):
        if transformed.get(key) is not False:
            raise BenchmarkIntegrityError(f"GIW transformed lead must keep {key}=false.")
    if transformed.get("tracked_official_process_or_label_paths") != []:
        raise BenchmarkIntegrityError("GIW transformed lead unexpectedly exposes official-layout files.")

    if labeller.get("repository") != EDIT_REPOSITORY or labeller.get("pinned_commit_sha1") != EDIT_COMMIT:
        raise BenchmarkIntegrityError("GIW labeller-filename source identity drifted.")
    if labeller.get("classification") != "local_path_reference_only":
        raise BenchmarkIntegrityError("GIW labeller filename lead was over-promoted.")
    if labeller.get("referenced_labeller_filenames") != LABELLER_FILENAMES:
        raise BenchmarkIntegrityError("GIW reviewed labeller filename references drifted.")
    if labeller.get("referenced_labeller_files_repository_resident") is not False:
        raise BenchmarkIntegrityError("GIW referenced labeller files must remain non-resident.")
    if labeller.get("independent_annotation_streams_recovered") is not False:
        raise BenchmarkIntegrityError("GIW labeller references do not recover annotation streams.")
    if labeller.get("human_human_agreement_eligible") is not False:
        raise BenchmarkIntegrityError("GIW labeller references cannot open agreement analysis.")
    if labeller.get("tracked_official_process_or_label_paths") != []:
        raise BenchmarkIntegrityError("GIW labeller lead unexpectedly exposes official-layout files.")

    boundary = probe.get("scientific_boundary")
    if not isinstance(boundary, Mapping) or set(boundary) != set(_FALSE_BOUNDARY_KEYS):
        raise BenchmarkIntegrityError("GIW secondary-lead scientific boundary drifted.")
    if any(boundary.get(key) is not False for key in _FALSE_BOUNDARY_KEYS):
        raise BenchmarkIntegrityError("GIW secondary-lead scientific boundary was promoted.")
    return probe


def validate_gaze_in_wild_secondary_lead_evidence(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildSecondaryLeadEvidence:
    """Bind a fresh exact-commit probe to the reviewed immutable evidence record."""

    probe = validate_gaze_in_wild_secondary_lead_probe(probe_or_path)
    evidence = _load(evidence_or_path)
    if evidence.get("record_type") != EVIDENCE_RECORD_TYPE or evidence.get("dataset") != "Gaze-in-the-Wild":
        raise BenchmarkIntegrityError("GIW secondary-lead frozen evidence identity drifted.")
    observed_evidence = _fingerprint(evidence, "evidence_fingerprint_sha256")
    if evidence.get("evidence_fingerprint_sha256") != observed_evidence:
        raise BenchmarkIntegrityError("GIW secondary-lead evidence fingerprint drifted.")
    if evidence.get("source_probe_fingerprint_sha256") != probe["probe_fingerprint_sha256"]:
        raise BenchmarkIntegrityError("GIW secondary-lead live probe no longer matches frozen evidence.")
    if evidence.get("sources") != probe.get("sources"):
        raise BenchmarkIntegrityError("GIW secondary-lead source evidence drifted.")
    if evidence.get("scientific_boundary") != probe.get("scientific_boundary"):
        raise BenchmarkIntegrityError("GIW secondary-lead frozen scientific boundary drifted.")
    if evidence.get("claim_limit") != probe.get("claim_limit"):
        raise BenchmarkIntegrityError("GIW secondary-lead frozen claim limit drifted.")
    return GazeInWildSecondaryLeadEvidence(
        probe_fingerprint_sha256=str(probe["probe_fingerprint_sha256"]),
        evidence_fingerprint_sha256=observed_evidence,
    )
