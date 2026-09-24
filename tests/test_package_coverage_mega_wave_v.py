from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import gazeforge.gaze_in_wild_historical_tree_recovery as history
import gazeforge.hollywood2_explicit_crosswalk_intake as crosswalk
from gazeforge.exceptions import BenchmarkIntegrityError

HISTORY_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-historical-tree-recovery-evidence-v1.json"
)


# ============================================================
# HOLLYWOOD2 FIXTURES
# ============================================================


def _entries():
    groups = ["active"] * 12 + ["free_viewing"] * 4

    return [
        {
            "gin_token": token,
            "original_subject_id": f"S{index:02d}",
            "task_group": groups[index - 1],
        }
        for index, token in enumerate(
            crosswalk.GIN_TOKENS,
            start=1,
        )
    ]


def _write_crosswalk(
    tmp_path,
    *,
    entries=None,
):
    if entries is None:
        entries = _entries()

    source = tmp_path / "source.txt"
    source.write_bytes(b"explicit crosswalk source")

    manifest = {
        "record_type": (crosswalk.SOURCE_RECORD_TYPE),
        "source_reference": ("synthetic-test"),
        "source_authority_claim": ("author_statement"),
        "source_file_sha256": (hashlib.sha256(source.read_bytes()).hexdigest()),
        ("obtained_via_authorized_channel_affirmed"): True,
        "mapping_entries": entries,
    }

    manifest_path = tmp_path / "manifest.json"

    manifest_path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    return source, manifest_path


def _candidate(
    tmp_path,
):
    source, manifest = _write_crosswalk(tmp_path)

    record = crosswalk.inspect_explicit_crosswalk_candidate(
        source,
        manifest,
    )

    return source, manifest, record


def _refingerprint_candidate(
    record,
):
    record["candidate_fingerprint_sha256"] = crosswalk.candidate_fingerprint(record)


def _review_record(
    candidate,
):
    value = {
        "record_type": (crosswalk.REVIEW_RECORD_TYPE),
        "decision": "approved",
        ("candidate_fingerprint_sha256"): candidate["candidate_fingerprint_sha256"],
        "reviewer": "Reviewer",
        "reviewed_at": ("2026-09-24T12:00:00+03:00"),
        "source_authority_evidence": ("reviewed"),
        "mapping_explicitness_evidence": ("reviewed"),
        "mapping_transcription_evidence": ("reviewed"),
        "task_group_semantics_evidence": ("reviewed"),
        "source_version_scope_evidence": ("reviewed"),
        "source_authority_verified": True,
        ("mapping_explicit_in_source_verified"): True,
        "mapping_transcription_verified": True,
        "task_group_semantics_verified": True,
        "source_version_scope_verified": True,
        "rights_scope_promoted": False,
        "empirical_validation_created": False,
    }

    value["review_fingerprint_sha256"] = crosswalk.review_fingerprint(value)

    return value


def _write_review(
    tmp_path,
    value,
):
    path = tmp_path / "review.json"

    path.write_text(
        json.dumps(value),
        encoding="utf-8",
    )

    return path


# ============================================================
# CROSSWALK LOW-LEVEL HELPERS
# ============================================================


def test_crosswalk_canonical_bytes():
    assert crosswalk._canonical_bytes(
        {
            "b": 2,
            "a": 1,
        }
    ) == crosswalk._canonical_bytes(
        {
            "a": 1,
            "b": 2,
        }
    )


def test_crosswalk_sha_bytes():
    assert crosswalk._sha256_bytes(b"abc") == hashlib.sha256(b"abc").hexdigest()


@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "empty",
        "large",
    ],
)
def test_crosswalk_read_bounded(
    tmp_path,
    kind,
):
    path = tmp_path / "x"

    if kind == "empty":
        path.write_bytes(b"")
    elif kind == "large":
        path.write_bytes(b"ab")

    with pytest.raises(
        BenchmarkIntegrityError,
        match=("not a regular file" if kind == "missing" else "outside the allowed bound"),
    ):
        crosswalk._read_bounded(
            path,
            max_bytes=1,
            label="fixture",
        )


def test_crosswalk_read_bounded_valid(
    tmp_path,
):
    path = tmp_path / "x"

    path.write_bytes(b"a")

    assert (
        crosswalk._read_bounded(
            path,
            max_bytes=1,
            label="fixture",
        )
        == b"a"
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            b"{",
            "valid UTF-8 JSON",
        ),
        (
            b"\xff",
            "valid UTF-8 JSON",
        ),
        (
            b"[]",
            "one JSON object",
        ),
    ],
)
def test_crosswalk_json_loader_rejects(
    payload,
    message,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        crosswalk._load_json_bytes(
            payload,
            label="fixture",
        )


def test_crosswalk_json_loader_valid():
    assert crosswalk._load_json_bytes(
        b'{"x": 1}',
        label="fixture",
    ) == {"x": 1}


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "unknown",
        "TODO",
        "__unresolved__",
    ],
)
def test_crosswalk_resolved_text_rejects(
    value,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires resolved",
    ):
        crosswalk._resolved_text(
            value,
            label="fixture",
        )


def test_crosswalk_resolved_text_too_long():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="text-size guardrail",
    ):
        crosswalk._resolved_text(
            "x" * (crosswalk.MAX_TEXT_FIELD_LENGTH + 1),
            label="fixture",
        )


def test_crosswalk_resolved_text_valid():
    assert (
        crosswalk._resolved_text(
            " value ",
            label="fixture",
        )
        == "value"
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "a" * 63,
        "g" * 64,
    ],
)
def test_crosswalk_sha_invalid(
    value,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="lowercase SHA-256",
    ):
        crosswalk._sha256(
            value,
            label="fixture",
        )


def test_crosswalk_sha_normalizes():
    assert (
        crosswalk._sha256(
            "A" * 64,
            label="fixture",
        )
        == "a" * 64
    )


# ============================================================
# CROSSWALK MANIFEST CONTRACT
# ============================================================


def _manifest(
    raw=b"source",
):
    return {
        "record_type": (crosswalk.SOURCE_RECORD_TYPE),
        "source_reference": "source",
        "source_authority_claim": ("author_statement"),
        "source_file_sha256": (hashlib.sha256(raw).hexdigest()),
        ("obtained_via_authorized_channel_affirmed"): True,
        "mapping_entries": _entries(),
    }


def test_crosswalk_manifest_record_type():
    raw = b"source"
    value = _manifest(raw)

    value["record_type"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record type drifted",
    ):
        crosswalk._validate_manifest(
            value,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_crosswalk_manifest_source_reference():
    raw = b"source"
    value = _manifest(raw)

    value["source_reference"] = "review_required"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires resolved",
    ):
        crosswalk._validate_manifest(
            value,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_crosswalk_manifest_authority():
    raw = b"source"
    value = _manifest(raw)

    value["source_authority_claim"] = "third-party"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="unsupported",
    ):
        crosswalk._validate_manifest(
            value,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_crosswalk_manifest_sha_mismatch():
    raw = b"source"
    value = _manifest(raw)

    value["source_file_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="declared SHA-256",
    ):
        crosswalk._validate_manifest(
            value,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_crosswalk_manifest_authorized_channel():
    raw = b"source"
    value = _manifest(raw)

    value["obtained_via_authorized_channel_affirmed"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="authorized-channel",
    ):
        crosswalk._validate_manifest(
            value,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


@pytest.mark.parametrize(
    "entries",
    [
        None,
        [],
        {},
    ],
)
def test_crosswalk_manifest_entries_required(
    entries,
):
    raw = b"source"
    value = _manifest(raw)

    value["mapping_entries"] = entries

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires mapping_entries",
    ):
        crosswalk._validate_manifest(
            value,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_crosswalk_manifest_too_many():
    raw = b"source"
    value = _manifest(raw)

    value["mapping_entries"].append(copy.deepcopy(value["mapping_entries"][0]))

    with pytest.raises(
        BenchmarkIntegrityError,
        match="too many GIN-token",
    ):
        crosswalk._validate_manifest(
            value,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_crosswalk_manifest_nonobject_entry():
    raw = b"source"
    value = _manifest(raw)

    value["mapping_entries"][0] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be JSON objects",
    ):
        crosswalk._validate_manifest(
            value,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_crosswalk_manifest_unknown_token():
    raw = b"source"
    value = _manifest(raw)

    value["mapping_entries"][0]["gin_token"] = "BAD"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="unknown GIN token",
    ):
        crosswalk._validate_manifest(
            value,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_crosswalk_manifest_duplicate_token():
    raw = b"source"
    value = _manifest(raw)

    value["mapping_entries"][-1]["gin_token"] = value["mapping_entries"][0]["gin_token"]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="duplicates GIN token",
    ):
        crosswalk._validate_manifest(
            value,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


@pytest.mark.parametrize(
    "field",
    [
        "original_subject_id",
        "task_group",
    ],
)
def test_crosswalk_manifest_unresolved_mapping(
    field,
):
    raw = b"source"
    value = _manifest(raw)

    value["mapping_entries"][0][field] = "unknown"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires resolved",
    ):
        crosswalk._validate_manifest(
            value,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_crosswalk_manifest_sorted_result():
    raw = b"source"
    value = _manifest(raw)

    value["mapping_entries"] = list(reversed(value["mapping_entries"]))

    observed = crosswalk._validate_manifest(
        value,
        source_sha256=(hashlib.sha256(raw).hexdigest()),
    )

    assert [item["gin_token"] for item in observed] == sorted(crosswalk.GIN_TOKENS)


# ============================================================
# CROSSWALK CANDIDATE VALIDATOR
# ============================================================


@pytest.mark.parametrize(
    (
        "field",
        "value",
        "message",
    ),
    [
        (
            "record_type",
            "bad",
            "record type drifted",
        ),
        (
            "status",
            "bad",
            "status drifted",
        ),
        (
            ("crosswalk_exhaustion_evidence_fingerprint_sha256"),
            "0" * 64,
            "binding drifted",
        ),
    ],
)
def test_crosswalk_candidate_identity(
    tmp_path,
    field,
    value,
    message,
):
    _, _, record = _candidate(tmp_path)

    record[field] = value

    _refingerprint_candidate(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        crosswalk.validate_candidate_record(record)


def test_crosswalk_candidate_fingerprint(tmp_path):
    _, _, record = _candidate(tmp_path)

    record["candidate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint drifted",
    ):
        crosswalk.validate_candidate_record(record)


@pytest.mark.parametrize(
    "section",
    [
        "mapping_summary",
        "review_boundary",
        "scientific_boundary",
    ],
)
def test_crosswalk_candidate_sections(
    tmp_path,
    section,
):
    _, _, record = _candidate(tmp_path)

    record[section] = None

    _refingerprint_candidate(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sections are missing",
    ):
        crosswalk.validate_candidate_record(record)


@pytest.mark.parametrize(
    "tokens",
    [
        ["BAD"],
        [
            crosswalk.GIN_TOKENS[0],
            crosswalk.GIN_TOKENS[0],
        ],
    ],
)
def test_crosswalk_candidate_tokens(
    tmp_path,
    tokens,
):
    _, _, record = _candidate(tmp_path)

    record["mapping_summary"]["gin_tokens_present"] = tokens

    _refingerprint_candidate(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="token coverage is invalid",
    ):
        crosswalk.validate_candidate_record(record)


@pytest.mark.parametrize(
    "field",
    [
        ("raw_subject_ids_copied_to_candidate_record"),
        ("raw_task_group_labels_copied_to_candidate_record"),
    ],
)
def test_crosswalk_candidate_mapping_leaks(
    tmp_path,
    field,
):
    _, _, record = _candidate(tmp_path)

    record["mapping_summary"][field] = True

    _refingerprint_candidate(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="leaked",
    ):
        crosswalk.validate_candidate_record(record)


@pytest.mark.parametrize(
    "field",
    [
        "source_authority_verified",
        ("mapping_explicit_in_source_verified"),
        "mapping_transcription_verified",
        "task_group_semantics_verified",
        "source_version_scope_verified",
        ("gin_token_to_original_subject_id_verified"),
        ("gin_token_to_task_group_verified"),
        ("participant_identity_mapping_verified"),
    ],
)
def test_crosswalk_candidate_review_promotions(
    tmp_path,
    field,
):
    _, _, record = _candidate(tmp_path)

    record["review_boundary"][field] = True

    _refingerprint_candidate(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        crosswalk.validate_candidate_record(record)


def test_crosswalk_candidate_manual_gate(
    tmp_path,
):
    _, _, record = _candidate(tmp_path)

    record["review_boundary"]["manual_review_required"] = False

    _refingerprint_candidate(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="manual-review gate",
    ):
        crosswalk.validate_candidate_record(record)


@pytest.mark.parametrize(
    "field",
    [
        ("participant_disjoint_model_validation_created"),
        ("cross_dataset_validation_created"),
        ("new_empirical_performance_claim_created"),
        "rights_scope_promoted",
        "raw_gaze_inspected",
        "raw_gaze_redistributed",
    ],
)
def test_crosswalk_candidate_scientific_promotions(
    tmp_path,
    field,
):
    _, _, record = _candidate(tmp_path)

    record["scientific_boundary"][field] = True

    _refingerprint_candidate(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        crosswalk.validate_candidate_record(record)


# ============================================================
# CROSSWALK REVIEW HELPERS
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        "bad",
        "2026-09-24",
        "2026-09-24T12:00:00",
    ],
)
def test_crosswalk_review_timestamp_rejects(
    value,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="ISO-8601|timezone offset",
    ):
        crosswalk._validate_review_timestamp(value)


@pytest.mark.parametrize(
    "value",
    [
        "2026-09-24T12:00:00Z",
        "2026-09-24T12:00:00+03:00",
    ],
)
def test_crosswalk_review_timestamp_valid(
    value,
):
    assert crosswalk._validate_review_timestamp(value) == value


def test_crosswalk_load_review_missing(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="not a regular file",
    ):
        crosswalk._load_review(tmp_path / "missing.json")


def test_crosswalk_load_review_valid(
    tmp_path,
):
    path = tmp_path / "review.json"

    path.write_text(
        '{"x": 1}',
        encoding="utf-8",
    )

    assert crosswalk._load_review(path) == {"x": 1}


def test_crosswalk_review_wrong_record_type(
    tmp_path,
):
    source, manifest, candidate = _candidate(tmp_path)

    value = _review_record(candidate)

    value["record_type"] = "bad"

    value["review_fingerprint_sha256"] = crosswalk.review_fingerprint(value)

    review_path = _write_review(
        tmp_path,
        value,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record type drifted",
    ):
        crosswalk.require_reviewed_explicit_crosswalk(
            source,
            manifest,
            candidate,
            review_path,
        )


def test_crosswalk_review_unresolved_reviewer(
    tmp_path,
):
    source, manifest, candidate = _candidate(tmp_path)

    value = _review_record(candidate)

    value["reviewer"] = "unknown"

    value["review_fingerprint_sha256"] = crosswalk.review_fingerprint(value)

    review_path = _write_review(
        tmp_path,
        value,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires resolved reviewer",
    ):
        crosswalk.require_reviewed_explicit_crosswalk(
            source,
            manifest,
            candidate,
            review_path,
        )


@pytest.mark.parametrize(
    "field",
    [
        "source_authority_evidence",
        "mapping_explicitness_evidence",
        "mapping_transcription_evidence",
        "task_group_semantics_evidence",
        "source_version_scope_evidence",
    ],
)
def test_crosswalk_review_evidence_required(
    tmp_path,
    field,
):
    source, manifest, candidate = _candidate(tmp_path)

    value = _review_record(candidate)

    value[field] = "unknown"

    value["review_fingerprint_sha256"] = crosswalk.review_fingerprint(value)

    review_path = _write_review(
        tmp_path,
        value,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires resolved",
    ):
        crosswalk.require_reviewed_explicit_crosswalk(
            source,
            manifest,
            candidate,
            review_path,
        )


@pytest.mark.parametrize(
    "field",
    [
        "source_authority_verified",
        ("mapping_explicit_in_source_verified"),
        "mapping_transcription_verified",
        "task_group_semantics_verified",
        "source_version_scope_verified",
    ],
)
def test_crosswalk_review_all_gates(
    tmp_path,
    field,
):
    source, manifest, candidate = _candidate(tmp_path)

    value = _review_record(candidate)

    value[field] = False

    value["review_fingerprint_sha256"] = crosswalk.review_fingerprint(value)

    review_path = _write_review(
        tmp_path,
        value,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=field,
    ):
        crosswalk.require_reviewed_explicit_crosswalk(
            source,
            manifest,
            candidate,
            review_path,
        )


def test_crosswalk_review_success(
    tmp_path,
):
    source, manifest, candidate = _candidate(tmp_path)

    review_path = _write_review(
        tmp_path,
        _review_record(candidate),
    )

    result = crosswalk.require_reviewed_explicit_crosswalk(
        source,
        manifest,
        candidate,
        review_path,
    )

    assert len(result.mapping) == len(crosswalk.GIN_TOKENS)

    assert result.certificate["status"] == crosswalk.CERTIFICATE_STATUS


# ============================================================
# GIW HISTORICAL RECOVERY FIXTURE
# ============================================================


def _history():
    return json.loads(HISTORY_EVIDENCE.read_text(encoding="utf-8"))


def _history_refingerprint(
    record,
):
    record["evidence_fingerprint_sha256"] = history.evidence_fingerprint(record)


# ============================================================
# HISTORY HELPERS / LOADER
# ============================================================


def test_history_canonical_bytes():
    assert history._canonical_bytes(
        {
            "b": 2,
            "a": 1,
        }
    ) == history._canonical_bytes(
        {
            "a": 1,
            "b": 2,
        }
    )


def test_history_fingerprint_ignores_self():
    record = {
        "x": 1,
        "evidence_fingerprint_sha256": ("a" * 64),
    }

    first = history.evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = "b" * 64

    assert history.evidence_fingerprint(record) == first


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            b"{",
            "Could not load",
        ),
        (
            b"\xff",
            "Could not load",
        ),
        (
            b"[]",
            "Evidence root must be a JSON object",
        ),
    ],
)
def test_history_loader_rejects(
    tmp_path,
    payload,
    message,
):
    path = tmp_path / "evidence.json"

    path.write_bytes(payload)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match=message,
    ):
        history.load_evidence(path)


def test_history_loader_missing(
    tmp_path,
):
    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="Could not load",
    ):
        history.load_evidence(tmp_path / "missing.json")


def test_history_mapping_helper():
    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="fixture must be an object",
    ):
        history._mapping(
            {"fixture": []},
            "fixture",
        )


def test_history_require_true():
    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="flag must be true",
    ):
        history._require_true(
            {"flag": False},
            "flag",
        )


def test_history_require_false():
    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="flag must be false",
    ):
        history._require_false(
            {"flag": True},
            "flag",
        )


def test_history_reject_raw_path_nested_dict():
    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="Raw Path2Data disclosure",
    ):
        history._reject_raw_path_key({"x": {"Path2Data": "secret"}})


def test_history_reject_raw_path_nested_list():
    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="Raw Path2Data disclosure",
    ):
        history._reject_raw_path_key([{"raw_path2data": "secret"}])


def test_history_reject_raw_path_scalar_noop():
    history._reject_raw_path_key("safe")


# ============================================================
# HISTORY TOP-LEVEL CONTRACT
# ============================================================


def test_history_record_type():
    record = _history()

    record["record_type"] = "bad"

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="record type",
    ):
        history.validate_evidence(record)


@pytest.mark.parametrize(
    (
        "field",
        "value",
        "message",
    ),
    [
        (
            "repository",
            "other",
            "repository identity",
        ),
        (
            "pinned_commit_sha1",
            "0" * 40,
            "commit drifted",
        ),
        (
            "reachable_commit_count",
            55,
            "commit count",
        ),
    ],
)
def test_history_scope(
    field,
    value,
    message,
):
    record = _history()

    record["scope"][field] = value

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match=message,
    ):
        history.validate_evidence(record)


def test_history_scope_missing():
    record = _history()

    record["scope"] = None

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="scope must be an object",
    ):
        history.validate_evidence(record)


def test_history_parent_binding():
    record = _history()

    record["parent_evidence"]["repository_history_fingerprint_sha256"] = "0" * 64

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="Parent evidence binding",
    ):
        history.validate_evidence(record)


# ============================================================
# HISTORY REACHABLE TREE
# ============================================================


def test_history_reachable_missing():
    record = _history()

    record["reachable_history"] = None

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="reachable_history must be an object",
    ):
        history.validate_evidence(record)


def test_history_reachable_all_checked():
    record = _history()

    record["reachable_history"]["all_reachable_commit_trees_checked"] = False

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="must be true",
    ):
        history.validate_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        ("tracked_mat_path_count_across_reachable_trees"),
        ("exact_distribution_filename_path_count"),
        ("alternate_labeller_mat_path_count"),
        "tag_ref_count",
        "release_count",
    ],
)
def test_history_zero_counts(
    field,
):
    record = _history()

    record["reachable_history"][field] = 1

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="Unexpected historical count",
    ):
        history.validate_evidence(record)


def test_history_archive_count():
    record = _history()

    record["reachable_history"]["archive_path_count"] = 2

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="archive count",
    ):
        history.validate_evidence(record)


def test_history_only_branch():
    record = _history()

    record["reachable_history"]["only_branch"] = "main"

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="branch inventory",
    ):
        history.validate_evidence(record)


# ============================================================
# HISTORY ARCHIVE CONTRACT
# ============================================================


@pytest.mark.parametrize(
    (
        "field",
        "value",
        "message",
    ),
    [
        (
            "path",
            "other.zip",
            "archive path",
        ),
        (
            "git_blob_sha1",
            "0" * 40,
            "Git blob",
        ),
        (
            "sha256",
            "0" * 64,
            "SHA-256",
        ),
        (
            "member_count",
            11,
            "member count",
        ),
    ],
)
def test_history_archive_identity(
    field,
    value,
    message,
):
    record = _history()

    record["preprocessing_archive"][field] = value

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match=message,
    ):
        history.validate_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "labeldata_member_present",
        ("exact_distribution_filename_member_present"),
    ],
)
def test_history_archive_false_flags(
    field,
):
    record = _history()

    record["preprocessing_archive"][field] = True

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="must be false",
    ):
        history.validate_evidence(record)


# ============================================================
# HISTORY EMBEDDED PROCESSDATA CONTRACT
# ============================================================


@pytest.mark.parametrize(
    (
        "field",
        "value",
        "message",
    ),
    [
        (
            "member_path",
            "other.mat",
            "ProcessData path",
        ),
        (
            "member_sha256",
            "0" * 64,
            "SHA-256",
        ),
        (
            "member_size_bytes",
            1,
            "size drifted",
        ),
    ],
)
def test_history_embedded_identity(
    field,
    value,
    message,
):
    record = _history()

    record["embedded_processdata"][field] = value

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match=message,
    ):
        history.validate_evidence(record)


def test_history_embedded_identity_mapping():
    record = _history()

    record["embedded_processdata"]["identity"]["DepthPresent"] = 1

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="identity drifted",
    ):
        history.validate_evidence(record)


def test_history_embedded_first_party_true():
    record = _history()

    record["embedded_processdata"]["first_party_data_bearing_processdata_object_verified"] = False

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="must be true",
    ):
        history.validate_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        ("published_distribution_filename_match"),
        ("exact_distribution_file_equivalence_verified"),
        ("separate_labeldata_recovered"),
        ("independent_labeller_streams_recovered"),
    ],
)
def test_history_embedded_false_flags(
    field,
):
    record = _history()

    record["embedded_processdata"][field] = True

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="must be false",
    ):
        history.validate_evidence(record)


# ============================================================
# HISTORY SCIENTIFIC BOUNDARY
# ============================================================


@pytest.mark.parametrize(
    "field",
    list(history.FALSE_BOUNDARIES),
)
def test_history_all_false_boundaries(
    field,
):
    record = _history()

    record["scientific_boundary"][field] = True

    _history_refingerprint(record)

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="must be false",
    ):
        history.validate_evidence(record)


def test_history_fingerprint_mismatch():
    record = _history()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        history.HistoricalTreeRecoveryEvidenceError,
        match="fingerprint mismatch",
    ):
        history.validate_evidence(record)


def test_history_valid():
    record = _history()

    assert history.validate_evidence(record) == record
