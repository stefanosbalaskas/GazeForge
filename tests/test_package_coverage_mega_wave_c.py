from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest
from test_hollywood2_coordinate_evidence import _reviewed_live_probe

import gazeforge.cross_dataset_evidence as cross
import gazeforge.gaze_in_wild_candidate_preflight as preflight
import gazeforge.gaze_in_wild_exact_copy_review as exact_copy
import gazeforge.hollywood2_coordinate_evidence as coordinate
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.source_audit_lineage import SourceAuditLineageReceipt

ROOT = Path(__file__).resolve().parents[1]

COORDINATE_EVIDENCE = (
    ROOT
    / "validation"
    / "evidence"
    / "hollywood2"
    / "hollywood2-coordinate-semantics-evidence-v1.json"
)


def _set_path(payload, path, value):
    cursor = payload

    for key in path[:-1]:
        cursor = cursor[key]

    cursor[path[-1]] = value
    return payload


# =====================================================================
# GIW EXACT-COPY REVIEW
# =====================================================================


def _exact_record(*, exact_match=False, reviewed=False):
    candidate_fp = "d" * 64
    reference_fp = candidate_fp if exact_match else "e" * 64

    comparison = {
        "method": ("complete_relative_path_byte_size_sha256_manifest_equality"),
        "candidate_file_count": 1,
        "reference_file_count": 1,
        "candidate_total_bytes": 10,
        "reference_total_bytes": 10,
        "shared_path_count": (1 if exact_match else 0),
        "candidate_only_path_count": (0 if exact_match else 1),
        "reference_only_path_count": (0 if exact_match else 1),
        "shared_path_content_mismatch_count": 0,
        "path_set_equal": exact_match,
        "exact_manifest_match": exact_match,
    }

    status = "reviewed" if reviewed else "pending_review"
    reference_verified = bool(reviewed and exact_match)

    decision, result = exact_copy._derive_result(
        review_status=status,
        reference_binding_verified=reference_verified,
        exact_manifest_match=exact_match,
    )

    record = {
        "record_type": exact_copy.RECORD_TYPE,
        "dataset": "Gaze-in-the-Wild",
        "readiness_record_fingerprint_sha256": "1" * 64,
        "first_party_binding": {
            "request_fingerprint_sha256": "2" * 64,
            "response_fingerprint_sha256": "3" * 64,
            "correspondence_sha256": "4" * 64,
        },
        "candidate_binding": {
            "candidate_kind": "unknown_recovered_copy",
            "recovery_record_fingerprint_sha256": "5" * 64,
            "recovery_tree_fingerprint_sha256": "6" * 64,
            "candidate_screen_fingerprint_sha256": "7" * 64,
            "candidate_inventory_fingerprint_sha256": candidate_fp,
            "selected_file": {
                "relative_path": "ProcessData/example.mat",
                "sha256": "8" * 64,
                "bytes": 10,
            },
        },
        "reference_binding": {
            "reference_inventory_fingerprint_sha256": reference_fp,
            "reference_file_count": 1,
            "reference_total_bytes": 10,
            "reference_provenance_sha256": "9" * 64,
        },
        "comparison": comparison,
        "review": {
            "status": status,
            "reviewer": ("Reviewer" if reviewed else "REVIEW_REQUIRED"),
            "reviewed_at": ("2026-09-23T10:00:00Z" if reviewed else "REVIEW_REQUIRED"),
            "reference_binding_verified": reference_verified,
            "evidence_basis": (
                "Reviewed local reference manifest" if reviewed else "REVIEW_REQUIRED"
            ),
        },
        "decision": decision,
        "result": result,
        "privacy_boundary": dict(exact_copy._PRIVACY_BOUNDARY),
        "scientific_boundary": dict(exact_copy._SCIENTIFIC_BOUNDARY),
        "claim_limit": exact_copy.CLAIM_LIMIT,
    }

    record["record_fingerprint_sha256"] = exact_copy.exact_copy_review_fingerprint(record)

    return record


def _resign_exact(record):
    record["record_fingerprint_sha256"] = exact_copy.exact_copy_review_fingerprint(record)


def test_exact_copy_valid_pending_and_reviewed_records():
    pending = exact_copy.validate_gaze_in_wild_exact_copy_review(_exact_record())

    assert pending.decision == "pending_review"
    assert not pending.exact_copy_identity_verified

    reviewed = exact_copy.validate_gaze_in_wild_exact_copy_review(
        _exact_record(
            exact_match=True,
            reviewed=True,
        )
    )

    assert reviewed.decision == "verified_against_reviewed_reference_manifest"
    assert reviewed.exact_copy_identity_verified


@pytest.mark.parametrize(
    "value",
    [
        "",
        "unknown",
        "__unresolved__",
        None,
    ],
)
def test_exact_copy_resolved_guard(value):
    with pytest.raises(BenchmarkIntegrityError):
        exact_copy._resolved(
            value,
            label="demo",
        )


def test_exact_copy_sha_guard():
    with pytest.raises(BenchmarkIntegrityError):
        exact_copy._sha256(
            "bad",
            label="demo",
        )


def test_exact_copy_file_sha_requires_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        exact_copy._file_sha256(tmp_path / "missing")


def test_exact_copy_json_loader_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        exact_copy._load_json_object(
            tmp_path / "missing.json",
            label="demo",
        )


@pytest.mark.parametrize(
    "content",
    [
        "{",
        "[]",
    ],
)
def test_exact_copy_json_loader_invalid(
    tmp_path,
    content,
):
    path = tmp_path / "input.json"
    path.write_text(
        content,
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy._load_json_object(
            path,
            label="demo",
        )


def test_exact_copy_mapping_guard():
    with pytest.raises(BenchmarkIntegrityError):
        exact_copy._mapping(
            {},
            "missing",
        )


def test_exact_copy_requires_distinct_trees(tmp_path):
    root = tmp_path / "tree"
    child = root / "child"

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy._assert_distinct_trees(
            root,
            root,
        )

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy._assert_distinct_trees(
            root,
            child,
        )


def test_exact_copy_provenance_must_be_external(
    tmp_path,
):
    candidate = tmp_path / "candidate"
    reference = tmp_path / "reference"

    candidate.mkdir()
    reference.mkdir()

    evidence = candidate / "evidence.txt"
    evidence.write_text(
        "x",
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy._reference_provenance_digest(
            evidence,
            candidate_root=candidate,
            reference_root=reference,
        )


@pytest.mark.parametrize(
    "inventory",
    [
        None,
        {},
        {"files": []},
        {"files": ["wrong"]},
    ],
)
def test_exact_copy_recovery_manifest_guards(
    inventory,
):
    record = {}

    if inventory is not None:
        record["inventory"] = inventory

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy._recovery_manifest(record)


def test_exact_copy_decision_derivations():
    decision, result = exact_copy._derive_result(
        review_status="pending_review",
        reference_binding_verified=False,
        exact_manifest_match=True,
    )

    assert decision == "pending_review"
    assert not result["exact_copy_identity_verified"]

    decision, result = exact_copy._derive_result(
        review_status="reviewed",
        reference_binding_verified=True,
        exact_manifest_match=True,
    )

    assert decision == "verified_against_reviewed_reference_manifest"
    assert result["exact_copy_identity_verified"]

    decision, _ = exact_copy._derive_result(
        review_status="reviewed",
        reference_binding_verified=False,
        exact_manifest_match=True,
    )

    assert decision == "not_verified"


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (
            ("candidate_kind",),
            "authoritative_copy",
        ),
        (
            ("recovery_record_fingerprint_sha256",),
            "bad",
        ),
        (
            ("recovery_tree_fingerprint_sha256",),
            "bad",
        ),
        (
            ("candidate_screen_fingerprint_sha256",),
            "bad",
        ),
        (
            ("candidate_inventory_fingerprint_sha256",),
            "bad",
        ),
        (
            (
                "selected_file",
                "relative_path",
            ),
            "../escape.mat",
        ),
        (
            (
                "selected_file",
                "sha256",
            ),
            "bad",
        ),
        (
            (
                "selected_file",
                "bytes",
            ),
            True,
        ),
        (
            (
                "selected_file",
                "bytes",
            ),
            0,
        ),
    ],
)
def test_exact_copy_candidate_binding_guards(
    path,
    value,
):
    record = _exact_record()

    _set_path(
        record["candidate_binding"],
        path,
        value,
    )

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


def test_exact_copy_candidate_schema_guard():
    record = _exact_record()
    record["candidate_binding"]["unexpected"] = True

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


def test_exact_copy_selected_file_schema_guard():
    record = _exact_record()
    record["candidate_binding"]["selected_file"]["extra"] = True

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (
            ("reference_inventory_fingerprint_sha256",),
            "bad",
        ),
        (
            ("reference_provenance_sha256",),
            "bad",
        ),
        (
            ("reference_file_count",),
            True,
        ),
        (
            ("reference_file_count",),
            0,
        ),
        (
            ("reference_total_bytes",),
            0,
        ),
        (
            (
                "comparison",
                "method",
            ),
            "wrong",
        ),
        (
            (
                "comparison",
                "candidate_file_count",
            ),
            -1,
        ),
        (
            (
                "comparison",
                "path_set_equal",
            ),
            "yes",
        ),
        (
            (
                "comparison",
                "exact_manifest_match",
            ),
            1,
        ),
        (
            (
                "comparison",
                "reference_file_count",
            ),
            2,
        ),
        (
            (
                "comparison",
                "reference_total_bytes",
            ),
            20,
        ),
    ],
)
def test_exact_copy_reference_comparison_guards(
    path,
    value,
):
    record = _exact_record()

    _set_path(
        record,
        path,
        value,
    )

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


def test_exact_copy_reference_schema_guard():
    record = _exact_record()
    record["reference_binding"]["extra"] = True

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


def test_exact_copy_comparison_schema_guard():
    record = _exact_record()
    record["comparison"]["extra"] = True

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


def test_exact_copy_manifest_fingerprint_derivation_guard():
    record = _exact_record()
    record["comparison"]["exact_manifest_match"] = True

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


def test_exact_copy_exact_match_requires_identical_paths():
    record = _exact_record(
        exact_match=True,
        reviewed=True,
    )

    record["comparison"]["path_set_equal"] = False

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


def test_exact_copy_exact_match_requires_zero_differences():
    record = _exact_record(
        exact_match=True,
        reviewed=True,
    )

    record["comparison"]["candidate_only_path_count"] = 1

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (
            ("record_type",),
            "wrong",
        ),
        (
            ("dataset",),
            "wrong",
        ),
        (
            ("readiness_record_fingerprint_sha256",),
            "bad",
        ),
        (
            (
                "first_party_binding",
                "request_fingerprint_sha256",
            ),
            "bad",
        ),
        (
            (
                "review",
                "status",
            ),
            "bad",
        ),
        (
            (
                "review",
                "reference_binding_verified",
            ),
            "yes",
        ),
        (
            ("decision",),
            "wrong",
        ),
        (
            ("result",),
            {},
        ),
        (
            ("privacy_boundary",),
            {},
        ),
        (
            ("scientific_boundary",),
            {},
        ),
        (
            ("claim_limit",),
            "wrong",
        ),
        (
            ("record_fingerprint_sha256",),
            "0" * 64,
        ),
    ],
)
def test_exact_copy_top_level_semantic_guards(
    path,
    value,
):
    record = _exact_record()

    _set_path(
        record,
        path,
        value,
    )

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


def test_exact_copy_top_level_schema_guard():
    record = _exact_record()
    record["extra"] = True

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


def test_exact_copy_first_party_schema_guard():
    record = _exact_record()
    record["first_party_binding"]["extra"] = True

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


def test_exact_copy_review_schema_guard():
    record = _exact_record()
    record["review"]["extra"] = True

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


def test_exact_copy_pending_cannot_verify_reference():
    record = _exact_record()
    record["review"]["reference_binding_verified"] = True

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


@pytest.mark.parametrize(
    "field",
    [
        "reviewer",
        "reviewed_at",
        "evidence_basis",
    ],
)
def test_exact_copy_reviewed_fields_must_be_resolved(
    field,
):
    record = _exact_record(
        exact_match=False,
        reviewed=True,
    )

    record["review"][field] = "unknown"

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.validate_gaze_in_wild_exact_copy_review(record)


def test_exact_copy_review_function_requires_boolean():
    with pytest.raises(ValueError):
        exact_copy.review_gaze_in_wild_exact_copy_record(
            _exact_record(),
            reviewer="Reviewer",
            reviewed_at="2026-09-23T10:00:00Z",
            reference_binding_verified="yes",
            evidence_basis="review",
        )


def test_exact_copy_write_guards(
    tmp_path,
):
    candidate = tmp_path / "candidate"
    reference = tmp_path / "reference"

    candidate.mkdir()
    reference.mkdir()

    record = _exact_record()

    with pytest.raises(BenchmarkIntegrityError):
        exact_copy.write_gaze_in_wild_exact_copy_review(
            record,
            candidate / "review.json",
            candidate_root=candidate,
            reference_root=reference,
        )

    target = tmp_path / "review.json"

    assert (
        exact_copy.write_gaze_in_wild_exact_copy_review(
            record,
            target,
            candidate_root=candidate,
            reference_root=reference,
        )
        == target
    )

    with pytest.raises(FileExistsError):
        exact_copy.write_gaze_in_wild_exact_copy_review(
            record,
            target,
            candidate_root=candidate,
            reference_root=reference,
        )


def test_exact_copy_bind_type_guards():
    with pytest.raises(TypeError):
        exact_copy.bind_verified_exact_copy_review_to_quarantine_exit(
            object(),
            object(),
        )


# =====================================================================
# GIW CANDIDATE PREFLIGHT
# =====================================================================


def _screen_record():
    record = {
        "record_type": preflight.RECORD_TYPE,
        "candidate_status": preflight.CANDIDATE_STATUS,
        "dataset": "Gaze-in-the-Wild",
        "candidate_kind": "unknown_recovered_copy",
        "recovery_record_fingerprint_sha256": "a" * 64,
        "recovery_tree_fingerprint_sha256": "b" * 64,
        "selected_file": {
            "relative_path": "ProcessData/example.mat",
            "sha256": "c" * 64,
            "bytes": 100,
            "generic_recovery_role": "unclassified",
        },
        "processdata_preflight": {
            "path": "ProcessData/example.mat",
            "sha256": "c" * 64,
            "bytes": 100,
            "participant_index": 1,
            "trial_index": 2,
            "stored_rate_hz": 300.0,
            "inferred_processed_rate_hz": 300.0,
            "timestamp_count": 8,
            "timestamp_start_s": 0.0,
            "timestamp_end_s": 0.1,
            "por_shape": [8, 2],
            "confidence_shape": [8],
            "scene_resolution_px": [1920, 1080],
            "labels_present": True,
            "labels_shape": [8],
            "top_level_labeldata_present": False,
            "adapter_coordinate_fields_compatible": True,
            "timestamp_grid_valid": True,
        },
        "screening_policy": dict(preflight._SCREENING_POLICY),
        "scientific_boundary": dict(preflight._SCIENTIFIC_BOUNDARY),
        "claim_limit": preflight.CLAIM_LIMIT,
    }

    record["record_fingerprint_sha256"] = preflight.candidate_processdata_screen_fingerprint(record)

    return record


def _resign_screen(record):
    record["record_fingerprint_sha256"] = preflight.candidate_processdata_screen_fingerprint(record)


def test_candidate_preflight_valid_record():
    record = _screen_record()

    assert preflight.validate_gaze_in_wild_candidate_processdata_screen(record) == record


def test_candidate_preflight_json_loader_missing(
    tmp_path,
):
    with pytest.raises(FileNotFoundError):
        preflight._load_json_object(
            tmp_path / "missing.json",
            label="demo",
        )


@pytest.mark.parametrize(
    "content",
    [
        "{",
        "[]",
    ],
)
def test_candidate_preflight_json_loader_invalid(
    tmp_path,
    content,
):
    path = tmp_path / "record.json"
    path.write_text(
        content,
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError):
        preflight._load_json_object(
            path,
            label="demo",
        )


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "../x.mat",
        "/absolute.mat",
    ],
)
def test_candidate_safe_path_guards(value):
    with pytest.raises(BenchmarkIntegrityError):
        preflight._safe_relative_path(value)


def test_candidate_inventory_requires_mapping():
    with pytest.raises(BenchmarkIntegrityError):
        preflight._inventory_file(
            {},
            "a.mat",
        )


def test_candidate_inventory_requires_file_list():
    with pytest.raises(BenchmarkIntegrityError):
        preflight._inventory_file(
            {
                "inventory": {},
            },
            "a.mat",
        )


def test_candidate_inventory_requires_unclassified_role():
    recovery = {
        "inventory": {
            "files": [
                {
                    "path": "a.mat",
                    "role": "process_data",
                    "sha256": "a" * 64,
                    "bytes": 1,
                }
            ]
        }
    }

    with pytest.raises(BenchmarkIntegrityError):
        preflight._inventory_file(
            recovery,
            "a.mat",
        )


@pytest.mark.parametrize(
    "value",
    [
        True,
        0,
        1.5,
    ],
)
def test_candidate_positive_integer_guard(value):
    with pytest.raises(BenchmarkIntegrityError):
        preflight._positive_integer(
            value,
            field_name="demo",
        )


@pytest.mark.parametrize(
    "value",
    [
        True,
        "1",
        np.inf,
        np.nan,
    ],
)
def test_candidate_finite_number_guard(value):
    with pytest.raises(BenchmarkIntegrityError):
        preflight._finite_number(
            value,
            field_name="demo",
        )


def test_candidate_positive_number_guard():
    with pytest.raises(BenchmarkIntegrityError):
        preflight._finite_number(
            0.0,
            field_name="demo",
            positive=True,
        )


@pytest.mark.parametrize(
    "value",
    [
        "wrong",
        [1],
        [1, 0],
    ],
)
def test_candidate_shape_guard(value):
    with pytest.raises(BenchmarkIntegrityError):
        preflight._integer_shape(
            value,
            field_name="demo",
            length=2,
        )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (
            ("record_type",),
            "wrong",
        ),
        (
            ("candidate_status",),
            "verified",
        ),
        (
            ("dataset",),
            "wrong",
        ),
        (
            ("candidate_kind",),
            "authoritative",
        ),
        (
            ("recovery_record_fingerprint_sha256",),
            "bad",
        ),
        (
            ("recovery_tree_fingerprint_sha256",),
            "bad",
        ),
        (
            (
                "selected_file",
                "relative_path",
            ),
            "./ProcessData/example.mat",
        ),
        (
            (
                "selected_file",
                "sha256",
            ),
            "bad",
        ),
        (
            (
                "selected_file",
                "bytes",
            ),
            True,
        ),
        (
            (
                "selected_file",
                "bytes",
            ),
            -1,
        ),
        (
            (
                "selected_file",
                "generic_recovery_role",
            ),
            "process_data",
        ),
        (
            ("screening_policy",),
            {},
        ),
        (
            ("scientific_boundary",),
            {},
        ),
        (
            ("claim_limit",),
            "wrong",
        ),
        (
            ("record_fingerprint_sha256",),
            "0" * 64,
        ),
    ],
)
def test_candidate_screen_top_level_guards(
    path,
    value,
):
    record = _screen_record()

    _set_path(
        record,
        path,
        value,
    )

    with pytest.raises(BenchmarkIntegrityError):
        preflight.validate_gaze_in_wild_candidate_processdata_screen(record)


def test_candidate_selected_file_must_be_mapping():
    record = _screen_record()
    record["selected_file"] = None

    with pytest.raises(BenchmarkIntegrityError):
        preflight.validate_gaze_in_wild_candidate_processdata_screen(record)


def test_candidate_preflight_must_be_mapping():
    record = _screen_record()
    record["processdata_preflight"] = None

    with pytest.raises(BenchmarkIntegrityError):
        preflight.validate_gaze_in_wild_candidate_processdata_screen(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("path", "wrong.mat"),
        ("sha256", "d" * 64),
        ("bytes", 99),
        ("participant_index", 0),
        ("trial_index", True),
        ("stored_rate_hz", 0.0),
        (
            "inferred_processed_rate_hz",
            np.inf,
        ),
        ("timestamp_count", 1),
        ("timestamp_start_s", np.nan),
        ("timestamp_end_s", -1.0),
        ("por_shape", [7, 2]),
        ("confidence_shape", [7]),
        ("scene_resolution_px", [1920]),
        ("labels_present", "yes"),
        ("labels_shape", [7]),
        (
            "top_level_labeldata_present",
            "no",
        ),
        (
            "adapter_coordinate_fields_compatible",
            False,
        ),
        (
            "timestamp_grid_valid",
            False,
        ),
    ],
)
def test_candidate_processdata_observation_guards(
    field,
    value,
):
    record = _screen_record()

    record["processdata_preflight"][field] = value

    with pytest.raises(BenchmarkIntegrityError):
        preflight.validate_gaze_in_wild_candidate_processdata_screen(record)


def test_candidate_labels_shape_must_be_null_when_absent():
    record = _screen_record()

    record["processdata_preflight"]["labels_present"] = False

    record["processdata_preflight"]["labels_shape"] = [8]

    with pytest.raises(BenchmarkIntegrityError):
        preflight.validate_gaze_in_wild_candidate_processdata_screen(record)


def test_candidate_labels_absent_with_null_shape_valid():
    record = _screen_record()

    record["processdata_preflight"]["labels_present"] = False

    record["processdata_preflight"]["labels_shape"] = None

    _resign_screen(record)

    preflight.validate_gaze_in_wild_candidate_processdata_screen(record)


# =====================================================================
# CROSS-DATASET EVIDENCE
# =====================================================================


def _lineage_receipt():
    return SourceAuditLineageReceipt(
        dataset_key="hollywood2em",
        audit_template_fingerprint_sha256="1" * 64,
        authorization_fingerprint_sha256="2" * 64,
        authorized_spec_fingerprint_sha256="3" * 64,
        audit_report_fingerprint_sha256="4" * 64,
        source_manifest_fingerprints_sha256={
            "source": "5" * 64,
        },
        source_revision="reviewed-revision",
    )


def _cross_report():
    receipt = _lineage_receipt()
    receipt_dict = receipt.to_dict()

    design = {
        "design": "harmonised_cross_dataset_event_benchmark",
        "validation_design": "leave_one_dataset_out",
        "dataset_ids": [
            "Hollywood2EM",
            "Lund2013",
        ],
        "target_sampling_rate_hz": 60.0,
        "require_resolved_participants": True,
        "require_verified_coordinates": True,
        "require_source_audits": True,
        "models": [
            "RandomForest",
            "ContextMLP",
        ],
    }

    hollywood = {
        "participant_identity_resolved": True,
        "coordinate_unit_verified": True,
        "sampling_origin_at_analysis": "resampled",
        "target_sampling_rate_hz": 60.0,
        "source_audit_status": "verified",
        "source_audit_lineage_receipt_fingerprint_sha256": (
            receipt_dict["receipt_fingerprint_sha256"]
        ),
        "source_audit_report_fingerprint_sha256": (receipt.audit_report_fingerprint_sha256),
        "source_audit_spec_fingerprint_sha256": (receipt.authorized_spec_fingerprint_sha256),
        "source_manifest_fingerprint_sha256": (
            receipt.source_manifest_fingerprints_sha256["source"]
        ),
    }

    lund = {
        "participant_identity_resolved": True,
        "coordinate_unit_verified": True,
        "sampling_origin_at_analysis": "resampled",
        "target_sampling_rate_hz": 60.0,
    }

    reports = {
        "Hollywood2EM": hollywood,
        "Lund2013": lund,
    }

    summary = [
        {
            "model": model,
            "held_out_dataset": dataset,
            "n_test_rows": 10,
        }
        for model in (
            "RandomForest",
            "ContextMLP",
        )
        for dataset in (
            "Hollywood2EM",
            "Lund2013",
        )
    ]

    validation_fp = benchmark_fingerprint(
        {
            "design": design,
            "dataset_reports": reports,
            "summary": summary,
        }
    )

    body = {
        "benchmark": {
            "name": cross.CROSS_DATASET_BENCHMARK_NAME,
            "validation_scope": (cross.CROSS_DATASET_VALIDATION_SCOPE),
            "annotation_origin": "expert-manual",
            "sampling_origin": "resampled",
            "reference_strength": ("derived-human-reference"),
            "sampling_rates_hz": [60.0],
        },
        "model": {
            "models": [
                "RandomForest",
                "ContextMLP",
            ]
        },
        "protocol": {
            "evidence_schema": (cross.CROSS_DATASET_EVIDENCE_SCHEMA),
            "validation_design": design,
            "dataset_reports": reports,
            "hollywood2_source_audit_lineage": (receipt_dict),
            "cross_dataset_validation_fingerprint_sha256": (validation_fp),
            "scientific_boundary": dict(cross._BOUNDARY),
        },
        "metrics": {
            "summary": summary,
        },
    }

    return {
        **body,
        "report_fingerprint_sha256": (benchmark_fingerprint(body)),
    }


def _resign_cross(report):
    body = {
        key: report[key]
        for key in (
            "benchmark",
            "model",
            "protocol",
            "metrics",
        )
    }

    report["report_fingerprint_sha256"] = benchmark_fingerprint(body)


def test_cross_dataset_valid_synthetic_frozen_report():
    report = _cross_report()

    assert cross.validate_cross_dataset_frozen_report(report) == report


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("a" * 64, True),
        ("A" * 64, False),
        ("g" * 64, False),
        ("a" * 63, False),
        (None, False),
    ],
)
def test_cross_sha_guard(value, expected):
    assert cross._valid_sha256(value) is expected


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        " ",
    ],
)
def test_cross_text_guard(value):
    with pytest.raises(BenchmarkIntegrityError):
        cross._require_text(
            value,
            field_name="demo",
        )


def test_cross_mapping_guard():
    with pytest.raises(BenchmarkIntegrityError):
        cross._require_mapping(
            [],
            field_name="demo",
        )


def test_cross_exact_keys_guard():
    with pytest.raises(BenchmarkIntegrityError):
        cross._require_exact_keys(
            {"a": 1},
            frozenset({"a", "b"}),
            label="demo",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "design",
            "wrong",
        ),
        (
            "validation_design",
            "wrong",
        ),
        (
            "dataset_ids",
            ["Lund2013"],
        ),
        (
            "target_sampling_rate_hz",
            120.0,
        ),
        (
            "require_resolved_participants",
            False,
        ),
        (
            "require_verified_coordinates",
            False,
        ),
        (
            "require_source_audits",
            False,
        ),
        (
            "models",
            ["RandomForest"],
        ),
    ],
)
def test_cross_design_guards(
    field,
    value,
):
    design = copy.deepcopy(_cross_report()["protocol"]["validation_design"])

    design[field] = value

    with pytest.raises(BenchmarkIntegrityError):
        cross._validate_design(design)


@pytest.mark.parametrize(
    ("dataset", "field", "value"),
    [
        (
            "Lund2013",
            "participant_identity_resolved",
            False,
        ),
        (
            "Lund2013",
            "coordinate_unit_verified",
            False,
        ),
        (
            "Lund2013",
            "sampling_origin_at_analysis",
            "native",
        ),
        (
            "Lund2013",
            "target_sampling_rate_hz",
            120.0,
        ),
        (
            "Hollywood2EM",
            "source_audit_status",
            "pending",
        ),
        (
            "Hollywood2EM",
            "source_audit_lineage_receipt_fingerprint_sha256",
            "bad",
        ),
        (
            "Hollywood2EM",
            "source_audit_report_fingerprint_sha256",
            "bad",
        ),
        (
            "Hollywood2EM",
            "source_audit_spec_fingerprint_sha256",
            "bad",
        ),
        (
            "Hollywood2EM",
            "source_manifest_fingerprint_sha256",
            "bad",
        ),
    ],
)
def test_cross_dataset_report_guards(
    dataset,
    field,
    value,
):
    reports = copy.deepcopy(_cross_report()["protocol"]["dataset_reports"])

    reports[dataset][field] = value

    with pytest.raises(BenchmarkIntegrityError):
        cross._validate_dataset_reports(reports)


def test_cross_dataset_reports_require_exact_datasets():
    reports = copy.deepcopy(_cross_report()["protocol"]["dataset_reports"])

    reports.pop("Lund2013")

    with pytest.raises(BenchmarkIntegrityError):
        cross._validate_dataset_reports(reports)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "source_audit_lineage_receipt_fingerprint_sha256",
            "a" * 64,
        ),
        (
            "source_audit_report_fingerprint_sha256",
            "a" * 64,
        ),
        (
            "source_audit_spec_fingerprint_sha256",
            "a" * 64,
        ),
        (
            "source_manifest_fingerprint_sha256",
            "a" * 64,
        ),
    ],
)
def test_cross_lineage_must_match_runner_provenance(
    field,
    value,
):
    report = _cross_report()

    report["protocol"]["dataset_reports"]["Hollywood2EM"][field] = value

    with pytest.raises(BenchmarkIntegrityError):
        cross._validate_hollywood_lineage(
            report["protocol"]["hollywood2_source_audit_lineage"],
            report["protocol"]["dataset_reports"],
        )


def test_cross_lineage_requires_hollywood_receipt():
    payload = _lineage_receipt().to_dict()
    payload["dataset_key"] = "gaze-in-the-wild"

    body = dict(payload)
    body.pop(
        "receipt_fingerprint_sha256",
        None,
    )

    payload["receipt_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(BenchmarkIntegrityError):
        cross._validate_hollywood_lineage(
            payload,
            _cross_report()["protocol"]["dataset_reports"],
        )


def test_cross_summary_requires_four_rows():
    with pytest.raises(BenchmarkIntegrityError):
        cross._validate_summary([])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model", "Wrong"),
        ("held_out_dataset", "Wrong"),
        ("n_test_rows", 0),
    ],
)
def test_cross_summary_row_guards(
    field,
    value,
):
    rows = copy.deepcopy(_cross_report()["metrics"]["summary"])

    rows[0][field] = value

    with pytest.raises(BenchmarkIntegrityError):
        cross._validate_summary(rows)


def test_cross_summary_requires_mapping_rows():
    rows = copy.deepcopy(_cross_report()["metrics"]["summary"])

    rows[0] = "wrong"

    with pytest.raises(BenchmarkIntegrityError):
        cross._validate_summary(rows)


def test_cross_summary_duplicate_guard():
    rows = copy.deepcopy(_cross_report()["metrics"]["summary"])

    rows[1] = copy.deepcopy(rows[0])

    with pytest.raises(BenchmarkIntegrityError):
        cross._validate_summary(rows)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (
            ("report_fingerprint_sha256",),
            "bad",
        ),
        (
            (
                "benchmark",
                "name",
            ),
            "wrong",
        ),
        (
            (
                "benchmark",
                "validation_scope",
            ),
            "wrong",
        ),
        (
            (
                "benchmark",
                "annotation_origin",
            ),
            "automatic",
        ),
        (
            (
                "benchmark",
                "sampling_origin",
            ),
            "native",
        ),
        (
            (
                "benchmark",
                "reference_strength",
            ),
            "gold-standard",
        ),
        (
            (
                "benchmark",
                "sampling_rates_hz",
            ),
            [120.0],
        ),
        (
            (
                "model",
                "models",
            ),
            ["RandomForest"],
        ),
        (
            (
                "protocol",
                "evidence_schema",
            ),
            "wrong",
        ),
        (
            (
                "protocol",
                "scientific_boundary",
            ),
            {},
        ),
        (
            ("metrics",),
            {
                "summary": [],
                "extra": [],
            },
        ),
        (
            (
                "protocol",
                "cross_dataset_validation_fingerprint_sha256",
            ),
            "0" * 64,
        ),
    ],
)
def test_cross_frozen_report_semantic_guards(
    path,
    value,
):
    report = _cross_report()

    _set_path(
        report,
        path,
        value,
    )

    if path != ("report_fingerprint_sha256",):
        _resign_cross(report)

    with pytest.raises(BenchmarkIntegrityError):
        cross.validate_cross_dataset_frozen_report(report)


def test_cross_frozen_report_top_schema_guard():
    report = _cross_report()
    report["extra"] = True

    with pytest.raises(BenchmarkIntegrityError):
        cross.validate_cross_dataset_frozen_report(report)


def test_cross_protocol_schema_guard():
    report = _cross_report()

    report["protocol"]["extra"] = True
    _resign_cross(report)

    with pytest.raises(BenchmarkIntegrityError):
        cross.validate_cross_dataset_frozen_report(report)


def test_cross_report_fingerprint_mismatch():
    report = _cross_report()

    report["benchmark"]["name"] = "changed"

    with pytest.raises(BenchmarkIntegrityError):
        cross.validate_cross_dataset_frozen_report(report)


def test_cross_load_missing(tmp_path):
    with pytest.raises(BenchmarkIntegrityError):
        cross.load_cross_dataset_frozen_report(tmp_path / "missing.json")


@pytest.mark.parametrize(
    "content",
    [
        "{",
        "[]",
    ],
)
def test_cross_load_invalid(
    tmp_path,
    content,
):
    path = tmp_path / "report.json"
    path.write_text(
        content,
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError):
        cross.load_cross_dataset_frozen_report(path)


def test_cross_builder_type_guards():
    with pytest.raises(TypeError):
        cross.build_lund_hollywood2_cross_dataset_report(
            object(),
            object(),
            hollywood2_lineage=_lineage_receipt(),
            benchmark_version="1",
        )


def test_cross_freeze_roundtrip(
    tmp_path,
):
    report = _cross_report()

    path = tmp_path / "report.json"

    frozen = cross.freeze_cross_dataset_frozen_report(
        report,
        path,
    )

    assert frozen == path

    loaded = cross.load_cross_dataset_frozen_report(path)

    assert loaded == report


# =====================================================================
# HOLLYWOOD2 COORDINATE EVIDENCE
# =====================================================================


def _coordinate_record():
    return json.loads(COORDINATE_EVIDENCE.read_text(encoding="utf-8"))


def _mutated_coordinate(
    monkeypatch,
    path,
    value,
):
    record = _coordinate_record()

    _set_path(
        record,
        path,
        value,
    )

    fingerprint = coordinate.evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = fingerprint

    monkeypatch.setattr(
        coordinate,
        "EVIDENCE_FINGERPRINT",
        fingerprint,
    )

    return record


def test_coordinate_immutable_baseline():
    record = coordinate.validate_hollywood2_coordinate_evidence(COORDINATE_EVIDENCE)

    assert record["verification"]["coordinate_unit_verified"] is True


def test_coordinate_require_false_guard():
    with pytest.raises(BenchmarkIntegrityError):
        coordinate._require_false(
            {
                "x": True,
            },
            "x",
        )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (
            ("record_type",),
            "wrong",
        ),
        (
            ("status",),
            "wrong",
        ),
        (
            (
                "canonical_source",
                "repository",
            ),
            "wrong",
        ),
        (
            (
                "canonical_source",
                "commit_sha1",
            ),
            "wrong",
        ),
        (
            (
                "canonical_source",
                "authoritative_ground_truth_evidence_fingerprint_sha256",
            ),
            "wrong",
        ),
        (
            (
                "author_input_convention",
                "repository",
            ),
            "wrong",
        ),
        (
            (
                "author_input_convention",
                "commit_sha1",
            ),
            "wrong",
        ),
        (
            (
                "author_input_convention",
                "readme_git_blob_sha1",
            ),
            "wrong",
        ),
        (
            (
                "author_input_convention",
                "coordinate_unit",
            ),
            "degrees",
        ),
        (
            (
                "author_input_convention",
                "time_unit",
            ),
            "seconds",
        ),
        (
            (
                "author_input_convention",
                "required_geometry_metadata_keys",
            ),
            [],
        ),
        (
            (
                "reviewed_header_probe",
                "probe_fingerprint_sha256",
            ),
            "wrong",
        ),
        (
            (
                "reviewed_header_probe",
                "arff_file_count",
            ),
            1,
        ),
        (
            (
                "reviewed_header_probe",
                "required_gaze_schema_file_count",
            ),
            1,
        ),
        (
            (
                "reviewed_header_probe",
                "author_convention_metadata_complete_file_count",
            ),
            1,
        ),
        (
            (
                "reviewed_header_probe",
                "metadata_key_file_counts",
            ),
            {},
        ),
        (
            (
                "reviewed_header_probe",
                "metadata_signature_count",
            ),
            1,
        ),
        (
            (
                "reviewed_header_probe",
                "attribute_signature",
            ),
            [],
        ),
        (
            (
                "reviewed_header_probe",
                "raw_source_rows_read",
            ),
            True,
        ),
        (
            (
                "verification",
                "coordinate_unit",
            ),
            "degrees",
        ),
        (
            (
                "verification",
                "coordinate_unit_verified",
            ),
            False,
        ),
        (
            (
                "rights_boundary",
                "new_analysis_permission_created",
            ),
            True,
        ),
        (
            (
                "rights_boundary",
                "new_redistribution_permission_created",
            ),
            True,
        ),
        (
            (
                "rights_boundary",
                "exact_annotation_repository_license_verified",
            ),
            True,
        ),
        (
            (
                "scientific_boundary",
                "pixel_to_visual_angle_conversion_verified",
            ),
            True,
        ),
        (
            (
                "scientific_boundary",
                "participant_identity_mapping_verified",
            ),
            True,
        ),
        (
            (
                "scientific_boundary",
                "cross_dataset_validation_created",
            ),
            True,
        ),
    ],
)
def test_coordinate_evidence_deep_guards(
    monkeypatch,
    path,
    value,
):
    record = _mutated_coordinate(
        monkeypatch,
        path,
        value,
    )

    with pytest.raises(BenchmarkIntegrityError):
        coordinate.validate_hollywood2_coordinate_evidence(record)


def test_coordinate_stored_fingerprint_guard():
    record = _coordinate_record()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(BenchmarkIntegrityError):
        coordinate.validate_hollywood2_coordinate_evidence(record)


def test_coordinate_content_fingerprint_guard():
    record = _coordinate_record()

    record["verification"]["coordinate_unit"] = "degrees"

    with pytest.raises(BenchmarkIntegrityError):
        coordinate.validate_hollywood2_coordinate_evidence(record)


def test_coordinate_author_convention_normalizes_whitespace():
    text = """
    %@METADATA width_px 1280
    %@METADATA height_px 720
    %@METADATA width_mm 400
    %@METADATA height_mm 225
    %@METADATA distance_mm 450

    time   (in   microseconds)

    coordinates   (in   pixels;
    """

    coordinate.validate_author_input_convention(text)


def _live_probe_context(monkeypatch):
    live = _reviewed_live_probe()

    monkeypatch.setattr(
        coordinate,
        "validate_hollywood2_coordinate_evidence",
        lambda value: {},
    )

    monkeypatch.setattr(
        coordinate,
        "REVIEWED_LIVE_PROBE_FINGERPRINT",
        live["probe_fingerprint_sha256"],
    )

    return live


def test_coordinate_live_probe_baseline(
    monkeypatch,
):
    live = _live_probe_context(monkeypatch)

    coordinate.validate_live_probe_against_coordinate_evidence(
        live,
        {},
    )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (
            (
                "source_binding",
                "repository",
            ),
            "wrong",
        ),
        (
            (
                "source_binding",
                "commit_sha1",
            ),
            "wrong",
        ),
        (
            (
                "header_inventory",
                "arff_file_count",
            ),
            1,
        ),
        (
            (
                "header_inventory",
                "required_gaze_schema_file_count",
            ),
            1,
        ),
        (
            (
                "header_inventory",
                "author_convention_metadata_complete_file_count",
            ),
            1,
        ),
        (
            (
                "header_inventory",
                "metadata_key_file_counts",
            ),
            {},
        ),
        (
            (
                "header_inventory",
                "attribute_signatures",
            ),
            [],
        ),
        (
            (
                "header_inventory",
                "metadata_signatures",
            ),
            [],
        ),
        (
            (
                "coordinate_boundary",
                "all_headers_match_author_input_metadata_convention",
            ),
            False,
        ),
        (
            (
                "coordinate_boundary",
                "coordinate_unit_candidate",
            ),
            "degrees",
        ),
        (
            (
                "coordinate_boundary",
                "coordinate_unit_verified",
            ),
            True,
        ),
        (
            (
                "mapping_boundary",
                "participant_identity_mapping_verified",
            ),
            True,
        ),
        (
            (
                "rights_boundary",
                "new_rights_permission_created",
            ),
            True,
        ),
        (
            (
                "scientific_boundary",
                "raw_source_rows_read",
            ),
            True,
        ),
        (
            (
                "scientific_boundary",
                "cross_dataset_validation_created",
            ),
            True,
        ),
    ],
)
def test_coordinate_live_probe_deep_guards(
    monkeypatch,
    path,
    value,
):
    live = _reviewed_live_probe()

    _set_path(
        live,
        path,
        value,
    )

    live["probe_fingerprint_sha256"] = coordinate.probe_fingerprint(live)

    monkeypatch.setattr(
        coordinate,
        "validate_hollywood2_coordinate_evidence",
        lambda value: {},
    )

    monkeypatch.setattr(
        coordinate,
        "REVIEWED_LIVE_PROBE_FINGERPRINT",
        live["probe_fingerprint_sha256"],
    )

    with pytest.raises(BenchmarkIntegrityError):
        coordinate.validate_live_probe_against_coordinate_evidence(
            live,
            {},
        )


def test_coordinate_live_geometry_signature_sum_guard(
    monkeypatch,
):
    live = _reviewed_live_probe()

    live["header_inventory"]["metadata_signatures"][0]["file_count"] = 2

    live["probe_fingerprint_sha256"] = coordinate.probe_fingerprint(live)

    monkeypatch.setattr(
        coordinate,
        "validate_hollywood2_coordinate_evidence",
        lambda value: {},
    )

    monkeypatch.setattr(
        coordinate,
        "REVIEWED_LIVE_PROBE_FINGERPRINT",
        live["probe_fingerprint_sha256"],
    )

    with pytest.raises(BenchmarkIntegrityError):
        coordinate.validate_live_probe_against_coordinate_evidence(
            live,
            {},
        )


def test_coordinate_live_probe_bad_self_fingerprint(
    monkeypatch,
):
    live = _reviewed_live_probe()

    monkeypatch.setattr(
        coordinate,
        "validate_hollywood2_coordinate_evidence",
        lambda value: {},
    )

    live["probe_fingerprint_sha256"] = "0" * 64

    with pytest.raises(BenchmarkIntegrityError):
        coordinate.validate_live_probe_against_coordinate_evidence(
            live,
            {},
        )
