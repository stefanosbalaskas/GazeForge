"""Validation for the pinned public VISUS-derived 60 Hz event-extension evidence.

This module certifies two complete public Tobii exports recovered from the
VISUS-supervised ``eye-slitscan`` repository. Participant identity and 60 Hz
event metrics are file-bound; the likely ``03-dialog`` stimulus identity is
explicitly retained as an inference rather than promoted to source resolution.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "visus-public-event-extension-evidence-v1"
STATUS = "verified-partial-empirical"
SOURCE_CLASS = "public-visus-supervised-derivative-event-extension"
UPSTREAM_REPOSITORY = "Maurice189/eye-slitscan"
UPSTREAM_COMMIT = "a8ea2402936122f9e5c98152460bd16a4ba97740"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "2f12bd83d71786bfae7101dec6515c49c5ff4e696df8675b3955300e5e5e6dfd"
)
EXPECTED_PROBE_FINGERPRINT_SHA256 = (
    "47316bcb77e3cf1a92fdb95df84cf401c31fdafd6fc6affce3b9f6405f92312e"
)

_EXPECTED_FILES: dict[str, dict[str, Any]] = {
    "P5B": {
        "path": "core/importer/eye-tracker-output/test/Tobii_exports/01-OK.tsv",
        "bytes": 263072,
        "git_blob_sha1": "fd2371fd6f44de8a188e52439a0fea6b2054f975",
        "sha256": "df9ee65adb3a9872121f5ae3204842b0ab2efe107682151a287168f526b2c4b6",
    },
    "P3A": {
        "path": "core/importer/eye-tracker-output/test/Tobii_exports/02-OK.tsv",
        "bytes": 256538,
        "git_blob_sha1": "e39b0c0d2c50c22dec76b93581a4ca2bce784546",
        "sha256": "619da12969d04b774b9456b1b50e8cba6b21c04df33e2e90ef1c798a511d2bbc",
    },
    "lock_P2B_dialog": {
        "path": (
            "core/importer/eye-tracker-output/test/Tobii_exports/"
            ".~lock.P2B-03-dialog.tsv#"
        ),
        "bytes": 86,
        "git_blob_sha1": "512f8242f20b8ecef29fcd45703e157f67d826c6",
        "sha256": "ba23784ed4914988227b6881b1f39fec527c9368a9a97a1377cff70f72fc327c",
    },
    "lock_P4B_dialog": {
        "path": (
            "core/importer/eye-tracker-output/test/Tobii_exports/"
            ".~lock.P4B-03-dialog.tsv#"
        ),
        "bytes": 86,
        "git_blob_sha1": "4ccb75c30a65dea74aa221f1082c3f0a789b2515",
        "sha256": "4f3b2a34d867d5dac51348fca110a3f0f0f121dcd786665326318fca3093346a",
    },
    "lock_P6A_dialog": {
        "path": (
            "core/importer/eye-tracker-output/test/Tobii_exports/"
            ".~lock.P6A-03-dialog.tsv#"
        ),
        "bytes": 86,
        "git_blob_sha1": "03bedf17e307276eb8d9aad5f7f8070f8121f9c5",
        "sha256": "373993fd133df932e9dd7a361cd13046aaa991a58002615f41b3e424d4a50401",
    },
    "upstream_test_source": {
        "path": "core/importer/eye-tracker-output/test/test.cc",
        "bytes": 6081,
        "git_blob_sha1": "d5f681eb4cc7b90c6078dc1fb7ceeccb4cc03c41",
        "sha256": "999ab4c53e0817a65fc12bb9c143e19490059bb71bab5c6a03a2533cc9e5d1ee",
    },
}
_EXPECTED_EXECUTION = {
    "probe_workflow_run_id": 33928088952,
    "probe_head_sha": "9308c79dc3f6ef9d42383e85ec2abc6bad0b783d",
    "probe_fingerprint_sha256": EXPECTED_PROBE_FINGERPRINT_SHA256,
    "artifact_id": 9957528541,
    "artifact_zip_sha256": (
        "cc9f139c9c7b27649fefd8a302801707bbe6dc6140f49fafd3525971a02f437d"
    ),
}
_EXPECTED_UNIT_TEST = {
    "path": "core/importer/eye-tracker-output/test/test.cc",
    "valid_export_filenames": [
        "Tobii_exports/01-OK.tsv",
        "Tobii_exports/02-OK.tsv",
    ],
    "row_value_assertions_verified": True,
    "required_assertion_count": 10,
    "provenance_only": True,
    "empirical_data": False,
}
_EXPECTED_COUNTS = {
    "P5B": {
        "sample_count": 1145,
        "valid_both_eye_samples": 1136,
        "fixation_event_count": 62,
        "total_fixation_duration_ms": 19765,
        "fixations_with_on_screen_mapped_point": 62,
        "movie_span_ms": 19063,
    },
    "P3A": {
        "sample_count": 1145,
        "valid_both_eye_samples": 1136,
        "fixation_event_count": 43,
        "total_fixation_duration_ms": 19849,
        "fixations_with_on_screen_mapped_point": 42,
        "movie_span_ms": 19069,
    },
}
_EXPECTED_LOCK_CONTENT = {
    "lock_P2B_dialog": (
        "Maurice Koch,maurice,n581,21.05.2017 18:40,"
        "file:///home/maurice/.config/libreoffice/4;"
    ),
    "lock_P4B_dialog": (
        "Maurice Koch,maurice,n581,21.05.2017 21:05,"
        "file:///home/maurice/.config/libreoffice/4;"
    ),
    "lock_P6A_dialog": (
        "Maurice Koch,maurice,n581,21.05.2017 22:27,"
        "file:///home/maurice/.config/libreoffice/4;"
    ),
}


@dataclass(frozen=True, slots=True)
class VisusPublicEventExtensionEvidence:
    """Compact identity of the validated VISUS public event-extension evidence."""

    path: Path | None
    fingerprint_sha256: str
    participant_count: int
    sample_count: int
    fixation_event_count: int
    observed_sampling_rate_hz: float
    stimulus_candidate: str
    stimulus_identity_resolved: bool


def _canonical_bytes(record: Mapping[str, Any]) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the SHA-256 fingerprint excluding the self-fingerprint field."""

    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _probe_fingerprint(record: Mapping[str, Any]) -> str:
    body = dict(record)
    body.pop("probe_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load_record(
    record_or_path: Mapping[str, Any] | str | Path,
) -> tuple[dict[str, Any], Path | None]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path), None
    path = Path(record_or_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load VISUS public event-extension evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "VISUS public event-extension evidence must be a JSON object."
        )
    return payload, path


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"VISUS public event-extension {label} does not match the frozen v1 contract."
        )


def _require_false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"VISUS event-extension must not promote {label}.")


def _require_true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"VISUS event-extension must preserve {label}.")


def _require_fraction(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise BenchmarkIntegrityError(
            f"VISUS event-extension {label} is not numeric."
        ) from exc
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise BenchmarkIntegrityError(
            f"VISUS event-extension {label} is outside [0, 1]."
        )
    return number


def _files_without_urls(files: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    cleaned: dict[str, dict[str, Any]] = {}
    for key, value in files.items():
        if not isinstance(value, Mapping):
            raise BenchmarkIntegrityError(
                f"VISUS event-extension source ledger {key} is malformed."
            )
        cleaned[key] = {
            name: item for name, item in value.items() if name != "url"
        }
    return cleaned


def _validate_boundaries(record: Mapping[str, Any]) -> None:
    inference = record.get("stimulus_inference")
    if not isinstance(inference, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS event-extension stimulus inference is missing."
        )
    _require_equal(inference.get("candidate"), "03-dialog", "stimulus candidate")
    _require_equal(
        inference.get("identity_status"),
        "strongly-inferred-not-file-bound",
        "stimulus identity status",
    )
    _require_false(
        inference.get("stimulus_identity_resolved"),
        "resolved stimulus identity",
    )
    _require_false(
        inference.get("aoi_annotation_recovered_for_candidate"),
        "candidate AOI annotation recovery",
    )
    _require_true(inference.get("duration_matches_candidate"), "19 s duration match")

    reuse = record.get("reuse_boundary")
    if not isinstance(reuse, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS event-extension reuse boundary is missing."
        )
    _require_true(reuse.get("analysis_use_basis_recorded"), "analysis-use basis")
    _require_false(
        reuse.get("source_license_resolved"),
        "source-license resolution",
    )
    _require_false(
        reuse.get("source_bytes_redistributed_by_gazeforge"),
        "source-byte redistribution",
    )
    _require_false(
        reuse.get("unrestricted_redistribution_asserted"),
        "unrestricted redistribution",
    )

    boundary = record.get("scientific_boundary")
    if not isinstance(boundary, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS event-extension scientific boundary is missing."
        )
    _require_true(
        boundary.get("real_external_tobii_60hz_exports"),
        "real Tobii 60 Hz status",
    )
    _require_true(
        boundary.get("participant_identity_file_bound"),
        "file-bound participant identity",
    )
    _require_false(
        boundary.get("stimulus_identity_file_bound"),
        "file-bound stimulus identity",
    )
    _require_true(
        boundary.get("dialog_assignment_is_inference"),
        "Dialog inference status",
    )
    for key, label in (
        ("dynamic_aoi_metrics_created", "dynamic AOI evidence"),
        ("human_human_agreement_created", "human-human agreement"),
        ("model_validation_created", "model validation"),
        ("native_gp3_evidence", "native GP3 evidence"),
        ("original_full_visus_source_resolved", "full VISUS source resolution"),
        ("frozen_evidence_created", "Frozen Evidence"),
    ):
        _require_false(boundary.get(key), label)


def _validate_participants(participants: Any) -> list[dict[str, Any]]:
    if not isinstance(participants, list) or len(participants) != 2:
        raise BenchmarkIntegrityError(
            "VISUS event-extension requires exactly two participant records."
        )
    _require_equal(
        tuple(str(row.get("participant")) for row in participants),
        ("P5B", "P3A"),
        "participant order",
    )
    for row in participants:
        participant = str(row.get("participant"))
        _require_equal(
            row.get("recording_name"),
            participant,
            f"{participant} recording name",
        )
        _require_equal(
            row.get("recording_resolution"),
            "1920 x 1200",
            "recording resolution",
        )
        _require_equal(row.get("media_geometry"), [[1920, 1080]], "media geometry")
        _require_equal(row.get("eye"), "Average", "eye setting")
        _require_equal(row.get("validity_filter"), "Normal", "validity filter")
        _require_equal(
            row.get("fixation_filter"),
            "Tobii fixation filter",
            "fixation filter",
        )
        _require_equal(
            int(row.get("velocity_threshold", -1)),
            35,
            "velocity threshold",
        )
        _require_equal(
            int(row.get("distance_threshold", -1)),
            35,
            "distance threshold",
        )
        for key, expected in _EXPECTED_COUNTS[participant].items():
            _require_equal(int(row.get(key, -1)), expected, f"{participant} {key}")
        rate = float(row.get("inferred_sampling_rate_hz", math.nan))
        if not math.isclose(
            rate,
            60.150375939849624,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise BenchmarkIntegrityError(
                "VISUS event-extension sampling rate drifted from ~60 Hz."
            )
        _require_equal(
            float(row.get("median_positive_sample_delta_us", -1)),
            16625.0,
            "sample delta",
        )
        _require_fraction(
            row.get("valid_both_eye_fraction"),
            "valid-eye fraction",
        )
        _require_fraction(
            row.get("on_screen_fixation_fraction"),
            "on-screen fixation fraction",
        )
    return participants


def _validate_aggregate(
    record: Mapping[str, Any],
    participants: list[dict[str, Any]],
) -> None:
    aggregate = record.get("aggregate")
    if not isinstance(aggregate, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS event-extension aggregate is missing."
        )
    expected = {
        "participant_count": len(participants),
        "sample_count": sum(int(row["sample_count"]) for row in participants),
        "valid_both_eye_samples": sum(
            int(row["valid_both_eye_samples"]) for row in participants
        ),
        "fixation_event_count": sum(
            int(row["fixation_event_count"]) for row in participants
        ),
        "total_fixation_duration_ms": sum(
            int(row["total_fixation_duration_ms"]) for row in participants
        ),
        "fixations_with_on_screen_mapped_point": sum(
            int(row["fixations_with_on_screen_mapped_point"]) for row in participants
        ),
    }
    expected["valid_both_eye_fraction"] = (
        expected["valid_both_eye_samples"] / expected["sample_count"]
    )
    expected["on_screen_fixation_fraction"] = (
        expected["fixations_with_on_screen_mapped_point"]
        / expected["fixation_event_count"]
    )
    _require_equal(set(aggregate), set(expected), "aggregate fields")
    for key, value in expected.items():
        actual = aggregate.get(key)
        if isinstance(value, float):
            if not math.isclose(
                float(actual),
                value,
                rel_tol=0.0,
                abs_tol=1e-15,
            ):
                raise BenchmarkIntegrityError(
                    f"VISUS event-extension aggregate {key} is inconsistent."
                )
        else:
            _require_equal(actual, value, f"aggregate {key}")
    _require_equal(
        int(aggregate["sample_count"]),
        2290,
        "aggregate sample count",
    )
    _require_equal(
        int(aggregate["fixation_event_count"]),
        105,
        "aggregate fixation count",
    )


def _validate_locks(locks: Any) -> None:
    if not isinstance(locks, list) or len(locks) != 3:
        raise BenchmarkIntegrityError(
            "VISUS event-extension requires three provenance lockfiles."
        )
    for row in locks:
        key = str(row.get("ledger_key"))
        if key not in _EXPECTED_LOCK_CONTENT:
            raise BenchmarkIntegrityError(
                f"Unexpected VISUS Dialog lockfile ledger key: {key}"
            )
        _require_equal(
            row.get("content"),
            _EXPECTED_LOCK_CONTENT[key],
            f"{key} content",
        )
        _require_true(
            row.get("provenance_only"),
            f"{key} provenance-only status",
        )
        _require_false(
            row.get("empirical_data"),
            f"{key} empirical-data status",
        )


def validate_visus_public_event_extension_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the immutable v1 VISUS public 60 Hz event-extension record."""

    record, _ = _load_record(record_or_path)
    _require_equal(record.get("record_type"), RECORD_TYPE, "record type")
    _require_equal(record.get("status"), STATUS, "status")
    _require_equal(record.get("source_class"), SOURCE_CLASS, "source class")

    upstream = record.get("upstream")
    if not isinstance(upstream, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS event-extension upstream identity is missing."
        )
    _require_equal(
        upstream.get("repository"),
        UPSTREAM_REPOSITORY,
        "upstream repository",
    )
    _require_equal(upstream.get("commit"), UPSTREAM_COMMIT, "upstream commit")
    _require_equal(upstream.get("files"), _EXPECTED_FILES, "source-file ledger")
    _require_equal(
        upstream.get("unit_test_provenance"),
        _EXPECTED_UNIT_TEST,
        "unit-test provenance",
    )
    _require_equal(
        record.get("execution"),
        _EXPECTED_EXECUTION,
        "probe execution identity",
    )

    coverage = record.get("coverage")
    if not isinstance(coverage, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS event-extension coverage is missing."
        )
    _require_equal(
        tuple(coverage.get("participants", [])),
        ("P5B", "P3A"),
        "participants",
    )
    _require_equal(
        int(coverage.get("participant_count", -1)),
        2,
        "participant count",
    )
    _require_equal(
        int(coverage.get("complete_tobii_exports", -1)),
        2,
        "complete export count",
    )
    _require_equal(
        int(coverage.get("provenance_lockfiles", -1)),
        3,
        "lockfile count",
    )
    _require_equal(
        int(coverage.get("full_visus_participant_count", -1)),
        25,
        "full participant count",
    )
    _require_equal(
        int(coverage.get("full_visus_stimulus_count", -1)),
        11,
        "full stimulus count",
    )
    _require_false(coverage.get("full_visus_recovered"), "full VISUS recovery")

    _validate_boundaries(record)
    participants = _validate_participants(record.get("participants"))
    _validate_aggregate(record, participants)
    _validate_locks(record.get("provenance_lockfiles"))

    duration = record.get("duration_semantics")
    if not isinstance(duration, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS event-extension duration semantics are missing."
        )
    _require_equal(
        int(duration.get("exported_fixation_duration_sum_ms", -1)),
        39614,
        "duration sum",
    )
    _require_equal(
        int(duration.get("participant_movie_span_sum_ms", -1)),
        38132,
        "movie-span sum",
    )
    _require_false(
        duration.get("fixation_durations_clipped_to_movie_boundaries"),
        "clipped fixation durations",
    )

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    calculated = evidence_fingerprint(record)
    if stored != calculated:
        raise BenchmarkIntegrityError(
            "VISUS event-extension evidence self-fingerprint is invalid."
        )
    if stored != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError(
            "VISUS event-extension immutable v1 fingerprint drifted."
        )
    return record


def validate_visus_public_event_extension_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Bind a freshly generated upstream probe to the immutable evidence record."""

    evidence = validate_visus_public_event_extension_evidence(evidence_or_path)
    probe, _ = _load_record(probe_or_path)
    _require_equal(
        probe.get("record_type"),
        "visus-public-event-extension-probe-v1",
        "probe type",
    )
    _require_equal(probe.get("status"), "probe_only", "probe status")
    stored_probe = str(probe.get("probe_fingerprint_sha256", ""))
    if stored_probe != _probe_fingerprint(probe):
        raise BenchmarkIntegrityError(
            "VISUS event-extension live probe fingerprint is invalid."
        )
    if stored_probe != EXPECTED_PROBE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError(
            "VISUS event-extension live probe drifted from frozen v1."
        )

    upstream = probe.get("upstream")
    if not isinstance(upstream, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS event-extension live probe upstream identity is missing."
        )
    _require_equal(
        upstream.get("repository"),
        UPSTREAM_REPOSITORY,
        "probe upstream repository",
    )
    _require_equal(
        upstream.get("commit"),
        UPSTREAM_COMMIT,
        "probe upstream commit",
    )
    probe_files = upstream.get("files")
    if not isinstance(probe_files, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS event-extension live probe source ledger is missing."
        )
    _require_equal(
        _files_without_urls(probe_files),
        evidence["upstream"]["files"],
        "live source ledger",
    )
    _require_equal(
        upstream.get("unit_test_provenance"),
        evidence["upstream"]["unit_test_provenance"],
        "live unit-test provenance",
    )
    _require_equal(
        probe.get("coverage"),
        evidence.get("coverage"),
        "live coverage",
    )
    _require_equal(
        probe.get("participants"),
        evidence.get("participants"),
        "live participants",
    )
    _require_equal(
        probe.get("aggregate"),
        evidence.get("aggregate"),
        "live aggregate",
    )
    _require_equal(
        probe.get("stimulus_inference"),
        evidence.get("stimulus_inference"),
        "live stimulus inference",
    )
    _require_equal(
        probe.get("provenance_lockfiles"),
        evidence.get("provenance_lockfiles"),
        "live lockfile provenance",
    )
    _validate_boundaries(probe)
    return evidence


def load_visus_public_event_extension_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> VisusPublicEventExtensionEvidence:
    """Validate and return a compact typed identity for the frozen evidence."""

    record, path = _load_record(record_or_path)
    validated = validate_visus_public_event_extension_evidence(record)
    participants = validated["participants"]
    return VisusPublicEventExtensionEvidence(
        path=path,
        fingerprint_sha256=validated["evidence_fingerprint_sha256"],
        participant_count=int(validated["coverage"]["participant_count"]),
        sample_count=int(validated["aggregate"]["sample_count"]),
        fixation_event_count=int(validated["aggregate"]["fixation_event_count"]),
        observed_sampling_rate_hz=float(
            participants[0]["inferred_sampling_rate_hz"]
        ),
        stimulus_candidate=str(validated["stimulus_inference"]["candidate"]),
        stimulus_identity_resolved=bool(
            validated["stimulus_inference"]["stimulus_identity_resolved"]
        ),
    )
