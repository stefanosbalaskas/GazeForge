"""Compile reviewed candidate mappings into deliberately non-empirical audit templates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_audit import (
    GazeInWildLabelFileRecord,
    GazeInWildProcessFileRecord,
    GazeInWildSourceAuditSpec,
)
from .hollywood2_audit import Hollywood2SourceAuditSpec, Hollywood2SourceFileRecord
from .source_candidate_review import CandidateSourceReviewScaffold

AuditTemplateSpec = Hollywood2SourceAuditSpec | GazeInWildSourceAuditSpec

_PLACEHOLDER = "REVIEW_REQUIRED"
_COMMON_REVIEW_FIELDS = (
    "dataset_version",
    "authoritative_source",
    "source_revision",
    "license_or_terms",
    "reuse_terms_source",
    "source_authority_evidence",
    "analysis_use_evidence",
    "redistribution_evidence",
    "coordinate_verification_basis",
    "participant_mapping_basis",
)
_DATASET_REVIEW_FIELDS = {
    "hollywood2em": (
        "annotation_columns_review",
        "sampling_rate_review",
    ),
    "gaze-in-the-wild": (
        "label_process_mapping_basis",
        "labeller_mapping_basis",
        "timestamp_sampling_basis",
    ),
}
_AUDIT_ROLES = {
    "hollywood2em": {"arff"},
    "gaze-in-the-wild": {"label", "process"},
}


def _reviewed_text(review: dict[str, Any], field_name: str) -> str:
    value = review.get(field_name)
    text = "" if value is None else str(value).strip()
    if not text or text == _PLACEHOLDER:
        raise BenchmarkIntegrityError(
            f"Candidate source audit-template compilation requires reviewed {field_name}."
        )
    return text


def _review_notes(scaffold: CandidateSourceReviewScaffold) -> list[str]:
    notes = scaffold.source_review.get("notes", [])
    if not isinstance(notes, list):
        raise BenchmarkIntegrityError("Candidate review notes must be a JSON list.")
    return [str(note) for note in notes]


def _require_review_ready(scaffold: CandidateSourceReviewScaffold) -> dict[str, Any]:
    if not isinstance(scaffold, CandidateSourceReviewScaffold):
        raise TypeError("scaffold must be a CandidateSourceReviewScaffold instance.")
    if scaffold.dataset_key not in _DATASET_REVIEW_FIELDS:
        raise BenchmarkIntegrityError("Unsupported candidate review dataset key.")
    review = dict(scaffold.source_review)
    if review.get("dataset_status") != "template":
        raise BenchmarkIntegrityError(
            "Candidate review must remain dataset_status='template' during audit-template "
            "compilation."
        )
    for field_name in _COMMON_REVIEW_FIELDS + _DATASET_REVIEW_FIELDS[scaffold.dataset_key]:
        _reviewed_text(review, field_name)
    _review_notes(scaffold)

    allowed_roles = _AUDIT_ROLES[scaffold.dataset_key]
    unexpected = sorted(
        {row.role for row in scaffold.files if row.include_in_audit and row.role not in allowed_roles}
    )
    if unexpected:
        raise BenchmarkIntegrityError(
            "Candidate audit-template compilation refuses included file roles outside the "
            f"dataset audit contract: {unexpected}."
        )
    return review


def _compiler_notes(scaffold: CandidateSourceReviewScaffold, review: dict[str, Any]) -> list[str]:
    return [
        *[str(note) for note in review.get("notes", [])],
        (
            "Generated from a GazeForge candidate-source-review scaffold. This output remains "
            "dataset_status='template' and does not authorize source audit or empirical evidence."
        ),
        (
            "Source authority, reuse permission, analysis permission, coordinate verification, "
            "and participant mapping remain unverified booleans in this compiled template even "
            "when supporting review text is present."
        ),
        (
            "Candidate inventory fingerprint: "
            f"{scaffold.candidate_inventory_fingerprint_sha256}"
        ),
        f"Source authority review evidence: {review['source_authority_evidence']}",
        f"Analysis-use review evidence: {review['analysis_use_evidence']}",
        f"Redistribution review evidence: {review['redistribution_evidence']}",
    ]


def _compile_hollywood2(
    scaffold: CandidateSourceReviewScaffold,
    review: dict[str, Any],
) -> Hollywood2SourceAuditSpec:
    coordinate_unit = str(review.get("coordinate_unit", "")).strip().lower()
    if coordinate_unit != "pixels":
        raise BenchmarkIntegrityError(
            "Hollywood2EM audit-template compilation requires the reviewer to record "
            "coordinate_unit='pixels'; the compiler will not infer coordinate units."
        )
    included = [row for row in scaffold.files if row.include_in_audit and row.role == "arff"]
    if not included:
        raise BenchmarkIntegrityError(
            "Hollywood2EM audit-template compilation requires at least one reviewed included "
            "ARFF row."
        )
    files = [
        Hollywood2SourceFileRecord(
            path=row.path,
            sha256=row.sha256,
            bytes=row.bytes,
            participant_id=str(row.participant_id),
            trial_id=str(row.trial_id),
        )
        for row in included
    ]
    notes = _compiler_notes(scaffold, review)
    notes.extend(
        [
            f"Annotation-column review: {review['annotation_columns_review']}",
            f"Sampling-rate review: {review['sampling_rate_review']}",
            (
                "The compiled template carries the existing Hollywood2EM audit-contract default "
                "expected_sampling_rate_hz=500.0; this compiler does not verify observed cadence."
            ),
        ]
    )
    return Hollywood2SourceAuditSpec(
        dataset_name="Hollywood2EM",
        dataset_version=_reviewed_text(review, "dataset_version"),
        source=_reviewed_text(review, "authoritative_source"),
        source_revision=_reviewed_text(review, "source_revision"),
        license=_reviewed_text(review, "license_or_terms"),
        reuse_terms_source=_reviewed_text(review, "reuse_terms_source"),
        dataset_status="template",
        reuse_terms_verified=False,
        analysis_use_permitted=False,
        redistribution_status="unknown",
        expected_sampling_rate_hz=500.0,
        sampling_rate_tolerance_fraction=0.05,
        coordinate_unit="pixels",
        coordinate_unit_verified=False,
        coordinate_verification_basis=_reviewed_text(review, "coordinate_verification_basis"),
        participant_identity_mapping_verified=False,
        participant_identity_mapping_basis=_reviewed_text(review, "participant_mapping_basis"),
        files=files,
        notes=notes,
    )


def _compile_gaze_in_wild(
    scaffold: CandidateSourceReviewScaffold,
    review: dict[str, Any],
) -> GazeInWildSourceAuditSpec:
    labels = [row for row in scaffold.files if row.include_in_audit and row.role == "label"]
    processes = [row for row in scaffold.files if row.include_in_audit and row.role == "process"]
    if not labels or not processes:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild audit-template compilation requires reviewed included label and "
            "process rows."
        )
    label_files = [
        GazeInWildLabelFileRecord(
            path=row.path,
            sha256=row.sha256,
            bytes=row.bytes,
            participant_id=str(row.participant_id),
            trial_id=str(row.trial_id),
            labeller_id=int(row.labeller_id),
            process_path=str(row.process_path),
        )
        for row in labels
    ]
    process_files = [
        GazeInWildProcessFileRecord(path=row.path, sha256=row.sha256, bytes=row.bytes)
        for row in processes
    ]
    notes = _compiler_notes(scaffold, review)
    notes.extend(
        [
            f"Label/process mapping review: {review['label_process_mapping_basis']}",
            f"Labeller mapping review: {review['labeller_mapping_basis']}",
            f"Timestamp/sampling review: {review['timestamp_sampling_basis']}",
            (
                "The compiled template carries the existing Gaze-in-the-Wild audit-contract "
                "published_hardware_sampling_rate_hz=120.0; the compiler does not equate this "
                "with timestamp-inferred file cadence."
            ),
        ]
    )
    coordinate_unit = str(review.get("coordinate_unit", "unverified")).strip()
    if not coordinate_unit:
        raise BenchmarkIntegrityError("Reviewed Gaze-in-the-Wild coordinate_unit must not be empty.")
    return GazeInWildSourceAuditSpec(
        dataset_name="Gaze-in-the-Wild",
        dataset_version=_reviewed_text(review, "dataset_version"),
        source=_reviewed_text(review, "authoritative_source"),
        source_revision=_reviewed_text(review, "source_revision"),
        license=_reviewed_text(review, "license_or_terms"),
        reuse_terms_source=_reviewed_text(review, "reuse_terms_source"),
        dataset_status="template",
        reuse_terms_verified=False,
        analysis_use_permitted=False,
        redistribution_status="unknown",
        participant_mapping_verified=False,
        participant_mapping_basis=_reviewed_text(review, "participant_mapping_basis"),
        coordinate_unit=coordinate_unit,
        coordinate_unit_verified=False,
        coordinate_verification_basis=_reviewed_text(review, "coordinate_verification_basis"),
        pixel_kinematics_compatible=False,
        confidence_threshold=0.30,
        published_hardware_sampling_rate_hz=120.0,
        label_files=label_files,
        process_files=process_files,
        notes=notes,
    )


def compile_candidate_source_audit_template(
    scaffold: CandidateSourceReviewScaffold,
) -> AuditTemplateSpec:
    """Compile a reviewed candidate worksheet into an existing audit-spec template type.

    The compiler never sets ``dataset_status='empirical'`` and never sets any scientific approval
    boolean to true. Its output is directly loadable by the existing dataset-specific audit-spec
    loaders, but the empirical audit runners continue to reject it until a separate explicit human
    authorization step updates the relevant evidence fields.
    """
    review = _require_review_ready(scaffold)
    if scaffold.dataset_key == "hollywood2em":
        return _compile_hollywood2(scaffold, review)
    return _compile_gaze_in_wild(scaffold, review)


def write_candidate_source_audit_template(
    spec: AuditTemplateSpec,
    path: str | Path,
    *,
    candidate_root: str | Path,
    overwrite: bool = False,
) -> Path:
    """Write one non-empirical audit-spec template outside the candidate source tree."""
    if not isinstance(spec, (Hollywood2SourceAuditSpec, GazeInWildSourceAuditSpec)):
        raise TypeError("spec must be a Hollywood2SourceAuditSpec or GazeInWildSourceAuditSpec.")
    if spec.dataset_status != "template":
        raise BenchmarkIntegrityError(
            "Candidate compiler output must remain dataset_status='template'."
        )
    if spec.reuse_terms_verified or spec.analysis_use_permitted:
        raise BenchmarkIntegrityError(
            "Candidate compiler output cannot mark reuse terms verified or analysis use permitted."
        )
    root = Path(candidate_root).resolve()
    target = Path(path)
    resolved_target = target.resolve(strict=False)
    if resolved_target == root or root in resolved_target.parents:
        raise BenchmarkIntegrityError(
            "Candidate audit-template output must be outside the candidate source tree."
        )
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(spec.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return target
