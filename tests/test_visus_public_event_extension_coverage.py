from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any

import pytest
from test_visus_public_event_extension import (
    EVIDENCE,
    _probe_from_evidence,
    _record,
    _refingerprint,
)

import gazeforge.visus_public_event_extension as extension
from gazeforge.exceptions import BenchmarkIntegrityError


def _fake_probe_fingerprint(
    probe: dict[str, Any],
) -> str:
    return extension._probe_fingerprint(probe)


def _authorize_modified_probe(
    probe: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fingerprint = _fake_probe_fingerprint(probe)
    probe["probe_fingerprint_sha256"] = fingerprint
    monkeypatch.setattr(
        extension,
        "EXPECTED_PROBE_FINGERPRINT_SHA256",
        fingerprint,
    )


def test_canonical_bytes_are_deterministic() -> None:
    assert extension._canonical_bytes({"b": 2, "a": 1}) == extension._canonical_bytes(
        {"a": 1, "b": 2}
    )


def test_evidence_fingerprint_ignores_self_field() -> None:
    value = {"x": 1}

    first = extension.evidence_fingerprint(value)
    value["evidence_fingerprint_sha256"] = "0" * 64
    second = extension.evidence_fingerprint(value)

    assert first == second
    assert len(first) == 64


def test_probe_fingerprint_ignores_self_field() -> None:
    value = {"x": 1}

    first = extension._probe_fingerprint(value)
    value["probe_fingerprint_sha256"] = "0" * 64
    second = extension._probe_fingerprint(value)

    assert first == second
    assert len(first) == 64


def test_load_record_mapping_success() -> None:
    original = {"x": 1}

    observed, path = extension._load_record(original)

    assert observed == original
    assert observed is not original
    assert path is None


def test_load_record_path_success() -> None:
    observed, path = extension._load_record(EVIDENCE)

    assert isinstance(observed, dict)
    assert path == EVIDENCE


def test_load_record_missing_guard(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load VISUS public event-extension evidence",
    ):
        extension._load_record(tmp_path / "missing.json")


def test_load_record_invalid_json_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load VISUS public event-extension evidence",
    ):
        extension._load_record(path)


def test_load_record_requires_object(
    tmp_path: Path,
) -> None:
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        extension._load_record(path)


def test_require_equal_success() -> None:
    extension._require_equal(
        "same",
        "same",
        "fixture",
    )


def test_require_equal_guard() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not match the frozen v1 contract",
    ):
        extension._require_equal(
            "actual",
            "expected",
            "fixture",
        )


def test_require_false_success() -> None:
    extension._require_false(
        False,
        "fixture",
    )


@pytest.mark.parametrize(
    "value",
    [
        True,
        None,
        0,
        "",
    ],
)
def test_require_false_guard(
    value: Any,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote fixture",
    ):
        extension._require_false(
            value,
            "fixture",
        )


def test_require_true_success() -> None:
    extension._require_true(
        True,
        "fixture",
    )


@pytest.mark.parametrize(
    "value",
    [
        False,
        None,
        1,
        "",
    ],
)
def test_require_true_guard(
    value: Any,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve fixture",
    ):
        extension._require_true(
            value,
            "fixture",
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        "not-numeric",
        object(),
    ],
)
def test_require_fraction_numeric_guard(
    value: Any,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="is not numeric",
    ):
        extension._require_fraction(
            value,
            "fixture",
        )


@pytest.mark.parametrize(
    "value",
    [
        -0.1,
        1.1,
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_require_fraction_bounds_guard(
    value: float,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match=r"outside \[0, 1\]",
    ):
        extension._require_fraction(
            value,
            "fixture",
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0.0),
        (1, 1.0),
        ("0.5", 0.5),
    ],
)
def test_require_fraction_success(
    value: Any,
    expected: float,
) -> None:
    assert extension._require_fraction(
        value,
        "fixture",
    ) == pytest.approx(expected)


def test_files_without_urls_success() -> None:
    value = {
        "a": {
            "path": "x",
            "sha256": "a",
            "url": "https://example.invalid",
        },
    }

    assert extension._files_without_urls(value) == {
        "a": {
            "path": "x",
            "sha256": "a",
        }
    }


def test_files_without_urls_mapping_guard() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="source ledger bad is malformed",
    ):
        extension._files_without_urls(
            {
                "bad": "not-an-object",
            }
        )


def test_boundaries_success() -> None:
    extension._validate_boundaries(_record())


def test_boundaries_missing_inference_guard() -> None:
    record = _record()
    record["stimulus_inference"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="stimulus inference is missing",
    ):
        extension._validate_boundaries(record)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "candidate",
            "wrong",
            "stimulus candidate",
        ),
        (
            "identity_status",
            "resolved",
            "stimulus identity status",
        ),
        (
            "stimulus_identity_resolved",
            True,
            "resolved stimulus identity",
        ),
        (
            "aoi_annotation_recovered_for_candidate",
            True,
            "candidate AOI annotation recovery",
        ),
        (
            "duration_matches_candidate",
            False,
            "19 s duration match",
        ),
    ],
)
def test_inference_boundary_guards(
    field: str,
    value: Any,
    match: str,
) -> None:
    record = _record()
    record["stimulus_inference"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        extension._validate_boundaries(record)


def test_boundaries_missing_reuse_guard() -> None:
    record = _record()
    record["reuse_boundary"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="reuse boundary is missing",
    ):
        extension._validate_boundaries(record)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "analysis_use_basis_recorded",
            False,
            "analysis-use basis",
        ),
        (
            "source_license_resolved",
            True,
            "source-license resolution",
        ),
        (
            "source_bytes_redistributed_by_gazeforge",
            True,
            "source-byte redistribution",
        ),
        (
            "unrestricted_redistribution_asserted",
            True,
            "unrestricted redistribution",
        ),
    ],
)
def test_reuse_boundary_guards(
    field: str,
    value: Any,
    match: str,
) -> None:
    record = _record()
    record["reuse_boundary"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        extension._validate_boundaries(record)


def test_boundaries_missing_scientific_guard() -> None:
    record = _record()
    record["scientific_boundary"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="scientific boundary is missing",
    ):
        extension._validate_boundaries(record)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "real_external_tobii_60hz_exports",
            False,
            "real Tobii 60 Hz status",
        ),
        (
            "participant_identity_file_bound",
            False,
            "file-bound participant identity",
        ),
        (
            "stimulus_identity_file_bound",
            True,
            "file-bound stimulus identity",
        ),
        (
            "dialog_assignment_is_inference",
            False,
            "Dialog inference status",
        ),
        (
            "dynamic_aoi_metrics_created",
            True,
            "dynamic AOI evidence",
        ),
        (
            "human_human_agreement_created",
            True,
            "human-human agreement",
        ),
        (
            "model_validation_created",
            True,
            "model validation",
        ),
        (
            "native_gp3_evidence",
            True,
            "native GP3 evidence",
        ),
        (
            "original_full_visus_source_resolved",
            True,
            "full VISUS source resolution",
        ),
        (
            "frozen_evidence_created",
            True,
            "Frozen Evidence",
        ),
    ],
)
def test_scientific_boundary_guards(
    field: str,
    value: Any,
    match: str,
) -> None:
    record = _record()
    record["scientific_boundary"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        extension._validate_boundaries(record)


def test_participants_success() -> None:
    participants = copy.deepcopy(_record()["participants"])

    assert extension._validate_participants(participants) == participants


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        [{}],
        [{}, {}, {}],
    ],
)
def test_participant_shape_guard(
    value: Any,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly two participant records",
    ):
        extension._validate_participants(value)


def test_participant_nonobject_guard() -> None:
    participants = copy.deepcopy(_record()["participants"])

    participants[1] = "bad-row"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="participant record must be an object",
    ):
        extension._validate_participants(participants)


def test_participant_order_guard() -> None:
    participants = copy.deepcopy(_record()["participants"])

    participants.reverse()

    with pytest.raises(
        BenchmarkIntegrityError,
        match="participant order",
    ):
        extension._validate_participants(participants)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "recording_name",
            "wrong",
            "recording name",
        ),
        (
            "recording_resolution",
            "1280 x 720",
            "recording resolution",
        ),
        (
            "media_geometry",
            [[1280, 720]],
            "media geometry",
        ),
        (
            "eye",
            "Left",
            "eye setting",
        ),
        (
            "validity_filter",
            "Strict",
            "validity filter",
        ),
        (
            "fixation_filter",
            "wrong",
            "fixation filter",
        ),
        (
            "velocity_threshold",
            34,
            "velocity threshold",
        ),
        (
            "distance_threshold",
            34,
            "distance threshold",
        ),
    ],
)
def test_participant_fixed_contract_guards(
    field: str,
    value: Any,
    match: str,
) -> None:
    participants = copy.deepcopy(_record()["participants"])

    participants[0][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        extension._validate_participants(participants)


@pytest.mark.parametrize(
    "field",
    [
        "sample_count",
        "valid_both_eye_samples",
        "fixation_event_count",
        "total_fixation_duration_ms",
        "fixations_with_on_screen_mapped_point",
        "movie_span_ms",
    ],
)
def test_participant_frozen_count_guards(
    field: str,
) -> None:
    participants = copy.deepcopy(_record()["participants"])

    participants[0][field] += 1

    with pytest.raises(
        BenchmarkIntegrityError,
        match=field,
    ):
        extension._validate_participants(participants)


def test_participant_sampling_rate_guard() -> None:
    participants = copy.deepcopy(_record()["participants"])

    participants[0]["inferred_sampling_rate_hz"] = 60.0

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sampling rate drifted",
    ):
        extension._validate_participants(participants)


def test_participant_sample_delta_guard() -> None:
    participants = copy.deepcopy(_record()["participants"])

    participants[0]["median_positive_sample_delta_us"] = 16000.0

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sample delta",
    ):
        extension._validate_participants(participants)


@pytest.mark.parametrize(
    "field",
    [
        "valid_both_eye_fraction",
        "on_screen_fixation_fraction",
    ],
)
def test_participant_fraction_guards(
    field: str,
) -> None:
    participants = copy.deepcopy(_record()["participants"])

    participants[0][field] = 2.0

    with pytest.raises(
        BenchmarkIntegrityError,
        match=r"outside \[0, 1\]",
    ):
        extension._validate_participants(participants)


def test_aggregate_success() -> None:
    record = _record()

    extension._validate_aggregate(
        record,
        record["participants"],
    )


def test_aggregate_mapping_guard() -> None:
    record = _record()
    record["aggregate"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="aggregate is missing",
    ):
        extension._validate_aggregate(
            record,
            record["participants"],
        )


def test_aggregate_field_set_guard() -> None:
    record = _record()

    record["aggregate"]["unexpected"] = 1

    with pytest.raises(
        BenchmarkIntegrityError,
        match="aggregate fields",
    ):
        extension._validate_aggregate(
            record,
            record["participants"],
        )


def test_aggregate_float_consistency_guard() -> None:
    record = _record()

    record["aggregate"]["valid_both_eye_fraction"] += 0.01

    with pytest.raises(
        BenchmarkIntegrityError,
        match="aggregate valid_both_eye_fraction is inconsistent",
    ):
        extension._validate_aggregate(
            record,
            record["participants"],
        )


def test_aggregate_integer_consistency_guard() -> None:
    record = _record()

    record["aggregate"]["valid_both_eye_samples"] += 1

    with pytest.raises(
        BenchmarkIntegrityError,
        match="aggregate valid_both_eye_samples",
    ):
        extension._validate_aggregate(
            record,
            record["participants"],
        )


def test_aggregate_frozen_sample_total_guard() -> None:
    record = _record()

    participants = copy.deepcopy(record["participants"])

    participants[0]["sample_count"] += 1

    aggregate = copy.deepcopy(record["aggregate"])

    aggregate["sample_count"] += 1

    aggregate["valid_both_eye_fraction"] = (
        aggregate["valid_both_eye_samples"] / aggregate["sample_count"]
    )

    modified = copy.deepcopy(record)
    modified["aggregate"] = aggregate

    with pytest.raises(
        BenchmarkIntegrityError,
        match="aggregate sample count",
    ):
        extension._validate_aggregate(
            modified,
            participants,
        )


def test_aggregate_frozen_fixation_total_guard() -> None:
    record = _record()

    participants = copy.deepcopy(record["participants"])

    participants[0]["fixation_event_count"] += 1

    aggregate = copy.deepcopy(record["aggregate"])

    aggregate["fixation_event_count"] += 1

    aggregate["on_screen_fixation_fraction"] = (
        aggregate["fixations_with_on_screen_mapped_point"] / aggregate["fixation_event_count"]
    )

    modified = copy.deepcopy(record)
    modified["aggregate"] = aggregate

    with pytest.raises(
        BenchmarkIntegrityError,
        match="aggregate fixation count",
    ):
        extension._validate_aggregate(
            modified,
            participants,
        )


def test_locks_success() -> None:
    extension._validate_locks(copy.deepcopy(_record()["provenance_lockfiles"]))


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        [{}, {}],
        [{}, {}, {}, {}],
    ],
)
def test_lock_shape_guard(
    value: Any,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="three provenance lockfiles",
    ):
        extension._validate_locks(value)


def test_lock_nonobject_guard() -> None:
    locks = copy.deepcopy(_record()["provenance_lockfiles"])

    locks[1] = "bad-row"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lockfile record must be an object",
    ):
        extension._validate_locks(locks)


def test_lock_unknown_key_guard() -> None:
    locks = copy.deepcopy(_record()["provenance_lockfiles"])

    locks[0]["ledger_key"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Unexpected VISUS Dialog lockfile ledger key",
    ):
        extension._validate_locks(locks)


def test_lock_content_guard() -> None:
    locks = copy.deepcopy(_record()["provenance_lockfiles"])

    locks[0]["content"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="content",
    ):
        extension._validate_locks(locks)


def test_lock_provenance_only_guard() -> None:
    locks = copy.deepcopy(_record()["provenance_lockfiles"])

    locks[0]["provenance_only"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="provenance-only status",
    ):
        extension._validate_locks(locks)


def test_lock_empirical_data_guard() -> None:
    locks = copy.deepcopy(_record()["provenance_lockfiles"])

    locks[0]["empirical_data"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="empirical-data status",
    ):
        extension._validate_locks(locks)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "record_type",
            "wrong",
            "record type",
        ),
        (
            "status",
            "wrong",
            "status",
        ),
        (
            "source_class",
            "wrong",
            "source class",
        ),
    ],
)
def test_evidence_top_level_guards(
    field: str,
    value: str,
    match: str,
) -> None:
    record = _record()
    record[field] = value
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        extension.validate_visus_public_event_extension_evidence(record)


def test_evidence_upstream_mapping_guard() -> None:
    record = _record()
    record["upstream"] = None
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="upstream identity is missing",
    ):
        extension.validate_visus_public_event_extension_evidence(record)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "repository",
            "wrong/repo",
            "upstream repository",
        ),
        (
            "commit",
            "0" * 40,
            "upstream commit",
        ),
    ],
)
def test_evidence_upstream_identity_guards(
    field: str,
    value: str,
    match: str,
) -> None:
    record = _record()
    record["upstream"][field] = value
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        extension.validate_visus_public_event_extension_evidence(record)


def test_evidence_source_ledger_guard() -> None:
    record = _record()

    record["upstream"]["files"]["P5B"]["sha256"] = "0" * 64

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source-file ledger",
    ):
        extension.validate_visus_public_event_extension_evidence(record)


def test_evidence_unit_test_provenance_guard() -> None:
    record = _record()

    record["upstream"]["unit_test_provenance"]["required_assertion_count"] += 1

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="unit-test provenance",
    ):
        extension.validate_visus_public_event_extension_evidence(record)


def test_evidence_execution_guard() -> None:
    record = _record()

    record["execution"]["artifact_id"] += 1

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="probe execution identity",
    ):
        extension.validate_visus_public_event_extension_evidence(record)


def test_evidence_coverage_mapping_guard() -> None:
    record = _record()
    record["coverage"] = None
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="coverage is missing",
    ):
        extension.validate_visus_public_event_extension_evidence(record)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "participants",
            ["P5B"],
            "participants",
        ),
        (
            "participant_count",
            1,
            "participant count",
        ),
        (
            "complete_tobii_exports",
            1,
            "complete export count",
        ),
        (
            "provenance_lockfiles",
            2,
            "lockfile count",
        ),
        (
            "full_visus_participant_count",
            24,
            "full participant count",
        ),
        (
            "full_visus_stimulus_count",
            10,
            "full stimulus count",
        ),
        (
            "full_visus_recovered",
            True,
            "full VISUS recovery",
        ),
    ],
)
def test_evidence_coverage_guards(
    field: str,
    value: Any,
    match: str,
) -> None:
    record = _record()
    record["coverage"][field] = value
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        extension.validate_visus_public_event_extension_evidence(record)


def test_duration_mapping_guard() -> None:
    record = _record()
    record["duration_semantics"] = None
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="duration semantics are missing",
    ):
        extension.validate_visus_public_event_extension_evidence(record)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "exported_fixation_duration_sum_ms",
            39615,
            "duration sum",
        ),
        (
            "participant_movie_span_sum_ms",
            38133,
            "movie-span sum",
        ),
        (
            "fixation_durations_clipped_to_movie_boundaries",
            True,
            "clipped fixation durations",
        ),
    ],
)
def test_duration_contract_guards(
    field: str,
    value: Any,
    match: str,
) -> None:
    record = _record()
    record["duration_semantics"][field] = value
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        extension.validate_visus_public_event_extension_evidence(record)


def test_evidence_self_fingerprint_guard() -> None:
    record = _record()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint is invalid",
    ):
        extension.validate_visus_public_event_extension_evidence(record)


def test_evidence_immutable_fingerprint_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _record()
    fake = "f" * 64

    record["evidence_fingerprint_sha256"] = fake

    monkeypatch.setattr(
        extension,
        "evidence_fingerprint",
        lambda value: fake,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="immutable v1 fingerprint drifted",
    ):
        extension.validate_visus_public_event_extension_evidence(record)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "record_type",
            "wrong",
            "probe type",
        ),
        (
            "status",
            "wrong",
            "probe status",
        ),
    ],
)
def test_probe_top_level_guards(
    field: str,
    value: str,
    match: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _probe_from_evidence()
    probe[field] = value

    _authorize_modified_probe(
        probe,
        monkeypatch,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        extension.validate_visus_public_event_extension_probe(
            probe,
            EVIDENCE,
        )


def test_probe_self_fingerprint_guard() -> None:
    probe = _probe_from_evidence()

    probe["probe_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="live probe fingerprint is invalid",
    ):
        extension.validate_visus_public_event_extension_probe(
            probe,
            EVIDENCE,
        )


def test_probe_immutable_fingerprint_guard() -> None:
    probe = _probe_from_evidence()

    probe["extra"] = False

    probe["probe_fingerprint_sha256"] = extension._probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted from frozen v1",
    ):
        extension.validate_visus_public_event_extension_probe(
            probe,
            EVIDENCE,
        )


def test_probe_upstream_mapping_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _probe_from_evidence()
    probe["upstream"] = None

    _authorize_modified_probe(
        probe,
        monkeypatch,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="live probe upstream identity is missing",
    ):
        extension.validate_visus_public_event_extension_probe(
            probe,
            EVIDENCE,
        )


@pytest.mark.parametrize(
    ("field", "match"),
    [
        (
            "repository",
            "probe upstream repository",
        ),
        (
            "commit",
            "probe upstream commit",
        ),
    ],
)
def test_probe_upstream_identity_guards(
    field: str,
    match: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _probe_from_evidence()

    probe["upstream"][field] = "wrong"

    _authorize_modified_probe(
        probe,
        monkeypatch,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        extension.validate_visus_public_event_extension_probe(
            probe,
            EVIDENCE,
        )


def test_probe_source_ledger_mapping_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _probe_from_evidence()

    probe["upstream"]["files"] = None

    _authorize_modified_probe(
        probe,
        monkeypatch,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="live probe source ledger is missing",
    ):
        extension.validate_visus_public_event_extension_probe(
            probe,
            EVIDENCE,
        )


def test_probe_source_ledger_row_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _probe_from_evidence()

    probe["upstream"]["files"]["P5B"] = "bad-row"

    _authorize_modified_probe(
        probe,
        monkeypatch,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source ledger P5B is malformed",
    ):
        extension.validate_visus_public_event_extension_probe(
            probe,
            EVIDENCE,
        )


def test_probe_source_ledger_identity_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _probe_from_evidence()

    probe["upstream"]["files"]["P5B"]["sha256"] = "0" * 64

    _authorize_modified_probe(
        probe,
        monkeypatch,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="live source ledger",
    ):
        extension.validate_visus_public_event_extension_probe(
            probe,
            EVIDENCE,
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "unit_test_provenance",
            {"wrong": True},
            "live unit-test provenance",
        ),
        (
            "coverage",
            {"wrong": True},
            "live coverage",
        ),
        (
            "participants",
            [],
            "live participants",
        ),
        (
            "aggregate",
            {"wrong": True},
            "live aggregate",
        ),
        (
            "stimulus_inference",
            {"wrong": True},
            "live stimulus inference",
        ),
        (
            "provenance_lockfiles",
            [],
            "live lockfile provenance",
        ),
    ],
)
def test_probe_evidence_binding_guards(
    field: str,
    value: Any,
    match: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _probe_from_evidence()

    if field == "unit_test_provenance":
        probe["upstream"][field] = value
    else:
        probe[field] = value

    _authorize_modified_probe(
        probe,
        monkeypatch,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        extension.validate_visus_public_event_extension_probe(
            probe,
            EVIDENCE,
        )


def test_probe_boundary_validation_reached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _probe_from_evidence()

    probe["scientific_boundary"]["native_gp3_evidence"] = True

    _authorize_modified_probe(
        probe,
        monkeypatch,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="native GP3 evidence",
    ):
        extension.validate_visus_public_event_extension_probe(
            probe,
            EVIDENCE,
        )


def test_compact_loader_mapping_has_no_path() -> None:
    record = _record()

    result = extension.load_visus_public_event_extension_evidence(record)

    assert result.path is None
    assert result.participant_count == 2
    assert result.sample_count == 2290
    assert result.fixation_event_count == 105
    assert result.stimulus_candidate == "03-dialog"
    assert result.stimulus_identity_resolved is False


def test_compact_loader_path_contract() -> None:
    result = extension.load_visus_public_event_extension_evidence(EVIDENCE)

    assert result.path == EVIDENCE
    assert result.fingerprint_sha256 == extension.EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert result.observed_sampling_rate_hz == pytest.approx(60.150375939849624)
