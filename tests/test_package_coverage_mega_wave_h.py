from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import gazeforge.gaze_in_wild_exact_copy_review as exact_copy
import gazeforge.gaze_in_wild_history_evidence as history
import gazeforge.gaze_in_wild_quarantine_exit as quarantine
from gazeforge.exceptions import BenchmarkIntegrityError

_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-repository-history-evidence-v1.json"
)


# ============================================================
# HISTORY HELPERS
# ============================================================


def _evidence():
    return json.loads(_EVIDENCE.read_text(encoding="utf-8"))


def _write(tmp_path, payload, name="record.json"):
    path = tmp_path / name
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    return path


def test_history_canonical_bytes_deterministic():
    assert history._canonical_bytes({"b": 2, "a": 1}) == history._canonical_bytes({"a": 1, "b": 2})


def test_history_evidence_fingerprint_ignores_stored():
    record = {
        "x": 1,
        "evidence_fingerprint_sha256": "bad",
    }

    first = history.evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = "other"

    assert history.evidence_fingerprint(record) == first


def test_history_probe_fingerprint_ignores_stored():
    record = {
        "x": 1,
        "probe_fingerprint_sha256": "bad",
    }

    first = history.probe_fingerprint(record)

    record["probe_fingerprint_sha256"] = "other"

    assert history.probe_fingerprint(record) == first


def test_history_load_mapping():
    original = {"x": 1}

    loaded, path = history._load(
        original,
        label="fixture",
    )

    assert loaded == original
    assert loaded is not original
    assert path is None


def test_history_load_missing_file(tmp_path):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        history._load(
            tmp_path / "missing.json",
            label="fixture",
        )


def test_history_load_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        history._load(
            path,
            label="fixture",
        )


def test_history_load_nonobject(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        history._load(
            path,
            label="fixture",
        )


def test_history_mapping_success():
    value = {"x": 1}

    assert (
        history._mapping(
            {"section": value},
            "section",
        )
        == value
    )


def test_history_mapping_missing():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        history._mapping(
            {},
            "section",
        )


def test_history_equal_success():
    history._equal(
        1,
        1,
        "fixture",
    )


def test_history_equal_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        history._equal(
            1,
            2,
            "fixture",
        )


@pytest.mark.parametrize(
    "value",
    [False, 0, 1, None, "true"],
)
def test_history_true_requires_literal_true(value):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        history._true(
            value,
            "fixture",
        )


def test_history_true_success():
    history._true(
        True,
        "fixture",
    )


@pytest.mark.parametrize(
    "value",
    [True, 0, 1, None, "false"],
)
def test_history_false_requires_literal_false(value):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        history._false(
            value,
            "fixture",
        )


def test_history_false_success():
    history._false(
        False,
        "fixture",
    )


def test_history_fingerprint_value_deterministic():
    assert history._fingerprint_value({"b": [2], "a": 1}) == history._fingerprint_value(
        {"a": 1, "b": [2]}
    )


# ============================================================
# IMMUTABLE HISTORY EVIDENCE VALIDATOR
# ============================================================


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("record_type",), "wrong", "record type"),
        (("status",), "wrong", "status"),
        (("checked_on",), "1900-01-01", "review date"),
        (("dataset",), "wrong", "dataset identity"),
        (("scope", "repository"), "wrong", "repository"),
        (("scope", "pinned_commit_sha1"), "0" * 40, "pinned commit"),
        (("scope", "pinned_root_tree_sha1"), "0" * 40, "pinned tree"),
        (("scope", "history_scope"), "wrong", "history scope"),
        (("execution", "workflow_run_id"), 1, "workflow run"),
        (("execution", "workflow_head_sha"), "0" * 40, "workflow head"),
        (("execution", "artifact_id"), 1, "artifact id"),
        (("execution", "artifact_digest_sha256"), "0" * 64, "artifact digest"),
        (
            ("execution", "live_probe_record_type"),
            "wrong",
            "probe record type",
        ),
        (
            ("execution", "live_probe_fingerprint_sha256"),
            "0" * 64,
            "probe fingerprint",
        ),
        (
            ("execution", "live_probe_file_sha256"),
            "0" * 64,
            "probe file fingerprint",
        ),
        (
            ("repository_history", "reachable_commit_count"),
            55,
            "commit count",
        ),
        (
            ("repository_history", "root_commit_sha1"),
            "0" * 40,
            "root commit",
        ),
        (
            ("repository_history", "head_commit_sha1"),
            "0" * 40,
            "head commit",
        ),
        (
            ("repository_history", "author_names"),
            ["other"],
            "authors",
        ),
        (
            (
                "repository_history",
                "commit_ledger_fingerprint_sha256",
            ),
            "0" * 64,
            "commit ledger",
        ),
        (
            (
                "key_path_history",
                "key_path_inventory_fingerprint_sha256",
            ),
            "0" * 64,
            "key-path",
        ),
        (
            ("readme_history", "unique_blob_count"),
            5,
            "README blob count",
        ),
        (
            (
                "readme_history",
                "revision_inventory_fingerprint_sha256",
            ),
            "0" * 64,
            "README revision",
        ),
        (
            ("readme_history", "revision_blob_sha1s"),
            [],
            "README blobs",
        ),
        (
            (
                "software_license_history",
                "license_file_first_seen_commit_sha1",
            ),
            "0" * 40,
            "license first-seen",
        ),
        (
            (
                "software_license_history",
                "license_file_blob_sha1",
            ),
            "0" * 40,
            "license blob",
        ),
        (
            ("software_license_history", "license_scope"),
            "wrong",
            "license scope",
        ),
        (
            ("repository_tree", "tracked_path_count"),
            1,
            "tracked path count",
        ),
        (
            (
                "repository_tree",
                "distributed_process_or_label_mat_path_count",
            ),
            1,
            "distributed dataset-like",
        ),
    ],
)
def test_history_field_drift_rejected(
    path,
    value,
    message,
):
    record = _evidence()

    target = record

    for key in path[:-1]:
        target = target[key]

    target[path[-1]] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


@pytest.mark.parametrize(
    "section",
    [
        "scope",
        "execution",
        "repository_history",
        "key_path_history",
        "readme_history",
        "software_license_history",
        "repository_tree",
        "scientific_boundary",
    ],
)
def test_history_required_mapping_sections(section):
    record = _evidence()
    record[section] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


@pytest.mark.parametrize(
    "path_name",
    [
        "README.md",
        "License.md",
        "DataExtraction/GetParticipantInfo.m",
        "DataExtraction/ReadData_function.m",
        "PlotLabels.m",
    ],
)
def test_history_key_path_presence_required(path_name):
    record = _evidence()

    record["key_path_history"][path_name]["present_at_pinned_head"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="presence",
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


@pytest.mark.parametrize(
    "path_name",
    [
        "README.md",
        "License.md",
        "DataExtraction/GetParticipantInfo.m",
        "DataExtraction/ReadData_function.m",
        "PlotLabels.m",
    ],
)
def test_history_key_path_first_seen_required(path_name):
    record = _evidence()

    record["key_path_history"][path_name]["first_seen_commit_sha1"] = "0" * 40

    with pytest.raises(
        BenchmarkIntegrityError,
        match="first-seen",
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


@pytest.mark.parametrize(
    "path_name",
    [
        "README.md",
        "License.md",
        "DataExtraction/GetParticipantInfo.m",
        "DataExtraction/ReadData_function.m",
        "PlotLabels.m",
    ],
)
def test_history_key_path_blob_required(path_name):
    record = _evidence()

    record["key_path_history"][path_name]["pinned_blob_sha1"] = "0" * 40

    with pytest.raises(
        BenchmarkIntegrityError,
        match="pinned blob",
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


@pytest.mark.parametrize(
    "key",
    [
        "pinned_distribution_url_present",
        "pinned_all_data_files_download_webpage_statement_present",
        "pinned_raw_data_over_14tb_statement_present",
        "pinned_raw_data_contact_authors_statement_present",
    ],
)
def test_history_readme_markers_required(key):
    record = _evidence()
    record["readme_history"][key] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


@pytest.mark.parametrize(
    "key",
    [
        "license_file_present_at_pinned_head",
        "license_file_identifies_mit",
    ],
)
def test_history_license_true_boundaries(key):
    record = _evidence()

    record["software_license_history"][key] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


def test_history_license_cannot_promote_dataset_files():
    record = _evidence()

    record["software_license_history"]["license_scope_promoted_to_external_dataset_files"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


def test_history_tree_cannot_be_exact_copy():
    record = _evidence()

    record["repository_tree"]["repository_is_exact_compressed_dataset_copy"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exact-copy",
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


@pytest.mark.parametrize(
    "key",
    [
        "complete_reachable_repository_history_audited",
        "repository_mit_license_verified_for_software",
    ],
)
def test_history_required_positive_boundaries(key):
    record = _evidence()
    record["scientific_boundary"][key] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


@pytest.mark.parametrize(
    "key",
    [
        "exact_external_dataset_copy_obtained",
        "external_dataset_file_rights_resolved",
        "external_dataset_file_license_verified",
        "software_mit_is_external_dataset_license",
        "published_distribution_url_is_current_direct_copy_verified",
        "participant_identity_mapping_from_history_verified",
        "complete_trial_to_task_mapping_from_history_verified",
        "human_human_agreement_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "frozen_evidence_performance_claim_created",
    ],
)
def test_history_scientific_claims_remain_false(key):
    record = _evidence()
    record["scientific_boundary"][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("claim_limits", [], "claim limits"),
        ("claim_limits", "bad", "claim limits"),
        ("next_required_actions", [], "next actions"),
        ("next_required_actions", "bad", "next actions"),
    ],
)
def test_history_retains_limits_and_actions(
    field,
    value,
    message,
):
    record = _evidence()
    record[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


def test_history_self_fingerprint_guard():
    record = _evidence()
    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint",
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


def test_history_immutable_fingerprint_guard():
    record = _evidence()

    # Extra metadata is ignored by the fixed semantic field checks,
    # but correctly changes the immutable whole-record identity.
    record["extra_unreviewed_field"] = "drift"

    record["evidence_fingerprint_sha256"] = history.evidence_fingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="immutable repository-history fingerprint drifted",
    ):
        history.validate_gaze_in_wild_repository_history_evidence(record)


def test_history_mapping_input_validates():
    record = _evidence()

    result = history.validate_gaze_in_wild_repository_history_evidence(record)

    assert result["record_type"] == history.RECORD_TYPE


def test_history_typed_loader_mapping_path_is_none():
    typed = history.load_gaze_in_wild_repository_history_evidence(_evidence())

    assert typed.path is None
    assert typed.commit_count == 56


def test_history_typed_loader_file_path():
    typed = history.load_gaze_in_wild_repository_history_evidence(_EVIDENCE)

    assert typed.path == _EVIDENCE
    assert typed.repository_mit_verified_for_software is True
    assert typed.exact_dataset_copy_obtained is False
    assert typed.participant_identity_mapping_verified is False


# ============================================================
# LIVE PROBE VALIDATION
# ============================================================


def _probe_fixture(monkeypatch):
    evidence = _evidence()

    probe = {
        "record_type": history.PROBE_RECORD_TYPE,
        "repository": history.REPOSITORY,
        "pinned_commit_sha1": history.PINNED_COMMIT,
        "pinned_root_tree_sha1": history.PINNED_TREE,
        "reachable_commit_count": 56,
        "root_commit_sha1": history.ROOT_COMMIT,
        "author_names": ["RSKothari", "rakshit"],
        "probe_fingerprint_sha256": (history.EXPECTED_PROBE_FINGERPRINT_SHA256),
        "commit_ledger": {"fixture": "ledger"},
        "key_path_history": {"fixture": "keys"},
        "readme_history": {
            "revisions": [
                {"blob_sha1": value} for value in evidence["readme_history"]["revision_blob_sha1s"]
            ],
        },
        "software_license_history": {
            key: evidence["software_license_history"][key]
            for key in (
                "license_file_present_at_pinned_head",
                "license_file_first_seen_commit_sha1",
                "license_file_blob_sha1",
                "license_file_identifies_mit",
                "license_scope_promoted_to_external_dataset_files",
            )
        },
        "repository_tree": copy.deepcopy(evidence["repository_tree"]),
        "scientific_boundary": {
            "official_first_author_repository_history_verified": True,
            "exact_external_dataset_copy_obtained": False,
            "external_dataset_file_rights_resolved": False,
            "software_mit_is_external_dataset_license": False,
            "published_distribution_url_is_current_direct_copy_verified": False,
            "participant_identity_mapping_from_history_verified": False,
            "complete_trial_to_task_mapping_from_history_verified": False,
            "human_human_agreement_created": False,
            "participant_disjoint_model_validation_created": False,
            "frozen_evidence_performance_claim_created": False,
        },
    }

    monkeypatch.setattr(
        history,
        "probe_fingerprint",
        lambda record: record["probe_fingerprint_sha256"],
    )

    real_fingerprint = history._fingerprint_value

    def fake_fingerprint(value):
        if value is probe["commit_ledger"]:
            return evidence["repository_history"]["commit_ledger_fingerprint_sha256"]

        if value is probe["key_path_history"]:
            return evidence["key_path_history"]["key_path_inventory_fingerprint_sha256"]

        if value is probe["readme_history"]["revisions"]:
            return evidence["readme_history"]["revision_inventory_fingerprint_sha256"]

        return real_fingerprint(value)

    monkeypatch.setattr(
        history,
        "_fingerprint_value",
        fake_fingerprint,
    )

    return probe, evidence


def test_history_probe_valid(monkeypatch):
    probe, evidence = _probe_fixture(monkeypatch)

    result = history.validate_gaze_in_wild_repository_history_probe(
        probe,
        evidence,
    )

    assert result == probe


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("record_type", "bad", "record type"),
        ("repository", "bad", "repository"),
        ("pinned_commit_sha1", "0" * 40, "pinned commit"),
        ("pinned_root_tree_sha1", "0" * 40, "pinned tree"),
        ("reachable_commit_count", 55, "commit count"),
        ("root_commit_sha1", "0" * 40, "root commit"),
        ("author_names", ["other"], "authors"),
    ],
)
def test_history_probe_identity_drift(
    monkeypatch,
    field,
    value,
    message,
):
    probe, evidence = _probe_fixture(monkeypatch)

    probe[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        history.validate_gaze_in_wild_repository_history_probe(
            probe,
            evidence,
        )


def test_history_probe_self_fingerprint_drift(monkeypatch):
    probe, evidence = _probe_fixture(monkeypatch)

    monkeypatch.setattr(
        history,
        "probe_fingerprint",
        lambda record: "0" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint",
    ):
        history.validate_gaze_in_wild_repository_history_probe(
            probe,
            evidence,
        )


def test_history_probe_reviewed_fingerprint_drift(monkeypatch):
    probe, evidence = _probe_fixture(monkeypatch)

    probe["probe_fingerprint_sha256"] = "0" * 64

    monkeypatch.setattr(
        history,
        "probe_fingerprint",
        lambda record: "0" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="reviewed probe fingerprint",
    ):
        history.validate_gaze_in_wild_repository_history_probe(
            probe,
            evidence,
        )


def test_history_probe_readme_blob_drift(monkeypatch):
    probe, evidence = _probe_fixture(monkeypatch)

    probe["readme_history"]["revisions"][0]["blob_sha1"] = "0" * 40

    with pytest.raises(
        BenchmarkIntegrityError,
        match="README blobs",
    ):
        history.validate_gaze_in_wild_repository_history_probe(
            probe,
            evidence,
        )


def test_history_probe_license_drift(monkeypatch):
    probe, evidence = _probe_fixture(monkeypatch)

    probe["software_license_history"]["license_file_identifies_mit"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="live license",
    ):
        history.validate_gaze_in_wild_repository_history_probe(
            probe,
            evidence,
        )


def test_history_probe_tree_drift(monkeypatch):
    probe, evidence = _probe_fixture(monkeypatch)

    probe["repository_tree"]["tracked_path_count"] = 999

    with pytest.raises(
        BenchmarkIntegrityError,
        match="live tree",
    ):
        history.validate_gaze_in_wild_repository_history_probe(
            probe,
            evidence,
        )


def test_history_probe_requires_positive_live_boundary(monkeypatch):
    probe, evidence = _probe_fixture(monkeypatch)

    probe["scientific_boundary"]["official_first_author_repository_history_verified"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        history.validate_gaze_in_wild_repository_history_probe(
            probe,
            evidence,
        )


@pytest.mark.parametrize(
    "key",
    [
        "exact_external_dataset_copy_obtained",
        "external_dataset_file_rights_resolved",
        "software_mit_is_external_dataset_license",
        "published_distribution_url_is_current_direct_copy_verified",
        "participant_identity_mapping_from_history_verified",
        "complete_trial_to_task_mapping_from_history_verified",
        "human_human_agreement_created",
        "participant_disjoint_model_validation_created",
        "frozen_evidence_performance_claim_created",
    ],
)
def test_history_probe_cannot_promote_claims(
    monkeypatch,
    key,
):
    probe, evidence = _probe_fixture(monkeypatch)

    probe["scientific_boundary"][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        history.validate_gaze_in_wild_repository_history_probe(
            probe,
            evidence,
        )


# ============================================================
# QUARANTINE EXIT PURE HELPERS
# ============================================================


def _pending(**changes):
    values = {
        "recovery_candidate_kind": "unknown_recovered_copy",
        "recovery_record_fingerprint_sha256": "1" * 64,
        "recovery_tree_fingerprint_sha256": "2" * 64,
        "candidate_inventory_fingerprint_sha256": "3" * 64,
        "audit_template_fingerprint_sha256": "4" * 64,
    }

    values.update(changes)

    return quarantine.GazeInWildQuarantineExitAuthorization(**values)


def _authorized(**changes):
    values = {
        "recovery_candidate_kind": "unknown_recovered_copy",
        "recovery_record_fingerprint_sha256": "1" * 64,
        "recovery_tree_fingerprint_sha256": "2" * 64,
        "candidate_inventory_fingerprint_sha256": "3" * 64,
        "audit_template_fingerprint_sha256": "4" * 64,
        "decision": "authorized",
        "reviewer": "reviewer",
        "reviewed_at": "2026-09-24",
        "source_authority_verified": True,
        "authoritative_source": "source",
        "authoritative_source_revision": "revision",
        "source_authority_evidence": "authority reviewed",
        "exact_copy_identity_verified": True,
        "exact_copy_identity_evidence": (
            "Structured GIW exact-copy review fingerprint: " + "a" * 64
        ),
        "dataset_file_rights_resolved": True,
        "reuse_terms_verified": True,
        "reuse_terms_source": "terms",
        "rights_evidence": "rights reviewed",
        "analysis_use_permitted": True,
        "analysis_use_evidence": "analysis reviewed",
        "redistribution_status": "restricted",
        "redistribution_evidence": "redistribution reviewed",
        "authorization_basis": "independent review",
    }

    values.update(changes)

    return quarantine.GazeInWildQuarantineExitAuthorization(**values)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "a" * 63,
        "a" * 65,
        "g" * 64,
    ],
)
def test_quarantine_sha_invalid(value):
    with pytest.raises(
        ValueError,
        match="64 hexadecimal",
    ):
        quarantine._sha256(
            value,
            field_name="fixture",
        )


def test_quarantine_sha_normalizes():
    assert (
        quarantine._sha256(
            "A" * 64,
            field_name="fixture",
        )
        == "a" * 64
    )


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "REVIEW_REQUIRED",
        "__unresolved__",
        "unknown",
        "none",
        "nan",
    ],
)
def test_quarantine_resolved_rejects_unresolved(value):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="require reviewed",
    ):
        quarantine._resolved(
            value,
            field_name="fixture",
        )


def test_quarantine_resolved_success():
    assert (
        quarantine._resolved(
            " reviewed ",
            field_name="fixture",
        )
        == "reviewed"
    )


def test_quarantine_structured_exact_copy_valid():
    assert (
        quarantine._structured_exact_copy_fingerprint(
            "Structured GIW exact-copy review fingerprint: " + "a" * 64
        )
        == "a" * 64
    )


def test_quarantine_structured_exact_copy_free_text():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="free-text",
    ):
        quarantine._structured_exact_copy_fingerprint("manually reviewed")


def test_quarantine_load_mapping():
    original = {"x": 1}

    assert (
        quarantine._load_json_object(
            original,
            label="fixture",
        )
        == original
    )


def test_quarantine_load_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        quarantine._load_json_object(
            tmp_path / "missing.json",
            label="fixture",
        )


def test_quarantine_load_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        quarantine._load_json_object(
            path,
            label="fixture",
        )


def test_quarantine_load_nonobject(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        quarantine._load_json_object(
            path,
            label="fixture",
        )


def test_quarantine_template_wrong_type():
    with pytest.raises(
        TypeError,
        match="GazeInWildSourceAuditSpec",
    ):
        quarantine._template_fingerprint(object())


def test_quarantine_candidate_note():
    assert quarantine._candidate_inventory_note("a" * 64) == (
        "Candidate inventory fingerprint: " + "a" * 64
    )


def test_quarantine_recovery_files_missing_inventory():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="inventory is missing",
    ):
        quarantine._recovery_files({})


def test_quarantine_recovery_files_missing_manifest():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="file manifest is missing",
    ):
        quarantine._recovery_files({"inventory": {}})


def test_quarantine_recovery_files_invalid_row():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="manifest is invalid",
    ):
        quarantine._recovery_files(
            {
                "inventory": {
                    "files": ["bad"],
                }
            }
        )


def test_quarantine_recovery_files_success():
    assert quarantine._recovery_files(
        {
            "inventory": {
                "files": [
                    {
                        "path": "x.mat",
                        "sha256": "a" * 64,
                        "bytes": 10,
                    }
                ]
            }
        }
    ) == [
        {
            "path": "x.mat",
            "sha256": "a" * 64,
            "bytes": 10,
        }
    ]


@pytest.mark.parametrize(
    "decision",
    ["bad", "", "yes"],
)
def test_quarantine_invalid_decision(decision):
    with pytest.raises(ValueError, match="decision"):
        _pending(decision=decision)


@pytest.mark.parametrize(
    "status",
    ["bad", "", "yes"],
)
def test_quarantine_invalid_redistribution(status):
    with pytest.raises(
        ValueError,
        match="redistribution_status",
    ):
        _pending(redistribution_status=status)


@pytest.mark.parametrize(
    "field",
    [
        "source_authority_verified",
        "exact_copy_identity_verified",
        "dataset_file_rights_resolved",
        "reuse_terms_verified",
        "analysis_use_permitted",
    ],
)
def test_quarantine_boolean_fields_are_strict(field):
    with pytest.raises(
        ValueError,
        match="must be boolean",
    ):
        _pending(**{field: 1})


def test_quarantine_denied_requires_reviewer():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="reviewer",
    ):
        _pending(decision="denied")


def test_quarantine_denied_valid():
    denied = _pending(
        decision="denied",
        reviewer="reviewer",
        reviewed_at="2026-09-24",
        authorization_basis="reviewed",
    )

    assert denied.decision == "denied"


def test_quarantine_authorized_kind_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot leave quarantine",
    ):
        _authorized(recovery_candidate_kind="transformed_secondary_collection")


def test_quarantine_authorized_gate_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="affirmative",
    ):
        _authorized(analysis_use_permitted=False)


def test_quarantine_authorized_redistribution_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="redistribution_status",
    ):
        _authorized(redistribution_status="unknown")


def test_quarantine_authorized_resolved_field_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="authoritative_source",
    ):
        _authorized(authoritative_source="REVIEW_REQUIRED")


def test_quarantine_payload_excludes_runtime_state():
    pending = _pending()

    payload = pending.to_dict()

    assert "_binding_validated" not in payload
    assert payload["record_type"] == quarantine._RECORD_TYPE
    assert payload["scientific_boundary"] == quarantine._SCIENTIFIC_BOUNDARY
    assert len(payload["record_fingerprint_sha256"]) == 64


def test_quarantine_from_dict_roundtrip():
    pending = _pending(
        notes=("a", "b"),
    )

    loaded = quarantine.GazeInWildQuarantineExitAuthorization.from_dict(pending.to_dict())

    assert loaded == pending
    assert loaded.notes == ("a", "b")


def test_quarantine_from_dict_record_type():
    payload = _pending().to_dict()
    payload["record_type"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record_type",
    ):
        quarantine.GazeInWildQuarantineExitAuthorization.from_dict(payload)


def test_quarantine_from_dict_boundary():
    payload = _pending().to_dict()

    payload["scientific_boundary"]["empirical_evidence_created"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="scientific boundary",
    ):
        quarantine.GazeInWildQuarantineExitAuthorization.from_dict(payload)


def test_quarantine_from_dict_notes_type():
    payload = _pending().to_dict()
    payload["notes"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="notes must be a JSON list",
    ):
        quarantine.GazeInWildQuarantineExitAuthorization.from_dict(payload)


def test_quarantine_from_dict_invalid_constructor():
    payload = _pending().to_dict()
    payload["decision"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record is invalid",
    ):
        quarantine.GazeInWildQuarantineExitAuthorization.from_dict(payload)


def test_quarantine_from_dict_fingerprint_drift():
    payload = _pending().to_dict()
    payload["record_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint drifted",
    ):
        quarantine.GazeInWildQuarantineExitAuthorization.from_dict(payload)


def test_quarantine_template_consistency_pending_noop():
    quarantine._validate_authorized_template_consistency(
        _pending(),
        SimpleNamespace(
            source="different",
            source_revision="different",
            reuse_terms_source="different",
        ),
    )


def test_quarantine_template_consistency_valid():
    authorization = _authorized()

    quarantine._validate_authorized_template_consistency(
        authorization,
        SimpleNamespace(
            source="source",
            source_revision="revision",
            reuse_terms_source="terms",
        ),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", "different"),
        ("source_revision", "different"),
        ("reuse_terms_source", "different"),
    ],
)
def test_quarantine_template_consistency_mismatch(
    field,
    value,
):
    authorization = _authorized()

    spec = SimpleNamespace(
        source="source",
        source_revision="revision",
        reuse_terms_source="terms",
    )

    setattr(spec, field, value)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source/rights identity conflicts",
    ):
        quarantine._validate_authorized_template_consistency(
            authorization,
            spec,
        )


def _exact_copy_kwargs():
    return {
        "root": "candidate",
        "recovery_record_or_path": {"fixture": True},
        "exact_copy_review_record_or_path": {"fixture": True},
        "readiness_record_or_path": {"fixture": True},
        "candidate_screen_record_or_path": {"fixture": True},
        "reference_root": "reference",
        "reference_provenance_path": "reference.txt",
    }


def test_quarantine_exact_copy_noop_when_not_verified():
    quarantine._validate_structured_exact_copy_binding(
        _pending(),
        root="candidate",
        recovery_record_or_path={},
        exact_copy_review_record_or_path=None,
        readiness_record_or_path=None,
        candidate_screen_record_or_path=None,
        reference_root=None,
        reference_provenance_path=None,
    )


def test_quarantine_exact_copy_missing_inputs():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing inputs",
    ):
        quarantine._validate_structured_exact_copy_binding(
            _authorized(),
            root="candidate",
            recovery_record_or_path={},
            exact_copy_review_record_or_path=None,
            readiness_record_or_path=None,
            candidate_screen_record_or_path=None,
            reference_root=None,
            reference_provenance_path=None,
        )


def test_quarantine_exact_copy_unverified_live_record(
    monkeypatch,
):
    authorization = _authorized()

    monkeypatch.setattr(
        exact_copy,
        "verify_gaze_in_wild_exact_copy_review",
        lambda *args, **kwargs: SimpleNamespace(
            exact_copy_identity_verified=False,
            record_fingerprint_sha256="a" * 64,
            recovery_record_fingerprint_sha256="1" * 64,
            recovery_tree_fingerprint_sha256="2" * 64,
            candidate_inventory_fingerprint_sha256="3" * 64,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="live decision is not verified",
    ):
        quarantine._validate_structured_exact_copy_binding(
            authorization,
            **_exact_copy_kwargs(),
        )


def test_quarantine_exact_copy_fingerprint_mismatch(
    monkeypatch,
):
    authorization = _authorized()

    monkeypatch.setattr(
        exact_copy,
        "verify_gaze_in_wild_exact_copy_review",
        lambda *args, **kwargs: SimpleNamespace(
            exact_copy_identity_verified=True,
            record_fingerprint_sha256="b" * 64,
            recovery_record_fingerprint_sha256="1" * 64,
            recovery_tree_fingerprint_sha256="2" * 64,
            candidate_inventory_fingerprint_sha256="3" * 64,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not match",
    ):
        quarantine._validate_structured_exact_copy_binding(
            authorization,
            **_exact_copy_kwargs(),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "recovery_record_fingerprint_sha256",
            "f" * 64,
        ),
        (
            "recovery_tree_fingerprint_sha256",
            "f" * 64,
        ),
        (
            "candidate_inventory_fingerprint_sha256",
            "f" * 64,
        ),
    ],
)
def test_quarantine_exact_copy_binding_mismatch(
    monkeypatch,
    field,
    value,
):
    authorization = _authorized()

    verified = SimpleNamespace(
        exact_copy_identity_verified=True,
        record_fingerprint_sha256="a" * 64,
        recovery_record_fingerprint_sha256="1" * 64,
        recovery_tree_fingerprint_sha256="2" * 64,
        candidate_inventory_fingerprint_sha256="3" * 64,
    )

    setattr(
        verified,
        field,
        value,
    )

    monkeypatch.setattr(
        exact_copy,
        "verify_gaze_in_wild_exact_copy_review",
        lambda *args, **kwargs: verified,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not bound",
    ):
        quarantine._validate_structured_exact_copy_binding(
            authorization,
            **_exact_copy_kwargs(),
        )


def test_quarantine_exact_copy_valid(monkeypatch):
    authorization = _authorized()

    monkeypatch.setattr(
        exact_copy,
        "verify_gaze_in_wild_exact_copy_review",
        lambda *args, **kwargs: SimpleNamespace(
            exact_copy_identity_verified=True,
            record_fingerprint_sha256="a" * 64,
            recovery_record_fingerprint_sha256="1" * 64,
            recovery_tree_fingerprint_sha256="2" * 64,
            candidate_inventory_fingerprint_sha256="3" * 64,
        ),
    )

    quarantine._validate_structured_exact_copy_binding(
        authorization,
        **_exact_copy_kwargs(),
    )


def test_quarantine_require_wrong_type():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires a validated",
    ):
        quarantine.require_authorized_gaze_in_wild_quarantine_exit(
            object(),
            object(),
        )


def test_quarantine_require_fresh_validation():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="freshly revalidated",
    ):
        quarantine.require_authorized_gaze_in_wild_quarantine_exit(
            _authorized(),
            object(),
        )
