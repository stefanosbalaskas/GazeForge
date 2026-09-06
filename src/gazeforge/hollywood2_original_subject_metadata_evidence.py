"""Frozen evidence and fresh-live validation for original Hollywood-2 subject metadata."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .hollywood2_original_subject_metadata import (
    DESCRIPTION_URL,
    LICENSE_URL,
    RECORD_TYPE,
    STATUS,
    probe_fingerprint,
)

EVIDENCE_RECORD_TYPE = "hollywood2-original-subject-metadata-evidence-v1"
EVIDENCE_STATUS = (
    "reviewed-public-original-distribution-metadata-login-gated-no-subject-ledger"
)
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "ba7813dd4f87c4a20ee75f3a9e537e329bca74c519b7bc65a5ba5e5095dd8a5c"
)
ADVERTISED_ARCHIVE_URL = (
    "http://vision.imar.ro/eyetracking/getdata.php?"
    "filepath=data&filename=gaze_hollywood2.zip"
)
LOGIN_URL = "https://vision.imar.ro/eyetracking/main_login.php"

_REQUIRED_DESCRIPTION_MARKERS = (
    "sixteen_volunteers",
    "active_and_free_viewing_split",
    "twelve_active_subjects",
    "four_free_viewing_subjects",
    "active_action_recognition_task",
    "free_viewing_no_specific_task",
    "five_hundred_hz",
    "hollywood2_data_link_present",
)
_REQUIRED_LICENSE_MARKERS = (
    "academic_use_only",
    "limited_nonexclusive_nonassignable_nontransferable",
    "request_from_academic_address",
    "no_sublicense_or_transfer",
    "responsible_use_permission_clause",
)
_GIN_TOKENS = (
    "001",
    "002",
    "003",
    "004",
    "005",
    "006",
    "008",
    "010",
    "011",
    "012",
    "013",
    "014",
    "015",
    "017",
    "018",
    "019",
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Recompute the immutable evidence fingerprint."""
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(value: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    try:
        payload = json.loads(Path(value).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load Hollywood2 original-subject evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Hollywood2 original-subject evidence must be a JSON object."
        )
    return payload


def _map(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(
            f"Hollywood2 original-subject field {key!r} is missing."
        )
    return value


def _eq(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"Hollywood2 original-subject {label} drifted."
        )


def _must_true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(
            f"Hollywood2 original-subject must preserve {label}."
        )


def _must_false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(
            f"Hollywood2 original-subject must not promote {label}."
        )


def _validate_nonpromotion_boundaries(record: Mapping[str, Any]) -> None:
    rights = _map(record, "rights_boundary")
    _must_true(rights.get("public_license_page_observed"), "public license observation")
    for key in (
        "license_acceptance_or_academic_request_performed",
        "dataset_archive_download_performed",
        "dataset_use_authorized_by_this_probe",
        "dataset_redistribution_authorized_by_this_probe",
        "login_gate_bypassed",
    ):
        _must_false(rights.get(key), key)

    mapping = _map(record, "mapping_boundary")
    for key in (
        "original_subject_ids_recovered_from_public_metadata",
        "original_subject_group_id_ledger_recovered",
        "gin_token_to_original_subject_id_verified",
        "gin_token_to_task_group_verified",
        "participant_identity_mapping_verified",
        "participant_disjoint_model_validation_created",
    ):
        _must_false(mapping.get(key), key)

    scientific = _map(record, "scientific_boundary")
    for key in (
        "source_audit_ready",
        "cross_dataset_validation_created",
        "new_empirical_performance_claim_created",
    ):
        _must_false(scientific.get(key), key)


def validate_hollywood2_original_subject_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the immutable reviewed public-source/access-gate evidence."""
    record = _load(record_or_path)
    _eq(record.get("record_type"), EVIDENCE_RECORD_TYPE, "record type")
    _eq(record.get("status"), EVIDENCE_STATUS, "status")
    _eq(record.get("checked_on"), "2026-09-06", "review date")

    binding = _map(record, "source_binding")
    expected_binding = {
        "description_url": DESCRIPTION_URL,
        "license_url": LICENSE_URL,
        "advertised_hollywood2_archive_url": ADVERTISED_ARCHIVE_URL,
        "advertised_archive_filename": "gaze_hollywood2.zip",
        "reviewed_archive_route_final_url": LOGIN_URL,
        "gin_repository": (
            "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
        ),
        "gin_commit_sha1": "870fa6d6209c9085260918d61433a0a2c70fd497",
        "gin_history_evidence_fingerprint_sha256": (
            "c7d2f477a66feca3676482ffdabff2b0778196db99e48b86104fe86d0f5bfae1"
        ),
        "gin_accessible_host_evidence_fingerprint_sha256": (
            "9e09bfe43a273fbcd8cfe258be547aee18e96b8f0928198d1fb5411555024ced"
        ),
        "author_license_statement_evidence_fingerprint_sha256": (
            "b01da719afe18f4eb0103a17d6e8c85f3750ba299050f8026063a9ebb55b1b2e"
        ),
        "underlying_source_rights_evidence_fingerprint_sha256": (
            "6227045c3cc831b3669b34ca74b955847df4b26fafbf825c9a1b5473e25bc943"
        ),
    }
    for key, expected in expected_binding.items():
        _eq(binding.get(key), expected, f"binding {key}")

    reviewed = _map(record, "reviewed_public_observation")
    description = _map(reviewed, "description")
    _eq(description.get("http_status"), 200, "reviewed description HTTP status")
    _eq(
        description.get("normalized_text_sha256"),
        "88b520eec8ceae3b6d015e4be8d31bbbaa6cd6685a68fffb80a878ce67faba64",
        "reviewed description SHA-256",
    )
    _eq(description.get("normalized_text_length"), 5791, "description length")
    markers = _map(description, "markers")
    for key in _REQUIRED_DESCRIPTION_MARKERS:
        _must_true(markers.get(key), f"reviewed description marker {key}")
    _must_false(
        markers.get("public_readme_link_present"),
        "reviewed public README link",
    )
    _eq(description.get("hollywood2_data_link_count"), 1, "reviewed data-link count")
    _eq(description.get("public_readme_link_count"), 0, "reviewed README-link count")

    license_page = _map(reviewed, "license_page")
    _eq(license_page.get("http_status"), 200, "reviewed license HTTP status")
    _eq(
        license_page.get("normalized_text_sha256"),
        "952fd2ff8dfdba12037ad76a0959a01634039a18b0b59360a4e50d5ede7591da",
        "reviewed license SHA-256",
    )
    _eq(license_page.get("normalized_text_length"), 3307, "license length")
    license_markers = _map(license_page, "markers")
    for key in _REQUIRED_LICENSE_MARKERS:
        _must_true(license_markers.get(key), f"reviewed license marker {key}")

    head = _map(reviewed, "advertised_data_link_head")
    _eq(head.get("requested_url"), ADVERTISED_ARCHIVE_URL, "reviewed archive URL")
    _eq(head.get("final_url"), LOGIN_URL, "reviewed login-gate URL")
    _eq(head.get("http_status"), 200, "reviewed archive-route HTTP status")
    _eq(head.get("content_type"), "text/html; charset=utf-8", "reviewed content type")
    _eq(head.get("content_length"), "2889", "reviewed content length")
    _eq(head.get("content_disposition"), None, "reviewed Content-Disposition")

    token_context = _map(reviewed, "gin_filename_token_context")
    _eq(
        token_context.get("stable_three_digit_tokens"),
        list(_GIN_TOKENS),
        "reviewed GIN token ledger",
    )
    _eq(
        token_context.get("absent_numbers_within_001_to_019"),
        ["007", "009", "016"],
        "reviewed absent token numbers",
    )
    _eq(token_context.get("token_count"), 16, "reviewed token count")
    _must_true(
        token_context.get("token_count_matches_public_original_subject_count"),
        "reviewed count match",
    )
    _must_false(
        token_context.get("token_count_match_is_mapping_evidence"),
        "count-only mapping evidence",
    )

    _validate_nonpromotion_boundaries(record)

    execution = _map(record, "execution")
    expected_execution = {
        "workflow_run_id": 34060071078,
        "job_id": 101558892716,
        "probe_head_sha": "9eb7d0da9ae08cbc5d93e68e8a34dc29a159cfd1",
        "artifact_id": 9997181901,
        "artifact_zip_sha256": (
            "a8c15f0f38b3648786ce331f3cf50d4ad5683be093a0cf0d3505ff12e5529f7e"
        ),
        "live_probe_record_type": RECORD_TYPE,
        "live_probe_fingerprint_sha256": (
            "1965813fa733a77173d5248fa9d65bf2c2a6b81f33f706cfc2ee076602f99622"
        ),
    }
    for key, expected in expected_execution.items():
        _eq(execution.get(key), expected, f"execution {key}")

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    _eq(stored, evidence_fingerprint(record), "self-fingerprint")
    _eq(stored, EXPECTED_EVIDENCE_FINGERPRINT_SHA256, "immutable fingerprint")
    return record


def validate_hollywood2_original_subject_live_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Fail closed if the public source, access route, or mapping surface changes."""
    validate_hollywood2_original_subject_evidence(evidence_or_path)
    probe = _load(probe_or_path)
    _eq(probe.get("record_type"), RECORD_TYPE, "fresh record type")
    _eq(probe.get("status"), STATUS, "fresh status")
    _eq(
        probe.get("probe_fingerprint_sha256"),
        probe_fingerprint(probe),
        "fresh self-fingerprint",
    )

    description = _map(probe, "description")
    _eq(description.get("requested_url"), DESCRIPTION_URL, "fresh description URL")
    _eq(description.get("http_status"), 200, "fresh description HTTP status")
    markers = _map(description, "markers")
    for key in _REQUIRED_DESCRIPTION_MARKERS:
        _must_true(markers.get(key), f"fresh description marker {key}")
    _must_false(markers.get("public_readme_link_present"), "fresh public README")
    readme_links = description.get("public_readme_links")
    if readme_links != []:
        raise BenchmarkIntegrityError(
            "Hollywood2 original-subject public README/ledger surface appeared; "
            "manual review is required."
        )

    data_links = description.get("hollywood2_data_links")
    if not isinstance(data_links, list) or len(data_links) != 1:
        raise BenchmarkIntegrityError(
            "Hollywood2 original-subject advertised data-link surface changed."
        )
    link = data_links[0]
    if not isinstance(link, Mapping):
        raise BenchmarkIntegrityError(
            "Hollywood2 original-subject advertised data link is invalid."
        )
    _eq(link.get("resolved_url"), ADVERTISED_ARCHIVE_URL, "fresh archive URL")

    head = _map(probe, "advertised_data_link_head")
    _eq(head.get("requested_url"), ADVERTISED_ARCHIVE_URL, "fresh HEAD URL")
    _eq(head.get("final_url"), LOGIN_URL, "fresh login-gate target")
    _eq(head.get("http_status"), 200, "fresh archive-route HTTP status")
    content_type = str(head.get("content_type", "")).lower()
    if "text/html" not in content_type:
        raise BenchmarkIntegrityError(
            "Hollywood2 original-subject archive route no longer resolves to HTML; "
            "manual review is required and the archive must not be auto-downloaded."
        )
    _eq(head.get("content_disposition"), None, "fresh Content-Disposition")

    license_page = _map(probe, "license_page")
    _eq(license_page.get("requested_url"), LICENSE_URL, "fresh license URL")
    _eq(license_page.get("http_status"), 200, "fresh license HTTP status")
    license_markers = _map(license_page, "markers")
    for key in _REQUIRED_LICENSE_MARKERS:
        _must_true(license_markers.get(key), f"fresh license marker {key}")

    context = _map(probe, "observed_subject_context")
    _must_true(
        context.get("public_page_states_sixteen_volunteers"),
        "fresh 16-volunteer statement",
    )
    _must_true(
        context.get("public_page_states_twelve_active_subjects"),
        "fresh 12-active statement",
    )
    _must_true(
        context.get("public_page_states_four_free_viewing_subjects"),
        "fresh 4-free-viewing statement",
    )
    _must_true(
        context.get("public_page_distinguishes_task_groups"),
        "fresh task-group distinction",
    )
    _eq(context.get("advertised_hollywood2_data_link_count"), 1, "fresh data-link count")

    _validate_nonpromotion_boundaries(probe)
    return probe
