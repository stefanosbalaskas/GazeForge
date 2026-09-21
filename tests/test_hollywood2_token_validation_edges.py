from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import gazeforge.hollywood2_token_validation as token_validation
from gazeforge.benchmarks import BenchmarkDatasetCard, benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.hollywood2_token_validation import (
    HOLLYWOOD2_ANNOTATION_PROVENANCE_FINGERPRINT,
    HOLLYWOOD2_AUTHORITATIVE_EVIDENCE_FINGERPRINT,
    HOLLYWOOD2_CANONICAL_SOURCE_TOKENS,
    HOLLYWOOD2_GIN_COMMIT,
    HOLLYWOOD2_GIN_HISTORY_EVIDENCE_FINGERPRINT,
    HOLLYWOOD2_GIN_REPOSITORY,
    Hollywood2SourceTokenAnalysisAuthorization,
    Hollywood2SourceTokenPreparedBenchmark,
    _normalise_repository_url,
    _relative_clip_id,
    _verify_pinned_checkout,
    attach_hollywood2_source_tokens,
    authorization_fingerprint,
    load_hollywood2_source_token_analysis_authorization,
    prepare_hollywood2_source_token_benchmark,
    run_hollywood2_source_token_validation,
    validate_hollywood2_source_token_validation_report,
)

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = (
    ROOT
    / "validation"
    / "governance"
    / "hollywood2-source-token-analysis-authorization-v1.json"
)


def _authorization() -> Hollywood2SourceTokenAnalysisAuthorization:
    return load_hollywood2_source_token_analysis_authorization(AUTH_PATH)


def _refingerprint_authorization(payload: dict) -> dict:
    payload["authorization_fingerprint_sha256"] = authorization_fingerprint(payload)
    return payload


def _prepared_table() -> tuple[pd.DataFrame, dict]:
    rows = []
    for token_index, token in enumerate(HOLLYWOOD2_CANONICAL_SOURCE_TOKENS):
        rows.extend(
            [
                {
                    "participant_id": "__unresolved__",
                    "trial_id": f"test/clip-{token}/{token}_a",
                    "event_label": "fixation",
                    "source_token": token,
                    "timestamp_ms": float(token_index * 10),
                    "x_px": float(token_index),
                    "y_px": float(token_index + 1),
                },
                {
                    "participant_id": "__unresolved__",
                    "trial_id": f"test/clip-{token}/{token}_b",
                    "event_label": "saccade",
                    "source_token": token,
                    "timestamp_ms": float(token_index * 10 + 1),
                    "x_px": float(token_index + 2),
                    "y_px": float(token_index + 3),
                },
            ]
        )
    data = pd.DataFrame(rows)
    inventory = {
        "ground_truth_file_count": 697,
        "ground_truth_sample_count": 3_871_580,
        "clip_count": 56,
        "source_token_count": len(HOLLYWOOD2_CANONICAL_SOURCE_TOKENS),
        "source_tokens": list(HOLLYWOOD2_CANONICAL_SOURCE_TOKENS),
        "source_rate_min_hz": 500.0,
        "source_rate_median_hz": 500.0,
        "source_rate_max_hz": 500.0,
        "resampling": None,
    }
    return data, inventory


def _prepared_benchmark(tokens: tuple[str, ...] = ("001", "002")):
    rows = []
    for token in tokens:
        rows.extend(
            [
                {
                    "participant_id": "__unresolved__",
                    "trial_id": f"{token}-a",
                    "timestamp_ms": 0.0,
                    "x_px": 0.0,
                    "y_px": 0.0,
                    "event_label": "fixation",
                    "source_token": token,
                },
                {
                    "participant_id": "__unresolved__",
                    "trial_id": f"{token}-b",
                    "timestamp_ms": 16.0,
                    "x_px": 1.0,
                    "y_px": 1.0,
                    "event_label": "saccade",
                    "source_token": token,
                },
            ]
        )
    data = pd.DataFrame(rows)
    card = BenchmarkDatasetCard(
        name="Hollywood2EM",
        version=HOLLYWOOD2_GIN_COMMIT,
        source=HOLLYWOOD2_GIN_REPOSITORY,
        license="synthetic test",
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
    preparation = {
        "analysis_sampling_rate_hz": 60.0,
        "label_counts_analysis": {"fixation": len(tokens), "saccade": len(tokens)},
    }
    return Hollywood2SourceTokenPreparedBenchmark(
        data=data,
        dataset_card=card,
        preparation_report=preparation,
        authorization_fingerprint_sha256="synthetic",
    )


def _valid_report() -> dict:
    prepared, inventory = _prepared_table()
    card = BenchmarkDatasetCard(
        name="Hollywood2EM",
        version=HOLLYWOOD2_GIN_COMMIT,
        source=HOLLYWOOD2_GIN_REPOSITORY,
        license="synthetic validation fixture",
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
    protocol = {
        "scope": "hollywood2-source-token-disjoint-validation-v1",
        "preparation": {
            "authoritative_evidence_fingerprint_sha256": (
                HOLLYWOOD2_AUTHORITATIVE_EVIDENCE_FINGERPRINT
            ),
            "annotation_provenance_evidence_fingerprint_sha256": (
                HOLLYWOOD2_ANNOTATION_PROVENANCE_FINGERPRINT
            ),
            "gin_history_evidence_fingerprint_sha256": (
                HOLLYWOOD2_GIN_HISTORY_EVIDENCE_FINGERPRINT
            ),
            "inventory": inventory,
            "participant_identity_resolved": False,
        },
        "scientific_boundary": {
            "validation_split_unit": "canonical_file_subject_token",
            "source_token_to_participant_mapping_verified": False,
            "participant_identity_mapping_verified": False,
            "participant_disjoint_validation_created": False,
            "participant_generalization_claim": False,
            "cross_dataset_validation_created": False,
            "exact_license_identifier_verified": False,
            "exact_license_text_verified": False,
            "dataset_specific_analysis_terms_verified": False,
            "operator_authorized_nonredistributive_analysis": True,
            "raw_source_redistributed_by_gazeforge": False,
            "raw_predictions_embedded": False,
            "aggregate_metrics_only": True,
        },
    }
    body = {
        "benchmark": card.to_dict(),
        "metrics": {"summary": [], "analysis_rows": len(prepared)},
        "model": {"models": ["ivt"]},
        "protocol": protocol,
    }
    body["report_fingerprint_sha256"] = benchmark_fingerprint(body)
    return body


def _refingerprint_report(report: dict) -> dict:
    body = dict(report)
    body.pop("report_fingerprint_sha256", None)
    report["report_fingerprint_sha256"] = benchmark_fingerprint(body)
    return report


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"decision": "pending"}, "decision='authorized'"),
        ({"reviewer": ""}, "reviewer"),
        (
            {"authoritative_evidence_fingerprint_sha256": "0" * 64},
            "not bound to the frozen source",
        ),
        (
            {"aggregate_nonredistributive_analysis_authorized": False},
            "non-redistributive analysis was not authorized",
        ),
        (
            {"source_token_semantics_verified": False},
            "source-token semantics must be verified",
        ),
    ],
)
def test_authorization_constructor_fails_closed(changes, message):
    authorization = _authorization()

    with pytest.raises(BenchmarkIntegrityError, match=message):
        replace(authorization, **changes)


def test_authorization_fingerprint_accepts_typed_record_and_ignores_self_hash():
    authorization = _authorization()
    payload = authorization.to_dict()
    expected = authorization_fingerprint(authorization)
    payload["authorization_fingerprint_sha256"] = "ignored"

    assert authorization_fingerprint(payload) == expected
    assert authorization.notes == tuple(str(note) for note in authorization.notes)


def test_authorization_loader_rejects_missing_and_invalid_files(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_hollywood2_source_token_analysis_authorization(tmp_path / "missing.json")

    for name, raw in (("json", b"{"), ("utf8", b"\xff")):
        path = tmp_path / f"invalid-{name}.json"
        path.write_bytes(raw)
        with pytest.raises(BenchmarkIntegrityError, match="valid UTF-8 JSON"):
            load_hollywood2_source_token_analysis_authorization(path)


@pytest.mark.parametrize(
    ("mutator", "message", "refingerprint"),
    [
        (lambda p: p.update(record_type="wrong"), "record_type", False),
        (
            lambda p: p.update(scientific_boundary={}),
            "scientific boundary",
            False,
        ),
        (
            lambda p: p.pop("authorization_fingerprint_sha256"),
            "fingerprint is missing",
            False,
        ),
        (lambda p: p.update(reviewer="tampered"), "does not match content", False),
        (lambda p: p.update(notes="not-a-list"), "notes must be a JSON list", True),
        (lambda p: p.update(unknown_field=True), "authorization is invalid", True),
    ],
)
def test_authorization_loader_rejects_record_drift(
    tmp_path,
    mutator,
    message,
    refingerprint,
):
    payload = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    mutator(payload)
    if refingerprint:
        _refingerprint_authorization(payload)
    path = tmp_path / "authorization.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match=message):
        load_hollywood2_source_token_analysis_authorization(path)


def test_attach_source_tokens_requires_declared_source_column():
    with pytest.raises(SchemaError, match="Missing Hollywood2 source-file column"):
        attach_hollywood2_source_tokens(pd.DataFrame({"other": ["001_a.arff"]}))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://example.test/repo.git", "https://example.test/repo"),
        ("https://example.test/repo/", "https://example.test/repo"),
    ],
)
def test_repository_url_normalization(value, expected):
    assert _normalise_repository_url(value) == expected


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        (Path("train/clip-1/001_a.arff"), "clip-1"),
        (Path("misc/001_a.arff"), "misc"),
        (Path("001_a.arff"), "001_a"),
    ],
)
def test_relative_clip_id_contract(relative, expected):
    assert _relative_clip_id(relative) == expected


def _checkout_runner(responses):
    def run(args, **kwargs):
        key = tuple(args)
        return responses.get(
            key,
            subprocess.CompletedProcess(args, 1, stdout="", stderr="unexpected command"),
        )

    return run


def test_pinned_checkout_requires_git_checkout(tmp_path):
    with pytest.raises(BenchmarkIntegrityError, match="canonical Git checkout"):
        _verify_pinned_checkout(tmp_path)


def test_pinned_checkout_rejects_git_command_failure(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(
        token_validation.subprocess,
        "run",
        _checkout_runner(
            {
                ("git", "rev-parse", "HEAD"): subprocess.CompletedProcess(
                    ["git"], 2, stdout="", stderr="synthetic failure"
                )
            }
        ),
    )

    with pytest.raises(BenchmarkIntegrityError, match="Could not verify"):
        _verify_pinned_checkout(tmp_path)


@pytest.mark.parametrize(
    ("head", "origin", "dirty", "message"),
    [
        ("bad", HOLLYWOOD2_GIN_REPOSITORY, "", "frozen authoritative commit"),
        (
            HOLLYWOOD2_GIN_COMMIT,
            "https://example.test/not-canonical.git",
            "",
            "origin is not the canonical",
        ),
        (
            HOLLYWOOD2_GIN_COMMIT,
            HOLLYWOOD2_GIN_REPOSITORY,
            " M tracked.arff",
            "tracked modifications",
        ),
    ],
)
def test_pinned_checkout_rejects_identity_drift(
    tmp_path,
    monkeypatch,
    head,
    origin,
    dirty,
    message,
):
    (tmp_path / ".git").mkdir()
    responses = {
        ("git", "rev-parse", "HEAD"): subprocess.CompletedProcess(
            ["git"], 0, stdout=head + "\n", stderr=""
        ),
        ("git", "remote", "get-url", "origin"): subprocess.CompletedProcess(
            ["git"], 0, stdout=origin + "\n", stderr=""
        ),
        (
            "git",
            "status",
            "--porcelain",
            "--untracked-files=no",
        ): subprocess.CompletedProcess(["git"], 0, stdout=dirty + "\n", stderr=""),
    }
    monkeypatch.setattr(
        token_validation.subprocess,
        "run",
        _checkout_runner(responses),
    )

    with pytest.raises(BenchmarkIntegrityError, match=message):
        _verify_pinned_checkout(tmp_path)


def test_pinned_checkout_returns_frozen_identity(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    responses = {
        ("git", "rev-parse", "HEAD"): subprocess.CompletedProcess(
            ["git"], 0, stdout=HOLLYWOOD2_GIN_COMMIT + "\n", stderr=""
        ),
        ("git", "remote", "get-url", "origin"): subprocess.CompletedProcess(
            ["git"], 0, stdout=HOLLYWOOD2_GIN_REPOSITORY + "\n", stderr=""
        ),
        (
            "git",
            "status",
            "--porcelain",
            "--untracked-files=no",
        ): subprocess.CompletedProcess(["git"], 0, stdout="", stderr=""),
    }
    monkeypatch.setattr(
        token_validation.subprocess,
        "run",
        _checkout_runner(responses),
    )

    assert _verify_pinned_checkout(tmp_path) == {
        "repository": HOLLYWOOD2_GIN_REPOSITORY,
        "commit_sha1": HOLLYWOOD2_GIN_COMMIT,
        "tracked_tree_clean": True,
    }


def _patch_preparation_boundaries(monkeypatch, data, inventory):
    monkeypatch.setattr(
        token_validation,
        "_verify_pinned_checkout",
        lambda root: {
            "repository": HOLLYWOOD2_GIN_REPOSITORY,
            "commit_sha1": HOLLYWOOD2_GIN_COMMIT,
            "tracked_tree_clean": True,
        },
    )
    monkeypatch.setattr(
        token_validation,
        "_load_and_prepare_files",
        lambda *args, **kwargs: (data.copy(), dict(inventory)),
    )


def test_prepare_benchmark_validates_root_authorization_and_sampling_rate(
    tmp_path,
    monkeypatch,
):
    authorization = _authorization()

    with pytest.raises(TypeError, match="authorization must be"):
        prepare_hollywood2_source_token_benchmark(tmp_path, object())

    with pytest.raises(FileNotFoundError):
        prepare_hollywood2_source_token_benchmark(
            tmp_path / "missing",
            authorization,
        )

    with pytest.raises(BenchmarkIntegrityError, match="ground_truth directory"):
        prepare_hollywood2_source_token_benchmark(tmp_path, authorization)

    ground_truth = tmp_path / "ground_truth"
    ground_truth.mkdir()
    monkeypatch.setattr(
        token_validation,
        "_verify_pinned_checkout",
        lambda root: {"repository": "synthetic"},
    )
    with pytest.raises(ValueError, match="target_sampling_rate_hz"):
        prepare_hollywood2_source_token_benchmark(
            tmp_path,
            authorization,
            target_sampling_rate_hz=0,
        )


@pytest.mark.parametrize(
    ("target_rate", "expected_origin", "expected_rates", "expected_strength"),
    [
        (None, "native", [500.0], "expert-human-reference"),
        (500.0, "native", [500.0], "expert-human-reference"),
        (60.0, "resampled", [500.0, 60.0], "derived-human-reference"),
    ],
)
def test_prepare_benchmark_preserves_sampling_and_identity_contract(
    tmp_path,
    monkeypatch,
    target_rate,
    expected_origin,
    expected_rates,
    expected_strength,
):
    authorization = _authorization()
    (tmp_path / "ground_truth").mkdir()
    data, inventory = _prepared_table()
    _patch_preparation_boundaries(monkeypatch, data, inventory)

    prepared = prepare_hollywood2_source_token_benchmark(
        tmp_path,
        authorization,
        target_sampling_rate_hz=target_rate,
    )

    assert prepared.preparation_report["sampling_origin"] == expected_origin
    assert prepared.dataset_card.sampling_rates_hz == expected_rates
    assert prepared.dataset_card.reference_strength == expected_strength
    assert prepared.dataset_card.participant_count is None
    assert set(prepared.data["participant_id"]) == {"__unresolved__"}
    assert prepared.preparation_report["source_filenames_embedded"] is False


def test_prepare_benchmark_rejects_participant_promotion(tmp_path, monkeypatch):
    authorization = _authorization()
    (tmp_path / "ground_truth").mkdir()
    data, inventory = _prepared_table()
    data.loc[0, "participant_id"] = "P01"
    _patch_preparation_boundaries(monkeypatch, data, inventory)

    with pytest.raises(BenchmarkIntegrityError, match="must not materialize participant"):
        prepare_hollywood2_source_token_benchmark(tmp_path, authorization)


def test_prepare_benchmark_rejects_insufficient_labels_after_exclusion(
    tmp_path,
    monkeypatch,
):
    authorization = _authorization()
    (tmp_path / "ground_truth").mkdir()
    data, inventory = _prepared_table()
    data["event_label"] = "ambiguous"
    _patch_preparation_boundaries(monkeypatch, data, inventory)

    with pytest.raises(SchemaError, match="insufficient labelled benchmark rows"):
        prepare_hollywood2_source_token_benchmark(tmp_path, authorization)


def test_prepare_benchmark_rejects_exclusion_of_entire_source_token(
    tmp_path,
    monkeypatch,
):
    authorization = _authorization()
    (tmp_path / "ground_truth").mkdir()
    data, inventory = _prepared_table()
    first = HOLLYWOOD2_CANONICAL_SOURCE_TOKENS[0]
    data.loc[data["source_token"] == first, "event_label"] = "ambiguous"
    _patch_preparation_boundaries(monkeypatch, data, inventory)

    with pytest.raises(BenchmarkIntegrityError, match="removed an entire canonical source token"):
        prepare_hollywood2_source_token_benchmark(tmp_path, authorization)


def _mock_comparison(predictions):
    return SimpleNamespace(
        predictions=predictions,
        fold_metrics=pd.DataFrame({"model": ["ivt"], "macro_f1": [0.5]}),
        summary=pd.DataFrame({"model": ["ivt"], "macro_f1": [0.5]}),
        design={
            "calibration_bins": 5,
            "include_event_level_metrics": True,
            "event_group_cols": ["participant_id", "trial_id"],
            "event_min_iou": 0.5,
            "event_excluded_labels": [],
            "models": ["ivt"],
        },
    )


def _patch_runner_summaries(monkeypatch, comparison):
    monkeypatch.setattr(
        token_validation,
        "compare_event_models_grouped",
        lambda *args, **kwargs: comparison,
    )
    monkeypatch.setattr(
        token_validation,
        "paired_model_metric_differences",
        lambda frame: SimpleNamespace(
            design={"paired": True},
            summary=pd.DataFrame(),
            deltas=pd.DataFrame(),
        ),
    )
    monkeypatch.setattr(
        token_validation,
        "summarize_event_predictions_by_stratum",
        lambda *args, **kwargs: SimpleNamespace(
            design={"stratified": True},
            summary=pd.DataFrame(),
            fold_metrics=pd.DataFrame(),
        ),
    )


def test_source_token_runner_requires_at_least_two_tokens(monkeypatch):
    prepared = _prepared_benchmark(("001",))
    monkeypatch.setattr(
        token_validation,
        "prepare_hollywood2_source_token_benchmark",
        lambda *args, **kwargs: prepared,
    )

    with pytest.raises(SchemaError, match="At least two source-token folds"):
        run_hollywood2_source_token_validation(
            "unused",
            _authorization(),
            n_splits=4,
        )


@pytest.mark.parametrize("mode", ["missing", "duplicate"])
def test_source_token_runner_rejects_invalid_fold_accountability(monkeypatch, mode):
    prepared = _prepared_benchmark()
    monkeypatch.setattr(
        token_validation,
        "prepare_hollywood2_source_token_benchmark",
        lambda *args, **kwargs: prepared,
    )
    if mode == "missing":
        predictions = pd.DataFrame(
            {
                "source_token": ["001"],
                "validation_fold": [0],
            }
        )
        message = "does not cover every canonical token"
    else:
        predictions = pd.DataFrame(
            {
                "source_token": ["001", "001", "002"],
                "validation_fold": [0, 1, 0],
            }
        )
        message = "appeared in more than one held-out fold"
    _patch_runner_summaries(monkeypatch, _mock_comparison(predictions))

    with pytest.raises(BenchmarkIntegrityError, match=message):
        run_hollywood2_source_token_validation(
            "unused",
            _authorization(),
            n_splits=2,
        )


def test_report_validator_accepts_json_path(tmp_path):
    report = _valid_report()
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    assert validate_hollywood2_source_token_validation_report(path) == report


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"{", "Could not load"),
        (b"[]", "must be one JSON object"),
        (b"\xff", "Could not load"),
    ],
)
def test_report_validator_rejects_invalid_serialized_input(tmp_path, raw, message):
    path = tmp_path / "report.json"
    path.write_bytes(raw)

    with pytest.raises(BenchmarkIntegrityError, match=message):
        validate_hollywood2_source_token_validation_report(path)


def test_report_validator_rejects_missing_file(tmp_path):
    with pytest.raises(BenchmarkIntegrityError, match="Could not load"):
        validate_hollywood2_source_token_validation_report(tmp_path / "missing.json")


def _mutate_report(report, path, value):
    target = report
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return _refingerprint_report(report)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("benchmark",), [], "structure is incomplete"),
        (("benchmark", "name"), "Other", "dataset identity drifted"),
        (("benchmark", "version"), "bad", "revision drifted"),
        (("benchmark", "split_unit"), "participant", "retain the source-token split"),
        (("protocol", "scope"), "bad", "scope drifted"),
        (("protocol", "scientific_boundary"), [], "scientific boundary is missing"),
        (
            ("protocol", "scientific_boundary", "validation_split_unit"),
            "participant",
            "validation split semantics drifted",
        ),
        (
            (
                "protocol",
                "scientific_boundary",
                "participant_generalization_claim",
            ),
            True,
            "attempted to promote",
        ),
        (
            (
                "protocol",
                "scientific_boundary",
                "operator_authorized_nonredistributive_analysis",
            ),
            False,
            "missing operator authorization",
        ),
        (
            ("protocol", "scientific_boundary", "aggregate_metrics_only"),
            False,
            "remain aggregate-only",
        ),
        (("protocol", "preparation"), [], "preparation provenance is missing"),
        (
            (
                "protocol",
                "preparation",
                "authoritative_evidence_fingerprint_sha256",
            ),
            "bad",
            "not bound to expected",
        ),
        (("protocol", "preparation", "inventory"), [], "source inventory is missing"),
        (
            ("protocol", "preparation", "inventory", "ground_truth_file_count"),
            1,
            "file count drifted",
        ),
        (
            ("protocol", "preparation", "inventory", "ground_truth_sample_count"),
            1,
            "sample count drifted",
        ),
        (
            ("protocol", "preparation", "inventory", "source_tokens"),
            [],
            "source-token inventory drifted",
        ),
        (
            ("protocol", "preparation", "participant_identity_resolved"),
            True,
            "preserve unresolved participant identity",
        ),
    ],
)
def test_report_validator_rejects_scientific_and_provenance_drift(
    path,
    value,
    message,
):
    report = _valid_report()
    _mutate_report(report, path, value)

    with pytest.raises(BenchmarkIntegrityError, match=message):
        validate_hollywood2_source_token_validation_report(report)


def test_report_validator_rejects_missing_or_mismatched_fingerprint():
    report = _valid_report()
    report["report_fingerprint_sha256"] = ""

    with pytest.raises(BenchmarkIntegrityError, match="fingerprint does not match"):
        validate_hollywood2_source_token_validation_report(report)

    report = _valid_report()
    report["model"]["tamper"] = True
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint does not match"):
        validate_hollywood2_source_token_validation_report(report)


def test_report_validator_rejects_raw_prediction_or_sample_payloads():
    for key in ("predictions", "raw_rows", "source_rows", "samples"):
        report = _valid_report()
        report["metrics"][key] = []
        _refingerprint_report(report)
        with pytest.raises(BenchmarkIntegrityError, match="must not embed raw"):
            validate_hollywood2_source_token_validation_report(report)
