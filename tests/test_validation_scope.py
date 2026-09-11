import json
from pathlib import Path

import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError
from gazeforge.validation_scope import (
    assert_validation_scope,
    build_validation_scope_certificate,
    derive_validation_scope,
    freeze_validation_scope_certificate,
    validate_validation_scope_certificate,
)


def frame(rows):
    return pd.DataFrame(
        rows,
        columns=["participant_id", "trial_id", "sample_index", "dataset_id", "value"],
    )


def test_sample_overlap_derives_sample_level():
    train = frame([("P1", "T1", 0, "D1", 1.0), ("P1", "T1", 1, "D1", 2.0)])
    test = frame([("P1", "T1", 1, "D1", 3.0), ("P1", "T1", 2, "D1", 4.0)])
    result = derive_validation_scope(train, test)
    assert result.scope == "sample_level"
    assert result.counts["n_overlapping_samples"] == 1
    assert result.counts["n_overlapping_trials"] == 1
    assert result.counts["n_overlapping_participants"] == 1


def test_trial_overlap_without_sample_overlap_derives_trial_level():
    train = frame([("P1", "T1", 0, "D1", 1.0), ("P1", "T1", 1, "D1", 2.0)])
    test = frame([("P1", "T1", 2, "D1", 3.0), ("P1", "T1", 3, "D1", 4.0)])
    result = derive_validation_scope(train, test)
    assert result.scope == "trial_level"
    assert result.counts["n_overlapping_samples"] == 0
    assert result.counts["n_overlapping_trials"] == 1


def test_same_participant_different_trials_derives_participant_within():
    train = frame([("P1", "T1", 0, "D1", 1.0), ("P1", "T1", 1, "D1", 2.0)])
    test = frame([("P1", "T2", 0, "D1", 3.0), ("P1", "T2", 1, "D1", 4.0)])
    result = derive_validation_scope(train, test)
    assert result.scope == "participant_within"
    assert result.counts["n_overlapping_trials"] == 0
    assert result.counts["n_overlapping_participants"] == 1


def test_disjoint_participants_same_dataset_derives_participant_disjoint():
    train = frame([("P1", "T1", 0, "D1", 1.0), ("P1", "T1", 1, "D1", 2.0)])
    test = frame([("P2", "T1", 0, "D1", 3.0), ("P2", "T1", 1, "D1", 4.0)])
    result = derive_validation_scope(train, test)
    assert result.scope == "participant_disjoint"
    assert result.dataset_metadata_available is True
    assert result.counts["n_overlapping_participants"] == 0
    assert result.counts["n_overlapping_datasets"] == 1


def test_disjoint_participants_and_datasets_derives_dataset_external():
    train = frame([("P1", "T1", 0, "D1", 1.0), ("P1", "T1", 1, "D1", 2.0)])
    test = frame([("P2", "T1", 0, "D2", 3.0), ("P2", "T1", 1, "D2", 4.0)])
    result = derive_validation_scope(train, test)
    assert result.scope == "dataset_external"
    assert result.counts["n_overlapping_participants"] == 0
    assert result.counts["n_overlapping_datasets"] == 0


def test_different_dataset_labels_cannot_hide_participant_overlap():
    train = frame([("P1", "T1", 0, "D1", 1.0)])
    test = frame([("P1", "T2", 0, "D2", 2.0)])
    result = derive_validation_scope(train, test)
    assert result.scope == "participant_within"
    assert result.counts["n_overlapping_datasets"] == 0
    assert result.counts["n_overlapping_participants"] == 1


def test_missing_dataset_column_caps_scope_at_participant_disjoint():
    train = frame([("P1", "T1", 0, "D1", 1.0)]).drop(columns="dataset_id")
    test = frame([("P2", "T1", 0, "D2", 2.0)]).drop(columns="dataset_id")
    result = derive_validation_scope(train, test)
    assert result.scope == "participant_disjoint"
    assert result.dataset_metadata_available is False
    assert result.counts["n_overlapping_datasets"] is None


@pytest.mark.parametrize("bad_value", [None, "", "   "])
def test_incomplete_dataset_identity_caps_scope_at_participant_disjoint(bad_value):
    train = frame([("P1", "T1", 0, "D1", 1.0)])
    test = frame([("P2", "T1", 0, bad_value, 2.0)])
    result = derive_validation_scope(train, test)
    assert result.scope == "participant_disjoint"
    assert result.dataset_metadata_available is False


@pytest.mark.parametrize("column", ["participant_id", "trial_id", "sample_index"])
def test_missing_required_identity_column_fails_closed(column):
    train = frame([("P1", "T1", 0, "D1", 1.0)]).drop(columns=column)
    test = frame([("P2", "T2", 0, "D2", 2.0)])
    with pytest.raises(SchemaError, match="missing identity columns"):
        derive_validation_scope(train, test)


@pytest.mark.parametrize("bad_value", [None, "", "   "])
def test_missing_or_blank_required_identity_fails_closed(bad_value):
    train = frame([(bad_value, "T1", 0, "D1", 1.0)])
    test = frame([("P2", "T2", 0, "D2", 2.0)])
    with pytest.raises(SchemaError, match="missing or blank identity values"):
        derive_validation_scope(train, test)


def test_empty_partition_fails_closed():
    columns = ["participant_id", "trial_id", "sample_index", "dataset_id", "value"]
    train = pd.DataFrame(columns=columns)
    test = frame([("P2", "T2", 0, "D2", 2.0)])
    with pytest.raises(SchemaError, match="at least one row"):
        derive_validation_scope(train, test)


def test_duplicate_sample_identity_fails_closed():
    train = frame([("P1", "T1", 0, "D1", 1.0), ("P1", "T1", 0, "D1", 2.0)])
    test = frame([("P2", "T2", 0, "D2", 3.0)])
    with pytest.raises(SchemaError, match="duplicate sample identity keys"):
        derive_validation_scope(train, test)


def test_minimum_scope_blocks_subject_generalization_when_participant_overlaps():
    train = frame([("P1", "T1", 0, "D1", 1.0)])
    test = frame([("P1", "T2", 0, "D1", 2.0)])
    assessment = derive_validation_scope(train, test)
    with pytest.raises(SchemaError, match="actual=participant_within"):
        assert_validation_scope(assessment, "participant_disjoint")
    with pytest.raises(SchemaError, match="required=participant_disjoint"):
        build_validation_scope_certificate(
            train, test, minimum_scope="participant_disjoint"
        )


def test_unknown_minimum_scope_is_rejected():
    train = frame([("P1", "T1", 0, "D1", 1.0)])
    test = frame([("P2", "T2", 0, "D2", 2.0)])
    with pytest.raises(ValueError, match="Unknown validation scope"):
        build_validation_scope_certificate(train, test, minimum_scope="magic")


def test_certificate_is_deterministic_replayable_and_does_not_store_raw_ids():
    train = frame([("P1", "T1", 0, "D1", 1.0), ("P1", "T1", 1, "D1", 2.0)])
    test = frame([("P2", "T2", 0, "D2", 3.0), ("P2", "T2", 1, "D2", 4.0)])
    first = build_validation_scope_certificate(
        train, test, minimum_scope="participant_disjoint"
    )
    second = build_validation_scope_certificate(
        train, test, minimum_scope="participant_disjoint"
    )
    assert first == second
    assert first["assessment"]["scope"] == "dataset_external"
    assert first["claim_boundary"]["participant_disjoint_evaluation"] is True
    assert first["claim_boundary"]["subject_generalization_eligible"] is True
    assert first["claim_boundary"]["cross_dataset_generalization_eligible"] is True
    assert first["claim_boundary"]["identity_semantics_verified"] is False
    assert first["claim_boundary"]["establishes_model_performance"] is False
    serialized = json.dumps(first, sort_keys=True)
    assert '"P1"' not in serialized
    assert '"P2"' not in serialized
    assert validate_validation_scope_certificate(first, train, test)


def test_participant_within_certificate_closes_generalization_claims():
    train = frame([("P1", "T1", 0, "D1", 1.0)])
    test = frame([("P1", "T2", 0, "D1", 2.0)])
    certificate = build_validation_scope_certificate(train, test)
    claims = certificate["claim_boundary"]
    assert certificate["assessment"]["scope"] == "participant_within"
    assert claims["trial_disjoint_evaluation"] is True
    assert claims["participant_disjoint_evaluation"] is False
    assert claims["dataset_external_evaluation"] is False
    assert claims["subject_generalization_eligible"] is False
    assert claims["cross_dataset_generalization_eligible"] is False


def test_resigned_claim_promotion_cannot_replay():
    train = frame([("P1", "T1", 0, "D1", 1.0)])
    test = frame([("P1", "T2", 0, "D1", 2.0)])
    certificate = build_validation_scope_certificate(train, test)
    promoted = dict(certificate)
    promoted["claim_boundary"] = dict(certificate["claim_boundary"])
    promoted["claim_boundary"]["subject_generalization_eligible"] = True
    body = {k: v for k, v in promoted.items() if k != "certificate_fingerprint_sha256"}
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(ValueError, match="does not replay"):
        validate_validation_scope_certificate(promoted, train, test)


def test_resigned_scope_promotion_cannot_replay():
    train = frame([("P1", "T1", 0, "D1", 1.0)])
    test = frame([("P1", "T2", 0, "D1", 2.0)])
    certificate = build_validation_scope_certificate(train, test)
    promoted = dict(certificate)
    promoted["assessment"] = dict(certificate["assessment"])
    promoted["assessment"]["scope"] = "participant_disjoint"
    promoted["assessment"]["scope_rank"] = 3
    body = {k: v for k, v in promoted.items() if k != "certificate_fingerprint_sha256"}
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(ValueError, match="does not replay"):
        validate_validation_scope_certificate(promoted, train, test)


def test_data_mutation_invalidates_certificate():
    train = frame([("P1", "T1", 0, "D1", 1.0)])
    test = frame([("P2", "T2", 0, "D1", 2.0)])
    certificate = build_validation_scope_certificate(train, test)
    changed = test.copy()
    changed.loc[0, "value"] = 99.0
    with pytest.raises(ValueError, match="does not replay"):
        validate_validation_scope_certificate(certificate, train, changed)


def test_freeze_requires_exact_replay_and_protects_existing_file(tmp_path: Path):
    train = frame([("P1", "T1", 0, "D1", 1.0)])
    test = frame([("P2", "T2", 0, "D1", 2.0)])
    certificate = build_validation_scope_certificate(train, test)
    target = tmp_path / "scope-certificate.json"
    written = freeze_validation_scope_certificate(
        certificate, target, train=train, test=test
    )
    assert written == target
    assert target.exists()
    with pytest.raises(FileExistsError):
        freeze_validation_scope_certificate(
            certificate, target, train=train, test=test
        )


def test_promoted_certificate_is_rejected_before_persistence(tmp_path: Path):
    train = frame([("P1", "T1", 0, "D1", 1.0)])
    test = frame([("P1", "T2", 0, "D1", 2.0)])
    certificate = build_validation_scope_certificate(train, test)
    promoted = dict(certificate)
    promoted["claim_boundary"] = dict(certificate["claim_boundary"])
    promoted["claim_boundary"]["participant_disjoint_evaluation"] = True
    body = {k: v for k, v in promoted.items() if k != "certificate_fingerprint_sha256"}
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    target = tmp_path / "promoted.json"
    with pytest.raises(ValueError, match="does not replay"):
        freeze_validation_scope_certificate(
            promoted, target, train=train, test=test
        )
    assert not target.exists()


def test_custom_identity_columns_are_supported():
    train = pd.DataFrame(
        {
            "person": ["A", "A"],
            "run": ["R1", "R1"],
            "sample": [0, 1],
            "corpus": ["C1", "C1"],
        }
    )
    test = pd.DataFrame(
        {
            "person": ["B", "B"],
            "run": ["R2", "R2"],
            "sample": [0, 1],
            "corpus": ["C2", "C2"],
        }
    )
    result = derive_validation_scope(
        train,
        test,
        participant_col="person",
        trial_col="run",
        sample_col="sample",
        dataset_col="corpus",
    )
    assert result.scope == "dataset_external"


def test_explicit_none_dataset_column_caps_at_participant_disjoint():
    train = frame([("P1", "T1", 0, "D1", 1.0)])
    test = frame([("P2", "T2", 0, "D2", 2.0)])
    result = derive_validation_scope(train, test, dataset_col=None)
    assert result.scope == "participant_disjoint"
    assert result.dataset_metadata_available is False
