from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.gaze_in_wild_first_party_readiness as ready
import gazeforge.gaze_in_wild_validation as validation
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError

# ============================================================
# FIRST-PARTY READINESS SYNTHETIC RECORD
# ============================================================


def _readiness_record(**observed_changes):
    observed = {
        "review_status": "reviewed",
        "authority_status": "verified",
        "analysis_use_status": "permitted",
        "redistribution_status": "restricted",
        "authoritative_archive_location_status": "provided",
    }
    observed.update(observed_changes)

    readiness, blockers, status = ready._derive_readiness(
        review_status=observed["review_status"],
        authority_status=observed["authority_status"],
        archive_status=observed["authoritative_archive_location_status"],
        analysis_use_status=observed["analysis_use_status"],
        redistribution_status=observed["redistribution_status"],
        candidate_kind="candidate_original_layout_unverified",
    )

    record = {
        "record_type": ready.RECORD_TYPE,
        "dataset": ready.DATASET,
        "handoff_status": status,
        "first_party_binding": {
            "request_fingerprint_sha256": "a" * 64,
            "response_fingerprint_sha256": "b" * 64,
            "correspondence_sha256": "c" * 64,
        },
        "candidate_binding": {
            "candidate_kind": ("candidate_original_layout_unverified"),
            "recovery_record_fingerprint_sha256": "d" * 64,
            "recovery_tree_fingerprint_sha256": "e" * 64,
            "candidate_screen_fingerprint_sha256": "f" * 64,
            "selected_file": {
                "relative_path": "opaque.mat",
                "sha256": "1" * 64,
                "bytes": 123,
            },
        },
        "observed_response": observed,
        "readiness": readiness,
        "blockers": blockers,
        "next_required_action": (ready._expected_next_action(status)),
        "privacy_boundary": {
            "raw_correspondence_serialized": False,
            "archive_location_serialized": False,
            "correspondence_represented_by_sha256_only": True,
        },
        "scientific_boundary": dict(ready._SCIENTIFIC_BOUNDARY),
        "claim_limit": ready.CLAIM_LIMIT,
    }

    record["record_fingerprint_sha256"] = ready.first_party_readiness_fingerprint(record)

    return record


def _refingerprint(record):
    record["record_fingerprint_sha256"] = ready.first_party_readiness_fingerprint(record)


# ============================================================
# READINESS HELPERS
# ============================================================


def test_ready_fingerprint_ignores_stored():
    record = _readiness_record()

    first = ready.first_party_readiness_fingerprint(record)

    record["record_fingerprint_sha256"] = "0" * 64

    assert ready.first_party_readiness_fingerprint(record) == first


def test_ready_load_mapping_copy():
    original = {"x": 1}

    result = ready._load_json_object(
        original,
        label="fixture",
    )

    assert result == original
    assert result is not original


def test_ready_load_missing(tmp_path):
    with pytest.raises(
        FileNotFoundError,
    ):
        ready._load_json_object(
            tmp_path / "missing.json",
            label="fixture",
        )


def test_ready_load_bad_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        ready._load_json_object(
            path,
            label="fixture",
        )


def test_ready_load_nonobject(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        ready._load_json_object(
            path,
            label="fixture",
        )


def test_ready_sha_normalizes():
    assert (
        ready._sha256(
            " " + ("A" * 64) + " ",
            label="fixture",
        )
        == "a" * 64
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "g" * 64,
        "a" * 63,
        None,
    ],
)
def test_ready_sha_rejects(value):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be SHA-256",
    ):
        ready._sha256(
            value,
            label="fixture",
        )


def test_ready_derive_complete():
    readiness, blockers, status = ready._derive_readiness(
        review_status="reviewed",
        authority_status="verified",
        archive_status="provided",
        analysis_use_status="permitted",
        redistribution_status="restricted",
        candidate_kind=("candidate_original_layout_unverified"),
    )

    assert status == ("ready_for_independent_exact_copy_review")

    assert readiness["ready_for_independent_exact_copy_review"]

    assert [item["id"] for item in blockers] == ["independent_exact_copy_identity_review_required"]


@pytest.mark.parametrize(
    (
        "changes",
        "blocker",
    ),
    [
        (
            {
                "review_status": "pending_review",
            },
            "response_review_required",
        ),
        (
            {
                "authority_status": "not_verified",
            },
            "source_authority_verification_required",
        ),
        (
            {
                "archive_status": "not_available",
            },
            "authoritative_archive_location_required",
        ),
        (
            {
                "analysis_use_status": "restricted",
            },
            "dataset_file_analysis_permission_required",
        ),
        (
            {
                "redistribution_status": "unresolved",
            },
            "redistribution_terms_review_required",
        ),
        (
            {
                "redistribution_status": "prohibited",
            },
            "redistribution_status_mapping_review_required",
        ),
        (
            {
                "candidate_kind": ("transformed_secondary_collection"),
            },
            "exit_eligible_candidate_required",
        ),
    ],
)
def test_ready_derive_blockers(
    changes,
    blocker,
):
    args = {
        "review_status": "reviewed",
        "authority_status": "verified",
        "archive_status": "provided",
        "analysis_use_status": "permitted",
        "redistribution_status": "restricted",
        "candidate_kind": ("candidate_original_layout_unverified"),
    }

    args.update(changes)

    readiness, blockers, status = ready._derive_readiness(**args)

    assert status == "blocked_preconditions"
    assert not readiness["ready_for_independent_exact_copy_review"]

    assert blocker in {item["id"] for item in blockers}


def test_ready_expected_action_variants():
    assert "Independently compare" in (
        ready._expected_next_action("ready_for_independent_exact_copy_review")
    )

    assert "Resolve the listed" in (ready._expected_next_action("blocked_preconditions"))


# ============================================================
# READINESS VALIDATOR
# ============================================================


def test_ready_valid():
    record = _readiness_record()

    result = ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)

    assert result == record


def test_ready_file_valid(tmp_path):
    record = _readiness_record()

    path = tmp_path / "ready.json"
    path.write_text(
        json.dumps(record),
        encoding="utf-8",
    )

    assert ready.validate_gaze_in_wild_first_party_quarantine_readiness(path) == record


def test_ready_top_level_schema():
    record = _readiness_record()
    record["extra"] = True
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="top-level schema drifted",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "record_type",
            "bad",
            "record_type drifted",
        ),
        (
            "dataset",
            "bad",
            "dataset identity drifted",
        ),
    ],
)
def test_ready_identity(
    field,
    value,
    message,
):
    record = _readiness_record()
    record[field] = value
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


@pytest.mark.parametrize(
    "binding",
    [
        None,
        {},
        {
            "request_fingerprint_sha256": "a" * 64,
        },
    ],
)
def test_ready_first_party_binding_shape(
    binding,
):
    record = _readiness_record()
    record["first_party_binding"] = binding
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="response binding is invalid",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


def test_ready_first_party_sha():
    record = _readiness_record()

    record["first_party_binding"]["request_fingerprint_sha256"] = "bad"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be SHA-256",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


@pytest.mark.parametrize(
    "binding",
    [
        None,
        {},
        {
            "candidate_kind": "x",
        },
    ],
)
def test_ready_candidate_binding_shape(
    binding,
):
    record = _readiness_record()
    record["candidate_binding"] = binding
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="candidate binding is invalid",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


def test_ready_candidate_sha():
    record = _readiness_record()

    record["candidate_binding"]["recovery_record_fingerprint_sha256"] = "bad"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be SHA-256",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


def test_ready_candidate_kind_missing():
    record = _readiness_record()

    record["candidate_binding"]["candidate_kind"] = ""

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="candidate kind is missing",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


@pytest.mark.parametrize(
    "selected",
    [
        None,
        {},
        {
            "relative_path": "x",
        },
    ],
)
def test_ready_selected_file_shape(
    selected,
):
    record = _readiness_record()

    record["candidate_binding"]["selected_file"] = selected

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="selected-file binding is invalid",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/absolute.mat",
        "../escape.mat",
        "a/../escape.mat",
    ],
)
def test_ready_selected_file_path(path):
    record = _readiness_record()

    record["candidate_binding"]["selected_file"]["relative_path"] = path

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="path is unsafe",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


def test_ready_selected_file_sha():
    record = _readiness_record()

    record["candidate_binding"]["selected_file"]["sha256"] = "bad"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be SHA-256",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


@pytest.mark.parametrize(
    "value",
    [
        True,
        -1,
        1.5,
        "1",
    ],
)
def test_ready_selected_file_bytes(value):
    record = _readiness_record()

    record["candidate_binding"]["selected_file"]["bytes"] = value

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="bytes are invalid",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


@pytest.mark.parametrize(
    "observed",
    [
        None,
        {},
    ],
)
def test_ready_observed_shape(observed):
    record = _readiness_record()
    record["observed_response"] = observed
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="observed response is invalid",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "review_status",
            "bad",
            "review status is invalid",
        ),
        (
            "authority_status",
            "bad",
            "authority status is invalid",
        ),
        (
            "analysis_use_status",
            "bad",
            "rights status is invalid",
        ),
        (
            "redistribution_status",
            "bad",
            "rights status is invalid",
        ),
        (
            "authoritative_archive_location_status",
            "bad",
            "archive status is invalid",
        ),
    ],
)
def test_ready_observed_statuses(
    field,
    value,
    message,
):
    record = _readiness_record()

    record["observed_response"][field] = value

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


def test_ready_readiness_drift():
    record = _readiness_record()

    record["readiness"]["quarantine_exit_ready"] = True

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="readiness derivation drifted",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


def test_ready_blocker_drift():
    record = _readiness_record()
    record["blockers"] = []
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="blocker list drifted",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


def test_ready_handoff_drift():
    record = _readiness_record()

    record["handoff_status"] = "blocked_preconditions"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="handoff status drifted",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


def test_ready_next_action_drift():
    record = _readiness_record()
    record["next_required_action"] = "bad"
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="next action drifted",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


def test_ready_privacy_boundary():
    record = _readiness_record()

    record["privacy_boundary"]["raw_correspondence_serialized"] = True

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="privacy boundary drifted",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


def test_ready_scientific_boundary():
    record = _readiness_record()

    record["scientific_boundary"]["quarantine_exit_authorized"] = True

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="scientific boundary cannot promote",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


def test_ready_claim_limit():
    record = _readiness_record()
    record["claim_limit"] = "bad"
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="claim limit drifted",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


def test_ready_fingerprint_mismatch():
    record = _readiness_record()

    record["record_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record fingerprint drifted",
    ):
        ready.validate_gaze_in_wild_first_party_quarantine_readiness(record)


# ============================================================
# READINESS VERIFY + WRITE WITHOUT PRIVATE INPUTS
# ============================================================


def test_ready_verify_match(monkeypatch):
    record = _readiness_record()

    monkeypatch.setattr(
        ready,
        "validate_gaze_in_wild_first_party_quarantine_readiness",
        lambda value: copy.deepcopy(record),
    )

    monkeypatch.setattr(
        ready,
        "build_gaze_in_wild_first_party_quarantine_readiness",
        lambda *args, **kwargs: copy.deepcopy(record),
    )

    result = ready.verify_gaze_in_wild_first_party_quarantine_readiness(
        record,
        {},
        "dummy.eml",
        object(),
        candidate_root="candidate",
        recovery_record_or_path={},
        candidate_screen_record_or_path={},
    )

    assert result == record


def test_ready_verify_drift(monkeypatch):
    record = _readiness_record()
    rebuilt = copy.deepcopy(record)
    rebuilt["handoff_status"] = "blocked_preconditions"

    monkeypatch.setattr(
        ready,
        "validate_gaze_in_wild_first_party_quarantine_readiness",
        lambda value: copy.deepcopy(record),
    )

    monkeypatch.setattr(
        ready,
        "build_gaze_in_wild_first_party_quarantine_readiness",
        lambda *args, **kwargs: rebuilt,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="no longer matches",
    ):
        ready.verify_gaze_in_wild_first_party_quarantine_readiness(
            record,
            {},
            "dummy.eml",
            object(),
            candidate_root="candidate",
            recovery_record_or_path={},
            candidate_screen_record_or_path={},
        )


def test_ready_write_inside_candidate_rejected(
    monkeypatch,
    tmp_path,
):
    record = _readiness_record()
    root = tmp_path / "candidate"
    root.mkdir()

    monkeypatch.setattr(
        ready,
        "verify_gaze_in_wild_first_party_quarantine_readiness",
        lambda *args, **kwargs: record,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="outside",
    ):
        ready.write_gaze_in_wild_first_party_quarantine_readiness(
            record,
            root / "ready.json",
            response_record_or_path={},
            correspondence_path="dummy",
            request=object(),
            candidate_root=root,
            recovery_record_or_path={},
            candidate_screen_record_or_path={},
        )


def test_ready_write_existing_rejected(
    monkeypatch,
    tmp_path,
):
    record = _readiness_record()
    root = tmp_path / "candidate"
    root.mkdir()

    target = tmp_path / "ready.json"
    target.write_text(
        "{}",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        ready,
        "verify_gaze_in_wild_first_party_quarantine_readiness",
        lambda *args, **kwargs: record,
    )

    with pytest.raises(
        FileExistsError,
    ):
        ready.write_gaze_in_wild_first_party_quarantine_readiness(
            record,
            target,
            response_record_or_path={},
            correspondence_path="dummy",
            request=object(),
            candidate_root=root,
            recovery_record_or_path={},
            candidate_screen_record_or_path={},
        )


def test_ready_write_success(
    monkeypatch,
    tmp_path,
):
    record = _readiness_record()
    root = tmp_path / "candidate"
    root.mkdir()

    target = tmp_path / "out" / "ready.json"

    monkeypatch.setattr(
        ready,
        "verify_gaze_in_wild_first_party_quarantine_readiness",
        lambda *args, **kwargs: record,
    )

    written = ready.write_gaze_in_wild_first_party_quarantine_readiness(
        record,
        target,
        response_record_or_path={},
        correspondence_path="dummy",
        request=object(),
        candidate_root=root,
        recovery_record_or_path={},
        candidate_screen_record_or_path={},
    )

    assert written == target

    payload = json.loads(target.read_text(encoding="utf-8"))

    assert payload == record


# ============================================================
# GIW VALIDATION HELPERS
# ============================================================


def test_validation_json_safe_records():
    frame = pd.DataFrame(
        {
            "x": [1.0, np.nan],
            "y": ["a", None],
        }
    )

    records = validation._json_safe_records(frame)

    assert records == [
        {
            "x": 1.0,
            "y": "a",
        },
        {
            "x": None,
            "y": None,
        },
    ]


def _audited_item(
    *,
    labeller=1,
    participant="P1",
    trial="T1",
    path="b.mat",
):
    return SimpleNamespace(
        record=SimpleNamespace(
            labeller_id=labeller,
            participant_id=participant,
            trial_id=trial,
            path=path,
        )
    )


def test_validation_selected_files_positive():
    audit = SimpleNamespace(
        files=[
            _audited_item(
                participant="P2",
                path="z.mat",
            ),
            _audited_item(
                participant="P1",
                path="a.mat",
            ),
            _audited_item(
                labeller=2,
                participant="P3",
            ),
        ]
    )

    selected = validation._selected_files(
        audit,
        1,
    )

    assert [item.record.participant_id for item in selected] == [
        "P1",
        "P2",
    ]


def test_validation_selected_files_labeller():
    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        validation._selected_files(
            SimpleNamespace(files=[]),
            0,
        )


def test_validation_selected_files_none():
    with pytest.raises(
        SchemaError,
        match="No audited",
    ):
        validation._selected_files(
            SimpleNamespace(files=[]),
            1,
        )


def test_validation_selected_files_duplicate():
    audit = SimpleNamespace(
        files=[
            _audited_item(
                participant="P1",
                trial="T1",
                path="a.mat",
            ),
            _audited_item(
                participant="P1",
                trial="T1",
                path="b.mat",
            ),
        ]
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="duplicate participant/trial",
    ):
        validation._selected_files(
            audit,
            1,
        )


def test_validation_interpolate_exact():
    result = validation._interpolate_adjacent(
        np.array([0.0, 10.0, 20.0]),
        np.array([1.0, 2.0, 3.0]),
        np.array([10.0]),
        max_gap_ms=20.0,
    )

    assert result[0] == 2.0


def test_validation_interpolate_linear():
    result = validation._interpolate_adjacent(
        np.array([0.0, 10.0]),
        np.array([0.0, 10.0]),
        np.array([5.0]),
        max_gap_ms=20.0,
    )

    assert result[0] == pytest.approx(5.0)


@pytest.mark.parametrize(
    (
        "times",
        "values",
        "target",
        "gap",
    ),
    [
        (
            [0.0, 10.0],
            [0.0, 10.0],
            [-1.0],
            20.0,
        ),
        (
            [0.0, 10.0],
            [0.0, 10.0],
            [11.0],
            20.0,
        ),
        (
            [0.0, 100.0],
            [0.0, 10.0],
            [50.0],
            20.0,
        ),
        (
            [0.0, 10.0],
            [np.nan, 10.0],
            [5.0],
            20.0,
        ),
        (
            [0.0, 10.0],
            [0.0, np.nan],
            [5.0],
            20.0,
        ),
    ],
)
def test_validation_interpolate_refuses(
    times,
    values,
    target,
    gap,
):
    result = validation._interpolate_adjacent(
        np.asarray(times),
        np.asarray(values),
        np.asarray(target),
        max_gap_ms=gap,
    )

    assert np.isnan(result[0])


def test_validation_interpolate_exact_nonfinite():
    result = validation._interpolate_adjacent(
        np.array([0.0, 10.0]),
        np.array([1.0, np.nan]),
        np.array([10.0]),
        max_gap_ms=20.0,
    )

    assert np.isnan(result[0])


# ============================================================
# PREPARE FILE — NATIVE + MOCKED RESAMPLING
# ============================================================


def _file_item(rate=60.0):
    frame = pd.DataFrame(
        {
            "timestamp_ms": [
                0.0,
                1000.0 / rate,
                2000.0 / rate,
            ],
            "x_px": [
                10.0,
                20.0,
                30.0,
            ],
            "y_px": [
                15.0,
                25.0,
                35.0,
            ],
            "confidence": [
                1.0,
                0.9,
                0.8,
            ],
            "validity": [
                True,
                True,
                True,
            ],
            "event_label": [
                "fixation",
                "saccade",
                "fixation",
            ],
            "participant_id": [
                "P1",
                "P1",
                "P1",
            ],
            "trial_id": [
                "T1",
                "T1",
                "T1",
            ],
            "annotator": [
                "A",
                "A",
                "A",
            ],
            "dataset_id": [
                "GIW",
                "GIW",
                "GIW",
            ],
            "source_file": [
                "x",
                "x",
                "x",
            ],
        }
    )

    return SimpleNamespace(
        gaze=SimpleNamespace(
            data=frame,
            sampling_rate_hz=rate,
            metadata={
                "source_audit_report_fingerprint_sha256": ("a" * 64),
                "source_audit_spec_fingerprint_sha256": ("b" * 64),
            },
        ),
        record=SimpleNamespace(
            labeller_id=1,
            participant_id="P1",
            trial_id="T1",
            path="LabelData/P1_T1.mat",
            process_path="ProcessData/P1_T1.mat",
        ),
    )


def test_validation_prepare_file_upsampling():
    with pytest.raises(
        SchemaError,
        match="refuses upsampling",
    ):
        validation._prepare_file(
            _file_item(60.0),
            target_sampling_rate_hz=120.0,
            min_label_purity=0.75,
            max_coordinate_gap_factor=1.5,
            confidence_threshold=0.5,
        )


def test_validation_prepare_file_native():
    prepared, report = validation._prepare_file(
        _file_item(60.0),
        target_sampling_rate_hz=60.0,
        min_label_purity=0.75,
        max_coordinate_gap_factor=1.5,
        confidence_threshold=0.5,
    )

    assert report["sampling_origin"] == "native"

    assert (prepared["benchmark_label_purity"] == 1.0).all()


def test_validation_prepare_file_resampled(
    monkeypatch,
):
    source_item = _file_item(120.0)

    resampled = pd.DataFrame(
        {
            "timestamp_ms": [
                0.0,
                1000.0 / 60.0,
            ],
            "event_label": [
                "fixation",
                "saccade",
            ],
            "participant_id": [
                "P1",
                "P1",
            ],
            "trial_id": [
                "T1",
                "T1",
            ],
            "annotator": [
                "A",
                "A",
            ],
            "dataset_id": [
                "GIW",
                "GIW",
            ],
            "source_file": [
                "x",
                "x",
            ],
            "benchmark_label_purity": [
                1.0,
                1.0,
            ],
            "benchmark_label_source_samples": [
                2,
                2,
            ],
            "benchmark_label_ambiguous": [
                False,
                False,
            ],
        }
    )

    monkeypatch.setattr(
        validation,
        "resample_labeled_gaze",
        lambda *args, **kwargs: SimpleNamespace(
            data=resampled.copy(),
            report={
                "resampled": True,
            },
        ),
    )

    prepared, report = validation._prepare_file(
        source_item,
        target_sampling_rate_hz=60.0,
        min_label_purity=0.75,
        max_coordinate_gap_factor=3.0,
        confidence_threshold=0.85,
    )

    assert report["sampling_origin"] == "resampled"

    assert report["resampling"]["invalid_source_samples_are_not_bridged"] is True

    assert "validity" in prepared


# ============================================================
# TASK MAPPING
# ============================================================


def _analysis_data():
    return pd.DataFrame(
        {
            "participant_id": [
                "P1",
                "P2",
            ],
            "trial_id": [
                "T1",
                "T2",
            ],
            "event_label": [
                "fixation",
                "saccade",
            ],
        }
    )


def _task_mapping():
    return pd.DataFrame(
        {
            "participant_id": [
                "P1",
                "P2",
            ],
            "trial_id": [
                "T1",
                "T2",
            ],
            "task_label": [
                "indoor",
                "outdoor",
            ],
        }
    )


def test_validation_mapping_missing_columns():
    with pytest.raises(
        SchemaError,
        match="requires columns",
    ):
        validation._attach_task_mapping(
            _analysis_data(),
            pd.DataFrame({"participant_id": ["P1"]}),
            task_col="task_label",
        )


def test_validation_mapping_missing_values():
    mapping = _task_mapping()
    mapping.loc[0, "task_label"] = None

    with pytest.raises(
        SchemaError,
        match="cannot contain missing",
    ):
        validation._attach_task_mapping(
            _analysis_data(),
            mapping,
            task_col="task_label",
        )


def test_validation_mapping_empty_values():
    mapping = _task_mapping()
    mapping.loc[0, "task_label"] = " "

    with pytest.raises(
        SchemaError,
        match="cannot contain empty",
    ):
        validation._attach_task_mapping(
            _analysis_data(),
            mapping,
            task_col="task_label",
        )


def test_validation_mapping_duplicate():
    mapping = pd.concat(
        [
            _task_mapping(),
            _task_mapping().iloc[[0]],
        ],
        ignore_index=True,
    )

    with pytest.raises(
        SchemaError,
        match="one row per participant/trial",
    ):
        validation._attach_task_mapping(
            _analysis_data(),
            mapping,
            task_col="task_label",
        )


def test_validation_mapping_exact_coverage():
    mapping = _task_mapping().iloc[[0]].copy()

    with pytest.raises(
        SchemaError,
        match="exactly cover",
    ):
        validation._attach_task_mapping(
            _analysis_data(),
            mapping,
            task_col="task_label",
        )


def test_validation_mapping_success():
    attached, report = validation._attach_task_mapping(
        _analysis_data(),
        _task_mapping(),
        task_col="task_label",
    )

    assert set(attached["task_label"]) == {
        "indoor",
        "outdoor",
    }

    assert report["task_labels_inferred_from_filenames"] is False

    assert len(report["mapping_fingerprint_sha256"]) == 64


# ============================================================
# PREPARE BENCHMARK PARAMETER + FAIL-CLOSED BRANCHES
# ============================================================


def _fake_audit():
    return SimpleNamespace(
        report={
            "coordinates": {
                "verified": True,
                "unit": "pixels",
                "pixel_kinematics_compatible": True,
            },
            "report_fingerprint_sha256": ("a" * 64),
            "spec_fingerprint_sha256": ("b" * 64),
            "label_inventory": {"manifest_fingerprint_sha256": ("c" * 64)},
            "process_inventory": {"manifest_fingerprint_sha256": ("d" * 64)},
        },
        spec=SimpleNamespace(
            confidence_threshold=0.5,
            dataset_name="GIW",
            dataset_version="test",
            source="synthetic-test",
            license="review-only",
            coordinate_unit="pixels",
            pixel_kinematics_compatible=True,
        ),
    )


def _patch_prepare_entry(monkeypatch):
    monkeypatch.setattr(
        validation,
        "_verify_audit_integrity",
        lambda audit, lineage: "e" * 64,
    )


def test_validation_prepare_coordinate_gate(
    monkeypatch,
):
    _patch_prepare_entry(monkeypatch)

    audit = _fake_audit()
    audit.report["coordinates"]["verified"] = False

    with pytest.raises(
        SchemaError,
        match="pixel-kinematics",
    ):
        validation.prepare_gaze_in_wild_benchmark(
            audit,
            object(),
            labeller_id=1,
        )


@pytest.mark.parametrize(
    "rate",
    [
        0,
        -1,
        np.nan,
    ],
)
def test_validation_prepare_target_rate(
    monkeypatch,
    rate,
):
    _patch_prepare_entry(monkeypatch)

    with pytest.raises(
        ValueError,
        match="finite and positive",
    ):
        validation.prepare_gaze_in_wild_benchmark(
            _fake_audit(),
            object(),
            labeller_id=1,
            target_sampling_rate_hz=rate,
        )


@pytest.mark.parametrize(
    "purity",
    [
        0,
        -1,
        1.1,
        np.nan,
    ],
)
def test_validation_prepare_purity(
    monkeypatch,
    purity,
):
    _patch_prepare_entry(monkeypatch)

    with pytest.raises(
        ValueError,
        match=r"\(0, 1\]",
    ):
        validation.prepare_gaze_in_wild_benchmark(
            _fake_audit(),
            object(),
            labeller_id=1,
            min_label_purity=purity,
        )


@pytest.mark.parametrize(
    "factor",
    [
        0,
        0.9,
        np.nan,
    ],
)
def test_validation_prepare_gap(
    monkeypatch,
    factor,
):
    _patch_prepare_entry(monkeypatch)

    with pytest.raises(
        ValueError,
        match="at least 1.0",
    ):
        validation.prepare_gaze_in_wild_benchmark(
            _fake_audit(),
            object(),
            labeller_id=1,
            max_coordinate_gap_factor=factor,
        )


def _mock_prepared_frame(
    labels,
    participants,
):
    n = len(labels)

    return pd.DataFrame(
        {
            "participant_id": participants,
            "trial_id": [f"T{i}" for i in range(n)],
            "event_label": labels,
            "benchmark_label_ambiguous": [False] * n,
        }
    )


def _patch_prepare_payload(
    monkeypatch,
    frame,
    *,
    origins=("native",),
):
    _patch_prepare_entry(monkeypatch)

    selected = [SimpleNamespace() for _ in origins]

    monkeypatch.setattr(
        validation,
        "_selected_files",
        lambda audit, labeller_id: selected,
    )

    frames = [frame.iloc[[index % len(frame)]].copy() for index in range(len(origins))]

    reports = [
        {
            "source_sampling_rate_hz": (60.0 if origin == "native" else 120.0),
            "sampling_origin": origin,
            "source_rows": len(frames[index]),
            "prepared_rows": len(frames[index]),
        }
        for index, origin in enumerate(origins)
    ]

    iterator = iter(
        zip(
            frames,
            reports,
            strict=True,
        )
    )

    monkeypatch.setattr(
        validation,
        "_prepare_file",
        lambda *args, **kwargs: next(iterator),
    )


def test_validation_prepare_unknown_labels(
    monkeypatch,
):
    frame = _mock_prepared_frame(
        [
            "unknown_99",
            "fixation",
        ],
        [
            "P1",
            "P2",
        ],
    )

    _patch_prepare_payload(
        monkeypatch,
        frame,
        origins=(
            "native",
            "native",
        ),
    )

    with pytest.raises(
        SchemaError,
        match="outside the supported",
    ):
        validation.prepare_gaze_in_wild_benchmark(
            _fake_audit(),
            object(),
            labeller_id=1,
        )


def test_validation_prepare_excludes_all(
    monkeypatch,
):
    frame = _mock_prepared_frame(
        [
            "ambiguous",
            "unlabelled",
        ],
        [
            "P1",
            "P2",
        ],
    )

    _patch_prepare_payload(
        monkeypatch,
        frame,
        origins=(
            "native",
            "native",
        ),
    )

    with pytest.raises(
        SchemaError,
        match="excluded every",
    ):
        validation.prepare_gaze_in_wild_benchmark(
            _fake_audit(),
            object(),
            labeller_id=1,
        )


def test_validation_prepare_one_class(
    monkeypatch,
):
    frame = _mock_prepared_frame(
        [
            "fixation",
            "fixation",
        ],
        [
            "P1",
            "P2",
        ],
    )

    _patch_prepare_payload(
        monkeypatch,
        frame,
        origins=(
            "native",
            "native",
        ),
    )

    with pytest.raises(
        SchemaError,
        match="fewer than two event classes",
    ):
        validation.prepare_gaze_in_wild_benchmark(
            _fake_audit(),
            object(),
            labeller_id=1,
        )


def test_validation_prepare_one_participant(
    monkeypatch,
):
    frame = _mock_prepared_frame(
        [
            "fixation",
            "saccade",
        ],
        [
            "P1",
            "P1",
        ],
    )

    _patch_prepare_payload(
        monkeypatch,
        frame,
        origins=(
            "native",
            "native",
        ),
    )

    with pytest.raises(
        SchemaError,
        match="at least two participants",
    ):
        validation.prepare_gaze_in_wild_benchmark(
            _fake_audit(),
            object(),
            labeller_id=1,
        )


# ============================================================
# CLASS-SENSITIVITY HELPERS
# ============================================================


def test_validation_sample_class_sensitivity():
    predictions = pd.DataFrame(
        {
            "comparison_model": [
                "A",
                "A",
                "A",
                "A",
            ],
            "event_label": [
                "fixation",
                "fixation",
                "saccade",
                "saccade",
            ],
            "predicted_event": [
                "fixation",
                "saccade",
                "saccade",
                "saccade",
            ],
        }
    )

    output = validation._sample_class_sensitivity(
        predictions,
        label_col="event_label",
    )

    assert set(output["event_label"]) == {
        "fixation",
        "saccade",
    }


def test_validation_event_class_sensitivity(
    monkeypatch,
):
    predictions = pd.DataFrame(
        {
            "comparison_model": [
                "A",
                "B",
            ],
        }
    )

    monkeypatch.setattr(
        validation,
        "evaluate_sample_event_predictions",
        lambda *args, **kwargs: SimpleNamespace(
            per_class=pd.DataFrame(
                {
                    "event_label": ["fixation"],
                    "f1": [0.5],
                }
            )
        ),
    )

    output = validation._event_class_sensitivity(
        predictions,
        sampling_rate_hz=60.0,
        event_min_iou=0.5,
        event_excluded_labels=(),
    )

    assert set(output["model"]) == {
        "A",
        "B",
    }


def test_validation_event_class_empty():
    output = validation._event_class_sensitivity(
        pd.DataFrame(columns=["comparison_model"]),
        sampling_rate_hz=60.0,
        event_min_iou=0.5,
        event_excluded_labels=(),
    )

    assert output.empty


# ============================================================
# RUN VALIDATION WITHOUT FITTING
# ============================================================


def _prepared_stub(
    participants=("P1", "P2"),
):
    return SimpleNamespace(
        data=pd.DataFrame(
            {
                "participant_id": list(participants),
                "trial_id": [f"T{i}" for i in range(len(participants))],
                "event_label": [
                    "fixation" if i % 2 == 0 else "saccade" for i in range(len(participants))
                ],
            }
        ),
        dataset_card="card",
        preparation_report={
            "label_counts_analysis": {
                "fixation": 1,
                "saccade": 1,
            }
        },
    )


def test_validation_run_requires_two_folds(
    monkeypatch,
):
    monkeypatch.setattr(
        validation,
        "prepare_gaze_in_wild_benchmark",
        lambda *args, **kwargs: _prepared_stub(("P1",)),
    )

    with pytest.raises(
        SchemaError,
        match="At least two",
    ):
        validation.run_gaze_in_wild_model_validation(
            object(),
            object(),
            labeller_id=1,
        )


def test_validation_run_threshold_guard(
    monkeypatch,
):
    monkeypatch.setattr(
        validation,
        "prepare_gaze_in_wild_benchmark",
        lambda *args, **kwargs: _prepared_stub(),
    )

    with pytest.raises(
        ValueError,
        match="finite and positive",
    ):
        validation.run_gaze_in_wild_model_validation(
            object(),
            object(),
            labeller_id=1,
            ivt_velocity_threshold_px_s=0,
        )


def _patch_validation_run(
    monkeypatch,
):
    prepared = _prepared_stub()

    monkeypatch.setattr(
        validation,
        "prepare_gaze_in_wild_benchmark",
        lambda *args, **kwargs: prepared,
    )

    comparison = SimpleNamespace(
        summary=pd.DataFrame(
            {
                "model": ["A"],
                "f1": [0.5],
            }
        ),
        fold_metrics=pd.DataFrame(
            {
                "model": ["A"],
                "validation_fold": [0],
                "f1": [0.5],
            }
        ),
        predictions=pd.DataFrame(
            {
                "comparison_model": [
                    "A",
                    "A",
                ],
                "participant_id": [
                    "P1",
                    "P2",
                ],
                "trial_id": [
                    "T0",
                    "T1",
                ],
                "event_label": [
                    "fixation",
                    "saccade",
                ],
                "predicted_event": [
                    "fixation",
                    "saccade",
                ],
                "task_label": [
                    "indoor",
                    "outdoor",
                ],
            }
        ),
        design={
            "models": ["A"],
            "calibration_bins": 4,
        },
    )

    monkeypatch.setattr(
        validation,
        "compare_event_models_grouped",
        lambda *args, **kwargs: comparison,
    )

    paired = SimpleNamespace(
        summary=pd.DataFrame(
            {
                "contrast": ["A-B"],
                "delta": [0.0],
            }
        ),
        deltas=pd.DataFrame(
            {
                "contrast": ["A-B"],
                "validation_fold": [0],
                "delta": [0.0],
            }
        ),
        design={
            "paired": True,
        },
    )

    monkeypatch.setattr(
        validation,
        "paired_model_metric_differences",
        lambda *args, **kwargs: paired,
    )

    monkeypatch.setattr(
        validation,
        "_sample_class_sensitivity",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "model": ["A"],
                "event_label": ["fixation"],
                "f1": [0.5],
            }
        ),
    )

    monkeypatch.setattr(
        validation,
        "_event_class_sensitivity",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "model": ["A"],
                "event_label": ["fixation"],
                "f1": [0.5],
            }
        ),
    )

    monkeypatch.setattr(
        validation,
        "build_benchmark_report",
        lambda **kwargs: {
            "synthetic_report": True,
            "protocol": kwargs["protocol"],
        },
    )

    return comparison


def test_validation_run_mocked_no_task(
    monkeypatch,
):
    _patch_validation_run(monkeypatch)

    run = validation.run_gaze_in_wild_model_validation(
        object(),
        object(),
        labeller_id=1,
        n_splits=5,
    )

    assert run.task_performance is None

    assert run.report["synthetic_report"] is True


def test_validation_run_mocked_task(
    monkeypatch,
):
    _patch_validation_run(monkeypatch)

    task = SimpleNamespace(
        summary=pd.DataFrame(
            {
                "task_label": ["indoor"],
                "f1": [0.5],
            }
        ),
        fold_metrics=pd.DataFrame(
            {
                "task_label": ["indoor"],
                "validation_fold": [0],
                "f1": [0.5],
            }
        ),
        design={
            "models_refit_by_stratum": False,
        },
    )

    monkeypatch.setattr(
        validation,
        "summarize_event_predictions_by_stratum",
        lambda *args, **kwargs: task,
    )

    run = validation.run_gaze_in_wild_model_validation(
        object(),
        object(),
        labeller_id=1,
        task_mapping=pd.DataFrame(
            {
                "participant_id": [
                    "P1",
                    "P2",
                ],
                "trial_id": [
                    "T0",
                    "T1",
                ],
                "task_label": [
                    "indoor",
                    "outdoor",
                ],
            }
        ),
        task_col="task_label",
    )

    assert run.task_performance is task

    assert run.report["protocol"]["task_sensitivity_design"]["models_refit_by_stratum"] is False
