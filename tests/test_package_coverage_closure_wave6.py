from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

import gazeforge.cross_dataset_scientific_review as cross_review
import gazeforge.gaze_in_wild_audit as giw_audit
import gazeforge.gaze_in_wild_coordinate_evidence as giw_coordinate
import gazeforge.gaze_in_wild_exact_validation_v2 as giw_exact_v2
import gazeforge.gaze_in_wild_explicit_task_mapping_intake as giw_task_intake
import gazeforge.gaze_in_wild_participant_task_evidence as giw_participant
import gazeforge.lund_suite as lund_suite
import gazeforge.native_scientific_review as native_review
import gazeforge.source_audit_lineage as lineage
import gazeforge.source_candidate_review as candidate_review
import gazeforge.visus_intake as visus_intake
import gazeforge.visus_prediction as visus_prediction
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError

# ======================================================================
# source_audit_lineage.py
# ======================================================================


def _lineage_kwargs(dataset_key="hollywood2em"):
    values = {
        "dataset_key": dataset_key,
        "audit_template_fingerprint_sha256": "a" * 64,
        "authorization_fingerprint_sha256": "b" * 64,
        "authorized_spec_fingerprint_sha256": "c" * 64,
        "audit_report_fingerprint_sha256": "d" * 64,
        "source_manifest_fingerprints_sha256": (
            {"source": "e" * 64}
            if dataset_key == "hollywood2em"
            else {
                "label": "e" * 64,
                "process": "f" * 64,
            }
        ),
        "source_revision": "reviewed-revision",
    }
    if dataset_key == "gaze-in-the-wild":
        values["quarantine_exit_fingerprint_sha256"] = "9" * 64
    return values


def test_lineage_receipt_rejects_unknown_dataset():
    values = _lineage_kwargs()
    values["dataset_key"] = "unknown"

    with pytest.raises(ValueError, match="Unsupported"):
        lineage.SourceAuditLineageReceipt(**values)


def test_lineage_receipt_rejects_bad_core_digest():
    values = _lineage_kwargs()
    values["audit_template_fingerprint_sha256"] = "bad"

    with pytest.raises(ValueError, match="64 hexadecimal"):
        lineage.SourceAuditLineageReceipt(**values)


def test_lineage_giw_requires_quarantine_exit():
    values = _lineage_kwargs("gaze-in-the-wild")
    values["quarantine_exit_fingerprint_sha256"] = None

    with pytest.raises(ValueError, match="requires a quarantine-exit"):
        lineage.SourceAuditLineageReceipt(**values)


def test_lineage_giw_rejects_bad_quarantine_digest():
    values = _lineage_kwargs("gaze-in-the-wild")
    values["quarantine_exit_fingerprint_sha256"] = "bad"

    with pytest.raises(ValueError, match="64 hexadecimal"):
        lineage.SourceAuditLineageReceipt(**values)


def test_lineage_hollywood_rejects_quarantine_exit():
    values = _lineage_kwargs()
    values["quarantine_exit_fingerprint_sha256"] = "9" * 64

    with pytest.raises(ValueError, match="cannot carry"):
        lineage.SourceAuditLineageReceipt(**values)


def test_lineage_requires_true_audit_verified():
    values = _lineage_kwargs()
    values["source_audit_verified"] = False

    with pytest.raises(ValueError, match="source_audit_verified"):
        lineage.SourceAuditLineageReceipt(**values)


def test_lineage_requires_true_lineage_verified():
    values = _lineage_kwargs()
    values["lineage_verified"] = False

    with pytest.raises(ValueError, match="lineage_verified"):
        lineage.SourceAuditLineageReceipt(**values)


def test_lineage_requires_source_revision():
    values = _lineage_kwargs()
    values["source_revision"] = " "

    with pytest.raises(ValueError, match="source_revision"):
        lineage.SourceAuditLineageReceipt(**values)


def test_lineage_manifest_keys_follow_dataset_contract():
    values = _lineage_kwargs()
    values["source_manifest_fingerprints_sha256"] = {
        "label": "e" * 64,
    }

    with pytest.raises(ValueError, match="dataset audit contract"):
        lineage.SourceAuditLineageReceipt(**values)


def test_lineage_manifest_digest_must_be_sha256():
    values = _lineage_kwargs()
    values["source_manifest_fingerprints_sha256"] = {
        "source": "bad",
    }

    with pytest.raises(ValueError, match="64 hexadecimal"):
        lineage.SourceAuditLineageReceipt(**values)


def test_lineage_to_dict_hollywood_omits_quarantine_exit():
    receipt = lineage.SourceAuditLineageReceipt(**_lineage_kwargs())
    payload = receipt.to_dict()

    assert "quarantine_exit_fingerprint_sha256" not in payload
    assert payload["record_type"] == lineage._RECORD_TYPE


def test_lineage_to_dict_giw_retains_quarantine_exit():
    receipt = lineage.SourceAuditLineageReceipt(**_lineage_kwargs("gaze-in-the-wild"))
    payload = receipt.to_dict()

    assert payload["quarantine_exit_fingerprint_sha256"] == "9" * 64


def test_lineage_from_dict_rejects_record_type():
    with pytest.raises(BenchmarkIntegrityError, match="record_type"):
        lineage.SourceAuditLineageReceipt.from_dict({"record_type": "wrong"})


def test_lineage_from_dict_rejects_boundary():
    with pytest.raises(BenchmarkIntegrityError, match="scientific_boundary"):
        lineage.SourceAuditLineageReceipt.from_dict(
            {
                "record_type": lineage._RECORD_TYPE,
                "scientific_boundary": {},
            }
        )


def test_lineage_from_dict_rejects_invalid_fingerprint():
    with pytest.raises(BenchmarkIntegrityError, match="receipt_fingerprint"):
        lineage.SourceAuditLineageReceipt.from_dict(
            {
                "record_type": lineage._RECORD_TYPE,
                "scientific_boundary": dict(lineage._SCIENTIFIC_BOUNDARY),
                "receipt_fingerprint_sha256": "bad",
            }
        )


def test_lineage_from_dict_rejects_fingerprint_mismatch():
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint mismatch"):
        lineage.SourceAuditLineageReceipt.from_dict(
            {
                "record_type": lineage._RECORD_TYPE,
                "scientific_boundary": dict(lineage._SCIENTIFIC_BOUNDARY),
                "receipt_fingerprint_sha256": "a" * 64,
            }
        )


def test_lineage_dataset_key_rejects_wrong_spec_type():
    with pytest.raises(TypeError, match="spec must be"):
        lineage._dataset_key(object())


def test_lineage_mapping_guard():
    with pytest.raises(BenchmarkIntegrityError, match="JSON object"):
        lineage._require_mapping(
            [],
            field_name="demo",
        )


def test_lineage_report_fingerprint_missing():
    with pytest.raises(BenchmarkIntegrityError, match="missing or invalid"):
        lineage._validate_report_fingerprint({})


def test_lineage_report_fingerprint_mismatch():
    with pytest.raises(BenchmarkIntegrityError, match="mismatch"):
        lineage._validate_report_fingerprint(
            {
                "report_fingerprint_sha256": "a" * 64,
                "value": 1,
            }
        )


def test_lineage_equality_guard():
    with pytest.raises(BenchmarkIntegrityError, match="does not match"):
        lineage._require_equal(
            "a",
            "b",
            field_name="demo",
        )


def test_lineage_inventory_requires_exact_match():
    with pytest.raises(BenchmarkIntegrityError, match="exact inventory"):
        lineage._validated_inventory_fingerprint(
            {
                "exact_inventory_match": False,
            },
            fingerprint_key="manifest_fingerprint_sha256",
            label="demo",
        )


def test_lineage_inventory_requires_list():
    with pytest.raises(BenchmarkIntegrityError, match="JSON list"):
        lineage._validated_inventory_fingerprint(
            {
                "exact_inventory_match": True,
                "files": {},
            },
            fingerprint_key="manifest_fingerprint_sha256",
            label="demo",
        )


def test_lineage_inventory_requires_matching_count():
    with pytest.raises(BenchmarkIntegrityError, match="file count"):
        lineage._validated_inventory_fingerprint(
            {
                "exact_inventory_match": True,
                "files": [],
                "file_count": 1,
            },
            fingerprint_key="manifest_fingerprint_sha256",
            label="demo",
        )


def test_lineage_inventory_requires_valid_fingerprint():
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint is invalid"):
        lineage._validated_inventory_fingerprint(
            {
                "exact_inventory_match": True,
                "files": [],
                "file_count": 0,
                "manifest_fingerprint_sha256": "bad",
            },
            fingerprint_key="manifest_fingerprint_sha256",
            label="demo",
        )


def test_lineage_inventory_rejects_fingerprint_mismatch():
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint mismatch"):
        lineage._validated_inventory_fingerprint(
            {
                "exact_inventory_match": True,
                "files": [],
                "file_count": 0,
                "manifest_fingerprint_sha256": "a" * 64,
            },
            fingerprint_key="manifest_fingerprint_sha256",
            label="demo",
        )


def test_lineage_inventory_success():
    files = [{"path": "x"}]
    expected = benchmark_fingerprint(files)

    observed = lineage._validated_inventory_fingerprint(
        {
            "exact_inventory_match": True,
            "files": files,
            "file_count": 1,
            "manifest_fingerprint_sha256": expected,
        },
        fingerprint_key="manifest_fingerprint_sha256",
        label="demo",
    )

    assert observed == expected


def test_lineage_write_requires_receipt(tmp_path):
    with pytest.raises(TypeError, match="receipt must be"):
        lineage.write_source_audit_lineage_receipt(
            object(),
            tmp_path / "receipt.json",
            candidate_root=tmp_path / "candidate",
        )


def test_lineage_load_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        lineage.load_source_audit_lineage_receipt(tmp_path / "missing.json")


def test_lineage_load_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="valid UTF-8 JSON"):
        lineage.load_source_audit_lineage_receipt(path)


def test_lineage_load_nonobject(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="one JSON object"):
        lineage.load_source_audit_lineage_receipt(path)


# ======================================================================
# gaze_in_wild_audit.py
# ======================================================================


@pytest.mark.parametrize(
    "value",
    [
        "/absolute/file.mat",
        "../escape.mat",
        "folder/../escape.mat",
    ],
)
def test_giw_audit_safe_mat_path_rejects_unsafe(value):
    with pytest.raises(ValueError, match="safe relative"):
        giw_audit._safe_mat_path(
            value,
            field_name="demo",
        )


def test_giw_audit_safe_mat_path_requires_mat():
    with pytest.raises(ValueError, match=r"\.mat"):
        giw_audit._safe_mat_path(
            "file.txt",
            field_name="demo",
        )


def test_giw_audit_sha256_guard():
    with pytest.raises(ValueError, match="64 hexadecimal"):
        giw_audit._sha256(
            "bad",
            field_name="demo",
        )


@pytest.mark.parametrize(
    "value",
    ["", "__unresolved__", "unknown", "none"],
)
def test_giw_audit_resolved_identity_guard(value):
    with pytest.raises(ValueError, match="resolved identity"):
        giw_audit._resolved(
            value,
            field_name="demo",
        )


def test_giw_process_file_requires_positive_bytes():
    with pytest.raises(ValueError, match="process bytes"):
        giw_audit.GazeInWildProcessFileRecord(
            path="ProcessData/test.mat",
            sha256="a" * 64,
            bytes=0,
        )


def test_giw_label_file_requires_positive_bytes():
    with pytest.raises(ValueError, match="label bytes"):
        giw_audit.GazeInWildLabelFileRecord(
            path="LabelData/test.mat",
            sha256="a" * 64,
            bytes=0,
            participant_id="P1",
            trial_id="T1",
            labeller_id=1,
            process_path="ProcessData/test.mat",
        )


def test_giw_label_file_requires_resolved_participant():
    with pytest.raises(ValueError, match="participant_id"):
        giw_audit.GazeInWildLabelFileRecord(
            path="LabelData/test.mat",
            sha256="a" * 64,
            bytes=1,
            participant_id="unknown",
            trial_id="T1",
            labeller_id=1,
            process_path="ProcessData/test.mat",
        )


def test_giw_label_file_requires_positive_labeller():
    with pytest.raises(ValueError, match="labeller_id"):
        giw_audit.GazeInWildLabelFileRecord(
            path="LabelData/test.mat",
            sha256="a" * 64,
            bytes=1,
            participant_id="P1",
            trial_id="T1",
            labeller_id=0,
            process_path="ProcessData/test.mat",
        )


def test_giw_audit_spec_loader_rejects_nonobject(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="one JSON object"):
        giw_audit.load_gaze_in_wild_source_audit_spec(path)


def test_giw_inventory_detects_missing_manifest_file(tmp_path):
    record = SimpleNamespace(path="missing.mat")

    with pytest.raises(SchemaError, match="inventory does not match"):
        giw_audit._inventory(
            tmp_path,
            [record],
            label="demo",
        )


def test_giw_group_by_labeller_requires_run():
    with pytest.raises(TypeError, match="GazeInWildSourceAuditRun"):
        giw_audit.audited_gaze_in_wild_files_by_labeller(object())


def test_giw_sampling_table_requires_run():
    with pytest.raises(TypeError, match="GazeInWildSourceAuditRun"):
        giw_audit.gaze_in_wild_sampling_rate_table(object())


# ======================================================================
# explicit task mapping intake
# ======================================================================


def test_task_intake_exact_keys_guard():
    with pytest.raises(BenchmarkIntegrityError, match="schema drifted"):
        giw_task_intake._require_exact_keys(
            {"a": 1},
            {"a", "b"},
            label="demo",
        )


def test_task_intake_read_bounded_requires_file(tmp_path):
    with pytest.raises(BenchmarkIntegrityError, match="not a regular file"):
        giw_task_intake._read_bounded(
            tmp_path / "missing.json",
            max_bytes=100,
            label="demo",
        )


def test_task_intake_read_bounded_rejects_empty(tmp_path):
    path = tmp_path / "empty.json"
    path.write_bytes(b"")

    with pytest.raises(BenchmarkIntegrityError, match="outside the allowed"):
        giw_task_intake._read_bounded(
            path,
            max_bytes=100,
            label="demo",
        )


def test_task_intake_read_bounded_rejects_oversized(tmp_path):
    path = tmp_path / "large.json"
    path.write_bytes(b"12")

    with pytest.raises(BenchmarkIntegrityError, match="outside the allowed"):
        giw_task_intake._read_bounded(
            path,
            max_bytes=1,
            label="demo",
        )


@pytest.mark.parametrize(
    "payload",
    [
        b"\xff",
        b"{",
    ],
)
def test_task_intake_json_bytes_reject_invalid(payload):
    with pytest.raises(BenchmarkIntegrityError, match="valid UTF-8 JSON"):
        giw_task_intake._load_json_bytes(
            payload,
            label="demo",
        )


def test_task_intake_json_bytes_requires_object():
    with pytest.raises(BenchmarkIntegrityError, match="one JSON object"):
        giw_task_intake._load_json_bytes(
            b"[]",
            label="demo",
        )


def test_task_intake_resolved_text_required():
    with pytest.raises(BenchmarkIntegrityError, match="requires resolved"):
        giw_task_intake._resolved_text(
            None,
            label="demo",
        )


def test_task_intake_resolved_text_length_guard():
    with pytest.raises(BenchmarkIntegrityError, match="text-size guardrail"):
        giw_task_intake._resolved_text(
            "x" * (giw_task_intake.MAX_TEXT_FIELD_LENGTH + 1),
            label="demo",
        )


def test_task_intake_sha_guard():
    with pytest.raises(BenchmarkIntegrityError, match="lowercase SHA-256"):
        giw_task_intake._sha256(
            "A" * 64,
            label="demo",
        )


@pytest.mark.parametrize(
    "value",
    [
        True,
        "not-an-index",
        1.5,
    ],
)
def test_task_intake_trial_index_type_guard(value):
    with pytest.raises(BenchmarkIntegrityError, match="integer"):
        giw_task_intake._trial_index(value)


def test_task_intake_trial_index_range_guard():
    with pytest.raises(BenchmarkIntegrityError, match="unknown TrIdx"):
        giw_task_intake._trial_index(99)


def test_task_intake_trial_index_accepts_string_integer():
    assert giw_task_intake._trial_index("1") == 1


def test_task_intake_review_timestamp_requires_iso():
    with pytest.raises(BenchmarkIntegrityError, match="ISO-8601"):
        giw_task_intake._validate_review_timestamp("not-a-time")


def test_task_intake_review_timestamp_requires_timezone():
    with pytest.raises(BenchmarkIntegrityError, match="timezone"):
        giw_task_intake._validate_review_timestamp("2026-09-23T01:00:00")


def test_task_intake_review_timestamp_accepts_utc():
    observed = giw_task_intake._validate_review_timestamp("2026-09-23T01:00:00Z")

    assert observed.endswith("Z")


# ======================================================================
# participant/task evidence
# ======================================================================


def test_participant_task_require_false_guard():
    with pytest.raises(BenchmarkIntegrityError, match="must remain false"):
        giw_participant._require_false(
            {"promoted": True},
            "promoted",
        )


def test_participant_matrix_rejects_participant_set():
    with pytest.raises(BenchmarkIntegrityError, match="participant set"):
        giw_participant._validate_matrix({})


def _matrix_prefix():
    return {
        "participant_ids": list(giw_participant.PARTICIPANT_IDS),
        "participant_count": len(giw_participant.PARTICIPANT_IDS),
        "task_columns": list(giw_participant.TASKS),
        "status_counts": dict(giw_participant._EXPECTED_STATUS_COUNTS),
    }


def test_participant_matrix_rejects_row_count():
    matrix = _matrix_prefix()
    matrix["participants"] = []

    with pytest.raises(BenchmarkIntegrityError, match="row count"):
        giw_participant._validate_matrix(matrix)


def test_participant_matrix_requires_mapping_rows():
    matrix = _matrix_prefix()
    matrix["participants"] = [None for _ in giw_participant.PARTICIPANT_IDS]

    with pytest.raises(BenchmarkIntegrityError, match="must be a mapping"):
        giw_participant._validate_matrix(matrix)


def test_participant_matrix_rejects_identity_type():
    matrix = _matrix_prefix()
    matrix["participants"] = [
        {
            "participant_id": "bad",
            "tasks": {},
        }
        for _ in giw_participant.PARTICIPANT_IDS
    ]

    with pytest.raises(BenchmarkIntegrityError, match="identity is invalid"):
        giw_participant._validate_matrix(matrix)


def test_participant_matrix_rejects_task_shape():
    matrix = _matrix_prefix()
    matrix["participants"] = [
        {
            "participant_id": participant_id,
            "tasks": {},
        }
        for participant_id in giw_participant.PARTICIPANT_IDS
    ]

    with pytest.raises(BenchmarkIntegrityError, match="task row shape"):
        giw_participant._validate_matrix(matrix)


def test_participant_matrix_rejects_unknown_status():
    matrix = _matrix_prefix()

    first = giw_participant.PARTICIPANT_IDS[0]

    matrix["participants"] = [
        {
            "participant_id": participant_id,
            "tasks": {
                task: (
                    "not-a-status"
                    if participant_id == first
                    else next(iter(giw_participant._ALLOWED_STATUSES))
                )
                for task in giw_participant.TASKS
            },
        }
        for participant_id in giw_participant.PARTICIPANT_IDS
    ]

    with pytest.raises(BenchmarkIntegrityError, match="status is invalid"):
        giw_participant._validate_matrix(matrix)


# ======================================================================
# candidate source review
# ======================================================================


def test_candidate_review_blank_schema_branches():
    hollywood = candidate_review._blank_source_review("hollywood2em")
    giw = candidate_review._blank_source_review("gaze-in-the-wild")

    assert "annotation_columns_review" in hollywood
    assert "label_process_mapping_basis" in giw


def test_candidate_review_build_requires_inventory():
    with pytest.raises(TypeError, match="CandidateSourceInventory"):
        candidate_review.build_candidate_source_review_scaffold(object())


def test_candidate_review_write_requires_scaffold(tmp_path):
    with pytest.raises(TypeError, match="CandidateSourceReviewScaffold"):
        candidate_review.write_candidate_source_review_scaffold(
            object(),
            tmp_path / "review.json",
        )


def test_candidate_review_load_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        candidate_review._load_payload(tmp_path / "missing.json")


def test_candidate_review_load_invalid_json(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="valid UTF-8 JSON"):
        candidate_review._load_payload(path)


def test_candidate_review_load_nonobject(tmp_path):
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="one JSON object"):
        candidate_review._load_payload(path)


def _review_row(**updates):
    row = {
        "path": "sample.arff",
        "sha256": "a" * 64,
        "bytes": 1,
        "role": "arff",
        "include_in_audit": True,
        "participant_id": "P1",
        "trial_id": "T1",
        "labeller_id": None,
        "process_path": None,
    }
    row.update(updates)
    return row


def test_candidate_review_rejects_unknown_role():
    with pytest.raises(BenchmarkIntegrityError, match="Unsupported review role"):
        candidate_review._review_file_from_payload(
            _review_row(role="not-a-role"),
            dataset_key="hollywood2em",
        )


def test_candidate_review_requires_boolean_include():
    with pytest.raises(BenchmarkIntegrityError, match="must be boolean"):
        candidate_review._review_file_from_payload(
            _review_row(include_in_audit=1),
            dataset_key="hollywood2em",
        )


def test_candidate_review_rejects_boolean_labeller():
    with pytest.raises(BenchmarkIntegrityError, match="positive integer"):
        candidate_review._review_file_from_payload(
            _review_row(labeller_id=True),
            dataset_key="hollywood2em",
        )


def test_candidate_review_rejects_nonpositive_labeller():
    with pytest.raises(BenchmarkIntegrityError, match="positive integer"):
        candidate_review._review_file_from_payload(
            _review_row(labeller_id=0),
            dataset_key="hollywood2em",
        )


def test_candidate_review_rejects_malformed_row():
    row = _review_row()
    row.pop("role")

    with pytest.raises(BenchmarkIntegrityError, match="row is invalid"):
        candidate_review._review_file_from_payload(
            row,
            dataset_key="hollywood2em",
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, False),
        ("", False),
        ("   ", False),
        ("resolved", True),
    ],
)
def test_candidate_review_resolved_text(value, expected):
    assert candidate_review._resolved_text(value) is expected


# ======================================================================
# cross-dataset scientific review
# ======================================================================


def test_cross_review_exact_keys_guard():
    with pytest.raises(BenchmarkIntegrityError, match="schema drifted"):
        cross_review._require_exact_keys(
            {"a": 1},
            frozenset({"a", "b"}),
            label="demo",
        )


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
def test_cross_review_sha_validation(value, expected):
    assert cross_review._valid_sha256(value) is expected


def test_cross_review_required_text_requires_string():
    with pytest.raises(BenchmarkIntegrityError, match="must be text"):
        cross_review._required_text(
            123,
            label="demo",
        )


def test_cross_review_required_text_requires_nonempty():
    with pytest.raises(BenchmarkIntegrityError, match="non-empty"):
        cross_review._required_text(
            " ",
            label="demo",
        )


def test_cross_review_required_text_length_guard():
    with pytest.raises(BenchmarkIntegrityError, match="too long"):
        cross_review._required_text(
            "x" * (cross_review._MAX_TEXT_LENGTH + 1),
            label="demo",
        )


def test_cross_review_timestamp_requires_iso():
    with pytest.raises(BenchmarkIntegrityError, match="ISO-8601"):
        cross_review._utc_timestamp("not-a-time")


def test_cross_review_timestamp_requires_utc():
    with pytest.raises(BenchmarkIntegrityError, match="explicit UTC"):
        cross_review._utc_timestamp("2026-09-23T01:00:00+03:00")


def test_cross_review_timestamp_accepts_z():
    assert cross_review._utc_timestamp("2026-09-22T22:00:00Z") == "2026-09-22T22:00:00Z"


@pytest.mark.parametrize(
    "value",
    [
        "../report.json",
        "folder/report.json",
        ".",
        "..",
    ],
)
def test_cross_review_safe_report_name(value):
    with pytest.raises(BenchmarkIntegrityError, match="sibling basename"):
        cross_review._safe_report_name(value)


def test_cross_review_lineage_requires_protocol(tmp_path):
    with pytest.raises(BenchmarkIntegrityError, match="protocol is invalid"):
        cross_review._lineage_from_report(
            tmp_path / "report.json",
            {},
        )


def test_cross_review_lineage_requires_provenance_sections(tmp_path):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="provenance sections are invalid",
    ):
        cross_review._lineage_from_report(
            tmp_path / "report.json",
            {"protocol": {}},
        )


def test_cross_review_lineage_requires_hollywood_provenance(tmp_path):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Hollywood2EM provenance is missing",
    ):
        cross_review._lineage_from_report(
            tmp_path / "report.json",
            {
                "protocol": {
                    "validation_design": {},
                    "dataset_reports": {},
                }
            },
        )


# ======================================================================
# native scientific review
# ======================================================================


def test_native_review_exact_keys_guard():
    with pytest.raises(BenchmarkIntegrityError, match="schema drifted"):
        native_review._require_exact_keys(
            {"a": 1},
            frozenset({"a", "b"}),
            label="demo",
        )


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
def test_native_review_sha_validation(value, expected):
    assert native_review._valid_sha256(value) is expected


def test_native_review_required_text_requires_string():
    with pytest.raises(BenchmarkIntegrityError, match="must be text"):
        native_review._required_text(
            object(),
            label="demo",
        )


def test_native_review_required_text_requires_nonempty():
    with pytest.raises(BenchmarkIntegrityError, match="non-empty"):
        native_review._required_text(
            " ",
            label="demo",
        )


def test_native_review_required_text_length_guard():
    with pytest.raises(BenchmarkIntegrityError, match="too long"):
        native_review._required_text(
            "x" * (native_review._MAX_TEXT_LENGTH + 1),
            label="demo",
        )


def test_native_review_timestamp_requires_iso():
    with pytest.raises(BenchmarkIntegrityError, match="ISO-8601"):
        native_review._utc_timestamp("bad")


def test_native_review_timestamp_requires_utc():
    with pytest.raises(BenchmarkIntegrityError, match="explicit UTC"):
        native_review._utc_timestamp("2026-09-23T01:00:00+03:00")


def test_native_review_root_directory(tmp_path):
    root, review_path = native_review._review_root(tmp_path)

    assert root == tmp_path
    assert review_path.name == (native_review.NATIVE_SCIENTIFIC_REVIEW_FILENAME)


def test_native_review_root_file(tmp_path):
    path = tmp_path / native_review.NATIVE_SCIENTIFIC_REVIEW_FILENAME

    root, review_path = native_review._review_root(path)

    assert root == tmp_path
    assert review_path == path


def test_native_review_suite_lineage_requires_source():
    with pytest.raises(BenchmarkIntegrityError, match="source identity"):
        native_review._suite_lineage({"source": []})


# ======================================================================
# GIW coordinate evidence
# ======================================================================


def test_coordinate_require_false_guard():
    with pytest.raises(BenchmarkIntegrityError, match="must be false"):
        giw_coordinate._require_false(
            {"x": True},
            "x",
        )


def test_coordinate_normalized_source_collapses_whitespace():
    assert giw_coordinate._normalized_source(" a \n\t b ") == "a b"


def test_coordinate_first_party_source_requires_markers():
    with pytest.raises(BenchmarkIntegrityError, match="markers are missing"):
        giw_coordinate.validate_first_party_por_source("")


def test_coordinate_source_requires_single_por_assignment():
    source = "\n".join(giw_coordinate._REQUIRED_SOURCE_MARKERS)
    source = source + "\n" + giw_coordinate._REQUIRED_SOURCE_MARKERS[-1]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly one reviewed",
    ):
        giw_coordinate.validate_first_party_por_source(source)


def test_coordinate_live_probe_rejects_unpinned_source():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="do not match the pinned Git blob",
    ):
        giw_coordinate.build_first_party_por_live_probe("not-the-pinned-source")


def test_coordinate_git_blob_digest_shape():
    digest = giw_coordinate.git_blob_sha1(b"abc")

    assert len(digest) == 40


# ======================================================================
# VISUS intake
# ======================================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", False),
        ("REPLACE_ME", False),
        ("VERIFY_VALUE", False),
        ("resolved", True),
    ],
)
def test_visus_intake_resolved(value, expected):
    assert visus_intake._resolved(value) is expected


def test_visus_intake_audit_type_guard():
    with pytest.raises(TypeError, match="VisusSourceAuditRun"):
        visus_intake._verify_audit_integrity(object())


def test_visus_intake_numeric_requires_finite():
    with pytest.raises(SchemaError, match="finite numeric"):
        visus_intake._numeric(
            pd.DataFrame({"x": ["bad"]}),
            "x",
        )


def test_visus_intake_rows_require_columns():
    with pytest.raises(SchemaError, match="missing columns"):
        visus_intake._validate_rows(
            pd.DataFrame(),
            manifest={},
            frame_index_base=0,
            video_rate_hz=25.0,
            coordinate_unit="pixels",
            video_resolution_px=(1920, 1080),
            require_complete_manifest_coverage=False,
        )


def test_visus_intake_rows_reject_empty_table():
    frame = pd.DataFrame(columns=list(visus_intake._REQUIRED_COLUMNS))

    with pytest.raises(SchemaError, match="cannot be empty"):
        visus_intake._validate_rows(
            frame,
            manifest={},
            frame_index_base=0,
            video_rate_hz=25.0,
            coordinate_unit="pixels",
            video_resolution_px=(1920, 1080),
            require_complete_manifest_coverage=False,
        )


# ======================================================================
# VISUS prediction
# ======================================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", False),
        ("REPLACE_ME", False),
        ("VERIFY_VALUE", False),
        ("resolved", True),
    ],
)
def test_visus_prediction_resolved(value, expected):
    assert visus_prediction._resolved(value) is expected


def test_visus_prediction_audit_type_guard():
    with pytest.raises(TypeError, match="VisusSourceAuditRun"):
        visus_prediction._verify_audit_integrity(object())


def test_visus_prediction_requires_stimulus_identities():
    audit = SimpleNamespace(
        report={
            "identity": {
                "stimulus_ids": [],
            }
        }
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="no verified stimulus",
    ):
        visus_prediction._audited_stimuli(audit)


def test_visus_prediction_requires_one_video_per_stimulus():
    audit = SimpleNamespace(files=[])

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly one audited video",
    ):
        visus_prediction._video_ledger(
            audit,
            ["S1"],
        )


def test_visus_prediction_numeric_requires_finite():
    with pytest.raises(SchemaError, match="finite numeric"):
        visus_prediction._numeric(
            pd.DataFrame({"x": ["bad"]}),
            "x",
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("px", "pixels"),
        ("pixel", "pixels"),
        ("pixels", "pixels"),
        ("normalized", "normalized"),
    ],
)
def test_visus_prediction_coordinate_unit_normalization(
    value,
    expected,
):
    assert visus_prediction._normalize_coordinate_unit(value) == expected


def test_visus_prediction_model_artifact_none():
    assert visus_prediction._validate_model_artifact_sha256(None) is None


def test_visus_prediction_model_artifact_invalid():
    with pytest.raises(ValueError, match="64-character"):
        visus_prediction._validate_model_artifact_sha256("bad")


def test_visus_prediction_model_artifact_normalizes_case():
    observed = visus_prediction._validate_model_artifact_sha256("A" * 64)

    assert observed == "a" * 64


def test_visus_prediction_rows_require_columns():
    with pytest.raises(SchemaError, match="missing columns"):
        visus_prediction._validate_prediction_rows(
            pd.DataFrame(),
            stimuli=["S1"],
            frame_index_base=0,
            video_rate_hz=25.0,
            coordinate_unit="pixels",
            video_resolution_px=(1920, 1080),
            require_complete_stimulus_coverage=False,
        )


def test_visus_prediction_rows_reject_empty():
    frame = pd.DataFrame(columns=list(visus_prediction._REQUIRED_COLUMNS))

    with pytest.raises(SchemaError, match="cannot be empty"):
        visus_prediction._validate_prediction_rows(
            frame,
            stimuli=["S1"],
            frame_index_base=0,
            video_rate_hz=25.0,
            coordinate_unit="pixels",
            video_resolution_px=(1920, 1080),
            require_complete_stimulus_coverage=False,
        )


# ======================================================================
# GIW exact-validation v2 early fail-closed protocol contracts
# ======================================================================


def test_exact_protocol_v2_rejects_record_type():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Unexpected GIW exact execution protocol",
    ):
        giw_exact_v2.validate_exact_execution_protocol_v2(
            {
                "record_type": "wrong",
            }
        )


def test_exact_protocol_v2_requires_expected_fingerprint():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint drifted",
    ):
        giw_exact_v2.validate_exact_execution_protocol_v2(
            {
                "record_type": (giw_exact_v2.EXECUTION_PROTOCOL_V2_TYPE),
            }
        )


def test_exact_protocol_v2_rejects_body_drift():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="body drifted",
    ):
        giw_exact_v2.validate_exact_execution_protocol_v2(
            {
                "record_type": (giw_exact_v2.EXECUTION_PROTOCOL_V2_TYPE),
                "evidence_fingerprint_sha256": (giw_exact_v2.EXECUTION_PROTOCOL_V2_FINGERPRINT),
            }
        )


# ======================================================================
# Lund suite
# ======================================================================


def test_lund_preflight_overwrite_skips_existing(tmp_path):
    target = tmp_path / "child.json"
    target.write_text("x", encoding="utf-8")

    lund_suite._preflight_targets(
        {"child": target},
        tmp_path / "manifest.json",
        overwrite=True,
    )


def test_lund_preflight_rejects_existing(tmp_path):
    target = tmp_path / "child.json"
    target.write_text("x", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        lund_suite._preflight_targets(
            {"child": target},
            tmp_path / "manifest.json",
            overwrite=False,
        )


def test_lund_child_report_requires_fingerprint():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing a report fingerprint",
    ):
        lund_suite._validate_child_report(
            "demo",
            {},
        )


def test_lund_child_report_rejects_fingerprint_mismatch():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint mismatch",
    ):
        lund_suite._validate_child_report(
            "demo",
            {
                "value": 1,
                "report_fingerprint_sha256": "a" * 64,
            },
        )


def test_lund_child_report_success():
    body = {
        "value": 1,
    }
    fingerprint = benchmark_fingerprint(body)

    observed = lund_suite._validate_child_report(
        "demo",
        {
            **body,
            "report_fingerprint_sha256": fingerprint,
        },
    )

    assert observed == fingerprint


def test_lund_manifest_path_directory(tmp_path):
    assert lund_suite._manifest_path(tmp_path) == tmp_path / lund_suite._SUITE_MANIFEST_NAME


def test_lund_manifest_path_file(tmp_path):
    path = tmp_path / "manifest.json"

    assert lund_suite._manifest_path(path) == path


@pytest.mark.parametrize(
    "relative",
    [
        "../escape.json",
        "/absolute.json",
    ],
)
def test_lund_safe_child_path_rejects_unsafe(tmp_path, relative):
    candidate = relative
    if relative == "/absolute.json":
        candidate = f"{tmp_path.anchor}absolute.json"

    with pytest.raises(BenchmarkIntegrityError, match="unsafe report path"):
        lund_suite._safe_child_path(
            tmp_path,
            candidate,
        )


def test_lund_source_summary_allows_none():
    lund_suite._validate_suite_source_summary(None)


def test_lund_source_summary_requires_object():
    with pytest.raises(BenchmarkIntegrityError, match="object or null"):
        lund_suite._validate_suite_source_summary([])


def test_lund_source_summary_rejects_repository_drift():
    with pytest.raises(BenchmarkIntegrityError, match="repository"):
        lund_suite._validate_suite_source_summary(
            {
                "repository": "wrong",
                "commit": lund_suite.LUND2013_COMMIT,
                "data_path": lund_suite.LUND2013_DATA_PATH,
                "manifest_fingerprint_sha256": "a" * 64,
            }
        )


def test_lund_source_summary_requires_manifest_fingerprint():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing its manifest fingerprint",
    ):
        lund_suite._validate_suite_source_summary(
            {
                "repository": lund_suite.LUND2013_REPOSITORY,
                "commit": lund_suite.LUND2013_COMMIT,
                "data_path": lund_suite.LUND2013_DATA_PATH,
            }
        )


def test_lund_manifest_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        lund_suite.validate_lund2013_suite_manifest(tmp_path / "missing.json")


def test_lund_manifest_invalid_json(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="not valid JSON"):
        lund_suite.validate_lund2013_suite_manifest(path)


def test_lund_manifest_requires_object(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="JSON object"):
        lund_suite.validate_lund2013_suite_manifest(path)


def test_lund_manifest_requires_fields(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="missing required fields"):
        lund_suite.validate_lund2013_suite_manifest(path)
