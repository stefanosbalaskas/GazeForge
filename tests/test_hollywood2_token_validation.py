import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from gazeforge.benchmarks import BenchmarkDatasetCard, benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.hollywood2_token_validation import (
    HOLLYWOOD2_ANNOTATION_PROVENANCE_FINGERPRINT,
    HOLLYWOOD2_AUTHORITATIVE_EVIDENCE_FINGERPRINT,
    HOLLYWOOD2_CANONICAL_SOURCE_TOKENS,
    HOLLYWOOD2_GIN_COMMIT,
    HOLLYWOOD2_GIN_HISTORY_EVIDENCE_FINGERPRINT,
    Hollywood2SourceTokenPreparedBenchmark,
    attach_hollywood2_source_tokens,
    authorization_fingerprint,
    hollywood2_source_token_from_filename,
    load_hollywood2_source_token_analysis_authorization,
    run_hollywood2_source_token_validation,
    validate_hollywood2_source_token_validation_report,
)

AUTH_PATH = Path(
    "validation/governance/hollywood2-source-token-analysis-authorization-v1.json"
)


def test_committed_hollywood2_source_token_authorization_is_self_bound():
    authorization = load_hollywood2_source_token_analysis_authorization(AUTH_PATH)
    payload = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    assert authorization.decision == "authorized"
    assert payload["authorization_fingerprint_sha256"] == authorization_fingerprint(payload)
    assert authorization.raw_source_redistribution_authorized is False
    assert authorization.participant_identity_mapping_verified is False
    assert authorization.participant_generalization_claim_authorized is False


def test_hollywood2_source_token_authorization_cannot_promote_participant_mapping():
    authorization = load_hollywood2_source_token_analysis_authorization(AUTH_PATH)
    with pytest.raises(BenchmarkIntegrityError, match="unresolved rights"):
        replace(authorization, participant_identity_mapping_verified=True)


def test_hollywood2_source_token_filename_semantics_are_opaque_and_strict():
    assert hollywood2_source_token_from_filename("001_actioncliptest00003.arff") == "001"
    assert hollywood2_source_token_from_filename(Path("019_clip_handlabels.arff")) == "019"
    with pytest.raises(SchemaError, match="three-digit token"):
        hollywood2_source_token_from_filename("participant01_clip.arff")


def test_attach_hollywood2_source_tokens_does_not_resolve_participants():
    source = pd.DataFrame(
        {
            "participant_id": ["__unresolved__", "__unresolved__"],
            "source_file": ["001_clip_a.arff", "019_clip_b.arff"],
        }
    )
    out = attach_hollywood2_source_tokens(source)
    assert out["source_token"].tolist() == ["001", "019"]
    assert set(out["participant_id"]) == {"__unresolved__"}


def _synthetic_prepared() -> Hollywood2SourceTokenPreparedBenchmark:
    rows: list[dict[str, object]] = []
    labels = ["fixation", "fixation", "saccade", "saccade", "pursuit", "noise"] * 4
    for token_index, token in enumerate(HOLLYWOOD2_CANONICAL_SOURCE_TOKENS):
        for sample, label in enumerate(labels):
            rows.append(
                {
                    "participant_id": "__unresolved__",
                    "trial_id": f"test/clip_{token}/{token}_clip",
                    "timestamp_ms": sample * (1000.0 / 60.0),
                    "x_px": float(100 + 8 * sample + token_index),
                    "y_px": float(200 + (sample % 5) * 3),
                    "event_label": label,
                    "source_token": token,
                }
            )
    data = pd.DataFrame(rows)
    card = BenchmarkDatasetCard(
        name="Hollywood2EM",
        version=HOLLYWOOD2_GIN_COMMIT,
        source="https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git",
        license="exact terms unresolved; aggregate synthetic test only",
        task="sample-level eye-movement event classification",
        sampling_rates_hz=[500.0, 60.0],
        participant_count=None,
        stimulus_count=56,
        split_unit="canonical_file_subject_token",
        validation_scope="external-empirical-source-token-held-out",
        annotation_origin="human-assisted",
        sampling_origin="resampled",
        reference_strength="derived-human-reference",
    )
    preparation_report = {
        "scope": "hollywood2-source-token-disjoint-validation-v1",
        "authoritative_evidence_fingerprint_sha256": (
            HOLLYWOOD2_AUTHORITATIVE_EVIDENCE_FINGERPRINT
        ),
        "annotation_provenance_evidence_fingerprint_sha256": (
            HOLLYWOOD2_ANNOTATION_PROVENANCE_FINGERPRINT
        ),
        "gin_history_evidence_fingerprint_sha256": (
            HOLLYWOOD2_GIN_HISTORY_EVIDENCE_FINGERPRINT
        ),
        "authorization_fingerprint_sha256": "synthetic-test",
        "analysis_sampling_rate_hz": 60.0,
        "sampling_origin": "resampled",
        "inventory": {
            "ground_truth_file_count": 697,
            "ground_truth_sample_count": 3_871_580,
            "clip_count": 56,
            "source_token_count": 16,
            "source_tokens": list(HOLLYWOOD2_CANONICAL_SOURCE_TOKENS),
        },
        "label_counts_analysis": data["event_label"].value_counts().sort_index().to_dict(),
        "participant_identity_resolved": False,
        "participant_id_value": "__unresolved__",
        "split_unit": "canonical_file_subject_token",
        "raw_source_rows_embedded": False,
        "source_filenames_embedded": False,
    }
    return Hollywood2SourceTokenPreparedBenchmark(
        data=data,
        dataset_card=card,
        preparation_report=preparation_report,
        authorization_fingerprint_sha256="synthetic-test",
    )


def test_source_token_runner_preserves_nonparticipant_claim_boundary(monkeypatch):
    prepared = _synthetic_prepared()
    monkeypatch.setattr(
        "gazeforge.hollywood2_token_validation.prepare_hollywood2_source_token_benchmark",
        lambda *args, **kwargs: prepared,
    )
    authorization = load_hollywood2_source_token_analysis_authorization(AUTH_PATH)
    run = run_hollywood2_source_token_validation(
        "unused-by-monkeypatch",
        authorization,
        target_sampling_rate_hz=60.0,
        n_splits=4,
        n_estimators=5,
        hidden_layer_sizes=(4,),
        temporal_max_iter=5,
    )
    report = validate_hollywood2_source_token_validation_report(run.report)
    boundary = report["protocol"]["scientific_boundary"]
    assert boundary["validation_split_unit"] == "canonical_file_subject_token"
    assert boundary["participant_identity_mapping_verified"] is False
    assert boundary["participant_disjoint_validation_created"] is False
    assert boundary["participant_generalization_claim"] is False
    assert boundary["raw_predictions_embedded"] is False
    assignment = pd.DataFrame(report["metrics"]["source_token_fold_assignment"])
    assert assignment["source_token"].nunique() == 16
    assert not assignment["source_token"].duplicated().any()


def test_source_token_report_validator_rejects_claim_promotion(monkeypatch):
    prepared = _synthetic_prepared()
    monkeypatch.setattr(
        "gazeforge.hollywood2_token_validation.prepare_hollywood2_source_token_benchmark",
        lambda *args, **kwargs: prepared,
    )
    authorization = load_hollywood2_source_token_analysis_authorization(AUTH_PATH)
    report = run_hollywood2_source_token_validation(
        "unused-by-monkeypatch",
        authorization,
        target_sampling_rate_hz=60.0,
        n_splits=4,
        n_estimators=3,
        hidden_layer_sizes=(4,),
        temporal_max_iter=3,
    ).report
    tampered = json.loads(json.dumps(report))
    tampered["protocol"]["scientific_boundary"]["participant_generalization_claim"] = True
    body = dict(tampered)
    body.pop("report_fingerprint_sha256")
    tampered["report_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(BenchmarkIntegrityError, match="promote"):
        validate_hollywood2_source_token_validation_report(tampered)
