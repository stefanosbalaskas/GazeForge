from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from test_visus_protocol_validation import _case

import gazeforge.visus_protocol_validation as validation
from gazeforge.exceptions import BenchmarkIntegrityError


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    root = tmp_path_factory.mktemp("visus-protocol-validation-coverage")

    run, batch, reference = _case(root)

    return {
        "root": root,
        "run": run,
        "batch": batch,
        "reference": reference,
    }


def _identity() -> dict[str, str]:
    return {
        key: character * 64
        for key, character in zip(
            validation._SOURCE_KEYS,
            ("a", "b", "c"),
            strict=True,
        )
    }


# ============================================================
# FINGERPRINT + SOURCE IDENTITY
# ============================================================


def test_revalidate_fingerprint_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint does not revalidate",
    ):
        validation._revalidate_fingerprint(
            {
                "x": 1,
                "fingerprint": "bad",
            },
            "fingerprint",
            label="fixture",
        )


def test_source_identity_requires_mapping():
    batch = SimpleNamespace(
        protocol_run=SimpleNamespace(
            protocol={
                "source": None,
            }
        )
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity is missing",
    ):
        validation._source_identity(batch)


def test_source_identity_requires_complete_hashes():
    source = _identity()
    source["source_manifest_fingerprint_sha256"] = "bad"

    batch = SimpleNamespace(
        protocol_run=SimpleNamespace(
            protocol={
                "source": source,
            }
        )
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source fingerprints are incomplete",
    ):
        validation._source_identity(batch)


def test_source_identity_success():
    source = _identity()

    batch = SimpleNamespace(
        protocol_run=SimpleNamespace(
            protocol={
                "source": source,
            }
        )
    )

    assert validation._source_identity(batch) == source


# ============================================================
# HUMAN REFERENCE SUMMARY
# ============================================================


def test_reference_summary_type_guard(
    case,
):
    with pytest.raises(
        TypeError,
        match="VisusCanonicalAOIIntakeRun",
    ):
        validation._reference_summary(
            case["batch"],
            object(),
        )


def test_reference_summary_status_guard(
    case,
):
    reference = copy.deepcopy(case["reference"])

    reference.report["status"] = "invalid"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="verified reference intake",
    ):
        validation._reference_summary(
            case["batch"],
            reference,
        )


def test_reference_summary_missing_frozen_stream(
    case,
    monkeypatch,
):
    reference = copy.deepcopy(case["reference"])

    monkeypatch.setattr(
        validation,
        "validation_settings_from_preexecution_protocol",
        lambda protocol_run: {
            "reference_stream_id": "missing_stream",
        },
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="reference stream is absent",
    ):
        validation._reference_summary(
            case["batch"],
            reference,
        )


def test_reference_summary_exact_stimulus_coverage_guard(
    case,
    monkeypatch,
):
    reference = copy.deepcopy(case["reference"])

    stream = reference.by_stream["published_curated"]

    stream.pop(sorted(stream)[-1])

    monkeypatch.setattr(
        validation,
        "_reference_keyframes_from_canonical",
        lambda canonical: reference.by_stream,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not exactly cover",
    ):
        validation._reference_summary(
            case["batch"],
            reference,
        )


# ============================================================
# PREDICTION SUMMARY
# ============================================================


def test_prediction_summary_status_guard(
    case,
):
    batch = copy.deepcopy(case["batch"])

    batch.prediction_intake.report["status"] = "invalid"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="verified prediction intake",
    ):
        validation._prediction_summary(batch)


def test_prediction_summary_source_identity_guard(
    case,
    monkeypatch,
):
    batch = copy.deepcopy(case["batch"])

    key = validation._SOURCE_KEYS[0]

    batch.prediction_intake.report[key] = "f" * 64

    monkeypatch.setattr(
        validation,
        "_revalidate_fingerprint",
        lambda *args, **kwargs: "a" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not share",
    ):
        validation._prediction_summary(batch)


def test_prediction_summary_batch_table_binding_guard(
    case,
    monkeypatch,
):
    batch = copy.deepcopy(case["batch"])

    canonical = batch.prediction_intake.canonical

    canonical_fp = batch.prediction_intake.report["canonical_table_fingerprint_sha256"]

    def fake_fingerprint(frame):
        if frame is canonical:
            return canonical_fp
        return "0" * 64

    monkeypatch.setattr(
        validation,
        "fingerprint_frame",
        fake_fingerprint,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="no longer bound to the batch prediction table",
    ):
        validation._prediction_summary(batch)


def test_prediction_summary_model_mapping_guard(
    case,
    monkeypatch,
):
    batch = copy.deepcopy(case["batch"])

    batch.prediction_intake.report["model"] = None

    monkeypatch.setattr(
        validation,
        "_revalidate_fingerprint",
        lambda *args, **kwargs: "a" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="model identity is missing",
    ):
        validation._prediction_summary(batch)


# ============================================================
# AUTOMATIC HUMAN-HUMAN AGREEMENT
# ============================================================


def _agreement_batch():
    return SimpleNamespace(
        audit=SimpleNamespace(
            report={
                "annotation_provenance": {
                    "human_human_agreement_ready": True,
                }
            },
            spec=SimpleNamespace(
                independent_annotation_streams_verified=True,
            ),
        )
    )


def test_automatic_agreement_requires_exactly_two_streams():
    reference = SimpleNamespace(
        by_stream={
            "a": {},
            "b": {},
            "c": {},
        }
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly two",
    ):
        validation._automatic_human_agreement_pair(
            _agreement_batch(),
            reference,
        )


def test_automatic_agreement_selects_two_streams():
    reference = SimpleNamespace(
        by_stream={
            "stream_b": {},
            "stream_a": {},
        }
    )

    assert validation._automatic_human_agreement_pair(
        _agreement_batch(),
        reference,
    ) == (
        "stream_a",
        "stream_b",
    )


# ============================================================
# TIMESTAMP LEDGERS
# ============================================================


def _timestamp_batch(
    evaluation,
):
    return SimpleNamespace(
        protocol_run=SimpleNamespace(
            protocol={
                "evaluation": evaluation,
            }
        )
    )


def test_timestamp_ledgers_require_evaluation_mapping():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="evaluation section is missing",
    ):
        validation._timestamp_ledgers_from_protocol(_timestamp_batch(None))


@pytest.mark.parametrize(
    "records",
    [
        None,
        [],
    ],
)
def test_timestamp_ledgers_require_records(
    records,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="timestamp grids are missing",
    ):
        validation._timestamp_ledgers_from_protocol(
            _timestamp_batch(
                {
                    "timestamp_grids": records,
                }
            )
        )


def test_timestamp_ledgers_require_mapping_rows():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="record is malformed",
    ):
        validation._timestamp_ledgers_from_protocol(
            _timestamp_batch(
                {
                    "timestamp_grids": [
                        "bad-row",
                    ],
                }
            )
        )


@pytest.mark.parametrize(
    "values",
    [
        None,
        [],
    ],
)
def test_timestamp_ledgers_require_values(
    values,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="values are missing",
    ):
        validation._timestamp_ledgers_from_protocol(
            _timestamp_batch(
                {
                    "timestamp_grids": [
                        {
                            "stimulus_id": "S01",
                            "timestamps_ms": values,
                        }
                    ],
                }
            )
        )


def test_timestamp_ledgers_success():
    observed = validation._timestamp_ledgers_from_protocol(
        _timestamp_batch(
            {
                "timestamp_grids": [
                    {
                        "stimulus_id": "S01",
                        "timestamps_ms": [
                            0.0,
                            40.0,
                        ],
                        "timestamp_grid_fingerprint_sha256": ("a" * 64),
                    }
                ],
            }
        )
    )

    assert observed == [
        {
            "stimulus_id": "S01",
            "n_timestamps": 2,
            "first_timestamp_ms": 0.0,
            "last_timestamp_ms": 40.0,
            "timestamp_grid_fingerprint_sha256": ("a" * 64),
        }
    ]


# ============================================================
# EXPECTED SUITE PROTOCOL
# ============================================================


def test_expected_suite_protocol_requires_model_mapping(
    monkeypatch,
):
    batch = SimpleNamespace(
        protocol_run=SimpleNamespace(),
        prediction_intake=SimpleNamespace(
            report={
                "model": None,
            }
        ),
    )

    monkeypatch.setattr(
        validation,
        "validation_settings_from_preexecution_protocol",
        lambda run: {},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="batch model identity is missing",
    ):
        validation._expected_suite_protocol(
            batch,
            fixation_assignment_enabled=False,
            human_pair=None,
        )


# ============================================================
# SUITE MANIFEST BINDING
# ============================================================


def _suite_contract_objects():
    identity = _identity()

    batch = SimpleNamespace(
        protocol_run=SimpleNamespace(
            protocol={
                "source": identity,
            }
        ),
        prediction_intake=SimpleNamespace(report={"report_fingerprint_sha256": ("d" * 64)}),
    )

    reference = SimpleNamespace(report={"report_fingerprint_sha256": ("e" * 64)})

    suite = SimpleNamespace(
        manifest_path=Path("unused.json"),
        suite_fingerprint_sha256=("f" * 64),
    )

    verified = {
        "suite_fingerprint_sha256": (suite.suite_fingerprint_sha256),
        "source": copy.deepcopy(identity),
        "protocol": {},
        "reports": [
            {
                "name": "model_prediction_intake",
                "report_fingerprint_sha256": ("d" * 64),
            },
            {
                "name": "human_reference_intake",
                "report_fingerprint_sha256": ("e" * 64),
            },
        ],
    }

    return (
        batch,
        reference,
        suite,
        verified,
    )


def _patch_suite_validation(
    monkeypatch,
    verified,
):
    monkeypatch.setattr(
        validation,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: verified,
    )

    monkeypatch.setattr(
        validation,
        "_expected_suite_protocol",
        lambda *args, **kwargs: {},
    )


def test_suite_object_fingerprint_guard(
    monkeypatch,
):
    (
        batch,
        reference,
        suite,
        verified,
    ) = _suite_contract_objects()

    verified["suite_fingerprint_sha256"] = "0" * 64

    _patch_suite_validation(
        monkeypatch,
        verified,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="object does not match",
    ):
        validation._assert_suite_matches_frozen_protocol(
            batch,
            reference,
            suite,
            fixation_assignment_enabled=False,
            human_pair=None,
        )


@pytest.mark.parametrize(
    "field",
    [
        "source",
        "protocol",
    ],
)
def test_suite_requires_source_and_protocol_mappings(
    monkeypatch,
    field,
):
    (
        batch,
        reference,
        suite,
        verified,
    ) = _suite_contract_objects()

    verified[field] = None

    _patch_suite_validation(
        monkeypatch,
        verified,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source/protocol sections are missing",
    ):
        validation._assert_suite_matches_frozen_protocol(
            batch,
            reference,
            suite,
            fixation_assignment_enabled=False,
            human_pair=None,
        )


def test_suite_source_identity_guard(
    monkeypatch,
):
    (
        batch,
        reference,
        suite,
        verified,
    ) = _suite_contract_objects()

    verified["source"][validation._SOURCE_KEYS[0]] = "9" * 64

    _patch_suite_validation(
        monkeypatch,
        verified,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity differs",
    ):
        validation._assert_suite_matches_frozen_protocol(
            batch,
            reference,
            suite,
            fixation_assignment_enabled=False,
            human_pair=None,
        )


def test_suite_prediction_intake_binding_guard(
    monkeypatch,
):
    (
        batch,
        reference,
        suite,
        verified,
    ) = _suite_contract_objects()

    verified["reports"][0]["report_fingerprint_sha256"] = "0" * 64

    _patch_suite_validation(
        monkeypatch,
        verified,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="protocol-batch prediction intake",
    ):
        validation._assert_suite_matches_frozen_protocol(
            batch,
            reference,
            suite,
            fixation_assignment_enabled=False,
            human_pair=None,
        )


def test_suite_reference_intake_binding_guard(
    monkeypatch,
):
    (
        batch,
        reference,
        suite,
        verified,
    ) = _suite_contract_objects()

    verified["reports"][1]["report_fingerprint_sha256"] = "0" * 64

    _patch_suite_validation(
        monkeypatch,
        verified,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="supplied human-reference intake",
    ):
        validation._assert_suite_matches_frozen_protocol(
            batch,
            reference,
            suite,
            fixation_assignment_enabled=False,
            human_pair=None,
        )


# ============================================================
# BINDING BODY
# ============================================================


def _binding_batch():
    identity = _identity()

    return SimpleNamespace(
        protocol_run=SimpleNamespace(
            protocol={
                "source": identity,
            },
            protocol_fingerprint_sha256=("1" * 64),
        ),
        prediction_intake=SimpleNamespace(
            report={
                "model": {
                    "name": "fixture-model",
                    "version": "1",
                }
            }
        ),
        batch_fingerprint_sha256=("2" * 64),
        report_path=Path("batch-report.json"),
        prediction_path=Path("predictions.csv"),
        report={
            "prediction_output": {
                "sha256": "3" * 64,
            },
            "frozen_evaluation_handoff": {
                "timestamp_grid_fingerprints": {
                    "S01": "4" * 64,
                }
            },
        },
    )


def _binding_settings():
    return {
        "reference_stream_id": "published_curated",
        "timestamp_grid_basis": "fixture",
        "max_interpolation_gap_ms": 80.0,
        "min_iou": 0.5,
        "require_label_match": True,
        "fixation_assignment_planned": False,
        "overlap_rule": "highest_confidence",
    }


def _suite_reports(
    *,
    model_human: Any,
    human_human: Any = None,
):
    reports = {}

    if model_human is not ...:
        reports["model_human_validation"] = model_human

    if human_human is not ...:
        reports["human_human_agreement"] = human_human

    return SimpleNamespace(
        suite_fingerprint_sha256=("5" * 64),
        reports=reports,
    )


def _call_binding_body(
    monkeypatch,
    suite,
    *,
    human_pair=None,
):
    monkeypatch.setattr(
        validation,
        "validation_settings_from_preexecution_protocol",
        lambda run: _binding_settings(),
    )

    return validation._binding_body(
        _binding_batch(),
        {},
        {},
        suite,
        human_pair=human_pair,
    )


def test_binding_body_requires_model_human_results(
    monkeypatch,
):
    suite = _suite_reports(model_human=...)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing model-human results",
    ):
        _call_binding_body(
            monkeypatch,
            suite,
        )


def test_binding_body_requires_model_human_fingerprint(
    monkeypatch,
):
    suite = _suite_reports(model_human={"report_fingerprint_sha256": ("bad")})

    with pytest.raises(
        BenchmarkIntegrityError,
        match="model-human report fingerprint is invalid",
    ):
        _call_binding_body(
            monkeypatch,
            suite,
        )


def test_binding_body_requires_human_human_results(
    monkeypatch,
):
    suite = _suite_reports(
        model_human={"report_fingerprint_sha256": ("6" * 64)},
        human_human=...,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing required human-human agreement",
    ):
        _call_binding_body(
            monkeypatch,
            suite,
            human_pair=(
                "human_a",
                "human_b",
            ),
        )


def test_binding_body_requires_human_human_fingerprint(
    monkeypatch,
):
    suite = _suite_reports(
        model_human={"report_fingerprint_sha256": ("6" * 64)},
        human_human={"report_fingerprint_sha256": ("bad")},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="human-human report fingerprint is invalid",
    ):
        _call_binding_body(
            monkeypatch,
            suite,
            human_pair=(
                "human_a",
                "human_b",
            ),
        )


def test_binding_body_human_human_success(
    monkeypatch,
):
    suite = _suite_reports(
        model_human={"report_fingerprint_sha256": ("6" * 64)},
        human_human={"report_fingerprint_sha256": ("7" * 64)},
    )

    observed = _call_binding_body(
        monkeypatch,
        suite,
        human_pair=(
            "human_a",
            "human_b",
        ),
    )

    assert observed["human_human_agreement_executed"] is True

    assert observed["human_human_report_fingerprint_sha256"] == "7" * 64


# ============================================================
# BINDING FILE I/O
# ============================================================


def test_load_binding_symlink_guard_portable(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "binding.json"

    path.write_text(
        "{}",
        encoding="utf-8",
    )

    original = Path.is_symlink

    def fake_is_symlink(self):
        if self == path:
            return True
        return original(self)

    monkeypatch.setattr(
        Path,
        "is_symlink",
        fake_is_symlink,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not be a symlink",
    ):
        validation._load_binding(path)


def test_load_binding_missing_file(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError,
    ):
        validation._load_binding(tmp_path / "missing.json")


def test_load_binding_invalid_json(
    tmp_path,
):
    path = tmp_path / "binding.json"

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not valid JSON",
    ):
        validation._load_binding(path)


def test_load_binding_requires_json_object(
    tmp_path,
):
    path = tmp_path / "binding.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        validation._load_binding(path)


def test_load_binding_success(
    tmp_path,
):
    path = tmp_path / "binding.json"

    path.write_text(
        '{"x": 1}',
        encoding="utf-8",
    )

    assert validation._load_binding(path) == {
        "x": 1,
    }


# ============================================================
# FINAL RUN VALIDATOR CLAIM / LINEAGE GUARDS
# ============================================================


def _validator_binding() -> dict[str, Any]:
    return {
        "schema": validation._BINDING_SCHEMA,
        "status": ("verified-protocol-bound-validation"),
        "binding_fingerprint_sha256": ("8" * 64),
        "model_human_validation_executed": True,
        "formal_preregistration_verified": False,
        "empirical_performance_claim_created": False,
        "dataset_source_authority_promoted": False,
        "dataset_rights_promoted": False,
        "frozen_evidence_created": False,
        "source_authority_certificate_required_separately": True,
        "source_authority_certificate_bound_by_this_layer": False,
    }


def _validator_run(
    binding=None,
    *,
    filename=validation._BINDING_FILENAME,
    object_fingerprint=None,
):
    value = _validator_binding() if binding is None else binding

    fingerprint = (
        value["binding_fingerprint_sha256"] if object_fingerprint is None else object_fingerprint
    )

    return validation.VisusProtocolBoundValidationRun(
        batch=SimpleNamespace(protocol_run=object()),
        reference_intake=object(),
        suite=object(),
        output_dir=Path("."),
        binding_path=Path(filename),
        binding=value,
        binding_fingerprint_sha256=fingerprint,
    )


def _patch_validator_dependencies(
    monkeypatch,
    run,
):
    monkeypatch.setattr(
        validation,
        "validate_visus_protocol_bound_batch_run",
        lambda batch: batch,
    )

    monkeypatch.setattr(
        validation,
        "_prediction_summary",
        lambda batch: {},
    )

    monkeypatch.setattr(
        validation,
        "_reference_summary",
        lambda batch, reference: {},
    )

    monkeypatch.setattr(
        validation,
        "validation_settings_from_preexecution_protocol",
        lambda protocol_run: {
            "fixation_assignment_planned": False,
        },
    )

    monkeypatch.setattr(
        validation,
        "_automatic_human_agreement_pair",
        lambda batch, reference: None,
    )

    monkeypatch.setattr(
        validation,
        "_revalidate_fingerprint",
        lambda record, field, label: record[field],
    )

    monkeypatch.setattr(
        validation,
        "_load_binding",
        lambda path: run.binding,
    )

    monkeypatch.setattr(
        validation,
        "_assert_suite_matches_frozen_protocol",
        lambda *args, **kwargs: {},
    )

    monkeypatch.setattr(
        validation,
        "_binding_body",
        lambda *args, **kwargs: {
            key: value for key, value in run.binding.items() if key != "binding_fingerprint_sha256"
        },
    )


def test_validation_run_type_guard():
    with pytest.raises(
        TypeError,
        match="VisusProtocolBoundValidationRun",
    ):
        validation.validate_visus_protocol_bound_validation_run(object())


def test_validation_run_schema_guard(
    monkeypatch,
):
    binding = _validator_binding()
    binding["schema"] = "wrong"

    run = _validator_run(binding)

    _patch_validator_dependencies(
        monkeypatch,
        run,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="schema drifted",
    ):
        validation.validate_visus_protocol_bound_validation_run(run)


def test_validation_run_status_guard(
    monkeypatch,
):
    binding = _validator_binding()
    binding["status"] = "wrong"

    run = _validator_run(binding)

    _patch_validator_dependencies(
        monkeypatch,
        run,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="status drifted",
    ):
        validation.validate_visus_protocol_bound_validation_run(run)


def test_validation_run_object_fingerprint_guard(
    monkeypatch,
):
    run = _validator_run(object_fingerprint=("9" * 64))

    _patch_validator_dependencies(
        monkeypatch,
        run,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint object drifted",
    ):
        validation.validate_visus_protocol_bound_validation_run(run)


def test_validation_run_filename_guard(
    monkeypatch,
):
    run = _validator_run(filename="wrong-name.json")

    _patch_validator_dependencies(
        monkeypatch,
        run,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="filename drifted",
    ):
        validation.validate_visus_protocol_bound_validation_run(run)


def test_validation_run_execution_status_guard(
    monkeypatch,
):
    binding = _validator_binding()

    binding["model_human_validation_executed"] = False

    run = _validator_run(binding)

    _patch_validator_dependencies(
        monkeypatch,
        run,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lost execution status",
    ):
        validation.validate_visus_protocol_bound_validation_run(run)


@pytest.mark.parametrize(
    "field",
    [
        "formal_preregistration_verified",
        "empirical_performance_claim_created",
        "dataset_source_authority_promoted",
        "dataset_rights_promoted",
        "frozen_evidence_created",
    ],
)
def test_validation_run_claim_promotion_guards(
    monkeypatch,
    field,
):
    binding = _validator_binding()

    binding[field] = True

    run = _validator_run(binding)

    _patch_validator_dependencies(
        monkeypatch,
        run,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=f"cannot promote {field}",
    ):
        validation.validate_visus_protocol_bound_validation_run(run)


def test_validation_run_requires_separate_authority_gate(
    monkeypatch,
):
    binding = _validator_binding()

    binding["source_authority_certificate_required_separately"] = False

    run = _validator_run(binding)

    _patch_validator_dependencies(
        monkeypatch,
        run,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot bypass the source-authority gate",
    ):
        validation.validate_visus_protocol_bound_validation_run(run)


def test_validation_run_cannot_self_certify_authority(
    monkeypatch,
):
    binding = _validator_binding()

    binding["source_authority_certificate_bound_by_this_layer"] = True

    run = _validator_run(binding)

    _patch_validator_dependencies(
        monkeypatch,
        run,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot self-certify source authority",
    ):
        validation.validate_visus_protocol_bound_validation_run(run)


def test_validation_run_success_contract(
    monkeypatch,
):
    run = _validator_run()

    _patch_validator_dependencies(
        monkeypatch,
        run,
    )

    assert validation.validate_visus_protocol_bound_validation_run(run) is run
