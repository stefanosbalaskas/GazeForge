from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from test_visus_preexecution_protocol import (
    _build,
    _FakeRuntime,
    _fixture,
    _freeze,
)

import gazeforge.visus_preexecution_protocol as protocol
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    root = tmp_path_factory.mktemp("preexecution-coverage")
    audit, plans, timestamps, checkpoint = _fixture(root)
    value = _build(audit, plans, timestamps)

    return {
        "root": root,
        "audit": audit,
        "plans": plans,
        "timestamps": timestamps,
        "checkpoint": checkpoint,
        "protocol": value,
    }


@pytest.fixture(scope="module")
def frozen_base(base):
    frozen = _freeze(
        base["root"],
        base["audit"],
        base["plans"],
        base["timestamps"],
    )

    runtime = _FakeRuntime()

    bound = protocol.run_grounded_sam2_from_preexecution_protocol(
        frozen,
        base["audit"],
        base["plans"]["S01"],
        runtime=runtime,
    )

    return {
        **base,
        "frozen": frozen,
        "bound": bound,
    }


def _resign_protocol(
    value: dict[str, Any],
) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != "protocol_fingerprint_sha256"}

    value["protocol_fingerprint_sha256"] = benchmark_fingerprint(body)

    return value


def _resign_audit_report(
    report: dict[str, Any],
) -> None:
    body = {key: value for key, value in report.items() if key != "report_fingerprint_sha256"}

    report["report_fingerprint_sha256"] = benchmark_fingerprint(body)


def _video_for(base, stimulus="S01"):
    return protocol._audited_videos(base["audit"])[stimulus]


def _plan_record(
    base,
    monkeypatch,
    mutate_config=None,
    mutate_video=None,
    plan=None,
):
    selected = base["plans"]["S01"] if plan is None else plan

    video = copy.deepcopy(_video_for(base))

    if mutate_video is not None:
        mutate_video(video)

    if mutate_config is not None:
        original = protocol._validate_config
        values = original(selected.config)
        mutate_config(values)

        monkeypatch.setattr(
            protocol,
            "_validate_config",
            lambda config: copy.deepcopy(values),
        )

    return protocol._plan_record(
        selected,
        audited_video=video,
        audited_frame_rate_hz=float(base["audit"].spec.published_video_frame_rate_hz),
    )


def _mutated_protocol(
    base,
    mutation,
    *,
    resign=True,
):
    value = copy.deepcopy(base["protocol"])

    mutation(value)

    if resign:
        _resign_protocol(value)

    return value


def _binding_call(
    frozen_base,
    monkeypatch,
    report,
):
    frozen = frozen_base["frozen"]
    frozen_protocol = frozen.protocol

    plan_record = next(
        copy.deepcopy(row) for row in frozen_protocol["stimuli"] if row["stimulus_id"] == "S01"
    )

    monkeypatch.setattr(
        protocol,
        "_assert_protocol_file_unchanged",
        lambda run: frozen_protocol,
    )

    monkeypatch.setattr(
        protocol,
        "_assert_audit_identity_matches_protocol",
        lambda audit, value: None,
    )

    monkeypatch.setattr(
        protocol,
        "_assert_plan_matches_protocol",
        lambda value, audit, plan: plan_record,
    )

    monkeypatch.setattr(
        protocol,
        "validate_grounded_sam2_run",
        lambda run: None,
    )

    backend = SimpleNamespace(report=report)

    return protocol.bind_grounded_sam2_to_preexecution_protocol(
        frozen,
        frozen_base["audit"],
        frozen_base["plans"]["S01"],
        backend,
        protocol_validated_before_backend_call=True,
    )


# ============================================================
# LOW-LEVEL INPUT CONTRACTS
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "REPLACE_ME",
        "please verify value",
    ],
)
def test_resolved_rejects_unresolved_values(
    value,
):
    with pytest.raises(
        ValueError,
        match="explicit resolved value",
    ):
        protocol._resolved(
            value,
            label="fixture",
        )


def test_resolved_success():
    assert (
        protocol._resolved(
            "  exact-value  ",
            label="fixture",
        )
        == "exact-value"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("a" * 64, True),
        ("A" * 64, True),
        ("a" * 63, False),
        ("g" * 64, False),
        ("", False),
    ],
)
def test_valid_sha256_branches(
    value,
    expected,
):
    assert protocol._valid_sha256(value) is expected


def test_file_sha256_missing(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError,
    ):
        protocol._file_sha256(
            tmp_path / "missing.bin",
            label="fixture",
        )


def test_file_sha256_empty(
    tmp_path,
):
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot be empty",
    ):
        protocol._file_sha256(
            path,
            label="fixture",
        )


def test_file_sha256_symlink_guard_portable(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "payload.bin"
    path.write_bytes(b"abc")

    original = Path.is_symlink

    def fake_is_symlink(self):
        if self == path:
            return True
        return original(self)

    monkeypatch.setattr(
        Path,
        "is_symlink",
        fake_is_symlink,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="symbolic link",
    ):
        protocol._file_sha256(
            path,
            label="fixture",
        )


def test_file_sha256_success(
    tmp_path,
):
    path = tmp_path / "payload.bin"
    path.write_bytes(b"abc")

    size, digest = protocol._file_sha256(
        path,
        label="fixture",
    )

    assert size == 3
    assert len(digest) == 64


# ============================================================
# AUDIT CONTRACTS
# ============================================================


def test_verify_audit_type_guard():
    with pytest.raises(
        TypeError,
        match="VisusSourceAuditRun",
    ):
        protocol._verify_audit(object())


def test_verify_audit_status_guard(
    base,
):
    audit = copy.deepcopy(base["audit"])

    audit.report["status"] = "invalid"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="verified source audit",
    ):
        protocol._verify_audit(audit)


def test_verify_audit_empirical_guard(
    base,
):
    audit = copy.deepcopy(base["audit"])

    object.__setattr__(
        audit.spec,
        "dataset_status",
        "template",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="empirical source audit",
    ):
        protocol._verify_audit(audit)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reuse_terms_verified", False),
        ("analysis_use_permitted", False),
    ],
)
def test_verify_audit_reuse_permission_guards(
    base,
    field,
    value,
):
    audit = copy.deepcopy(base["audit"])

    object.__setattr__(
        audit.spec,
        field,
        value,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="reviewed reuse terms",
    ):
        protocol._verify_audit(audit)


def test_verify_audit_report_fingerprint_guard(
    base,
):
    audit = copy.deepcopy(base["audit"])

    audit.report["report_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report fingerprint",
    ):
        protocol._verify_audit(audit)


def test_verify_audit_spec_fingerprint_guard(
    base,
):
    audit = copy.deepcopy(base["audit"])

    audit.report["spec_fingerprint_sha256"] = "0" * 64

    _resign_audit_report(audit.report)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="specification fingerprint",
    ):
        protocol._verify_audit(audit)


def test_verify_audit_manifest_fingerprint_guard(
    base,
):
    audit = copy.deepcopy(base["audit"])

    audit.report["inventory"]["manifest_fingerprint_sha256"] = "0" * 64

    _resign_audit_report(audit.report)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="manifest fingerprint",
    ):
        protocol._verify_audit(audit)


def test_verify_audit_success(
    base,
):
    result = protocol._verify_audit(base["audit"])

    assert set(result) == {
        "source_audit_report_fingerprint_sha256",
        "source_audit_spec_fingerprint_sha256",
        "source_manifest_fingerprint_sha256",
    }


# ============================================================
# AUDITED VIDEO CONTRACTS
# ============================================================


def test_audited_videos_requires_stimuli(
    base,
):
    report = copy.deepcopy(base["audit"].report)

    report["identity"]["stimulus_ids"] = []

    audit = SimpleNamespace(
        report=report,
        files=base["audit"].files,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="no stimulus identities",
    ):
        protocol._audited_videos(audit)


def test_audited_videos_requires_exactly_one_video(
    base,
):
    files = [
        item
        for item in base["audit"].files
        if not (item.record.role == "video" and str(item.record.stimulus_id) == "S01")
    ]

    audit = SimpleNamespace(
        report=base["audit"].report,
        files=files,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly one audited video",
    ):
        protocol._audited_videos(audit)


def test_audited_videos_detects_byte_drift(
    base,
    monkeypatch,
):
    original = protocol._file_sha256

    def fake(path, *, label):
        size, digest = original(
            path,
            label=label,
        )

        if "S01" in label:
            return size + 1, digest

        return size, digest

    monkeypatch.setattr(
        protocol,
        "_file_sha256",
        fake,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="bytes changed",
    ):
        protocol._audited_videos(base["audit"])


def test_audited_videos_success(
    base,
):
    videos = protocol._audited_videos(base["audit"])

    assert len(videos) == 11
    assert "S01" in videos


# ============================================================
# TIMESTAMPS / REGISTRATION
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        "0,40",
        b"0,40",
        12,
        None,
    ],
)
def test_timestamp_grid_requires_sequence(
    value,
):
    with pytest.raises(
        TypeError,
        match="sequence of numeric values",
    ):
        protocol._timestamp_grid_record(
            "S01",
            value,
        )


def test_timestamp_grid_success():
    value = protocol._timestamp_grid_record(
        "S01",
        [0.0, 40.0],
    )

    assert value["n_timestamps"] == 2


def test_registration_invalid_iso_timestamp():
    with pytest.raises(
        ValueError,
        match="valid ISO-8601 timestamp",
    ):
        protocol._validate_registration(
            "https://example.invalid/register",
            "definitely-not-a-date",
        )


def test_registration_none_success():
    value = protocol._validate_registration(
        None,
        None,
    )

    assert value["external_registration_metadata_recorded"] is False


# ============================================================
# PLAN RECORD CONTRACTS
# ============================================================


def test_plan_record_type_guard(
    base,
):
    with pytest.raises(
        TypeError,
        match="VisusGroundedSAM2StimulusPlan",
    ):
        protocol._plan_record(
            object(),
            audited_video=_video_for(base),
            audited_frame_rate_hz=25.0,
        )


def test_plan_record_config_type_guard(
    base,
):
    bad = replace(
        base["plans"]["S01"],
        config=object(),
    )

    with pytest.raises(
        TypeError,
        match="GroundedSAM2Config",
    ):
        protocol._plan_record(
            bad,
            audited_video=_video_for(base),
            audited_frame_rate_hz=25.0,
        )


def test_plan_record_source_sha_guard(
    base,
    monkeypatch,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="source SHA",
    ):
        _plan_record(
            base,
            monkeypatch,
            mutate_config=lambda values: values.__setitem__(
                "source_video_sha256",
                "0" * 64,
            ),
        )


def test_plan_record_derivation_binding_guard(
    base,
    monkeypatch,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Frame derivation is not bound",
    ):
        _plan_record(
            base,
            monkeypatch,
            mutate_video=lambda video: video.__setitem__(
                "bytes",
                int(video["bytes"]) + 1,
            ),
        )


def test_plan_record_frame_base_guard(
    base,
    monkeypatch,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="frame index base",
    ):
        _plan_record(
            base,
            monkeypatch,
            mutate_config=lambda values: values.__setitem__(
                "frame_index_base",
                1,
            ),
        )


def test_plan_record_frame_rate_guard(
    base,
    monkeypatch,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="frame rate differs",
    ):
        _plan_record(
            base,
            monkeypatch,
            mutate_config=lambda values: values.__setitem__(
                "frame_rate_hz",
                30.0,
            ),
        )


def test_plan_record_prompt_frame_guard(
    base,
    monkeypatch,
):
    with pytest.raises(
        SchemaError,
        match="outside the derived frames",
    ):
        _plan_record(
            base,
            monkeypatch,
            mutate_config=lambda values: values.__setitem__(
                "prompt_frame_index",
                999,
            ),
        )


# ============================================================
# BUILD INPUT CONTRACTS
# ============================================================


def test_build_requires_plan_mapping(
    base,
):
    with pytest.raises(
        TypeError,
        match="plans_by_stimulus",
    ):
        _build(
            base["audit"],
            [],
            base["timestamps"],
        )


def test_build_requires_timestamp_mapping(
    base,
):
    with pytest.raises(
        TypeError,
        match="timestamps_by_stimulus",
    ):
        _build(
            base["audit"],
            base["plans"],
            [],
        )


# ============================================================
# PAYLOAD VALIDATOR CONTRACTS
# ============================================================


def test_payload_requires_mapping():
    with pytest.raises(
        TypeError,
        match="protocol must be a mapping",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload([])


@pytest.mark.parametrize(
    "mode",
    [
        "missing",
        "extra",
    ],
)
def test_payload_exact_key_contract(
    base,
    mode,
):
    value = copy.deepcopy(base["protocol"])

    if mode == "missing":
        value.pop("claim_limits")
    else:
        value["unexpected"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="keys drifted",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_schema_guard(
    base,
):
    value = copy.deepcopy(base["protocol"])

    value["schema"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="schema drifted",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_status_guard(
    base,
):
    value = copy.deepcopy(base["protocol"])

    value["status"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="status drifted",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_source_authority_separation_guard(
    base,
):
    value = _mutated_protocol(
        base,
        lambda item: item.__setitem__(
            "source_authority_certificate_required_separately",
            False,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="keep source authority separate",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", None),
        ("global_model_policy", None),
    ],
)
def test_payload_source_policy_mapping_guards(
    base,
    field,
    value,
):
    protocol_value = _mutated_protocol(
        base,
        lambda item: item.__setitem__(
            field,
            value,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source/model policy is invalid",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(protocol_value)


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
    ],
)
def test_payload_stimulus_list_guard(
    base,
    value,
):
    protocol_value = _mutated_protocol(
        base,
        lambda item: item.__setitem__(
            "stimuli",
            value,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="stimulus plans are missing",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(protocol_value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("evaluation", None),
        ("registration", None),
    ],
)
def test_payload_evaluation_registration_mapping_guards(
    base,
    field,
    value,
):
    protocol_value = _mutated_protocol(
        base,
        lambda item: item.__setitem__(
            field,
            value,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="evaluation/registration sections are invalid",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(protocol_value)


@pytest.mark.parametrize(
    "field",
    [
        "source_audit_report_fingerprint_sha256",
        "source_audit_spec_fingerprint_sha256",
        "source_manifest_fingerprint_sha256",
    ],
)
def test_payload_source_fingerprint_guards(
    base,
    field,
):
    value = _mutated_protocol(
        base,
        lambda item: item["source"].__setitem__(
            field,
            "bad",
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source fingerprint",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_analysis_permission_guard(
    base,
):
    value = _mutated_protocol(
        base,
        lambda item: item["source"].__setitem__(
            "analysis_use_permitted",
            False,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lost analysis permission",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_reuse_terms_guard(
    base,
):
    value = _mutated_protocol(
        base,
        lambda item: item["source"].__setitem__(
            "reuse_terms_verified",
            False,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lost reviewed reuse terms",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_stimulus_record_mapping_guard(
    base,
):
    value = _mutated_protocol(
        base,
        lambda item: item["stimuli"].__setitem__(
            0,
            "bad-record",
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="stimulus record is invalid",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_empty_stimulus_identity_guard(
    base,
):
    value = _mutated_protocol(
        base,
        lambda item: item["stimuli"][0].__setitem__(
            "stimulus_id",
            "",
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="unique and resolved",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_duplicate_stimulus_identity_guard(
    base,
):
    def mutate(item):
        item["stimuli"][1]["stimulus_id"] = item["stimuli"][0]["stimulus_id"]

    value = _mutated_protocol(
        base,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="unique and resolved",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("semantic_labels", None),
        ("semantic_labels", []),
        ("prompt_text", ""),
    ],
)
def test_payload_semantic_prompt_guards(
    base,
    field,
    value,
):
    protocol_value = _mutated_protocol(
        base,
        lambda item: item["stimuli"][0].__setitem__(
            field,
            value,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="semantic prompt is invalid",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(protocol_value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_video", None),
        ("frame_derivation", None),
    ],
)
def test_payload_source_derivation_mapping_guards(
    base,
    field,
    value,
):
    protocol_value = _mutated_protocol(
        base,
        lambda item: item["stimuli"][0].__setitem__(
            field,
            value,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source/derivation record is invalid",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(protocol_value)


def test_payload_video_sha_guard(
    base,
):
    value = _mutated_protocol(
        base,
        lambda item: item["stimuli"][0]["source_video"].__setitem__(
            "sha256",
            "bad",
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="video SHA is invalid",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


@pytest.mark.parametrize(
    "field",
    [
        "report_fingerprint_sha256",
        "frame_manifest_fingerprint_sha256",
        "extractor_artifact_sha256",
    ],
)
def test_payload_derivation_fingerprint_guards(
    base,
    field,
):
    value = _mutated_protocol(
        base,
        lambda item: item["stimuli"][0]["frame_derivation"].__setitem__(
            field,
            "bad",
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="derivation",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
    ],
)
def test_payload_timestamp_grid_coverage_guards(
    base,
    value,
):
    protocol_value = _mutated_protocol(
        base,
        lambda item: item["evaluation"].__setitem__(
            "timestamp_grids",
            value,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="timestamp-grid coverage is invalid",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(protocol_value)


def test_payload_timestamp_grid_record_mapping_guard(
    base,
):
    value = _mutated_protocol(
        base,
        lambda item: item["evaluation"]["timestamp_grids"].__setitem__(
            0,
            "bad-record",
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="timestamp-grid record is invalid",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_timestamp_values_guard(
    base,
):
    value = _mutated_protocol(
        base,
        lambda item: item["evaluation"]["timestamp_grids"][0].__setitem__(
            "timestamps_ms",
            None,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="timestamp values are missing",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_timestamp_fingerprint_guard(
    base,
):
    value = _mutated_protocol(
        base,
        lambda item: item["evaluation"]["timestamp_grids"][0].__setitem__(
            "n_timestamps",
            999,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="timestamp-grid fingerprint drifted",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_timestamp_order_guard(
    base,
):
    def mutate(item):
        grids = item["evaluation"]["timestamp_grids"]

        grids[0], grids[1] = (
            grids[1],
            grids[0],
        )

    value = _mutated_protocol(
        base,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="ordering or coverage drifted",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_prediction_grid_guard(
    base,
):
    value = _mutated_protocol(
        base,
        lambda item: item["evaluation"].__setitem__(
            "prediction_emission_grid_used",
            True,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot use prediction emissions",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_complete_coverage_guard(
    base,
):
    value = _mutated_protocol(
        base,
        lambda item: item["evaluation"].__setitem__(
            "complete_audited_stimulus_coverage_required",
            False,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="complete stimulus coverage",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


def test_payload_registration_promotion_guard(
    base,
):
    value = _mutated_protocol(
        base,
        lambda item: item["registration"].__setitem__(
            "formal_preregistration_verified",
            True,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot verify formal preregistration",
    ):
        protocol.validate_visus_grounded_sam2_preexecution_protocol_payload(value)


# ============================================================
# FREEZE / LOAD / REPLAY
# ============================================================


def _freeze_to(
    base,
    output_path,
    *,
    overwrite=False,
):
    return protocol.freeze_visus_grounded_sam2_preexecution_protocol(
        base["audit"],
        base["plans"],
        base["timestamps"],
        output_path,
        reference_stream_id="published_curated",
        timestamp_grid_basis=("Fixed audited 25 Hz video-frame grid."),
        max_interpolation_gap_ms=80.0,
        min_iou=0.50,
        require_label_match=True,
        fixation_assignment_planned=False,
        overlap_rule="highest_confidence",
        overwrite=overwrite,
    )


def test_freeze_directory_output_branch(
    base,
    tmp_path,
):
    output = tmp_path / "protocol-dir"
    output.mkdir()

    run = _freeze_to(
        base,
        output,
    )

    assert run.protocol_path.name == protocol._PROTOCOL_FILENAME


def test_freeze_existing_path_requires_overwrite(
    base,
    tmp_path,
):
    output = tmp_path / "existing.json"
    output.write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
    ):
        _freeze_to(
            base,
            output,
        )


def test_load_missing_file(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError,
    ):
        protocol.load_visus_grounded_sam2_preexecution_protocol(tmp_path / "missing.json")


def test_load_invalid_json(
    tmp_path,
):
    path = tmp_path / "bad.json"
    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not valid JSON",
    ):
        protocol.load_visus_grounded_sam2_preexecution_protocol(path)


def test_assert_protocol_file_type_guard():
    with pytest.raises(
        TypeError,
        match="protocol_run",
    ):
        protocol._assert_protocol_file_unchanged(object())


def test_assert_protocol_file_fingerprint_mismatch(
    frozen_base,
):
    frozen = frozen_base["frozen"]

    bad = protocol.VisusGroundedSAM2PreexecutionProtocolRun(
        protocol_path=frozen.protocol_path,
        protocol=copy.deepcopy(frozen.protocol),
        protocol_fingerprint_sha256=("0" * 64),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="changed after loading",
    ):
        protocol._assert_protocol_file_unchanged(bad)


def test_assert_protocol_file_payload_mismatch(
    frozen_base,
):
    frozen = frozen_base["frozen"]

    changed = copy.deepcopy(frozen.protocol)

    changed["claim_limits"] = list(changed["claim_limits"]) + ["memory-only change"]

    bad = protocol.VisusGroundedSAM2PreexecutionProtocolRun(
        protocol_path=frozen.protocol_path,
        protocol=changed,
        protocol_fingerprint_sha256=(frozen.protocol_fingerprint_sha256),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="changed after loading",
    ):
        protocol._assert_protocol_file_unchanged(bad)


def test_replay_final_identity_guard(
    frozen_base,
    monkeypatch,
):
    frozen = frozen_base["frozen"]

    rebuilt = copy.deepcopy(frozen.protocol)

    rebuilt["claim_limits"] = list(rebuilt["claim_limits"]) + ["synthetic drift"]

    monkeypatch.setattr(
        protocol,
        "build_visus_grounded_sam2_preexecution_protocol",
        lambda *args, **kwargs: rebuilt,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="no longer match the frozen protocol",
    ):
        protocol.replay_visus_grounded_sam2_preexecution_protocol(
            frozen,
            frozen_base["audit"],
            frozen_base["plans"],
            frozen_base["timestamps"],
        )


# ============================================================
# PROTOCOL/PLAN LOOKUPS
# ============================================================


def test_protocol_plan_record_missing():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="lacks one unique plan",
    ):
        protocol._protocol_plan_record(
            {
                "stimuli": [],
            },
            "S01",
        )


def test_protocol_plan_record_duplicate():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="lacks one unique plan",
    ):
        protocol._protocol_plan_record(
            {
                "stimuli": [
                    {
                        "stimulus_id": "S01",
                    },
                    {
                        "stimulus_id": "S01",
                    },
                ],
            },
            "S01",
        )


def test_audit_identity_protocol_mismatch(
    monkeypatch,
):
    monkeypatch.setattr(
        protocol,
        "_verify_audit",
        lambda audit: {
            "x": "expected",
        },
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source audit does not match",
    ):
        protocol._assert_audit_identity_matches_protocol(
            object(),
            {
                "source": {
                    "x": "wrong",
                }
            },
        )


def test_assert_plan_stimulus_not_audited(
    base,
    monkeypatch,
):
    monkeypatch.setattr(
        protocol,
        "_audited_videos",
        lambda audit: {},
    )

    with pytest.raises(
        SchemaError,
        match="not in the audited VISUS source",
    ):
        protocol._assert_plan_matches_protocol(
            base["protocol"],
            base["audit"],
            base["plans"]["S01"],
        )


def test_assert_plan_record_mismatch(
    base,
    monkeypatch,
):
    monkeypatch.setattr(
        protocol,
        "_audited_videos",
        lambda audit: {
            "S01": {},
        },
    )

    monkeypatch.setattr(
        protocol,
        "_plan_record",
        lambda *args, **kwargs: (
            {
                "stimulus_id": "S01",
                "x": 1,
            },
            {
                "policy": 1,
            },
        ),
    )

    value = {
        "stimuli": [
            {
                "stimulus_id": "S01",
                "x": 2,
            }
        ],
        "global_model_policy": {
            "policy": 1,
        },
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="plan differs",
    ):
        protocol._assert_plan_matches_protocol(
            value,
            base["audit"],
            base["plans"]["S01"],
        )


def test_assert_plan_policy_mismatch(
    base,
    monkeypatch,
):
    record = {
        "stimulus_id": "S01",
        "x": 1,
    }

    monkeypatch.setattr(
        protocol,
        "_audited_videos",
        lambda audit: {
            "S01": {},
        },
    )

    monkeypatch.setattr(
        protocol,
        "_plan_record",
        lambda *args, **kwargs: (
            record,
            {
                "policy": 2,
            },
        ),
    )

    value = {
        "stimuli": [copy.deepcopy(record)],
        "global_model_policy": {
            "policy": 1,
        },
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="model policy differs",
    ):
        protocol._assert_plan_matches_protocol(
            value,
            base["audit"],
            base["plans"]["S01"],
        )


# ============================================================
# BACKEND BINDING DRIFT GUARDS
# ============================================================


def _backend_report(
    frozen_base,
):
    return copy.deepcopy(frozen_base["bound"].backend_run.report)


def test_binding_semantic_labels_guard(
    frozen_base,
    monkeypatch,
):
    report = _backend_report(frozen_base)

    report["semantic_labels"] = ["wrong"]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="semantic labels differ",
    ):
        _binding_call(
            frozen_base,
            monkeypatch,
            report,
        )


def test_binding_prompt_text_guard(
    frozen_base,
    monkeypatch,
):
    report = _backend_report(frozen_base)

    report["prompt_text"] = "wrong."

    with pytest.raises(
        BenchmarkIntegrityError,
        match="prompt text differs",
    ):
        _binding_call(
            frozen_base,
            monkeypatch,
            report,
        )


@pytest.mark.parametrize(
    "field",
    [
        "model_name",
        "model_version",
    ],
)
def test_binding_model_identity_guard(
    frozen_base,
    monkeypatch,
    field,
):
    report = _backend_report(frozen_base)

    report[field] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="model identity differs",
    ):
        _binding_call(
            frozen_base,
            monkeypatch,
            report,
        )


def test_binding_checkpoint_identity_guard(
    frozen_base,
    monkeypatch,
):
    report = _backend_report(frozen_base)

    report["model_identity"]["sam2_code_revision"] = "0" * 40

    with pytest.raises(
        BenchmarkIntegrityError,
        match="checkpoint/revision identity differs",
    ):
        _binding_call(
            frozen_base,
            monkeypatch,
            report,
        )


def test_binding_source_video_guard(
    frozen_base,
    monkeypatch,
):
    report = _backend_report(frozen_base)

    report["source_video"]["sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source video differs",
    ):
        _binding_call(
            frozen_base,
            monkeypatch,
            report,
        )


def test_binding_frame_manifest_guard(
    frozen_base,
    monkeypatch,
):
    report = _backend_report(frozen_base)

    report["frames"]["manifest_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="frame manifest differs",
    ):
        _binding_call(
            frozen_base,
            monkeypatch,
            report,
        )


def test_binding_prompt_frame_guard(
    frozen_base,
    monkeypatch,
):
    report = _backend_report(frozen_base)

    report["frames"]["prompt_frame_index"] = 999

    with pytest.raises(
        BenchmarkIntegrityError,
        match="prompt frame differs",
    ):
        _binding_call(
            frozen_base,
            monkeypatch,
            report,
        )


def test_binding_runtime_config_guard(
    frozen_base,
    monkeypatch,
):
    report = _backend_report(frozen_base)

    report["config"]["box_threshold"] = 0.99

    with pytest.raises(
        BenchmarkIntegrityError,
        match="runtime config differs",
    ):
        _binding_call(
            frozen_base,
            monkeypatch,
            report,
        )
