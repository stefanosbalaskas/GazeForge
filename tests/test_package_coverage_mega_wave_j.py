from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import gazeforge.gaze_in_wild_layout_convergence as layout
import gazeforge.gaze_in_wild_secondary_leads as secondary
from gazeforge.exceptions import BenchmarkIntegrityError

LAYOUT_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-layout-convergence-evidence-v1.json"
)

SECONDARY_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-secondary-recovery-lead-evidence-v1.json"
)


# ============================================================
# FIXTURES
# ============================================================


def _layout_evidence():
    return json.loads(LAYOUT_EVIDENCE.read_text(encoding="utf-8"))


def _layout_probe():
    return {
        "record_type": layout.PROBE_RECORD_TYPE,
        "probe_fingerprint_sha256": (layout.EXPECTED_PROBE_FINGERPRINT_SHA256),
        "first_party": {
            "repository": layout.FIRST_PARTY_REPOSITORY,
            "pinned_commit_sha1": layout.FIRST_PARTY_COMMIT,
            "plot_labels_path": "PlotLabels.m",
            "plot_labels_git_blob_sha1": (layout.FIRST_PARTY_PLOT_LABELS_BLOB),
            "gitignore_path": ".gitignore",
            "gitignore_git_blob_sha1": (layout.FIRST_PARTY_GITIGNORE_BLOB),
            "process_filename_pattern": (layout.PROCESS_FILENAME_PATTERN),
            "label_filename_pattern": (layout.LABEL_FILENAME_PATTERN),
            "process_variable": layout.PROCESS_VARIABLE,
            "label_variable": layout.LABEL_VARIABLE,
            "mat_files_ignored_by_processing_repository": True,
            "repository_is_exact_dataset_copy": False,
        },
        "secondary_sources": [
            {
                **dict(layout._SECONDARY_SOURCES[0]),
                "process_filename_grammar_matches_first_party": True,
                "label_filename_grammar_matches_first_party": True,
                "process_variable_matches_first_party": True,
                "label_variable_matches_first_party": True,
                "exact_copy_identity_verified": False,
                "dataset_file_rights_resolved": False,
            },
            {
                **dict(layout._SECONDARY_SOURCES[1]),
                "process_filename_grammar_matches_first_party": True,
                "label_filename_grammar_matches_first_party": True,
                "process_variable_matches_first_party": True,
                "label_variable_matches_first_party": True,
                "exact_copy_identity_verified": False,
                "dataset_file_rights_resolved": False,
            },
            {
                **dict(layout._SECONDARY_SOURCES[2]),
                "raw_giw_label_files_read": True,
                "label_variable_matches_first_party": True,
                "full_filename_grammar_independently_verified": False,
                "exact_copy_identity_verified": False,
                "dataset_file_rights_resolved": False,
            },
        ],
        "convergence": {
            "independent_downstream_source_count": 3,
            "full_layout_match_count": 2,
            "label_schema_corroboration_count": 3,
            "candidate_layout_screening_signal_only": True,
            "filename_or_schema_match_proves_exact_copy": False,
            "filename_or_schema_match_proves_source_authority": False,
            "filename_or_schema_match_proves_dataset_file_rights": False,
            "filename_or_schema_match_authorizes_empirical_use": False,
        },
        "scientific_boundary": {
            "authoritative_original_or_canonical_dataset_copy_obtained": False,
            "original_distribution_equivalence_verified": False,
            "dataset_file_rights_resolved": False,
            "analysis_use_permitted": False,
            "redistribution_authorized": False,
            "quarantine_exit_authorized": False,
            "source_audit_ready": False,
            "empirical_evidence_eligible": False,
            "human_human_agreement_created": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "gp3_validity_claim_created": False,
            "frozen_evidence_performance_claim_created": False,
        },
    }


def _secondary_evidence():
    return json.loads(SECONDARY_EVIDENCE.read_text(encoding="utf-8"))


def _secondary_probe():
    evidence = _secondary_evidence()

    return {
        "record_type": secondary.PROBE_RECORD_TYPE,
        "dataset": evidence["dataset"],
        "sources": copy.deepcopy(evidence["sources"]),
        "scientific_boundary": copy.deepcopy(evidence["scientific_boundary"]),
        "claim_limit": evidence["claim_limit"],
        "probe_fingerprint_sha256": (secondary.EXPECTED_PROBE_FINGERPRINT),
    }


# ============================================================
# LAYOUT CONVERGENCE HELPERS
# ============================================================


def test_layout_canonical_deterministic():
    assert layout._canonical_bytes({"b": 2, "a": 1}) == layout._canonical_bytes({"a": 1, "b": 2})


def test_layout_evidence_fingerprint_ignores_stored():
    record = {
        "x": 1,
        "evidence_fingerprint_sha256": "a",
    }

    first = layout.evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = "b"

    assert layout.evidence_fingerprint(record) == first


def test_layout_probe_fingerprint_ignores_stored():
    record = {
        "x": 1,
        "probe_fingerprint_sha256": "a",
    }

    first = layout.probe_fingerprint(record)

    record["probe_fingerprint_sha256"] = "b"

    assert layout.probe_fingerprint(record) == first


def test_layout_git_blob_deterministic():
    assert layout.git_blob_sha1(b"abc") == layout.git_blob_sha1(b"abc")


def test_layout_load_mapping_copy():
    original = {"x": 1}

    result, path = layout._load(
        original,
        label="fixture",
    )

    assert result == original
    assert result is not original
    assert path is None


def test_layout_load_missing(tmp_path):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        layout._load(
            tmp_path / "missing.json",
            label="fixture",
        )


def test_layout_load_bad_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        layout._load(
            path,
            label="fixture",
        )


def test_layout_load_nonobject(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        layout._load(
            path,
            label="fixture",
        )


def test_layout_mapping_missing():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        layout._mapping(
            {},
            "fixture",
        )


def test_layout_equal_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        layout._equal(
            1,
            2,
            "fixture",
        )


def test_layout_true_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        layout._true(
            False,
            "fixture",
        )


def test_layout_false_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        layout._false(
            True,
            "fixture",
        )


def test_layout_decode_success():
    assert (
        layout._decode(
            b"abc",
            "fixture",
        )
        == "abc"
    )


def test_layout_decode_invalid_utf8():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="UTF-8",
    ):
        layout._decode(
            b"\xff",
            "fixture",
        )


def test_layout_require_success():
    layout._require(
        "abc def",
        ("abc", "def"),
        "fixture",
    )


def test_layout_require_missing():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="required schema tokens",
    ):
        layout._require(
            "abc",
            ("abc", "missing"),
            "fixture",
        )


def test_layout_verify_blob_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Git blob drifted",
    ):
        layout._verify_blob(
            b"abc",
            "0" * 40,
            "fixture",
        )


# ============================================================
# LAYOUT EVIDENCE
# ============================================================


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "record_type",
            "bad",
            "record type",
        ),
        (
            "status",
            "bad",
            "status",
        ),
        (
            "checked_on",
            "1900-01-01",
            "review date",
        ),
        (
            "dataset",
            "bad",
            "dataset identity",
        ),
    ],
)
def test_layout_evidence_top_level_guards(
    field,
    value,
    message,
):
    record = _layout_evidence()
    record[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


@pytest.mark.parametrize(
    "section",
    [
        "parent_evidence",
        "first_party_schema",
        "downstream_convergence",
        "scientific_boundary",
    ],
)
def test_layout_evidence_required_mappings(
    section,
):
    record = _layout_evidence()
    record[section] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


@pytest.mark.parametrize(
    ("key", "message"),
    [
        (
            "repository_history_evidence_fingerprint_sha256",
            "repository-history",
        ),
        (
            "secondary_recovery_lead_evidence_fingerprint_sha256",
            "secondary-lead",
        ),
        (
            "distribution_availability_evidence_fingerprint_sha256",
            "distribution parent",
        ),
    ],
)
def test_layout_parent_drift(
    key,
    message,
):
    record = _layout_evidence()

    record["parent_evidence"][key] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


def test_layout_first_party_schema_drift():
    record = _layout_evidence()

    record["first_party_schema"]["process_variable"] = "Other"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="first-party schema",
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        (
            "reviewed_probe_record_type",
            "bad",
            "probe record type",
        ),
        (
            "reviewed_probe_fingerprint_sha256",
            "0" * 64,
            "probe fingerprint",
        ),
        (
            "independent_downstream_source_count",
            2,
            "source count",
        ),
        (
            "full_layout_match_count",
            1,
            "full-layout",
        ),
        (
            "label_schema_corroboration_count",
            2,
            "label-schema",
        ),
    ],
)
def test_layout_convergence_counts_and_identity(
    key,
    value,
    message,
):
    record = _layout_evidence()

    record["downstream_convergence"][key] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


def test_layout_sources_must_be_list():
    record = _layout_evidence()

    record["downstream_convergence"]["sources"] = {}

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sources must be a list",
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


def test_layout_source_inventory_drift():
    record = _layout_evidence()

    record["downstream_convergence"]["sources"][0]["path"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="secondary source inventory",
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


def test_layout_screening_signal_required():
    record = _layout_evidence()

    record["downstream_convergence"]["candidate_layout_screening_signal_only"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


@pytest.mark.parametrize(
    "key",
    [
        "convergence_is_exact_copy_identity_evidence",
        "convergence_is_dataset_file_rights_evidence",
        "convergence_is_empirical_authorization",
    ],
)
def test_layout_convergence_cannot_promote(
    key,
):
    record = _layout_evidence()

    record["downstream_convergence"][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


@pytest.mark.parametrize(
    "key",
    [
        "first_party_filename_and_matlab_variable_schema_verified",
        "independent_downstream_layout_convergence_verified",
    ],
)
def test_layout_positive_boundary_required(key):
    record = _layout_evidence()

    record["scientific_boundary"][key] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


@pytest.mark.parametrize(
    "key",
    [
        "authoritative_original_or_canonical_dataset_copy_obtained",
        "original_distribution_equivalence_verified",
        "dataset_file_rights_resolved",
        "analysis_use_permitted",
        "redistribution_authorized",
        "quarantine_exit_authorized",
        "source_audit_ready",
        "empirical_evidence_eligible",
        "human_human_agreement_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "frozen_evidence_performance_claim_created",
    ],
)
def test_layout_scientific_boundary_closed(
    key,
):
    record = _layout_evidence()

    record["scientific_boundary"][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "claim_limits",
            [],
            "claim limits",
        ),
        (
            "claim_limits",
            "bad",
            "claim limits",
        ),
        (
            "next_required_actions",
            [],
            "next actions",
        ),
        (
            "next_required_actions",
            "bad",
            "next actions",
        ),
    ],
)
def test_layout_claim_limits_and_actions(
    field,
    value,
    message,
):
    record = _layout_evidence()
    record[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


def test_layout_self_fingerprint_guard():
    record = _layout_evidence()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint",
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


def test_layout_immutable_fingerprint_guard(
    monkeypatch,
):
    record = _layout_evidence()

    monkeypatch.setattr(
        layout,
        "evidence_fingerprint",
        lambda value: "f" * 64,
    )

    record["evidence_fingerprint_sha256"] = "f" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="immutable fingerprint",
    ):
        layout.validate_gaze_in_wild_layout_convergence_evidence(record)


# ============================================================
# LAYOUT PROBE
# ============================================================


def _force_layout_probe_fingerprint(
    monkeypatch,
):
    monkeypatch.setattr(
        layout,
        "probe_fingerprint",
        lambda value: layout.EXPECTED_PROBE_FINGERPRINT_SHA256,
    )


def test_layout_probe_valid(monkeypatch):
    _force_layout_probe_fingerprint(monkeypatch)

    result = layout.validate_gaze_in_wild_layout_convergence_probe(
        _layout_probe(),
        LAYOUT_EVIDENCE,
    )

    assert result.full_layout_match_count == 2
    assert result.label_schema_corroboration_count == 3

    assert result.exact_copy_identity_verified is False


def test_layout_probe_record_type(monkeypatch):
    _force_layout_probe_fingerprint(monkeypatch)

    probe = _layout_probe()
    probe["record_type"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="probe record type",
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


def test_layout_probe_self_fingerprint(monkeypatch):
    probe = _layout_probe()

    monkeypatch.setattr(
        layout,
        "probe_fingerprint",
        lambda value: "0" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint",
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


def test_layout_probe_reviewed_fingerprint(monkeypatch):
    probe = _layout_probe()

    probe["probe_fingerprint_sha256"] = "0" * 64

    monkeypatch.setattr(
        layout,
        "probe_fingerprint",
        lambda value: "0" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="reviewed probe fingerprint",
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


def test_layout_probe_first_party_drift(
    monkeypatch,
):
    _force_layout_probe_fingerprint(monkeypatch)

    probe = _layout_probe()

    probe["first_party"]["process_variable"] = "Other"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fresh first-party schema",
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        [{}],
    ],
)
def test_layout_probe_three_sources_required(
    monkeypatch,
    value,
):
    _force_layout_probe_fingerprint(monkeypatch)

    probe = _layout_probe()
    probe["secondary_sources"] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="three sources",
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


def test_layout_probe_source_object_required(
    monkeypatch,
):
    _force_layout_probe_fingerprint(monkeypatch)

    probe = _layout_probe()
    probe["secondary_sources"][0] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source must be an object",
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


def test_layout_probe_source_identity_drift(
    monkeypatch,
):
    _force_layout_probe_fingerprint(monkeypatch)

    probe = _layout_probe()

    probe["secondary_sources"][0]["repository"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="probe source",
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


@pytest.mark.parametrize(
    "key",
    [
        "exact_copy_identity_verified",
        "dataset_file_rights_resolved",
    ],
)
def test_layout_probe_source_promotions(
    monkeypatch,
    key,
):
    _force_layout_probe_fingerprint(monkeypatch)

    probe = _layout_probe()

    probe["secondary_sources"][0][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


@pytest.mark.parametrize(
    "key",
    [
        "process_filename_grammar_matches_first_party",
        "label_filename_grammar_matches_first_party",
        "process_variable_matches_first_party",
        "label_variable_matches_first_party",
    ],
)
def test_layout_probe_full_match_flags_required(
    monkeypatch,
    key,
):
    _force_layout_probe_fingerprint(monkeypatch)

    probe = _layout_probe()

    probe["secondary_sources"][0][key] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        (
            "raw_giw_label_files_read",
            False,
        ),
        (
            "label_variable_matches_first_party",
            False,
        ),
        (
            "full_filename_grammar_independently_verified",
            True,
        ),
    ],
)
def test_layout_probe_leo_contract(
    monkeypatch,
    key,
    value,
):
    _force_layout_probe_fingerprint(monkeypatch)

    probe = _layout_probe()

    probe["secondary_sources"][2][key] = value

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        (
            "independent_downstream_source_count",
            2,
        ),
        (
            "full_layout_match_count",
            1,
        ),
        (
            "label_schema_corroboration_count",
            2,
        ),
        (
            "candidate_layout_screening_signal_only",
            False,
        ),
    ],
)
def test_layout_probe_convergence_contract(
    monkeypatch,
    key,
    value,
):
    _force_layout_probe_fingerprint(monkeypatch)

    probe = _layout_probe()

    probe["convergence"][key] = value

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


@pytest.mark.parametrize(
    "key",
    [
        "filename_or_schema_match_proves_exact_copy",
        "filename_or_schema_match_proves_source_authority",
        "filename_or_schema_match_proves_dataset_file_rights",
        "filename_or_schema_match_authorizes_empirical_use",
    ],
)
def test_layout_probe_convergence_cannot_promote(
    monkeypatch,
    key,
):
    _force_layout_probe_fingerprint(monkeypatch)

    probe = _layout_probe()
    probe["convergence"][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


def test_layout_probe_boundary_must_be_mapping(
    monkeypatch,
):
    _force_layout_probe_fingerprint(monkeypatch)

    probe = _layout_probe()
    probe["scientific_boundary"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


def test_layout_probe_boundary_cannot_promote(
    monkeypatch,
):
    _force_layout_probe_fingerprint(monkeypatch)

    probe = _layout_probe()

    probe["scientific_boundary"]["analysis_use_permitted"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        layout.validate_gaze_in_wild_layout_convergence_probe(
            probe,
            LAYOUT_EVIDENCE,
        )


# ============================================================
# SECONDARY-LEAD HELPERS
# ============================================================


def test_secondary_canonical_deterministic():
    assert secondary._canonical_bytes({"b": 2, "a": 1}) == secondary._canonical_bytes(
        {"a": 1, "b": 2}
    )


def test_secondary_fingerprint_ignores_key():
    record = {
        "x": 1,
        "digest": "a",
    }

    first = secondary._fingerprint(
        record,
        "digest",
    )

    record["digest"] = "b"

    assert (
        secondary._fingerprint(
            record,
            "digest",
        )
        == first
    )


def test_secondary_load_mapping_copy():
    original = {"x": 1}

    loaded = secondary._load(original)

    assert loaded == original
    assert loaded is not original


def test_secondary_load_missing(tmp_path):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        secondary._load(tmp_path / "missing.json")


def test_secondary_load_bad_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        secondary._load(path)


def test_secondary_load_nonobject(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="JSON object",
    ):
        secondary._load(path)


# ============================================================
# SECONDARY PROBE
# ============================================================


def _force_secondary_probe_fp(monkeypatch):
    monkeypatch.setattr(
        secondary,
        "_fingerprint",
        lambda value, key: secondary.EXPECTED_PROBE_FINGERPRINT,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "record_type",
            "bad",
        ),
        (
            "dataset",
            "bad",
        ),
    ],
)
def test_secondary_probe_identity(
    field,
    value,
):
    probe = _secondary_probe()
    probe[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="identity drifted",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


def test_secondary_probe_fingerprint():
    probe = _secondary_probe()

    probe["probe_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint drifted",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


def test_secondary_probe_reviewed_contract(
    monkeypatch,
):
    probe = _secondary_probe()

    probe["probe_fingerprint_sha256"] = "f" * 64

    monkeypatch.setattr(
        secondary,
        "_fingerprint",
        lambda value, key: "f" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="reviewed probe contract",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
    ],
)
def test_secondary_sources_mapping(
    monkeypatch,
    value,
):
    _force_secondary_probe_fp(monkeypatch)

    probe = _secondary_probe()
    probe["sources"] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sources are missing",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


def test_secondary_source_records_complete(
    monkeypatch,
):
    _force_secondary_probe_fp(monkeypatch)

    probe = _secondary_probe()

    probe["sources"]["transformed_collection_lead"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source records are incomplete",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "repository",
            "bad",
        ),
        (
            "pinned_commit_sha1",
            "0" * 40,
        ),
    ],
)
def test_secondary_transformed_identity(
    monkeypatch,
    field,
    value,
):
    _force_secondary_probe_fp(monkeypatch)

    probe = _secondary_probe()

    probe["sources"]["transformed_collection_lead"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity drifted",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


def test_secondary_transformed_classification(
    monkeypatch,
):
    _force_secondary_probe_fp(monkeypatch)

    probe = _secondary_probe()

    probe["sources"]["transformed_collection_lead"]["classification"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="misclassified",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


@pytest.mark.parametrize(
    "key",
    [
        "external_collection_contents_obtained_by_this_probe",
        "external_collection_contents_audited_by_this_probe",
        "authoritative_original_distribution_equivalence_verified",
    ],
)
def test_secondary_transformed_false_gates(
    monkeypatch,
    key,
):
    _force_secondary_probe_fp(monkeypatch)

    probe = _secondary_probe()

    probe["sources"]["transformed_collection_lead"][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must keep",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


def test_secondary_transformed_paths_empty(
    monkeypatch,
):
    _force_secondary_probe_fp(monkeypatch)

    probe = _secondary_probe()

    probe["sources"]["transformed_collection_lead"]["tracked_official_process_or_label_paths"] = [
        "x.mat"
    ]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="official-layout",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "repository",
            "bad",
        ),
        (
            "pinned_commit_sha1",
            "0" * 40,
        ),
    ],
)
def test_secondary_labeller_identity(
    monkeypatch,
    field,
    value,
):
    _force_secondary_probe_fp(monkeypatch)

    probe = _secondary_probe()

    probe["sources"]["labeller_filename_lead"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity drifted",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


def test_secondary_labeller_classification(
    monkeypatch,
):
    _force_secondary_probe_fp(monkeypatch)

    probe = _secondary_probe()

    probe["sources"]["labeller_filename_lead"]["classification"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="over-promoted",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


def test_secondary_labeller_filenames(
    monkeypatch,
):
    _force_secondary_probe_fp(monkeypatch)

    probe = _secondary_probe()

    probe["sources"]["labeller_filename_lead"]["referenced_labeller_filenames"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="filename references drifted",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


@pytest.mark.parametrize(
    ("key", "message"),
    [
        (
            "referenced_labeller_files_repository_resident",
            "non-resident",
        ),
        (
            "independent_annotation_streams_recovered",
            "do not recover",
        ),
        (
            "human_human_agreement_eligible",
            "cannot open agreement",
        ),
    ],
)
def test_secondary_labeller_false_gates(
    monkeypatch,
    key,
    message,
):
    _force_secondary_probe_fp(monkeypatch)

    probe = _secondary_probe()

    probe["sources"]["labeller_filename_lead"][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


def test_secondary_labeller_paths_empty(
    monkeypatch,
):
    _force_secondary_probe_fp(monkeypatch)

    probe = _secondary_probe()

    probe["sources"]["labeller_filename_lead"]["tracked_official_process_or_label_paths"] = [
        "x.mat"
    ]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="official-layout",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


def test_secondary_boundary_schema(
    monkeypatch,
):
    _force_secondary_probe_fp(monkeypatch)

    probe = _secondary_probe()

    probe["scientific_boundary"]["unexpected"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="boundary drifted",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


def test_secondary_boundary_promotion(
    monkeypatch,
):
    _force_secondary_probe_fp(monkeypatch)

    probe = _secondary_probe()

    first = next(iter(secondary._FALSE_BOUNDARY_KEYS))

    probe["scientific_boundary"][first] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="boundary was promoted",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_probe(probe)


# ============================================================
# SECONDARY FROZEN EVIDENCE
# ============================================================


def _force_secondary_all_fingerprints(
    monkeypatch,
):
    def fake(value, key):
        if key == "probe_fingerprint_sha256":
            return secondary.EXPECTED_PROBE_FINGERPRINT

        if key == "evidence_fingerprint_sha256":
            return secondary.EXPECTED_EVIDENCE_FINGERPRINT

        raise AssertionError(key)

    monkeypatch.setattr(
        secondary,
        "_fingerprint",
        fake,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "record_type",
            "bad",
        ),
        (
            "dataset",
            "bad",
        ),
    ],
)
def test_secondary_evidence_identity(
    monkeypatch,
    field,
    value,
):
    _force_secondary_all_fingerprints(monkeypatch)

    evidence = _secondary_evidence()
    evidence[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="frozen evidence identity",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_evidence(
            _secondary_probe(),
            evidence,
        )


def test_secondary_evidence_review_status(
    monkeypatch,
):
    _force_secondary_all_fingerprints(monkeypatch)

    evidence = _secondary_evidence()

    evidence["review_status"] = "empirical"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="remain quarantined",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_evidence(
            _secondary_probe(),
            evidence,
        )


def test_secondary_evidence_stored_fingerprint():
    evidence = _secondary_evidence()

    evidence["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="evidence fingerprint drifted",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_evidence(
            _secondary_probe(),
            evidence,
        )


def test_secondary_evidence_reviewed_contract(
    monkeypatch,
):
    evidence = _secondary_evidence()

    evidence["evidence_fingerprint_sha256"] = "f" * 64

    probe = _secondary_probe()

    def fake(value, key):
        if key == "probe_fingerprint_sha256":
            return secondary.EXPECTED_PROBE_FINGERPRINT
        return "f" * 64

    monkeypatch.setattr(
        secondary,
        "_fingerprint",
        fake,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="reviewed evidence contract",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_evidence(
            probe,
            evidence,
        )


def test_secondary_evidence_probe_binding(
    monkeypatch,
):
    _force_secondary_all_fingerprints(monkeypatch)

    evidence = _secondary_evidence()

    evidence["source_probe_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="live probe no longer matches",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_evidence(
            _secondary_probe(),
            evidence,
        )


def test_secondary_evidence_sources_binding(
    monkeypatch,
):
    _force_secondary_all_fingerprints(monkeypatch)

    evidence = _secondary_evidence()

    evidence["sources"] = {}

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source evidence drifted",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_evidence(
            _secondary_probe(),
            evidence,
        )


def test_secondary_evidence_boundary_binding(
    monkeypatch,
):
    _force_secondary_all_fingerprints(monkeypatch)

    evidence = _secondary_evidence()

    evidence["scientific_boundary"] = {}

    with pytest.raises(
        BenchmarkIntegrityError,
        match="frozen scientific boundary",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_evidence(
            _secondary_probe(),
            evidence,
        )


def test_secondary_evidence_claim_limit_binding(
    monkeypatch,
):
    _force_secondary_all_fingerprints(monkeypatch)

    evidence = _secondary_evidence()

    evidence["claim_limit"] = "changed"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="claim limit drifted",
    ):
        secondary.validate_gaze_in_wild_secondary_lead_evidence(
            _secondary_probe(),
            evidence,
        )
