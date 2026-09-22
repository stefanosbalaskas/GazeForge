from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any

import pytest
from test_visus_public_partial import (
    EVIDENCE,
    _probe_from_evidence,
    _record,
    _refingerprint,
)

import gazeforge.visus_public_partial as partial
from gazeforge.exceptions import BenchmarkIntegrityError


def test_canonical_bytes_deterministic() -> None:
    assert partial._canonical_bytes({"b": 2, "a": 1}) == partial._canonical_bytes({"a": 1, "b": 2})


def test_evidence_fingerprint_ignores_self_field() -> None:
    record = {"x": 1}
    first = partial.evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = "0" * 64
    second = partial.evidence_fingerprint(record)

    assert first == second
    assert len(first) == 64


def test_load_record_mapping_success() -> None:
    record = {"x": 1}

    observed, path = partial._load_record(record)

    assert observed == record
    assert observed is not record
    assert path is None


def test_load_record_path_success() -> None:
    observed, path = partial._load_record(EVIDENCE)

    assert isinstance(observed, dict)
    assert path == EVIDENCE


def test_load_record_missing_guard(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load VISUS public partial evidence",
    ):
        partial._load_record(tmp_path / "missing.json")


def test_load_record_invalid_json_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load VISUS public partial evidence",
    ):
        partial._load_record(path)


def test_load_record_requires_object(
    tmp_path: Path,
) -> None:
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        partial._load_record(path)


def test_require_equal_success() -> None:
    partial._require_equal(
        "same",
        "same",
        "fixture",
    )


def test_require_equal_guard() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not match the frozen v1 contract",
    ):
        partial._require_equal(
            "actual",
            "expected",
            "fixture",
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        "not-a-number",
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
        partial._require_fraction(
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
        partial._require_fraction(
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
    assert partial._require_fraction(
        value,
        "fixture",
    ) == pytest.approx(expected)


def test_aggregate_participants_success() -> None:
    record = _record()

    aggregate = partial._aggregate_from_participants(record["participants"])

    assert aggregate["sample_count"] == 4498
    assert aggregate["fixation_event_count"] == 185
    assert aggregate["inferred_sampling_rate_hz"] == pytest.approx(60.150375939849624)


def test_aggregate_sampling_rate_disagreement_guard() -> None:
    record = _record()

    participants = copy.deepcopy(record["participants"])

    participants[1]["inferred_sampling_rate_hz"] += 0.01

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sampling rates disagree",
    ):
        partial._aggregate_from_participants(participants)


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
def test_evidence_top_level_identity_guards(
    field: str,
    value: Any,
    match: str,
) -> None:
    record = _record()
    record[field] = value
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_upstream_mapping_guard() -> None:
    record = _record()
    record["upstream"] = None
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="upstream identity is missing",
    ):
        partial.validate_visus_public_partial_evidence(record)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "repository",
            "wrong/repository",
            "upstream repository",
        ),
        (
            "commit",
            "0" * 40,
            "upstream commit",
        ),
        (
            "introduction_commit",
            "0" * 40,
            "introduction commit",
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
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_execution_identity_guard() -> None:
    record = _record()

    record["execution"]["artifact_id"] += 1

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="probe execution identity",
    ):
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_coverage_mapping_guard() -> None:
    record = _record()
    record["coverage"] = None
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="coverage is missing",
    ):
        partial.validate_visus_public_partial_evidence(record)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "participants",
            ["P1A"],
            "participants",
        ),
        (
            "participant_count",
            2,
            "participant count",
        ),
        (
            "stimuli",
            ["wrong"],
            "stimuli",
        ),
        (
            "stimulus_count",
            2,
            "stimulus count",
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
    ],
)
def test_evidence_coverage_identity_guards(
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
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_full_recovery_guard() -> None:
    record = _record()

    record["coverage"]["full_visus_recovered"] = True

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="never claim full VISUS recovery",
    ):
        partial.validate_visus_public_partial_evidence(record)


@pytest.mark.parametrize(
    ("field", "expected", "match"),
    [
        (
            "aoi",
            partial._EXPECTED_AOI,
            "dynamic-AOI contract",
        ),
        (
            "reuse_boundary",
            partial._EXPECTED_REUSE_BOUNDARY,
            "reuse boundary",
        ),
        (
            "scientific_boundary",
            partial._EXPECTED_SCIENTIFIC_BOUNDARY,
            "scientific boundary",
        ),
    ],
)
def test_evidence_fixed_contract_guards(
    field: str,
    expected: dict[str, Any],
    match: str,
) -> None:
    record = _record()

    record[field] = copy.deepcopy(expected)

    first_key = next(iter(record[field]))
    record[field][first_key] = "wrong"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        partial.validate_visus_public_partial_evidence(record)


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        [{}, {}],
        [{}, {}, {}, {}],
    ],
)
def test_evidence_participant_shape_guard(
    value: Any,
) -> None:
    record = _record()
    record["participants"] = value
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly three participant records",
    ):
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_participant_nonobject_guard() -> None:
    record = _record()

    record["participants"][1] = "bad-participant-row"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="participant record must be an object",
    ):
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_participant_order_guard() -> None:
    record = _record()

    record["participants"][0], record["participants"][1] = (
        record["participants"][1],
        record["participants"][0],
    )

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="participant record order",
    ):
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_participant_geometry_guard() -> None:
    record = _record()

    record["participants"][0]["media_geometry"] = [[1280, 720]]

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="participant media geometry",
    ):
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_sampling_rate_guard() -> None:
    record = _record()

    record["participants"][0]["inferred_sampling_rate_hz"] = 60.0

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not the frozen 60 Hz corpus",
    ):
        partial.validate_visus_public_partial_evidence(record)


@pytest.mark.parametrize(
    ("field", "match"),
    [
        (
            "samples_within_625_frames",
            "no stimulus samples",
        ),
        (
            "fixation_event_count",
            "no fixation events",
        ),
    ],
)
def test_evidence_positive_count_guards(
    field: str,
    match: str,
) -> None:
    record = _record()

    record["participants"][0][field] = 0
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        partial.validate_visus_public_partial_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "valid_both_eye_fraction",
        "sample_dynamic_aoi_hit_fraction",
        "fixation_event_dynamic_aoi_hit_fraction",
        "fixation_duration_dynamic_aoi_fraction",
    ],
)
def test_evidence_participant_fraction_guards(
    field: str,
) -> None:
    record = _record()

    record["participants"][0][field] = 2.0
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=r"outside \[0, 1\]",
    ):
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_aggregate_mapping_guard() -> None:
    record = _record()
    record["aggregate"] = None
    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="aggregate is missing",
    ):
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_aggregate_field_set_guard() -> None:
    record = _record()

    record["aggregate"]["unexpected_metric"] = 1

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="aggregate fields do not match",
    ):
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_aggregate_float_consistency_guard() -> None:
    record = _record()

    record["aggregate"]["valid_both_eye_fraction"] += 0.01

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="aggregate valid_both_eye_fraction is inconsistent",
    ):
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_aggregate_integer_consistency_guard() -> None:
    record = _record()

    record["aggregate"]["valid_both_eye_samples"] += 1

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="aggregate valid_both_eye_samples is inconsistent",
    ):
        partial.validate_visus_public_partial_evidence(record)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "sample_count",
            4499,
            "aggregate sample count",
        ),
        (
            "fixation_event_count",
            186,
            "aggregate fixation count",
        ),
        (
            "fixation_events_hitting_any_dynamic_aoi",
            167,
            "aggregate AOI-hit fixation count",
        ),
        (
            "fixation_duration_hitting_any_dynamic_aoi_ms",
            70180,
            "aggregate AOI-hit fixation duration",
        ),
    ],
)
def test_evidence_frozen_aggregate_total_guards(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: int,
    match: str,
) -> None:
    record = _record()

    record["aggregate"][field] = value
    _refingerprint(record)

    monkeypatch.setattr(
        partial,
        "_aggregate_from_participants",
        lambda participants: copy.deepcopy(record["aggregate"]),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_self_fingerprint_guard() -> None:
    record = _record()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint is invalid",
    ):
        partial.validate_visus_public_partial_evidence(record)


def test_evidence_frozen_fingerprint_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _record()

    fake = "f" * 64

    record["evidence_fingerprint_sha256"] = fake

    monkeypatch.setattr(
        partial,
        "evidence_fingerprint",
        lambda value: fake,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not the frozen v1 record",
    ):
        partial.validate_visus_public_partial_evidence(record)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "record_type",
            "wrong",
            "probe record type",
        ),
        (
            "status",
            "wrong",
            "probe status",
        ),
    ],
)
def test_probe_top_level_contract_guards(
    field: str,
    value: str,
    match: str,
) -> None:
    probe = _probe_from_evidence()
    probe[field] = value

    body = dict(probe)
    body.pop(
        "probe_fingerprint_sha256",
        None,
    )
    probe["probe_fingerprint_sha256"] = partial.hashlib.sha256(
        partial._canonical_bytes(body)
    ).hexdigest()

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        partial.validate_visus_public_partial_probe(
            probe,
            EVIDENCE,
        )


def test_probe_fingerprint_guard() -> None:
    probe = _probe_from_evidence()

    probe["probe_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="probe fingerprint is invalid",
    ):
        partial.validate_visus_public_partial_probe(
            probe,
            EVIDENCE,
        )


def test_probe_upstream_mapping_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _probe_from_evidence()
    probe["upstream"] = None

    monkeypatch.setattr(
        partial,
        "_EXPECTED_PROBE_FINGERPRINT_SHA256",
        partial.hashlib.sha256(
            partial._canonical_bytes(
                {key: value for key, value in probe.items() if key != "probe_fingerprint_sha256"}
            )
        ).hexdigest(),
    )

    probe["probe_fingerprint_sha256"] = partial._EXPECTED_PROBE_FINGERPRINT_SHA256

    with pytest.raises(
        BenchmarkIntegrityError,
        match="probe upstream identity is missing",
    ):
        partial.validate_visus_public_partial_probe(
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
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    match: str,
) -> None:
    probe = _probe_from_evidence()

    probe["upstream"][field] = "wrong"

    body = {key: value for key, value in probe.items() if key != "probe_fingerprint_sha256"}

    fake = partial.hashlib.sha256(partial._canonical_bytes(body)).hexdigest()

    probe["probe_fingerprint_sha256"] = fake

    monkeypatch.setattr(
        partial,
        "_EXPECTED_PROBE_FINGERPRINT_SHA256",
        fake,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        partial.validate_visus_public_partial_probe(
            probe,
            EVIDENCE,
        )


def test_probe_file_ledger_shape_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _probe_from_evidence()

    del probe["upstream"]["files"]["P9B"]

    body = {key: value for key, value in probe.items() if key != "probe_fingerprint_sha256"}

    fake = partial.hashlib.sha256(partial._canonical_bytes(body)).hexdigest()

    probe["probe_fingerprint_sha256"] = fake

    monkeypatch.setattr(
        partial,
        "_EXPECTED_PROBE_FINGERPRINT_SHA256",
        fake,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source-file ledger is incomplete",
    ):
        partial.validate_visus_public_partial_probe(
            probe,
            EVIDENCE,
        )


def test_probe_file_entry_mapping_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _probe_from_evidence()

    probe["upstream"]["files"]["P1A"] = "bad-entry"

    body = {key: value for key, value in probe.items() if key != "probe_fingerprint_sha256"}

    fake = partial.hashlib.sha256(partial._canonical_bytes(body)).hexdigest()

    probe["probe_fingerprint_sha256"] = fake

    monkeypatch.setattr(
        partial,
        "_EXPECTED_PROBE_FINGERPRINT_SHA256",
        fake,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source-file entry is invalid",
    ):
        partial.validate_visus_public_partial_probe(
            probe,
            EVIDENCE,
        )


@pytest.mark.parametrize(
    "field",
    [
        "path",
        "bytes",
        "git_blob_sha1",
        "sha256",
    ],
)
def test_probe_file_entry_identity_guards(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    probe = _probe_from_evidence()

    probe["upstream"]["files"]["P1A"][field] = 0 if field == "bytes" else "wrong"

    body = {key: value for key, value in probe.items() if key != "probe_fingerprint_sha256"}

    fake = partial.hashlib.sha256(partial._canonical_bytes(body)).hexdigest()

    probe["probe_fingerprint_sha256"] = fake

    monkeypatch.setattr(
        partial,
        "_EXPECTED_PROBE_FINGERPRINT_SHA256",
        fake,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=f"probe P1A {field}",
    ):
        partial.validate_visus_public_partial_probe(
            probe,
            EVIDENCE,
        )


@pytest.mark.parametrize(
    ("field", "match"),
    [
        (
            "coverage",
            "probe coverage",
        ),
        (
            "aoi",
            "probe dynamic-AOI contract",
        ),
        (
            "participants",
            "probe participant metrics",
        ),
        (
            "scientific_boundary",
            "probe boundary",
        ),
    ],
)
def test_probe_evidence_binding_guards(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    match: str,
) -> None:
    probe = _probe_from_evidence()

    if isinstance(probe[field], list):
        probe[field] = []
    elif isinstance(probe[field], dict):
        probe[field] = {
            "wrong": True,
        }
    else:
        probe[field] = None

    body = {key: value for key, value in probe.items() if key != "probe_fingerprint_sha256"}

    fake = partial.hashlib.sha256(partial._canonical_bytes(body)).hexdigest()

    probe["probe_fingerprint_sha256"] = fake

    monkeypatch.setattr(
        partial,
        "_EXPECTED_PROBE_FINGERPRINT_SHA256",
        fake,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        partial.validate_visus_public_partial_probe(
            probe,
            EVIDENCE,
        )


def test_compact_loader_full_contract() -> None:
    evidence = partial.load_visus_public_partial_evidence(EVIDENCE)

    assert evidence.path == EVIDENCE
    assert evidence.fingerprint_sha256 == partial.EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert evidence.participant_count == 3
    assert evidence.stimulus_count == 1
    assert evidence.sample_count == 4498
    assert evidence.fixation_event_count == 185
