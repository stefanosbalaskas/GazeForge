"""Immutable Gaze-in-the-Wild participant/task publication evidence."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "gaze-in-wild-participant-task-metadata-evidence-v2"
STATUS = (
    "verified-publication-participant-task-matrix-with-"
    "distribution-task-file-mapping-unresolved"
)
EVIDENCE_FINGERPRINT = (
    "55b279fadd969e23b535fff3aac92327a45eb89cd0f365d90c0e5c6cae351017"
)
SOURCE_REPOSITORY = "https://github.com/RSKothari/Gaze-in-Wild"
SOURCE_COMMIT = "52262d44e366a53369e10ca73c5f41daf0e8f1e5"
SPRINGER_SHA256 = "b700b1deec97be82d81cba2cf4eba605d110ec5d8175b6c5681ac372b61c7f3d"
SPRINGER_TEXT_SHA256 = (
    "4ba1787fcc6d0dffb6195a5f3ac09cfe10c4145e53161a46465b64a633cbee6e"
)
ARXIV_SHA256 = "b4db32a89765aa96952ee2ae88e502600c1f97a607e3c58f9550ceb36e37fdd5"
ARXIV_TEXT_SHA256 = (
    "8a9f7302c63cafc40988a3549bdc22ab26473d92bce3707c409286404c769672"
)
TASKS = (
    "indoor_navigation",
    "ball_catching",
    "visual_search",
    "tea_making",
)
PARTICIPANT_IDS = (1, 2, 3, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23)
_ALLOWED_STATUSES = {
    "multiple_labellers",
    "single_labeller",
    "not_labeled",
    "discarded",
}
_EXPECTED_ROWS: dict[int, tuple[str, str, str, str]] = {
    1: ("multiple_labellers", "multiple_labellers", "discarded", "discarded"),
    2: ("multiple_labellers", "multiple_labellers", "discarded", "single_labeller"),
    3: ("single_labeller", "single_labeller", "discarded", "discarded"),
    6: ("single_labeller", "multiple_labellers", "discarded", "not_labeled"),
    8: ("single_labeller", "single_labeller", "single_labeller", "discarded"),
    9: ("single_labeller", "single_labeller", "not_labeled", "discarded"),
    10: ("single_labeller", "not_labeled", "not_labeled", "not_labeled"),
    11: ("not_labeled", "not_labeled", "discarded", "not_labeled"),
    12: ("single_labeller", "single_labeller", "single_labeller", "single_labeller"),
    13: ("not_labeled", "not_labeled", "not_labeled", "not_labeled"),
    14: ("not_labeled", "not_labeled", "not_labeled", "not_labeled"),
    15: ("not_labeled", "not_labeled", "single_labeller", "not_labeled"),
    16: ("single_labeller", "single_labeller", "not_labeled", "not_labeled"),
    17: ("single_labeller", "single_labeller", "single_labeller", "not_labeled"),
    18: ("single_labeller", "not_labeled", "single_labeller", "single_labeller"),
    19: ("not_labeled", "single_labeller", "single_labeller", "discarded"),
    20: ("single_labeller", "not_labeled", "single_labeller", "not_labeled"),
    22: ("single_labeller", "single_labeller", "single_labeller", "discarded"),
    23: ("not_labeled", "not_labeled", "not_labeled", "not_labeled"),
}
_EXPECTED_STATUS_COUNTS = {
    "multiple_labellers": 5,
    "single_labeller": 30,
    "not_labeled": 30,
    "discarded": 11,
}
_EXPECTED_SOURCE_BLOBS = {
    "readme_git_blob_sha1": "5b8536d0166d8c58e33d908fccd9c3f9c2b59a12",
    "automated_process_git_blob_sha1": "be7d76cd3d5b511b4febab393789b3fbd9a3ad9b",
    "participant_info_git_blob_sha1": "6c21df7554891015a1ae09182867b5d707b6a505",
    "read_dataset_git_blob_sha1": "83e1b33eb10352688d9b397d4f798fc32fa4b502",
    "plot_labels_git_blob_sha1": "511581250e04c62037c71d2da16271be4979d434",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load_record(record_or_path: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path)
    return json.loads(Path(record_or_path).read_text(encoding="utf-8"))


def _require_false(mapping: Mapping[str, Any], *keys: str) -> None:
    for key in keys:
        if mapping.get(key) is not False:
            raise BenchmarkIntegrityError(f"GIW boundary {key!r} must remain false.")


def _validate_matrix(matrix: Mapping[str, Any]) -> None:
    if matrix.get("participant_ids") != list(PARTICIPANT_IDS):
        raise BenchmarkIntegrityError("GIW publication participant set drifted.")
    if matrix.get("participant_count") != len(PARTICIPANT_IDS):
        raise BenchmarkIntegrityError("GIW publication participant count drifted.")
    if matrix.get("task_columns") != list(TASKS):
        raise BenchmarkIntegrityError("GIW publication task columns drifted.")
    if matrix.get("status_counts") != _EXPECTED_STATUS_COUNTS:
        raise BenchmarkIntegrityError("GIW publication status counts drifted.")

    rows = matrix.get("participants")
    if not isinstance(rows, list) or len(rows) != len(PARTICIPANT_IDS):
        raise BenchmarkIntegrityError("GIW publication matrix row count drifted.")
    observed: Counter[str] = Counter()
    seen: set[int] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise BenchmarkIntegrityError("GIW publication matrix row must be a mapping.")
        participant_id = row.get("participant_id")
        if not isinstance(participant_id, int) or participant_id in seen:
            raise BenchmarkIntegrityError("GIW publication participant identity is invalid.")
        seen.add(participant_id)
        tasks = row.get("tasks")
        if not isinstance(tasks, Mapping) or list(tasks.keys()) != list(TASKS):
            raise BenchmarkIntegrityError("GIW publication task row shape drifted.")
        statuses = tuple(tasks[task] for task in TASKS)
        if any(status not in _ALLOWED_STATUSES for status in statuses):
            raise BenchmarkIntegrityError("GIW publication task status is invalid.")
        if statuses != _EXPECTED_ROWS.get(participant_id):
            raise BenchmarkIntegrityError(
                f"GIW publication task row drifted for participant {participant_id}."
            )
        observed.update(statuses)
    if seen != set(PARTICIPANT_IDS):
        raise BenchmarkIntegrityError("GIW publication participant identities drifted.")
    if dict(observed) != _EXPECTED_STATUS_COUNTS:
        raise BenchmarkIntegrityError("GIW publication matrix aggregate drifted.")


def validate_gaze_in_wild_participant_task_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate immutable publication-level participant/task evidence."""
    record = _load_record(record_or_path)
    if record.get("record_type") != RECORD_TYPE or record.get("status") != STATUS:
        raise BenchmarkIntegrityError("Unexpected GIW participant/task evidence identity.")
    if record.get("evidence_fingerprint_sha256") != EVIDENCE_FINGERPRINT:
        raise BenchmarkIntegrityError("GIW participant/task stored fingerprint drifted.")
    if evidence_fingerprint(record) != EVIDENCE_FINGERPRINT:
        raise BenchmarkIntegrityError("GIW participant/task content fingerprint drifted.")

    publication = record.get("publication_source", {})
    if publication.get("doi") != "10.1038/s41598-020-59251-5":
        raise BenchmarkIntegrityError("GIW publication DOI drifted.")
    if publication.get("springer_pdf_sha256") != SPRINGER_SHA256:
        raise BenchmarkIntegrityError("GIW Springer supplement identity drifted.")
    if publication.get("springer_text_sha256_whitespace_canonical") != SPRINGER_TEXT_SHA256:
        raise BenchmarkIntegrityError("GIW Springer supplement text identity drifted.")
    if publication.get("springer_pdf_byte_size") != 5_514_416:
        raise BenchmarkIntegrityError("GIW Springer supplement byte size drifted.")
    if publication.get("springer_pdf_page_count") != 4:
        raise BenchmarkIntegrityError("GIW Springer supplement page count drifted.")
    if publication.get("arxiv_identifier") != "1905.13146v1":
        raise BenchmarkIntegrityError("GIW arXiv identity drifted.")
    if publication.get("arxiv_pdf_sha256") != ARXIV_SHA256:
        raise BenchmarkIntegrityError("GIW arXiv PDF identity drifted.")
    if publication.get("arxiv_text_sha256_whitespace_canonical") != ARXIV_TEXT_SHA256:
        raise BenchmarkIntegrityError("GIW arXiv text identity drifted.")
    if publication.get("publisher_and_author_copy_table_markers_agree") is not True:
        raise BenchmarkIntegrityError("GIW publisher/author table agreement must be true.")

    source = record.get("first_party_source", {})
    if source.get("repository") != SOURCE_REPOSITORY:
        raise BenchmarkIntegrityError("GIW first-party repository drifted.")
    if source.get("commit_sha1") != SOURCE_COMMIT:
        raise BenchmarkIntegrityError("GIW first-party source commit drifted.")
    for key, expected in _EXPECTED_SOURCE_BLOBS.items():
        if source.get(key) != expected:
            raise BenchmarkIntegrityError(f"GIW first-party source blob {key!r} drifted.")
    if source.get(
        "readme_designates_supplement_as_official_participant_task_label_availability_list"
    ) is not True:
        raise BenchmarkIntegrityError("GIW README authority chain drifted.")

    _validate_matrix(record.get("publication_matrix", {}))

    identity = record.get("processing_identity_convention", {})
    for key in (
        "participant_info_name_used_as_raw_participant_directory",
        "pridx_passed_to_processing_output_identity",
        "published_person_number_to_processing_pridx_convention_supported",
    ):
        if identity.get(key) is not True:
            raise BenchmarkIntegrityError(f"GIW processing identity {key!r} drifted.")
    if identity.get("processed_filename_pattern") != "PrIdx_%d_TrIdx_%d.mat":
        raise BenchmarkIntegrityError("GIW ProcessData filename convention drifted.")
    if identity.get("label_filename_pattern") != "PrIdx_%d_TrIdx_%d_Lbr_%d.mat":
        raise BenchmarkIntegrityError("GIW LabelData filename convention drifted.")
    if identity.get("age_used_as_identity_join") is not False:
        raise BenchmarkIntegrityError("GIW age must not become an identity join.")
    if identity.get("age_discrepancy_preserved") != {
        "participant_id": 18,
        "supplement_age": 34,
        "processing_metadata_age": 45,
    }:
        raise BenchmarkIntegrityError("GIW participant-18 age discrepancy drifted.")
    _require_false(identity, "exact_distributed_file_identity_verified")

    mapping = record.get("task_mapping_boundary", {})
    if mapping.get("publication_person_to_task_status_matrix_verified") is not True:
        raise BenchmarkIntegrityError("GIW publication task matrix is not verified.")
    if mapping.get("indoor_walk_context_for_tridx_1_observed_in_first_party_plotting_code") is not True:
        raise BenchmarkIntegrityError("GIW reviewed indoor-walk context drifted.")
    _require_false(
        mapping,
        "universal_tridx_to_task_name_mapping_verified",
        "task_directory_to_task_name_mapping_from_authoritative_distribution_verified",
        "exact_processdata_file_to_publication_task_mapping_verified",
        "global_tridx_mapping_inferred_from_that_context",
    )

    _require_false(
        record.get("rights_boundary", {}),
        "authoritative_full_distribution_obtained",
        "exact_distribution_equivalence_verified",
        "reuse_terms_verified",
        "analysis_use_permitted",
        "redistribution_permission_verified",
        "source_audit_ready",
    )
    _require_false(
        record.get("scientific_boundary", {}),
        "per_file_sampling_rate_distribution_frozen",
        "human_human_agreement_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "new_empirical_performance_claim_created",
    )
    return record


def validate_live_publication_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Bind a metadata-only fresh PDF probe to immutable evidence identities."""
    evidence = validate_gaze_in_wild_participant_task_evidence(evidence_or_path)
    probe = _load_record(probe_or_path)
    if probe.get("record_type") != "gaze-in-wild-participant-task-live-probe-v2":
        raise BenchmarkIntegrityError("Unexpected GIW participant/task live probe type.")
    springer = probe.get("springer", {})
    arxiv = probe.get("arxiv", {})
    if springer != {
        "sha256": SPRINGER_SHA256,
        "byte_size": 5_514_416,
        "page_count": 4,
        "text_sha256_whitespace_canonical": SPRINGER_TEXT_SHA256,
        "required_markers_present": True,
    }:
        raise BenchmarkIntegrityError("GIW live Springer supplement binding drifted.")
    if arxiv != {
        "sha256": ARXIV_SHA256,
        "byte_size": 9_437_264,
        "page_count": 23,
        "text_sha256_whitespace_canonical": ARXIV_TEXT_SHA256,
        "required_markers_present": True,
    }:
        raise BenchmarkIntegrityError("GIW live arXiv binding drifted.")
    boundaries = probe.get("boundaries", {})
    _require_false(
        boundaries,
        "exact_distribution_equivalence_verified",
        "universal_tridx_to_task_name_mapping_verified",
        "analysis_use_permitted",
        "redistribution_permission_verified",
        "new_empirical_performance_claim_created",
    )
    return evidence
