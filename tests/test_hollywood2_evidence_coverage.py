from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import gazeforge.hollywood2_evidence as h2
from gazeforge.exceptions import BenchmarkIntegrityError

EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-authoritative-ground-truth-evidence-v1.json"
)


def _record() -> dict[str, Any]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict[str, Any]) -> dict[str, Any]:
    record["evidence_fingerprint_sha256"] = h2.evidence_fingerprint(record)
    return record


def _resign_probe(
    probe: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fingerprint = h2._probe_fingerprint(probe)
    probe["probe_fingerprint_sha256"] = fingerprint

    monkeypatch.setattr(
        h2,
        "EXPECTED_PROBE_FINGERPRINT_SHA256",
        fingerprint,
    )


def _synthetic_live_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    ledger = [
        {
            "path": "ground_truth/test/example.arff",
            "sha256": "a" * 64,
        }
    ]

    ledger_fp = h2._ledger_fingerprint(ledger)

    monkeypatch.setattr(
        h2,
        "EXPECTED_LEDGER_FINGERPRINT_SHA256",
        ledger_fp,
    )

    probe: dict[str, Any] = {
        "record_type": "hollywood2-gin-live-probe-v2",
        "status": "verified_authoritative_source_probe",
        "repository": h2.UPSTREAM_REPOSITORY,
        "remote": {
            "default_ref": "refs/heads/master",
            "head_sha": h2.UPSTREAM_COMMIT,
        },
        "head": {
            "commit_sha1": h2.UPSTREAM_COMMIT,
        },
        "license_files": [],
        "ground_truth": {
            "file_count": 697,
            "total_bytes": 137328178,
            "total_rows": 3871580,
            "splits": {
                "test": 642,
                "train": 55,
            },
            "clip_count": 56,
            "file_subject_tokens": list(h2._EXPECTED_TOKENS),
            "schema_signatures": {
                ("31a6db306fded47592ad4c1647da8df3413df970a2b8abcba91e23d6261881c0"): 697
            },
            "global_label_counts": {"handlabeller_final": dict(h2._EXPECTED_FINAL_COUNTS)},
            "student_final_comparison": {
                "changed_sample_count": 291315,
                "confusion": dict(h2._EXPECTED_CONFUSION),
            },
            "source_identity_ledger": ledger,
        },
    }

    _resign_probe(probe, monkeypatch)

    return probe


def _bypass_authoritative_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        h2,
        "validate_hollywood2_authoritative_evidence",
        lambda value: _record(),
    )


def test_load_record_mapping_round_trip() -> None:
    source = {
        "x": 1,
    }

    loaded, path = h2._load_record(source)

    assert loaded == source
    assert loaded is not source
    assert path is None


def test_load_record_rejects_missing_bad_and_nonobject(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        h2._load_record(tmp_path / "missing.json")

    bad = tmp_path / "bad.json"
    bad.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        h2._load_record(bad)

    array = tmp_path / "array.json"
    array.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        h2._load_record(array)


def test_small_fail_closed_helpers() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="frozen authoritative",
    ):
        h2._require_equal(
            1,
            2,
            "test",
        )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        h2._require_true(
            False,
            "test",
        )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        h2._require_false(
            True,
            "test",
        )


@pytest.mark.parametrize(
    ("section", "match"),
    [
        (
            "coverage",
            "coverage is missing",
        ),
        (
            "schema",
            "schema is missing",
        ),
        (
            "final_labels",
            "final-label evidence is missing",
        ),
        (
            "student_vs_expert_corrected_sensitivity",
            "annotation-sensitivity evidence is missing",
        ),
        (
            "rights",
            "rights boundary is missing",
        ),
        (
            "scientific_boundary",
            "scientific boundary is missing",
        ),
        (
            "upstream",
            "upstream identity is missing",
        ),
        (
            "execution",
            "probe execution identity is missing",
        ),
        (
            "source_ledger",
            "source-ledger identity is missing",
        ),
        (
            "format_semantics",
            "format semantics are missing",
        ),
    ],
)
def test_authoritative_record_requires_mapping_sections(
    section: str,
    match: str,
) -> None:
    record = _record()
    record[section] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


def test_authoritative_readme_mapping_required() -> None:
    record = _record()
    record["upstream"]["readme"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="README identity is missing",
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


def test_final_label_fraction_mapping_required() -> None:
    record = _record()
    record["final_labels"]["fractions"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fractions are missing",
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


def test_publication_crosscheck_mapping_required() -> None:
    record = _record()
    record["final_labels"]["publication_crosscheck"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="publication cross-check is missing",
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


@pytest.mark.parametrize(
    "label",
    [
        "FIX",
        "NOISE",
        "SACCADE",
        "SP",
    ],
)
def test_final_label_fraction_drift_detected(
    label: str,
) -> None:
    record = _record()

    record["final_labels"]["fractions"][label] += 0.01

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=f"fraction {label} drifted",
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


def test_publication_crosscheck_false_detected() -> None:
    record = _record()

    record["final_labels"]["publication_crosscheck"]["counts_reproduce_reported_rounding"] = False

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="publication cross-check",
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


def test_sensitivity_raw_agreement_drift_detected() -> None:
    record = _record()

    record["student_vs_expert_corrected_sensitivity"]["raw_agreement_fraction"] = 0.0

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="raw agreement drifted",
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


def test_sensitivity_interpretation_boundary_detected() -> None:
    record = _record()

    record["student_vs_expert_corrected_sensitivity"]["interpretation"] = "independent reliability"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="distinct from independent reliability",
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


@pytest.mark.parametrize(
    ("key", "value", "match"),
    [
        (
            "repository_license_file_recovered",
            True,
            "repository license recovery",
        ),
        (
            "dataset_specific_license_verified",
            True,
            "dataset-license verification",
        ),
        (
            "article_cc_by_is_dataset_license",
            True,
            "article license as dataset license",
        ),
        (
            "source_bytes_redistributed_by_gazeforge",
            True,
            "source-byte redistribution",
        ),
        (
            "analysis_use_terms_status",
            "resolved",
            "analysis-use status",
        ),
        (
            "raw_data_redistribution_terms_status",
            "resolved",
            "redistribution status",
        ),
    ],
)
def test_rights_boundaries_fail_closed(
    key: str,
    value: Any,
    match: str,
) -> None:
    record = _record()

    record["rights"][key] = value

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


@pytest.mark.parametrize(
    ("key", "match"),
    [
        (
            "authoritative_repository_revision_resolved",
            "repository revision resolution",
        ),
        (
            "authoritative_ground_truth_blobs_recovered",
            "ground-truth blob recovery",
        ),
        (
            "ground_truth_source_identity_ledger_created",
            "source ledger",
        ),
        (
            "trial_clip_identity_file_bound",
            "file-bound clip identity",
        ),
        (
            "file_subject_tokens_recovered",
            "file subject-token recovery",
        ),
        (
            "time_unit_verified",
            "time-unit verification",
        ),
        (
            "coordinate_unit_verified",
            "coordinate-unit verification",
        ),
        (
            "student_vs_expert_corrected_sensitivity_created",
            "annotation sensitivity",
        ),
    ],
)
def test_required_scientific_boundaries_cannot_drop(
    key: str,
    match: str,
) -> None:
    record = _record()

    record["scientific_boundary"][key] = False

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


@pytest.mark.parametrize(
    ("key", "value", "match"),
    [
        (
            "ground_truth_file_count",
            1,
            "file count",
        ),
        (
            "ground_truth_total_bytes",
            1,
            "byte count",
        ),
        (
            "ground_truth_total_samples",
            1,
            "sample count",
        ),
        (
            "splits",
            {
                "test": 0,
                "train": 0,
            },
            "split counts",
        ),
        (
            "clip_count",
            1,
            "clip count",
        ),
        (
            "file_subject_token_count",
            1,
            "file subject-token count",
        ),
        (
            "file_subject_tokens",
            [],
            "tokens",
        ),
    ],
)
def test_coverage_contract_fields(
    key: str,
    value: Any,
    match: str,
) -> None:
    record = _record()

    record["coverage"][key] = value

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


@pytest.mark.parametrize(
    ("key", "value", "match"),
    [
        (
            "relation",
            "wrong",
            "ARFF relation",
        ),
        (
            "attributes",
            [],
            "ARFF schema",
        ),
        (
            "schema_signature_sha256",
            "0" * 64,
            "schema fingerprint",
        ),
        (
            "schema_signature_file_count",
            1,
            "schema coverage",
        ),
    ],
)
def test_schema_contract_fields(
    key: str,
    value: Any,
    match: str,
) -> None:
    record = _record()

    record["schema"][key] = value

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


@pytest.mark.parametrize(
    ("key", "value", "match"),
    [
        (
            "repository",
            "wrong",
            "upstream repository",
        ),
        (
            "default_ref",
            "wrong",
            "upstream default ref",
        ),
        (
            "commit_sha1",
            "0" * 40,
            "upstream commit",
        ),
    ],
)
def test_upstream_contract_fields(
    key: str,
    value: Any,
    match: str,
) -> None:
    record = _record()

    record["upstream"][key] = value

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


@pytest.mark.parametrize(
    ("key", "value", "match"),
    [
        (
            "git_blob_sha1",
            "0" * 40,
            "README blob",
        ),
        (
            "sha256",
            "0" * 64,
            "README SHA-256",
        ),
    ],
)
def test_readme_contract_fields(
    key: str,
    value: Any,
    match: str,
) -> None:
    record = _record()

    record["upstream"]["readme"][key] = value

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


@pytest.mark.parametrize(
    ("key", "value", "match"),
    [
        (
            "time_unit",
            "milliseconds",
            "time unit",
        ),
        (
            "coordinate_unit",
            "normalized",
            "coordinate unit",
        ),
        (
            "native_sampling_rate_hz_publication",
            60.0,
            "published sampling rate",
        ),
        (
            "author_implementation_commit_sha1",
            "0" * 40,
            "author format-source commit",
        ),
    ],
)
def test_format_semantics_contract_fields(
    key: str,
    value: Any,
    match: str,
) -> None:
    record = _record()

    record["format_semantics"][key] = value

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


def test_self_fingerprint_invalid_branch() -> None:
    record = _record()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint is invalid",
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


def test_immutable_expected_fingerprint_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _record()

    monkeypatch.setattr(
        h2,
        "EXPECTED_EVIDENCE_FINGERPRINT_SHA256",
        "0" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="immutable authoritative v1 fingerprint drifted",
    ):
        h2.validate_hollywood2_authoritative_evidence(record)


def test_live_probe_success_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bypass_authoritative_validation(monkeypatch)

    probe = _synthetic_live_probe(monkeypatch)

    result = h2.validate_hollywood2_gin_probe(
        probe,
        _record(),
    )

    assert result["record_type"] == h2.RECORD_TYPE
    assert result["coverage"]["ground_truth_file_count"] == 697


def test_live_probe_self_fingerprint_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bypass_authoritative_validation(monkeypatch)

    probe = _synthetic_live_probe(monkeypatch)

    probe["status"] = "verified_authoritative_source_probe"

    probe["probe_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint is invalid",
    ):
        h2.validate_hollywood2_gin_probe(
            probe,
            _record(),
        )


def test_live_probe_expected_fingerprint_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bypass_authoritative_validation(monkeypatch)

    probe = _synthetic_live_probe(monkeypatch)

    monkeypatch.setattr(
        h2,
        "EXPECTED_PROBE_FINGERPRINT_SHA256",
        "0" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted from frozen authoritative",
    ):
        h2.validate_hollywood2_gin_probe(
            probe,
            _record(),
        )


@pytest.mark.parametrize(
    ("case", "match"),
    [
        (
            "remote",
            "live upstream identity is missing",
        ),
        (
            "head",
            "live upstream identity is missing",
        ),
        (
            "license",
            "unexpectedly resolved a license file",
        ),
        (
            "ground",
            "ground-truth audit is missing",
        ),
        (
            "comparison",
            "student/final comparison is missing",
        ),
        (
            "ledger",
            "697-file source ledger drifted",
        ),
    ],
)
def test_live_probe_structural_guards(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    match: str,
) -> None:
    _bypass_authoritative_validation(monkeypatch)

    probe = _synthetic_live_probe(monkeypatch)

    if case == "remote":
        probe["remote"] = None

    elif case == "head":
        probe["head"] = None

    elif case == "license":
        probe["license_files"] = [
            "LICENSE",
        ]

    elif case == "ground":
        probe["ground_truth"] = None

    elif case == "comparison":
        probe["ground_truth"]["student_final_comparison"] = None

    elif case == "ledger":
        probe["ground_truth"]["source_identity_ledger"] = [
            {
                "changed": True,
            }
        ]

    _resign_probe(
        probe,
        monkeypatch,
    )

    if case == "ledger":
        monkeypatch.setattr(
            h2,
            "EXPECTED_LEDGER_FINGERPRINT_SHA256",
            "0" * 64,
        )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        h2.validate_hollywood2_gin_probe(
            probe,
            _record(),
        )


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (
            ("record_type",),
            "wrong",
            "live probe type",
        ),
        (
            ("status",),
            "wrong",
            "live probe status",
        ),
        (
            ("repository",),
            "wrong",
            "live repository",
        ),
        (
            ("remote", "default_ref"),
            "wrong",
            "live default ref",
        ),
        (
            ("remote", "head_sha"),
            "0" * 40,
            "live HEAD",
        ),
        (
            ("head", "commit_sha1"),
            "0" * 40,
            "live commit",
        ),
        (
            ("ground_truth", "file_count"),
            1,
            "live ground-truth file count",
        ),
        (
            ("ground_truth", "total_bytes"),
            1,
            "live ground-truth byte count",
        ),
        (
            ("ground_truth", "total_rows"),
            1,
            "live sample count",
        ),
        (
            ("ground_truth", "splits"),
            {},
            "live split counts",
        ),
        (
            ("ground_truth", "clip_count"),
            1,
            "live clip count",
        ),
        (
            (
                "ground_truth",
                "file_subject_tokens",
            ),
            [],
            "live tokens",
        ),
        (
            (
                "ground_truth",
                "schema_signatures",
            ),
            {},
            "live schema signatures",
        ),
        (
            (
                "ground_truth",
                "global_label_counts",
                "handlabeller_final",
            ),
            {},
            "live final-label counts",
        ),
        (
            (
                "ground_truth",
                "student_final_comparison",
                "changed_sample_count",
            ),
            1,
            "live changed samples",
        ),
        (
            (
                "ground_truth",
                "student_final_comparison",
                "confusion",
            ),
            {},
            "live confusion",
        ),
    ],
)
def test_live_probe_value_contracts(
    monkeypatch: pytest.MonkeyPatch,
    path: tuple[str, ...],
    value: Any,
    match: str,
) -> None:
    _bypass_authoritative_validation(monkeypatch)

    probe = _synthetic_live_probe(monkeypatch)

    target: dict[str, Any] = probe

    for key in path[:-1]:
        target = target[key]

    target[path[-1]] = value

    _resign_probe(
        probe,
        monkeypatch,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        h2.validate_hollywood2_gin_probe(
            probe,
            _record(),
        )
