"""Validation for the pinned public VISUS-derived 60 Hz partial evidence record.

This module is deliberately separate from :mod:`gazeforge.visus_evidence`.
The original VISUS Frozen Evidence gate remains reserved for a fully audited
25-participant by 11-stimulus source.  This record certifies only the exact
public derivative files and metrics recovered from the pinned VISUS-supervised
``eye-slitscan`` repository.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "visus-public-partial-evidence-v1"
STATUS = "verified-partial-empirical"
SOURCE_CLASS = "public-visus-supervised-derivative-partial-corpus"
UPSTREAM_REPOSITORY = "Maurice189/eye-slitscan"
UPSTREAM_COMMIT = "a8ea2402936122f9e5c98152460bd16a4ba97740"
INTRODUCTION_COMMIT = "7a3dc8277a8e74949a5f6f7ee24cf589da973db1"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "80e008228e39c2b17bae99a526e2a0157c2c850ebe803c5a370abe9167efde14"
)

_EXPECTED_FILES: dict[str, dict[str, Any]] = {
    "aoi": {
        "path": "core/similarity-measures/util/test/res/01-car pursuit.xml",
        "bytes": 67618,
        "git_blob_sha1": "10ccee08b5462892eab1506e0fbb455f253e75e9",
        "sha256": "891034bf11d8c5346716a8f8a156141e2b4edf756060fdda2aad2b2028164b23",
    },
    "P1A": {
        "path": "core/similarity-measures/util/test/res/P1A-01-car pursuit.tsv",
        "bytes": 324647,
        "git_blob_sha1": "52a613c44c9b68ee42c9ae1810cf0f375f60f649",
        "sha256": "5aa3d52a61975d98764fecafa4cfe97aae3ceda1e17867a5aad021b2ef74752c",
    },
    "P2B": {
        "path": "core/similarity-measures/util/test/res/P2B-01-car pursuit.tsv",
        "bytes": 339198,
        "git_blob_sha1": "81463dcfd65e99218eae08436db02b80bb65be71",
        "sha256": "b8d4f3ff6f88071817972e7e07e138e24cbce7eafd31dd2882eb48117fdb7950",
    },
    "P9B": {
        "path": "core/similarity-measures/util/test/res/P9B-01-car pursuit.tsv",
        "bytes": 343583,
        "git_blob_sha1": "54ed468b90bb99e74c29150563cb2750a59be7f6",
        "sha256": "ddb387472349d13ad165d03216334bfdb26abdb4a58715fb4cbe6c99de4e76af",
    },
}
_EXPECTED_PARTICIPANTS = ("P1A", "P2B", "P9B")
_EXPECTED_STIMULI = ("01-car pursuit",)
_EXPECTED_AOI = {
    "source_filename": "01-car pursuit.avi",
    "number_of_frames": 625,
    "width": 1920,
    "height": 1080,
    "fps": 25.0,
    "duration_seconds": 25.0,
    "object_names": ["Red Car", "White Car"],
    "object_spans": {"Red Car": [1, 625], "White Car": [553, 590]},
    "box_counts": {"Red Car": 625, "White Car": 38},
}
_EXPECTED_EXECUTION = {
    "probe_workflow_run_id": 33924318147,
    "probe_head_sha": "6d6a80aa5ea9b0ae6ad1878786ecf5346ad7196b",
    "probe_fingerprint_sha256": "b1a301151ffae7efefdfccce647f509ec2b7ffe911b88b4979834ca526d1d4b1",
    "artifact_id": 9956210827,
    "artifact_zip_sha256": "adb1aa1c32a980dbf298d9bd8878c1c723325234510737723eb5de041cc08e2c",
}
_EXPECTED_REUSE_BOUNDARY = {
    "analysis_use_basis_recorded": True,
    "analysis_use_basis": [
        (
            "The original VISUS benchmark publication presents the corpus as input for future "
            "visualization and analysis research and for developing new analysis techniques."
        ),
        (
            "The pinned public derivative repository documents a VISUS, University of Stuttgart "
            "bachelor-thesis project supervised by Kuno Kurzhals."
        ),
    ],
    "source_license_resolved": False,
    "source_bytes_redistributed_by_gazeforge": False,
    "unrestricted_redistribution_asserted": False,
}
_EXPECTED_SCIENTIFIC_BOUNDARY = {
    "empirical_metrics_created": True,
    "public_derivative_partial_corpus_only": True,
    "original_full_visus_source_resolved": False,
    "human_human_agreement_created": False,
    "native_gp3_evidence": False,
    "frozen_evidence_created": False,
    "model_validation_created": False,
}


@dataclass(frozen=True, slots=True)
class VisusPublicPartialEvidence:
    """Compact identity of the validated public VISUS-derived partial evidence."""

    path: Path | None
    fingerprint_sha256: str
    participant_count: int
    stimulus_count: int
    sample_count: int
    fixation_event_count: int
    observed_sampling_rate_hz: float


def _canonical_bytes(record: Mapping[str, Any]) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the SHA-256 fingerprint of an evidence record excluding its fingerprint field."""

    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
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
            f"Could not load VISUS public partial evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError("VISUS public partial evidence must be a JSON object.")
    return payload, path


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"VISUS public partial evidence {label} does not match the frozen v1 contract."
        )


def _require_fraction(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise BenchmarkIntegrityError(
            f"VISUS public partial evidence {label} is not numeric."
        ) from exc
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise BenchmarkIntegrityError(f"VISUS public partial evidence {label} is outside [0, 1].")
    return number


def _aggregate_from_participants(participants: list[dict[str, Any]]) -> dict[str, Any]:
    sample_count = sum(int(row["samples_within_625_frames"]) for row in participants)
    valid_samples = sum(int(row["valid_both_eye_samples"]) for row in participants)
    sample_hits = sum(int(row["samples_hitting_any_dynamic_aoi"]) for row in participants)
    event_count = sum(int(row["fixation_event_count"]) for row in participants)
    event_hits = sum(int(row["fixation_events_hitting_any_dynamic_aoi"]) for row in participants)
    duration = sum(int(row["total_fixation_duration_ms"]) for row in participants)
    duration_hits = sum(
        int(row["fixation_duration_hitting_any_dynamic_aoi_ms"]) for row in participants
    )
    event_by_aoi: dict[str, int] = {}
    for row in participants:
        for aoi, count in dict(row["fixation_events_by_aoi"]).items():
            event_by_aoi[aoi] = event_by_aoi.get(aoi, 0) + int(count)
    sampling_rates = [float(row["inferred_sampling_rate_hz"]) for row in participants]
    if max(sampling_rates) - min(sampling_rates) > 1e-12:
        raise BenchmarkIntegrityError("VISUS public partial participant sampling rates disagree.")
    return {
        "sample_count": sample_count,
        "valid_both_eye_samples": valid_samples,
        "valid_both_eye_fraction": valid_samples / sample_count,
        "inferred_sampling_rate_hz": sampling_rates[0],
        "samples_hitting_any_dynamic_aoi": sample_hits,
        "sample_dynamic_aoi_hit_fraction": sample_hits / sample_count,
        "fixation_event_count": event_count,
        "fixation_events_hitting_any_dynamic_aoi": event_hits,
        "fixation_event_dynamic_aoi_hit_fraction": event_hits / event_count,
        "fixation_events_by_aoi": dict(sorted(event_by_aoi.items())),
        "total_fixation_duration_ms": duration,
        "fixation_duration_hitting_any_dynamic_aoi_ms": duration_hits,
        "fixation_duration_dynamic_aoi_fraction": duration_hits / duration,
    }


def validate_visus_public_partial_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the immutable v1 public VISUS-derived partial empirical record.

    The validator certifies only the exact three public Tobii recordings and one
    dynamic-AOI stimulus recovered at the pinned upstream commit.  It explicitly
    does not confer full VISUS source-audit status, dataset redistribution rights,
    human-human agreement, model validation, Frozen Evidence eligibility, or
    native Gazepoint GP3 status.
    """

    record, _ = _load_record(record_or_path)
    _require_equal(record.get("record_type"), RECORD_TYPE, "record type")
    _require_equal(record.get("status"), STATUS, "status")
    _require_equal(record.get("source_class"), SOURCE_CLASS, "source class")

    upstream = record.get("upstream")
    if not isinstance(upstream, dict):
        raise BenchmarkIntegrityError("VISUS public partial evidence upstream identity is missing.")
    _require_equal(upstream.get("repository"), UPSTREAM_REPOSITORY, "upstream repository")
    _require_equal(upstream.get("commit"), UPSTREAM_COMMIT, "upstream commit")
    _require_equal(upstream.get("introduction_commit"), INTRODUCTION_COMMIT, "introduction commit")
    _require_equal(upstream.get("files"), _EXPECTED_FILES, "source-file ledger")

    _require_equal(record.get("execution"), _EXPECTED_EXECUTION, "probe execution identity")

    coverage = record.get("coverage")
    if not isinstance(coverage, dict):
        raise BenchmarkIntegrityError("VISUS public partial evidence coverage is missing.")
    _require_equal(tuple(coverage.get("participants", [])), _EXPECTED_PARTICIPANTS, "participants")
    _require_equal(int(coverage.get("participant_count", -1)), 3, "participant count")
    _require_equal(tuple(coverage.get("stimuli", [])), _EXPECTED_STIMULI, "stimuli")
    _require_equal(int(coverage.get("stimulus_count", -1)), 1, "stimulus count")
    _require_equal(
        int(coverage.get("full_visus_participant_count", -1)),
        25,
        "full participant count",
    )
    _require_equal(int(coverage.get("full_visus_stimulus_count", -1)), 11, "full stimulus count")
    if coverage.get("full_visus_recovered") is not False:
        raise BenchmarkIntegrityError("Partial evidence must never claim full VISUS recovery.")

    _require_equal(record.get("aoi"), _EXPECTED_AOI, "dynamic-AOI contract")
    _require_equal(record.get("reuse_boundary"), _EXPECTED_REUSE_BOUNDARY, "reuse boundary")
    _require_equal(
        record.get("scientific_boundary"),
        _EXPECTED_SCIENTIFIC_BOUNDARY,
        "scientific boundary",
    )

    participants = record.get("participants")
    if not isinstance(participants, list) or len(participants) != 3:
        raise BenchmarkIntegrityError(
            "VISUS public partial evidence must contain exactly three participant records."
        )
    _require_equal(
        tuple(str(row.get("participant")) for row in participants),
        _EXPECTED_PARTICIPANTS,
        "participant record order",
    )
    for row in participants:
        _require_equal(row.get("media_geometry"), [[1920, 1080]], "participant media geometry")
        rate = float(row.get("inferred_sampling_rate_hz", math.nan))
        if not math.isclose(rate, 60.150375939849624, rel_tol=0.0, abs_tol=1e-12):
            raise BenchmarkIntegrityError(
                "VISUS public partial evidence is not the frozen 60 Hz corpus."
            )
        if int(row.get("samples_within_625_frames", -1)) <= 0:
            raise BenchmarkIntegrityError("VISUS public partial evidence has no stimulus samples.")
        if int(row.get("fixation_event_count", -1)) <= 0:
            raise BenchmarkIntegrityError("VISUS public partial evidence has no fixation events.")
        _require_fraction(row.get("valid_both_eye_fraction"), "valid-eye fraction")
        _require_fraction(row.get("sample_dynamic_aoi_hit_fraction"), "sample AOI-hit fraction")
        _require_fraction(
            row.get("fixation_event_dynamic_aoi_hit_fraction"),
            "fixation AOI-hit fraction",
        )
        _require_fraction(
            row.get("fixation_duration_dynamic_aoi_fraction"),
            "duration AOI-hit fraction",
        )

    aggregate = record.get("aggregate")
    if not isinstance(aggregate, dict):
        raise BenchmarkIntegrityError("VISUS public partial aggregate is missing.")
    recomputed = _aggregate_from_participants(participants)
    if set(aggregate) != set(recomputed):
        raise BenchmarkIntegrityError("VISUS public partial aggregate fields do not match v1.")
    for key, expected in recomputed.items():
        actual = aggregate.get(key)
        if isinstance(expected, float):
            if not math.isclose(float(actual), expected, rel_tol=0.0, abs_tol=1e-15):
                raise BenchmarkIntegrityError(
                    f"VISUS public partial aggregate {key} is inconsistent."
                )
        elif actual != expected:
            raise BenchmarkIntegrityError(f"VISUS public partial aggregate {key} is inconsistent.")

    _require_equal(int(aggregate["sample_count"]), 4498, "aggregate sample count")
    _require_equal(int(aggregate["fixation_event_count"]), 185, "aggregate fixation count")
    _require_equal(
        int(aggregate["fixation_events_hitting_any_dynamic_aoi"]),
        166,
        "aggregate AOI-hit fixation count",
    )
    _require_equal(
        int(aggregate["fixation_duration_hitting_any_dynamic_aoi_ms"]),
        70179,
        "aggregate AOI-hit fixation duration",
    )

    stored_fingerprint = str(record.get("evidence_fingerprint_sha256", ""))
    calculated_fingerprint = evidence_fingerprint(record)
    if stored_fingerprint != calculated_fingerprint:
        raise BenchmarkIntegrityError("VISUS public partial evidence self-fingerprint is invalid.")
    if stored_fingerprint != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError("VISUS public partial evidence is not the frozen v1 record.")

    return record


_EXPECTED_PROBE_FINGERPRINT_SHA256 = (
    "b1a301151ffae7efefdfccce647f509ec2b7ffe911b88b4979834ca526d1d4b1"
)
_EXPECTED_PROBE_BOUNDARY = {
    "frozen_evidence_created": False,
    "human_human_agreement_created": False,
    "native_gp3_evidence": False,
    "original_full_visus_source_resolved": False,
    "public_derivative_partial_corpus_only": True,
    "unrestricted_redistribution_asserted": False,
}


def validate_visus_public_partial_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Bind a live exact-source probe to the immutable committed v1 evidence record."""

    probe, _ = _load_record(probe_or_path)
    evidence = validate_visus_public_partial_evidence(evidence_or_path)
    _require_equal(probe.get("record_type"), "visus-public-partial-probe-v1", "probe record type")
    _require_equal(probe.get("status"), "probe_only", "probe status")

    stored = str(probe.get("probe_fingerprint_sha256", ""))
    body = dict(probe)
    body.pop("probe_fingerprint_sha256", None)
    calculated = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    if stored != calculated or stored != _EXPECTED_PROBE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError("VISUS public partial probe fingerprint is invalid.")

    upstream = probe.get("upstream")
    if not isinstance(upstream, dict):
        raise BenchmarkIntegrityError("VISUS public partial probe upstream identity is missing.")
    _require_equal(upstream.get("repository"), UPSTREAM_REPOSITORY, "probe upstream repository")
    _require_equal(upstream.get("commit"), UPSTREAM_COMMIT, "probe upstream commit")
    files = upstream.get("files")
    if not isinstance(files, dict) or set(files) != set(_EXPECTED_FILES):
        raise BenchmarkIntegrityError(
            "VISUS public partial probe source-file ledger is incomplete."
        )
    for key, expected in _EXPECTED_FILES.items():
        observed = files[key]
        if not isinstance(observed, dict):
            raise BenchmarkIntegrityError(
                "VISUS public partial probe source-file entry is invalid."
            )
        for field in ("path", "bytes", "git_blob_sha1", "sha256"):
            _require_equal(observed.get(field), expected[field], f"probe {key} {field}")

    _require_equal(probe.get("coverage"), evidence["coverage"], "probe coverage")
    _require_equal(probe.get("aoi"), evidence["aoi"], "probe dynamic-AOI contract")
    _require_equal(probe.get("participants"), evidence["participants"], "probe participant metrics")
    _require_equal(probe.get("scientific_boundary"), _EXPECTED_PROBE_BOUNDARY, "probe boundary")
    return probe


def load_visus_public_partial_evidence(path: str | Path) -> VisusPublicPartialEvidence:
    """Load the committed v1 record and return a compact validated identity."""

    record = validate_visus_public_partial_evidence(path)
    aggregate = record["aggregate"]
    coverage = record["coverage"]
    return VisusPublicPartialEvidence(
        path=Path(path),
        fingerprint_sha256=str(record["evidence_fingerprint_sha256"]),
        participant_count=int(coverage["participant_count"]),
        stimulus_count=int(coverage["stimulus_count"]),
        sample_count=int(aggregate["sample_count"]),
        fixation_event_count=int(aggregate["fixation_event_count"]),
        observed_sampling_rate_hz=float(aggregate["inferred_sampling_rate_hz"]),
    )
