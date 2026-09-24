from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

import gazeforge.gaze_in_wild_overlap_hha_evidence as hha
import gazeforge.gaze_in_wild_participant_task_evidence as participant
from gazeforge.exceptions import BenchmarkIntegrityError

PARTICIPANT_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-participant-task-metadata-evidence-v2.json"
)

HHA_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-distributed-overlap-human-human-agreement-evidence-v1.json"
)


def _participant_record():
    return json.loads(PARTICIPANT_EVIDENCE.read_text(encoding="utf-8"))


def _hha_record():
    return json.loads(HHA_EVIDENCE.read_text(encoding="utf-8"))


def _valid_live_probe():
    return {
        "record_type": ("gaze-in-wild-participant-task-live-probe-v2"),
        "springer": {
            "sha256": participant.SPRINGER_SHA256,
            "byte_size": 5_514_416,
            "page_count": 4,
            "text_sha256_whitespace_canonical": (participant.SPRINGER_TEXT_SHA256),
            "required_markers_present": True,
        },
        "arxiv": {
            "sha256": participant.ARXIV_SHA256,
            "byte_size": 9_437_264,
            "page_count": 23,
            "text_sha256_whitespace_canonical": (participant.ARXIV_TEXT_SHA256),
            "required_markers_present": True,
        },
        "boundaries": {
            "exact_distribution_equivalence_verified": False,
            "universal_tridx_to_task_name_mapping_verified": False,
            "analysis_use_permitted": False,
            "redistribution_permission_verified": False,
            "new_empirical_performance_claim_created": False,
        },
    }


# ============================================================
# PARTICIPANT/TASK HELPERS
# ============================================================


def test_participant_canonical_bytes_order():
    assert participant._canonical_bytes({"b": 2, "a": 1}) == participant._canonical_bytes(
        {"a": 1, "b": 2}
    )


def test_participant_fingerprint_ignores_stored():
    record = {
        "x": 1,
        "evidence_fingerprint_sha256": "a",
    }

    first = participant.evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = "b"

    assert participant.evidence_fingerprint(record) == first


def test_participant_load_mapping_copy():
    original = {"x": 1}

    result = participant._load_record(original)

    assert result == original
    assert result is not original


def test_participant_load_file(tmp_path):
    path = tmp_path / "record.json"

    path.write_text(
        '{"x": 1}',
        encoding="utf-8",
    )

    assert participant._load_record(path) == {"x": 1}


def test_participant_require_false_success():
    participant._require_false(
        {
            "a": False,
            "b": False,
        },
        "a",
        "b",
    )


def test_participant_require_false_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must remain false",
    ):
        participant._require_false(
            {"a": True},
            "a",
        )


# ============================================================
# PARTICIPANT MATRIX
# ============================================================


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "participant_ids",
            [],
            "participant set",
        ),
        (
            "participant_count",
            99,
            "participant count",
        ),
        (
            "task_columns",
            [],
            "task columns",
        ),
        (
            "status_counts",
            {},
            "status counts",
        ),
    ],
)
def test_participant_matrix_top_contract(
    field,
    value,
    message,
):
    matrix = copy.deepcopy(_participant_record()["publication_matrix"])

    matrix[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        participant._validate_matrix(matrix)


@pytest.mark.parametrize(
    "rows",
    [
        None,
        [],
        "bad",
    ],
)
def test_participant_matrix_rows_contract(rows):
    matrix = copy.deepcopy(_participant_record()["publication_matrix"])

    matrix["participants"] = rows

    with pytest.raises(
        BenchmarkIntegrityError,
        match="row count",
    ):
        participant._validate_matrix(matrix)


def test_participant_matrix_row_mapping():
    matrix = copy.deepcopy(_participant_record()["publication_matrix"])

    matrix["participants"][0] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="row must be a mapping",
    ):
        participant._validate_matrix(matrix)


@pytest.mark.parametrize(
    "value",
    [
        "1",
        None,
    ],
)
def test_participant_matrix_identity_type(
    value,
):
    matrix = copy.deepcopy(_participant_record()["publication_matrix"])

    matrix["participants"][0]["participant_id"] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="participant identity",
    ):
        participant._validate_matrix(matrix)


def test_participant_matrix_duplicate_identity():
    matrix = copy.deepcopy(_participant_record()["publication_matrix"])

    matrix["participants"][1]["participant_id"] = 1

    with pytest.raises(
        BenchmarkIntegrityError,
        match="participant identity",
    ):
        participant._validate_matrix(matrix)


@pytest.mark.parametrize(
    "tasks",
    [
        None,
        {},
        {"indoor_navigation": "single_labeller"},
    ],
)
def test_participant_matrix_task_shape(
    tasks,
):
    matrix = copy.deepcopy(_participant_record()["publication_matrix"])

    matrix["participants"][0]["tasks"] = tasks

    with pytest.raises(
        BenchmarkIntegrityError,
        match="task row shape",
    ):
        participant._validate_matrix(matrix)


def test_participant_matrix_invalid_status():
    matrix = copy.deepcopy(_participant_record()["publication_matrix"])

    matrix["participants"][0]["tasks"]["indoor_navigation"] = "other"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="task status is invalid",
    ):
        participant._validate_matrix(matrix)


def test_participant_matrix_row_drift():
    matrix = copy.deepcopy(_participant_record()["publication_matrix"])

    matrix["participants"][0]["tasks"]["indoor_navigation"] = "single_labeller"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="task row drifted",
    ):
        participant._validate_matrix(matrix)


# ============================================================
# PARTICIPANT/TASK EVIDENCE
# ============================================================


def _force_participant_fingerprint(
    monkeypatch,
):
    monkeypatch.setattr(
        participant,
        "evidence_fingerprint",
        lambda record: record.get("evidence_fingerprint_sha256"),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "record_type",
            "bad",
        ),
        (
            "status",
            "bad",
        ),
    ],
)
def test_participant_identity_guard(
    field,
    value,
):
    record = _participant_record()
    record[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="evidence identity",
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


def test_participant_stored_fingerprint_guard():
    record = _participant_record()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="stored fingerprint",
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "doi",
            "bad",
            "DOI",
        ),
        (
            "springer_pdf_sha256",
            "0" * 64,
            "Springer supplement identity",
        ),
        (
            "springer_text_sha256_whitespace_canonical",
            "0" * 64,
            "supplement text identity",
        ),
        (
            "springer_pdf_byte_size",
            1,
            "byte size",
        ),
        (
            "springer_pdf_page_count",
            1,
            "page count",
        ),
        (
            "arxiv_identifier",
            "bad",
            "arXiv identity",
        ),
        (
            "arxiv_pdf_sha256",
            "0" * 64,
            "arXiv PDF identity",
        ),
        (
            "arxiv_text_sha256_whitespace_canonical",
            "0" * 64,
            "arXiv text identity",
        ),
        (
            "publisher_and_author_copy_table_markers_agree",
            False,
            "table agreement",
        ),
    ],
)
def test_participant_publication_contract(
    monkeypatch,
    field,
    value,
    message,
):
    _force_participant_fingerprint(monkeypatch)

    record = _participant_record()

    record["publication_source"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "repository",
            "bad",
            "repository",
        ),
        (
            "commit_sha1",
            "0" * 40,
            "source commit",
        ),
    ],
)
def test_participant_first_party_identity(
    monkeypatch,
    field,
    value,
    message,
):
    _force_participant_fingerprint(monkeypatch)

    record = _participant_record()

    record["first_party_source"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


@pytest.mark.parametrize(
    "field",
    list(participant._EXPECTED_SOURCE_BLOBS),
)
def test_participant_source_blob_drift(
    monkeypatch,
    field,
):
    _force_participant_fingerprint(monkeypatch)

    record = _participant_record()

    record["first_party_source"][field] = "0" * 40

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source blob",
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


def test_participant_readme_authority_guard(
    monkeypatch,
):
    _force_participant_fingerprint(monkeypatch)

    record = _participant_record()

    record["first_party_source"][
        "readme_designates_supplement_as_official_participant_task_label_availability_list"
    ] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="README authority",
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


@pytest.mark.parametrize(
    "key",
    [
        "participant_info_name_used_as_raw_participant_directory",
        "pridx_passed_to_processing_output_identity",
        "published_person_number_to_processing_pridx_convention_supported",
    ],
)
def test_participant_identity_positive_flags(
    monkeypatch,
    key,
):
    _force_participant_fingerprint(monkeypatch)

    record = _participant_record()

    record["processing_identity_convention"][key] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="processing identity",
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "processed_filename_pattern",
            "bad",
            "ProcessData filename",
        ),
        (
            "label_filename_pattern",
            "bad",
            "LabelData filename",
        ),
        (
            "age_used_as_identity_join",
            True,
            "age must not",
        ),
        (
            "age_discrepancy_preserved",
            {},
            "age discrepancy",
        ),
    ],
)
def test_participant_identity_convention(
    monkeypatch,
    field,
    value,
    message,
):
    _force_participant_fingerprint(monkeypatch)

    record = _participant_record()

    record["processing_identity_convention"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


def test_participant_exact_file_identity_closed(
    monkeypatch,
):
    _force_participant_fingerprint(monkeypatch)

    record = _participant_record()

    record["processing_identity_convention"]["exact_distributed_file_identity_verified"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must remain false",
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


@pytest.mark.parametrize(
    "key",
    [
        "publication_person_to_task_status_matrix_verified",
        "indoor_walk_context_for_tridx_1_observed_in_first_party_plotting_code",
    ],
)
def test_participant_mapping_positive_flags(
    monkeypatch,
    key,
):
    _force_participant_fingerprint(monkeypatch)

    record = _participant_record()

    record["task_mapping_boundary"][key] = False

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


@pytest.mark.parametrize(
    "key",
    [
        "universal_tridx_to_task_name_mapping_verified",
        "task_directory_to_task_name_mapping_from_authoritative_distribution_verified",
        "exact_processdata_file_to_publication_task_mapping_verified",
        "global_tridx_mapping_inferred_from_that_context",
    ],
)
def test_participant_mapping_closed(
    monkeypatch,
    key,
):
    _force_participant_fingerprint(monkeypatch)

    record = _participant_record()

    record["task_mapping_boundary"][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must remain false",
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


@pytest.mark.parametrize(
    "key",
    [
        "authoritative_full_distribution_obtained",
        "exact_distribution_equivalence_verified",
        "reuse_terms_verified",
        "analysis_use_permitted",
        "redistribution_permission_verified",
        "source_audit_ready",
    ],
)
def test_participant_rights_boundary_closed(
    monkeypatch,
    key,
):
    _force_participant_fingerprint(monkeypatch)

    record = _participant_record()

    record["rights_boundary"][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must remain false",
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


@pytest.mark.parametrize(
    "key",
    [
        "per_file_sampling_rate_distribution_frozen",
        "human_human_agreement_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "new_empirical_performance_claim_created",
    ],
)
def test_participant_scientific_boundary_closed(
    monkeypatch,
    key,
):
    _force_participant_fingerprint(monkeypatch)

    record = _participant_record()

    record["scientific_boundary"][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must remain false",
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


def test_participant_immutable_fingerprint_guard(
    monkeypatch,
):
    record = _participant_record()

    record["evidence_fingerprint_sha256"] = "f" * 64

    monkeypatch.setattr(
        participant,
        "evidence_fingerprint",
        lambda value: "f" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="immutable fingerprint",
    ):
        participant.validate_gaze_in_wild_participant_task_evidence(record)


# ============================================================
# LIVE PARTICIPANT/TASK PROBE
# ============================================================


def test_participant_live_probe_valid():
    result = participant.validate_live_publication_probe(
        _valid_live_probe(),
        PARTICIPANT_EVIDENCE,
    )

    assert result["evidence_fingerprint_sha256"] == participant.EVIDENCE_FINGERPRINT


def test_participant_live_probe_type():
    probe = _valid_live_probe()

    probe["record_type"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="live probe type",
    ):
        participant.validate_live_publication_probe(
            probe,
            PARTICIPANT_EVIDENCE,
        )


def test_participant_live_springer_binding():
    probe = _valid_live_probe()

    probe["springer"]["page_count"] = 99

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Springer supplement binding",
    ):
        participant.validate_live_publication_probe(
            probe,
            PARTICIPANT_EVIDENCE,
        )


def test_participant_live_arxiv_binding():
    probe = _valid_live_probe()

    probe["arxiv"]["page_count"] = 99

    with pytest.raises(
        BenchmarkIntegrityError,
        match="arXiv binding",
    ):
        participant.validate_live_publication_probe(
            probe,
            PARTICIPANT_EVIDENCE,
        )


@pytest.mark.parametrize(
    "key",
    [
        "exact_distribution_equivalence_verified",
        "universal_tridx_to_task_name_mapping_verified",
        "analysis_use_permitted",
        "redistribution_permission_verified",
        "new_empirical_performance_claim_created",
    ],
)
def test_participant_live_boundaries_closed(
    key,
):
    probe = _valid_live_probe()

    probe["boundaries"][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must remain false",
    ):
        participant.validate_live_publication_probe(
            probe,
            PARTICIPANT_EVIDENCE,
        )


# ============================================================
# OVERLAP-HHA HELPERS
# ============================================================


def test_hha_canonical_order():
    assert hha._canonical_bytes({"b": 2, "a": 1}) == hha._canonical_bytes({"a": 1, "b": 2})


def test_hha_fingerprint_ignores_stored():
    record = {
        "x": 1,
        "evidence_fingerprint_sha256": "a",
    }

    first = hha.evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = "b"

    assert hha.evidence_fingerprint(record) == first


def test_hha_load_mapping_copy():
    original = {"x": 1}

    record, path = hha._load(original)

    assert record == original
    assert record is not original
    assert path is None


def test_hha_load_missing(tmp_path):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        hha._load(tmp_path / "missing.json")


def test_hha_load_bad_json(tmp_path):
    path = tmp_path / "bad.json"

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        hha._load(path)


def test_hha_load_nonobject(tmp_path):
    path = tmp_path / "bad.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        hha._load(path)


def test_hha_mapping_missing():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        hha._mapping(
            {},
            "missing",
        )


def test_hha_equal_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        hha._equal(
            1,
            2,
            "fixture",
        )


def test_hha_true_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        hha._true(
            False,
            "fixture",
        )


def test_hha_false_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        hha._false(
            True,
            "fixture",
        )


@pytest.mark.parametrize(
    "value",
    [
        "bad",
        None,
    ],
)
def test_hha_probability_numeric(value):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be numeric",
    ):
        hha._probability(
            value,
            "fixture",
        )


@pytest.mark.parametrize(
    "value",
    [
        -0.01,
        1.01,
        np.nan,
        np.inf,
    ],
)
def test_hha_probability_range(value):
    with pytest.raises(
        BenchmarkIntegrityError,
        match=r"\[0, 1\]",
    ):
        hha._probability(
            value,
            "fixture",
        )


@pytest.mark.parametrize(
    "value",
    [
        0.0,
        0.5,
        1.0,
    ],
)
def test_hha_probability_valid(value):
    assert (
        hha._probability(
            value,
            "fixture",
        )
        == value
    )


@pytest.mark.parametrize(
    "value",
    [
        "bad",
        None,
    ],
)
def test_hha_kappa_numeric(value):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be numeric",
    ):
        hha._kappa(
            value,
            "fixture",
        )


@pytest.mark.parametrize(
    "value",
    [
        -1.01,
        1.01,
        np.nan,
        np.inf,
    ],
)
def test_hha_kappa_range(value):
    with pytest.raises(
        BenchmarkIntegrityError,
        match=r"\[-1, 1\]",
    ):
        hha._kappa(
            value,
            "fixture",
        )


@pytest.mark.parametrize(
    "value",
    [
        -1.0,
        0.0,
        1.0,
    ],
)
def test_hha_kappa_valid(value):
    assert (
        hha._kappa(
            value,
            "fixture",
        )
        == value
    )


# ============================================================
# HHA INPUTS + PROTOCOL
# ============================================================


@pytest.mark.parametrize(
    ("key", "value"),
    [
        (
            "selected_label_file_count",
            17,
        ),
        (
            "selected_recording_count",
            4,
        ),
        (
            "selected_total_size_bytes",
            1,
        ),
        (
            "download_attempt_distribution",
            {},
        ),
        (
            "distinct_inferred_sampling_rates_hz",
            [],
        ),
        (
            "recording_tokens",
            [],
        ),
    ],
)
def test_hha_inputs_expected_contract(
    key,
    value,
):
    record = _hha_record()

    record["verified_inputs"][key] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        hha._validate_inputs(record)


@pytest.mark.parametrize(
    "key",
    [
        "all_files_matched_prior_size_md5_sha256",
        "all_filename_internal_pridx_tridx_lbridx_agree",
        "all_raw_mat_bytes_deleted_after_inspection",
    ],
)
def test_hha_inputs_positive_flags(key):
    record = _hha_record()

    record["verified_inputs"][key] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        hha._validate_inputs(record)


def test_hha_recording_token_grammar(monkeypatch):
    invalid_token = "indoor_navigation"

    expected = list(hha.EXPECTED_RECORDINGS)
    expected[0] = invalid_token

    monkeypatch.setattr(
        hha,
        "EXPECTED_RECORDINGS",
        tuple(expected),
    )

    record = _hha_record()
    record["verified_inputs"]["recording_tokens"] = expected

    with pytest.raises(
        BenchmarkIntegrityError,
        match="token grammar",
    ):
        hha._validate_inputs(record)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        (
            "scope",
            "bad",
        ),
        (
            "event_min_iou",
            0.1,
        ),
        (
            "sampling_rate_policy",
            "bad",
        ),
        (
            "resampling",
            "yes",
        ),
        (
            "event_matching",
            "bad",
        ),
    ],
)
def test_hha_protocol_expected_contract(
    key,
    value,
):
    record = _hha_record()

    record["analysis_protocol"][key] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        hha._validate_protocol(record)


@pytest.mark.parametrize(
    "key",
    [
        "sample_all_labels_includes_unlabelled_code_0",
        "event_label_match_required",
        "event_metrics_bidirectional",
        "neither_labeller_treated_as_truth",
    ],
)
def test_hha_protocol_positive_flags(
    key,
):
    record = _hha_record()

    record["analysis_protocol"][key] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        hha._validate_protocol(record)


@pytest.mark.parametrize(
    "key",
    [
        "coordinate_data_used",
        "processdata_loaded",
        "tridx_to_publication_task_mapping_used",
    ],
)
def test_hha_protocol_negative_flags(
    key,
):
    record = _hha_record()

    record["analysis_protocol"][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        hha._validate_protocol(record)


# ============================================================
# HHA PAIR VALIDATION
# ============================================================


def test_hha_pair_coverage_drift():
    record = _hha_record()

    record["pair_shared_recording_counts"] = {}

    with pytest.raises(
        BenchmarkIntegrityError,
        match="pair coverage",
    ):
        hha._validate_pairs(record)


@pytest.mark.parametrize(
    "pairs",
    [
        None,
        [],
        [{}],
    ],
)
def test_hha_pair_inventory_count(pairs):
    record = _hha_record()
    record["pair_results"] = pairs

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly six",
    ):
        hha._validate_pairs(record)


def test_hha_pair_row_mapping():
    record = _hha_record()

    record["pair_results"][0] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="pair result is malformed",
    ):
        hha._validate_pairs(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "left_labeller_id",
            "1",
        ),
        (
            "right_labeller_id",
            None,
        ),
    ],
)
def test_hha_pair_id_type(
    field,
    value,
):
    record = _hha_record()

    record["pair_results"][0][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="ids must be integers",
    ):
        hha._validate_pairs(record)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (
            0,
            2,
        ),
        (
            2,
            1,
        ),
        (
            2,
            2,
        ),
    ],
)
def test_hha_pair_order(
    left,
    right,
):
    record = _hha_record()

    record["pair_results"][0]["left_labeller_id"] = left

    record["pair_results"][0]["right_labeller_id"] = right

    with pytest.raises(
        BenchmarkIntegrityError,
        match="pair order",
    ):
        hha._validate_pairs(record)


def test_hha_pair_unknown_identity():
    record = _hha_record()

    record["pair_results"][0]["left_labeller_id"] = 1

    record["pair_results"][0]["right_labeller_id"] = 99

    with pytest.raises(
        BenchmarkIntegrityError,
        match="pair set drifted",
    ):
        hha._validate_pairs(record)


def test_hha_pair_duplicate_identity():
    record = _hha_record()

    record["pair_results"][1]["left_labeller_id"] = 1

    record["pair_results"][1]["right_labeller_id"] = 2

    with pytest.raises(
        BenchmarkIntegrityError,
        match="pair set drifted",
    ):
        hha._validate_pairs(record)


def test_hha_pair_shared_count():
    record = _hha_record()

    record["pair_results"][0]["shared_recording_count"] = 99

    with pytest.raises(
        BenchmarkIntegrityError,
        match="coverage",
    ):
        hha._validate_pairs(record)


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        ["PrIdx_1_TrIdx_1"],
    ],
)
def test_hha_pair_shared_recordings_shape(
    value,
):
    record = _hha_record()

    record["pair_results"][0]["shared_recordings"] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="shared recordings drifted",
    ):
        hha._validate_pairs(record)


def test_hha_pair_widened_recording():
    record = _hha_record()

    record["pair_results"][0]["shared_recordings"][0] = "PrIdx_999_TrIdx_999"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="widened beyond reviewed",
    ):
        hha._validate_pairs(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "n_aligned_samples",
            "bad",
        ),
        (
            "n_pairwise_clearly_labelled_samples",
            None,
        ),
    ],
)
def test_hha_pair_sample_count_type(
    field,
    value,
):
    record = _hha_record()

    record["pair_results"][0][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sample counts must be integers",
    ):
        hha._validate_pairs(record)


@pytest.mark.parametrize(
    ("n_all", "n_clear"),
    [
        (
            100,
            0,
        ),
        (
            100,
            101,
        ),
    ],
)
def test_hha_pair_sample_count_range(
    n_all,
    n_clear,
):
    record = _hha_record()

    pair = record["pair_results"][0]

    pair["n_aligned_samples"] = n_all

    pair["n_pairwise_clearly_labelled_samples"] = n_clear

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sample counts are invalid",
    ):
        hha._validate_pairs(record)


def test_hha_pair_clear_fraction_inconsistent():
    record = _hha_record()

    record["pair_results"][0]["pairwise_clearly_labelled_fraction"] = 0.1

    with pytest.raises(
        BenchmarkIntegrityError,
        match="clear fraction is inconsistent",
    ):
        hha._validate_pairs(record)


def test_hha_pair_sample_all_mapping():
    record = _hha_record()

    record["pair_results"][0]["sample_all_labels"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        hha._validate_pairs(record)


def test_hha_pair_sample_clear_mapping():
    record = _hha_record()

    record["pair_results"][0]["sample_pairwise_clearly_labelled"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        hha._validate_pairs(record)


def test_hha_pair_event_mapping():
    record = _hha_record()

    record["pair_results"][0]["event_agreement"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        hha._validate_pairs(record)


def test_hha_pair_left_event_mapping():
    record = _hha_record()

    record["pair_results"][0]["event_agreement"]["left_as_reference"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        hha._validate_pairs(record)


@pytest.mark.parametrize(
    ("left_field", "right_field"),
    [
        (
            "precision",
            "recall",
        ),
        (
            "recall",
            "precision",
        ),
        (
            "false_positive",
            "false_negative",
        ),
        (
            "false_negative",
            "false_positive",
        ),
    ],
)
def test_hha_pair_symmetry(
    left_field,
    right_field,
):
    record = _hha_record()

    record["pair_results"][0]["event_agreement"]["left_as_reference"][left_field] = -999

    with pytest.raises(
        BenchmarkIntegrityError,
        match="symmetry",
    ):
        hha._validate_pairs(record)


# ============================================================
# HHA BOUNDARIES + FINAL VALIDATOR
# ============================================================


def test_hha_positive_boundary_required():
    record = _hha_record()

    record["scientific_boundary"][
        "human_human_agreement_created_for_distributed_overlap_subset"
    ] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        hha._validate_boundaries(record)


@pytest.mark.parametrize(
    "key",
    [
        "full_distributed_labeldata_hha_created",
        "task_stratified_hha_created",
        "gaze_coordinate_validation_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "complete_file_to_publication_task_mapping_verified",
        "quarantine_exit_authorized",
        "new_model_performance_claim_created",
    ],
)
def test_hha_scientific_boundary_closed(
    key,
):
    record = _hha_record()

    record["scientific_boundary"][key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        hha._validate_boundaries(record)


def test_hha_raw_bytes_not_retained():
    record = _hha_record()

    record["raw_dataset_bytes_retained"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        hha._validate_boundaries(record)


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
            "reviewed_on",
            "1900-01-01",
            "review date",
        ),
        (
            "evidence_fingerprint_sha256",
            "0" * 64,
            "stored evidence fingerprint",
        ),
    ],
)
def test_hha_top_level_identity(
    field,
    value,
    message,
):
    record = _hha_record()

    record[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        hha.validate_gaze_in_wild_overlap_hha_evidence(record)


def test_hha_recomputed_fingerprint_guard(
    monkeypatch,
):
    record = _hha_record()

    monkeypatch.setattr(
        hha,
        "evidence_fingerprint",
        lambda value: "0" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="recomputed evidence fingerprint",
    ):
        hha.validate_gaze_in_wild_overlap_hha_evidence(record)


@pytest.mark.parametrize(
    "key",
    list(hha.EXPECTED_BINDING),
)
def test_hha_source_binding_contract(
    monkeypatch,
    key,
):
    record = _hha_record()

    monkeypatch.setattr(
        hha,
        "evidence_fingerprint",
        lambda value: hha.EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    )

    record["source_binding"][key] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source binding",
    ):
        hha.validate_gaze_in_wild_overlap_hha_evidence(record)


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        "bad",
    ],
)
def test_hha_limitations_shape(
    monkeypatch,
    value,
):
    record = _hha_record()

    monkeypatch.setattr(
        hha,
        "evidence_fingerprint",
        lambda data: hha.EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    )

    record["limitations"] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="limitations must remain explicit",
    ):
        hha.validate_gaze_in_wild_overlap_hha_evidence(record)


@pytest.mark.parametrize(
    "phrase",
    [
        "no publication task-name mapping",
        "not gazeforge model validation",
        "no gaze coordinates",
        "gp3",
    ],
)
def test_hha_required_limitation_phrase(
    monkeypatch,
    phrase,
):
    record = _hha_record()

    monkeypatch.setattr(
        hha,
        "evidence_fingerprint",
        lambda data: hha.EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    )

    record["limitations"] = [
        item
        if phrase not in item.lower()
        else item.lower().replace(
            phrase,
            "removed phrase",
        )
        for item in record["limitations"]
    ]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="limitation",
    ):
        hha.validate_gaze_in_wild_overlap_hha_evidence(record)
