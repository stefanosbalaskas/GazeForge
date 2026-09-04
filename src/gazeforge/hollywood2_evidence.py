"""Validation for the pinned authoritative Hollywood2EM ground-truth evidence.

The evidence binds the canonical GIN repository to an exact revision and to
all 697 hand-labelled ground-truth ARFF blobs.  It also freezes the observed
student-to-expert-corrected annotation sensitivity while explicitly refusing
to reinterpret the sequential correction workflow as independent human-human
agreement.
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

RECORD_TYPE = "hollywood2-authoritative-ground-truth-evidence-v1"
STATUS = "verified-authoritative-empirical"
SOURCE_CLASS = "canonical-gin-hand-labelled-ground-truth"
UPSTREAM_REPOSITORY = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
UPSTREAM_COMMIT = "870fa6d6209c9085260918d61433a0a2c70fd497"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea"
)
EXPECTED_PROBE_FINGERPRINT_SHA256 = (
    "b3137d6bc4ff049802e6cdc62f6e9d3b8e490fe42384d501f789ba3bacb691dd"
)
EXPECTED_LEDGER_FINGERPRINT_SHA256 = (
    "51dd0883cf5b7966a4caea94fb9ac97e43bee6cf716423f26f268810041d3030"
)

_EXPECTED_TOKENS = (
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
_EXPECTED_FINAL_COUNTS = {
    "FIX": 2414211,
    "NOISE": 167248,
    "SACCADE": 353208,
    "SP": 936913,
}
_EXPECTED_SCHEMA = [
    {"name": "time", "type": "INTEGER"},
    {"name": "x", "type": "NUMERIC"},
    {"name": "y", "type": "NUMERIC"},
    {"name": "confidence", "type": "NUMERIC"},
    {"name": "handlabeller_1", "type": "{UNKNOWN,FIX,SACCADE,SP,NOISE}"},
    {"name": "handlabeller_final", "type": "{UNKNOWN,FIX,SACCADE,SP,NOISE}"},
]
_EXPECTED_CONFUSION = {
    "FIX->FIX": 2169287,
    "FIX->NOISE": 8334,
    "FIX->SACCADE": 4249,
    "FIX->SP": 8179,
    "NOISE->FIX": 1621,
    "NOISE->NOISE": 150316,
    "NOISE->SACCADE": 119,
    "NOISE->SP": 434,
    "SACCADE->FIX": 41644,
    "SACCADE->NOISE": 7796,
    "SACCADE->SACCADE": 347066,
    "SACCADE->SP": 14701,
    "SP->FIX": 201659,
    "SP->NOISE": 800,
    "SP->SACCADE": 1774,
    "SP->SP": 913596,
    "UNKNOWN->NOISE": 2,
    "UNKNOWN->SP": 3,
}


@dataclass(frozen=True, slots=True)
class Hollywood2AuthoritativeEvidence:
    """Compact identity of the validated Hollywood2EM evidence record."""

    path: Path | None
    fingerprint_sha256: str
    upstream_commit_sha1: str
    ground_truth_file_count: int
    sample_count: int
    clip_count: int
    file_subject_token_count: int
    student_final_raw_agreement: float


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the evidence SHA-256 excluding its self-fingerprint field."""

    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _probe_fingerprint(record: Mapping[str, Any]) -> str:
    body = dict(record)
    body.pop("probe_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _ledger_fingerprint(entries: Any) -> str:
    return hashlib.sha256(_canonical_bytes(entries)).hexdigest()


def _load_record(
    record_or_path: Mapping[str, Any] | str | Path,
) -> tuple[dict[str, Any], Path | None]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path), None
    path = Path(record_or_path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"Could not load Hollywood2 evidence: {exc}") from exc
    if not isinstance(value, dict):
        raise BenchmarkIntegrityError("Hollywood2 evidence must be a JSON object.")
    return value, path


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"Hollywood2 {label} does not match the frozen authoritative v1 contract."
        )


def _require_true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"Hollywood2 evidence must preserve {label}.")


def _require_false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"Hollywood2 evidence must not promote {label}.")


def _validate_coverage(record: Mapping[str, Any]) -> None:
    coverage = record.get("coverage")
    if not isinstance(coverage, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 coverage is missing.")
    _require_equal(int(coverage.get("ground_truth_file_count", -1)), 697, "file count")
    _require_equal(int(coverage.get("ground_truth_total_bytes", -1)), 137328178, "byte count")
    _require_equal(
        int(coverage.get("ground_truth_total_samples", -1)),
        3871580,
        "sample count",
    )
    _require_equal(coverage.get("splits"), {"test": 642, "train": 55}, "split counts")
    _require_equal(int(coverage.get("clip_count", -1)), 56, "clip count")
    _require_equal(
        int(coverage.get("file_subject_token_count", -1)),
        16,
        "file subject-token count",
    )
    _require_equal(tuple(coverage.get("file_subject_tokens", [])), _EXPECTED_TOKENS, "tokens")


def _validate_schema(record: Mapping[str, Any]) -> None:
    schema = record.get("schema")
    if not isinstance(schema, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 schema is missing.")
    _require_equal(schema.get("relation"), "gaze_labels", "ARFF relation")
    _require_equal(schema.get("attributes"), _EXPECTED_SCHEMA, "ARFF schema")
    _require_equal(
        schema.get("schema_signature_sha256"),
        "31a6db306fded47592ad4c1647da8df3413df970a2b8abcba91e23d6261881c0",
        "schema fingerprint",
    )
    _require_equal(int(schema.get("schema_signature_file_count", -1)), 697, "schema coverage")


def _validate_labels(record: Mapping[str, Any]) -> None:
    labels = record.get("final_labels")
    if not isinstance(labels, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 final-label evidence is missing.")
    counts = labels.get("counts")
    _require_equal(counts, _EXPECTED_FINAL_COUNTS, "final-label counts")
    fractions = labels.get("fractions")
    if not isinstance(fractions, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 final-label fractions are missing.")
    total = sum(_EXPECTED_FINAL_COUNTS.values())
    for key, count in _EXPECTED_FINAL_COUNTS.items():
        actual = float(fractions.get(key, math.nan))
        expected = count / total
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-15):
            raise BenchmarkIntegrityError(f"Hollywood2 final-label fraction {key} drifted.")
    crosscheck = labels.get("publication_crosscheck")
    if not isinstance(crosscheck, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 publication cross-check is missing.")
    _require_true(crosscheck.get("counts_reproduce_reported_rounding"), "publication cross-check")


def _validate_sensitivity(record: Mapping[str, Any]) -> None:
    sensitivity = record.get("student_vs_expert_corrected_sensitivity")
    if not isinstance(sensitivity, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 annotation-sensitivity evidence is missing.")
    _require_equal(int(sensitivity.get("sample_count", -1)), 3871580, "sensitivity sample count")
    _require_equal(int(sensitivity.get("equal_sample_count", -1)), 3580265, "equal sample count")
    _require_equal(int(sensitivity.get("changed_sample_count", -1)), 291315, "changed sample count")
    _require_equal(sensitivity.get("confusion"), _EXPECTED_CONFUSION, "student/final confusion")
    agreement = float(sensitivity.get("raw_agreement_fraction", math.nan))
    expected = 3580265 / 3871580
    if not math.isclose(agreement, expected, rel_tol=0.0, abs_tol=1e-15):
        raise BenchmarkIntegrityError("Hollywood2 student/final raw agreement drifted.")
    interpretation = str(sensitivity.get("interpretation", ""))
    if "not independent human-human" not in interpretation:
        raise BenchmarkIntegrityError(
            "Hollywood2 sensitivity must remain distinct from independent reliability."
        )


def _validate_boundaries(record: Mapping[str, Any]) -> None:
    rights = record.get("rights")
    if not isinstance(rights, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 rights boundary is missing.")
    _require_false(rights.get("repository_license_file_recovered"), "repository license recovery")
    _require_false(rights.get("dataset_specific_license_verified"), "dataset-license verification")
    _require_false(rights.get("article_cc_by_is_dataset_license"), "article license as dataset license")
    _require_false(rights.get("source_bytes_redistributed_by_gazeforge"), "source-byte redistribution")
    _require_equal(rights.get("analysis_use_terms_status"), "unresolved", "analysis-use status")
    _require_equal(
        rights.get("raw_data_redistribution_terms_status"),
        "unresolved",
        "redistribution status",
    )

    boundary = record.get("scientific_boundary")
    if not isinstance(boundary, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 scientific boundary is missing.")
    for key, label in (
        ("authoritative_repository_revision_resolved", "repository revision resolution"),
        ("authoritative_ground_truth_blobs_recovered", "ground-truth blob recovery"),
        ("ground_truth_source_identity_ledger_created", "source ledger"),
        ("trial_clip_identity_file_bound", "file-bound clip identity"),
        ("file_subject_tokens_recovered", "file subject-token recovery"),
        ("time_unit_verified", "time-unit verification"),
        ("coordinate_unit_verified", "coordinate-unit verification"),
        ("student_vs_expert_corrected_sensitivity_created", "annotation sensitivity"),
    ):
        _require_true(boundary.get(key), label)
    for key, label in (
        ("participant_identity_mapping_verified", "participant identity mapping"),
        ("independent_human_human_agreement_created", "independent human-human agreement"),
        ("model_validation_created", "model validation"),
        ("cross_dataset_validation_created", "cross-dataset validation"),
        ("full_original_hollywood2_video_dataset_recovered", "full video dataset recovery"),
        ("frozen_evidence_created", "canonical Frozen Evidence"),
    ):
        _require_false(boundary.get(key), label)


def validate_hollywood2_authoritative_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the immutable Hollywood2 authoritative ground-truth v1 record."""

    record, _ = _load_record(record_or_path)
    _require_equal(record.get("record_type"), RECORD_TYPE, "record type")
    _require_equal(record.get("status"), STATUS, "status")
    _require_equal(record.get("source_class"), SOURCE_CLASS, "source class")
    upstream = record.get("upstream")
    if not isinstance(upstream, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 upstream identity is missing.")
    _require_equal(upstream.get("repository"), UPSTREAM_REPOSITORY, "upstream repository")
    _require_equal(upstream.get("default_ref"), "refs/heads/master", "upstream default ref")
    _require_equal(upstream.get("commit_sha1"), UPSTREAM_COMMIT, "upstream commit")
    readme = upstream.get("readme")
    if not isinstance(readme, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 README identity is missing.")
    _require_equal(readme.get("git_blob_sha1"), "c8b7d126295e5f52a7748533952f044228423bf8", "README blob")
    _require_equal(readme.get("sha256"), "97f839bda127674b5de1eb5d8c3b1d2c82d65e7c6c1708c2e9f9711170ada383", "README SHA-256")

    execution = record.get("execution")
    if not isinstance(execution, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 probe execution identity is missing.")
    _require_equal(execution.get("probe_fingerprint_sha256"), EXPECTED_PROBE_FINGERPRINT_SHA256, "probe fingerprint")

    ledger = record.get("source_ledger")
    if not isinstance(ledger, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 source-ledger identity is missing.")
    _require_equal(int(ledger.get("entry_count", -1)), 697, "source-ledger entry count")
    _require_equal(ledger.get("entries_fingerprint_sha256"), EXPECTED_LEDGER_FINGERPRINT_SHA256, "source-ledger fingerprint")
    _require_false(ledger.get("raw_entry_ledger_committed"), "raw source-ledger byte embedding")
    _require_true(ledger.get("regenerable_from_pinned_upstream_commit"), "ledger regeneration")

    _validate_coverage(record)
    _validate_schema(record)
    _validate_labels(record)
    _validate_sensitivity(record)
    _validate_boundaries(record)

    semantics = record.get("format_semantics")
    if not isinstance(semantics, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 format semantics are missing.")
    _require_equal(semantics.get("time_unit"), "microseconds", "time unit")
    _require_equal(semantics.get("coordinate_unit"), "pixels", "coordinate unit")
    _require_equal(float(semantics.get("native_sampling_rate_hz_publication", -1)), 500.0, "published sampling rate")
    _require_equal(semantics.get("author_implementation_commit_sha1"), "9a345a37aab47ac6780ce0d4b5798cc15291c75b", "author format-source commit")

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    calculated = evidence_fingerprint(record)
    if stored != calculated:
        raise BenchmarkIntegrityError("Hollywood2 evidence self-fingerprint is invalid.")
    if stored != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError("Hollywood2 immutable authoritative v1 fingerprint drifted.")
    return record


def validate_hollywood2_gin_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Bind a freshly generated canonical GIN probe to the frozen evidence."""

    evidence = validate_hollywood2_authoritative_evidence(evidence_or_path)
    probe, _ = _load_record(probe_or_path)
    _require_equal(probe.get("record_type"), "hollywood2-gin-live-probe-v2", "live probe type")
    _require_equal(probe.get("status"), "verified_authoritative_source_probe", "live probe status")
    stored_probe = str(probe.get("probe_fingerprint_sha256", ""))
    if stored_probe != _probe_fingerprint(probe):
        raise BenchmarkIntegrityError("Hollywood2 live probe self-fingerprint is invalid.")
    if stored_probe != EXPECTED_PROBE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError("Hollywood2 live probe drifted from frozen authoritative v1.")

    _require_equal(probe.get("repository"), UPSTREAM_REPOSITORY, "live repository")
    remote = probe.get("remote")
    head = probe.get("head")
    if not isinstance(remote, Mapping) or not isinstance(head, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 live upstream identity is missing.")
    _require_equal(remote.get("default_ref"), "refs/heads/master", "live default ref")
    _require_equal(remote.get("head_sha"), UPSTREAM_COMMIT, "live HEAD")
    _require_equal(head.get("commit_sha1"), UPSTREAM_COMMIT, "live commit")
    if probe.get("license_files") != []:
        raise BenchmarkIntegrityError("Hollywood2 live probe unexpectedly resolved a license file.")

    ground = probe.get("ground_truth")
    if not isinstance(ground, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 live ground-truth audit is missing.")
    _require_equal(int(ground.get("file_count", -1)), 697, "live ground-truth file count")
    _require_equal(int(ground.get("total_bytes", -1)), 137328178, "live ground-truth byte count")
    _require_equal(int(ground.get("total_rows", -1)), 3871580, "live sample count")
    _require_equal(ground.get("splits"), {"test": 642, "train": 55}, "live split counts")
    _require_equal(int(ground.get("clip_count", -1)), 56, "live clip count")
    _require_equal(tuple(ground.get("file_subject_tokens", [])), _EXPECTED_TOKENS, "live tokens")
    signatures = ground.get("schema_signatures")
    _require_equal(
        signatures,
        {"31a6db306fded47592ad4c1647da8df3413df970a2b8abcba91e23d6261881c0": 697},
        "live schema signatures",
    )
    _require_equal(
        ground.get("global_label_counts", {}).get("handlabeller_final"),
        _EXPECTED_FINAL_COUNTS,
        "live final-label counts",
    )
    comparison = ground.get("student_final_comparison")
    if not isinstance(comparison, Mapping):
        raise BenchmarkIntegrityError("Hollywood2 live student/final comparison is missing.")
    _require_equal(int(comparison.get("changed_sample_count", -1)), 291315, "live changed samples")
    _require_equal(comparison.get("confusion"), _EXPECTED_CONFUSION, "live confusion")
    entries = ground.get("source_identity_ledger")
    if _ledger_fingerprint(entries) != EXPECTED_LEDGER_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError("Hollywood2 live 697-file source ledger drifted.")
    return evidence


def load_hollywood2_authoritative_evidence(
    path: str | Path,
) -> Hollywood2AuthoritativeEvidence:
    """Load and validate the evidence, returning a compact typed identity."""

    record, record_path = _load_record(path)
    record = validate_hollywood2_authoritative_evidence(record)
    coverage = record["coverage"]
    sensitivity = record["student_vs_expert_corrected_sensitivity"]
    return Hollywood2AuthoritativeEvidence(
        path=record_path,
        fingerprint_sha256=str(record["evidence_fingerprint_sha256"]),
        upstream_commit_sha1=str(record["upstream"]["commit_sha1"]),
        ground_truth_file_count=int(coverage["ground_truth_file_count"]),
        sample_count=int(coverage["ground_truth_total_samples"]),
        clip_count=int(coverage["clip_count"]),
        file_subject_token_count=int(coverage["file_subject_token_count"]),
        student_final_raw_agreement=float(sensitivity["raw_agreement_fraction"]),
    )
