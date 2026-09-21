from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from test_visus_preexecution_protocol import _FakeRuntime, _fixture, _freeze
from test_visus_protocol_batch import _resign, _resign_batch, _run

import gazeforge.visus_protocol_batch as batchmod
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError


def _protocol(tmp_path: Path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(
        tmp_path,
        audit,
        plans,
        timestamps,
    )
    return (
        audit,
        plans,
        timestamps,
        frozen,
    )


def _sync_intake_and_batch(run) -> None:
    _resign(
        run.prediction_intake.report,
        "report_fingerprint_sha256",
    )

    run.report["prediction_intake"] = batchmod._intake_summary(run.prediction_intake)

    _resign_batch(run)


def test_file_sha256_success_missing_and_empty(
    tmp_path: Path,
) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"abc")

    size, digest = batchmod._file_sha256(
        path,
        label="fixture",
    )

    assert size == 3
    assert len(digest) == 64

    with pytest.raises(FileNotFoundError):
        batchmod._file_sha256(
            tmp_path / "missing.bin",
            label="fixture",
        )

    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot be empty",
    ):
        batchmod._file_sha256(
            empty,
            label="fixture",
        )


def test_file_sha256_rejects_symlink(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.bin"
    target.write_bytes(b"abc")

    link = tmp_path / "link.bin"

    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation unavailable")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="symbolic link",
    ):
        batchmod._file_sha256(
            link,
            label="fixture",
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("a" * 64, True),
        ("A" * 64, True),
        ("f" * 63, False),
        ("g" * 64, False),
        (None, False),
    ],
)
def test_valid_sha256_contract(
    value: Any,
    expected: bool,
) -> None:
    assert batchmod._valid_sha256(value) is expected


def test_revalidate_fingerprint_success_and_failure() -> None:
    record = {
        "value": 1,
    }

    record["fp"] = benchmark_fingerprint(record)

    assert (
        batchmod._revalidate_fingerprint(
            record,
            "fp",
            label="fixture",
        )
        == record["fp"]
    )

    record["fp"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not revalidate",
    ):
        batchmod._revalidate_fingerprint(
            record,
            "fp",
            label="fixture",
        )


def test_load_exact_protocol_type_guard() -> None:
    with pytest.raises(
        TypeError,
        match="VisusGroundedSAM2PreexecutionProtocolRun",
    ):
        batchmod._load_exact_protocol(object())


def test_load_exact_protocol_object_drift(
    tmp_path: Path,
) -> None:
    (
        _,
        _,
        _,
        frozen,
    ) = _protocol(tmp_path)

    changed = replace(
        frozen,
        protocol=copy.deepcopy(frozen.protocol),
    )

    changed.protocol["evaluation"]["min_iou"] = 0.99

    with pytest.raises(
        BenchmarkIntegrityError,
        match="changed before batch execution",
    ):
        batchmod._load_exact_protocol(changed)


@pytest.mark.parametrize(
    ("value", "match"),
    [
        (
            {},
            "contains no stimulus plans",
        ),
        (
            {
                "stimuli": [],
            },
            "contains no stimulus plans",
        ),
        (
            {
                "stimuli": [
                    {
                        "stimulus_id": "",
                    }
                ],
            },
            "invalid or duplicated",
        ),
        (
            {
                "stimuli": [
                    {
                        "stimulus_id": "S01",
                    },
                    {
                        "stimulus_id": "S01",
                    },
                ],
            },
            "invalid or duplicated",
        ),
    ],
)
def test_stimulus_ids_guards(
    value: dict[str, Any],
    match: str,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        batchmod._stimulus_ids(value)


def test_stimulus_ids_success() -> None:
    assert batchmod._stimulus_ids(
        {
            "stimuli": [
                {
                    "stimulus_id": "S01",
                },
                {
                    "stimulus_id": "S02",
                },
            ]
        }
    ) == [
        "S01",
        "S02",
    ]


@pytest.mark.parametrize(
    ("protocol", "match"),
    [
        (
            {},
            "evaluation section is missing",
        ),
        (
            {
                "evaluation": {},
                "stimuli": [],
            },
            "timestamp grids are missing",
        ),
        (
            {
                "evaluation": {"timestamp_grids": ["bad"]},
                "stimuli": [
                    {
                        "stimulus_id": "S01",
                    }
                ],
            },
            "record is malformed",
        ),
        (
            {
                "evaluation": {
                    "timestamp_grids": [
                        {
                            "stimulus_id": "",
                            "timestamps_ms": [0.0],
                        }
                    ]
                },
                "stimuli": [
                    {
                        "stimulus_id": "S01",
                    }
                ],
            },
            "record is incomplete",
        ),
        (
            {
                "evaluation": {
                    "timestamp_grids": [
                        {
                            "stimulus_id": "S01",
                            "timestamps_ms": "bad",
                        }
                    ]
                },
                "stimuli": [
                    {
                        "stimulus_id": "S01",
                    }
                ],
            },
            "record is incomplete",
        ),
        (
            {
                "evaluation": {
                    "timestamp_grids": [
                        {
                            "stimulus_id": "S02",
                            "timestamps_ms": [0.0],
                        }
                    ]
                },
                "stimuli": [
                    {
                        "stimulus_id": "S01",
                    }
                ],
            },
            "order does not match",
        ),
    ],
)
def test_timestamps_from_protocol_guards(
    protocol: dict[str, Any],
    match: str,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        batchmod._timestamps_from_protocol(protocol)


def test_timestamps_from_protocol_success() -> None:
    result = batchmod._timestamps_from_protocol(
        {
            "stimuli": [
                {
                    "stimulus_id": "S01",
                }
            ],
            "evaluation": {
                "timestamp_grids": [
                    {
                        "stimulus_id": "S01",
                        "timestamps_ms": [
                            0,
                            40,
                        ],
                    }
                ]
            },
        }
    )

    assert result == {
        "S01": [
            0.0,
            40.0,
        ]
    }


def test_require_exact_plans_mapping_guard() -> None:
    with pytest.raises(
        TypeError,
        match="must be a mapping",
    ):
        batchmod._require_exact_plans(
            [],
            [
                "S01",
            ],
        )


def test_require_exact_plans_key_identity_guard(
    tmp_path: Path,
) -> None:
    (
        _,
        plans,
        _,
        _,
    ) = _protocol(tmp_path)

    changed = dict(plans)

    changed["S01"] = replace(
        changed["S01"],
        stimulus_id="S99",
    )

    with pytest.raises(
        SchemaError,
        match="mapping key",
    ):
        batchmod._require_exact_plans(
            changed,
            list(plans),
        )


def test_preflight_clean_directory_and_overwrite(
    tmp_path: Path,
) -> None:
    output = tmp_path / "batch"

    prediction, report = batchmod._preflight_output_dir(
        output,
        overwrite=False,
    )

    assert output.is_dir()

    prediction.write_text(
        "x",
        encoding="utf-8",
    )

    prediction2, report2 = batchmod._preflight_output_dir(
        output,
        overwrite=True,
    )

    assert prediction2 == prediction
    assert report2 == report


def test_write_prediction_csv_roundtrip(
    tmp_path: Path,
) -> None:
    table = pd.DataFrame(
        {
            "stimulus_id": [
                "S01",
            ],
            "aoi_id": [
                "A",
            ],
            "frame_index": [
                1,
            ],
            "confidence": [
                0.9,
            ],
        }
    )

    path = tmp_path / "pred.csv"

    size, digest = batchmod._write_prediction_csv(
        table,
        path,
    )

    assert size > 0
    assert len(digest) == 64
    assert path.is_file()
    assert not (tmp_path / "pred.csv.tmp").exists()


def test_load_report_file_guards(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        batchmod._load_report_file(tmp_path / "missing.json")

    bad = tmp_path / "bad.json"
    bad.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not valid JSON",
    ):
        batchmod._load_report_file(bad)

    array = tmp_path / "array.json"
    array.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        batchmod._load_report_file(array)


def test_load_report_file_symlink_guard(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.json"

    target.write_text(
        "{}",
        encoding="utf-8",
    )

    link = tmp_path / "link.json"

    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation unavailable")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="symbolic link",
    ):
        batchmod._load_report_file(link)


def test_binding_record_type_and_identity_guards(
    tmp_path: Path,
) -> None:
    batch, _, _, frozen, _ = _run(tmp_path)

    with pytest.raises(
        TypeError,
        match="wrong run type",
    ):
        batchmod._binding_record(
            "S01",
            object(),
            expected_protocol_fingerprint=(frozen.protocol_fingerprint_sha256),
            row_count=1,
            track_count=1,
        )

    bound = batch.per_stimulus["S01"]

    changed = replace(
        bound,
        stimulus_id="S99",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="identity mismatch",
    ):
        batchmod._binding_record(
            "S01",
            changed,
            expected_protocol_fingerprint=(frozen.protocol_fingerprint_sha256),
            row_count=1,
            track_count=1,
        )


@pytest.mark.parametrize(
    ("target", "field", "value", "match"),
    [
        (
            "protocol",
            "grounded_sam2_report_fingerprint_sha256",
            "0" * 64,
            "different backend run",
        ),
        (
            "frame",
            "grounded_sam2_report_fingerprint_sha256",
            "0" * 64,
            "different backend run",
        ),
        (
            "frame",
            "frame_derivation_report_fingerprint_sha256",
            "0" * 64,
            "disagree on derivation identity",
        ),
        (
            "protocol",
            "protocol_validated_before_backend_call",
            False,
            "pre-inference protocol validation",
        ),
        (
            "protocol",
            "local_execution_order_verified",
            False,
            "local execution-order proof",
        ),
        (
            "frame",
            "frame_derivation_mechanically_verified",
            False,
            "mechanical frame derivation",
        ),
    ],
)
def test_binding_record_lineage_guards(
    tmp_path: Path,
    target: str,
    field: str,
    value: Any,
    match: str,
) -> None:
    batch, _, _, frozen, _ = _run(tmp_path)

    bound = batch.per_stimulus["S01"]

    binding = bound.protocol_binding if target == "protocol" else bound.frame_derivation_binding

    binding[field] = value

    _resign(
        binding,
        "binding_fingerprint_sha256",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        batchmod._binding_record(
            "S01",
            bound,
            expected_protocol_fingerprint=(frozen.protocol_fingerprint_sha256),
            row_count=1,
            track_count=1,
        )


@pytest.mark.parametrize(
    "field",
    [
        "formal_preregistration_verified",
        "dataset_source_authority_promoted",
        "dataset_rights_promoted",
    ],
)
def test_protocol_binding_claim_guards(
    tmp_path: Path,
    field: str,
) -> None:
    batch, _, _, frozen, _ = _run(tmp_path)

    bound = batch.per_stimulus["S01"]

    bound.protocol_binding[field] = True

    _resign(
        bound.protocol_binding,
        "binding_fingerprint_sha256",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="improperly promotes",
    ):
        batchmod._binding_record(
            "S01",
            bound,
            expected_protocol_fingerprint=(frozen.protocol_fingerprint_sha256),
            row_count=1,
            track_count=1,
        )


@pytest.mark.parametrize(
    "field",
    [
        "empirical_performance_claim_created",
        "dataset_source_authority_implied",
        "grounded_sam2_backend_alone_claims_derivation_verification",
    ],
)
def test_frame_binding_claim_guards(
    tmp_path: Path,
    field: str,
) -> None:
    batch, _, _, frozen, _ = _run(tmp_path)

    bound = batch.per_stimulus["S01"]

    bound.frame_derivation_binding[field] = True

    _resign(
        bound.frame_derivation_binding,
        "binding_fingerprint_sha256",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="improperly promotes",
    ):
        batchmod._binding_record(
            "S01",
            bound,
            expected_protocol_fingerprint=(frozen.protocol_fingerprint_sha256),
            row_count=1,
            track_count=1,
        )


def test_binding_record_fingerprint_guards(
    tmp_path: Path,
) -> None:
    batch, _, _, frozen, _ = _run(tmp_path)

    bound = batch.per_stimulus["S01"]

    bound.protocol_binding["binding_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint does not revalidate",
    ):
        batchmod._binding_record(
            "S01",
            bound,
            expected_protocol_fingerprint=(frozen.protocol_fingerprint_sha256),
            row_count=1,
            track_count=1,
        )


def test_prediction_basis() -> None:
    result = batchmod._prediction_basis("abc")

    assert "abc" in result
    assert "Grounding DINO" in result


def test_summary_helpers(
    tmp_path: Path,
) -> None:
    batch, _, _, frozen, _ = _run(tmp_path)

    protocol = frozen.protocol

    assert batchmod._source_summary(protocol) == batch.report["source"]

    assert batchmod._model_summary(protocol) == batch.report["model"]

    assert batchmod._evaluation_handoff(protocol) == batch.report["frozen_evaluation_handoff"]

    assert batchmod._intake_summary(batch.prediction_intake) == batch.report["prediction_intake"]


def test_default_runtime_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        audit,
        plans,
        timestamps,
        frozen,
    ) = _protocol(tmp_path)

    runtime = _FakeRuntime()

    monkeypatch.setattr(
        batchmod,
        "HuggingFaceGroundedSAM2Runtime",
        lambda: runtime,
    )

    result = batchmod.run_visus_grounded_sam2_protocol_batch(
        frozen,
        audit,
        plans,
        tmp_path / "batch",
        runtime=None,
    )

    assert len(result.per_stimulus) == 11
    assert runtime.detect_calls == 11


def test_run_rejects_empty_prediction_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        audit,
        plans,
        _,
        frozen,
    ) = _protocol(tmp_path)

    monkeypatch.setattr(
        batchmod,
        "grounded_sam2_to_visus_prediction_table",
        lambda *args, **kwargs: pd.DataFrame(),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="no prediction rows",
    ):
        batchmod.run_visus_grounded_sam2_protocol_batch(
            frozen,
            audit,
            plans,
            tmp_path / "batch",
            runtime=_FakeRuntime(),
        )


def test_run_rejects_wrong_prediction_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        audit,
        plans,
        _,
        frozen,
    ) = _protocol(tmp_path)

    original = batchmod.grounded_sam2_to_visus_prediction_table

    def changed(*args, **kwargs):
        table = original(
            *args,
            **kwargs,
        )

        if kwargs.get("stimulus_id") == "S01":
            table = table.copy()
            table["stimulus_id"] = "WRONG"

        return table

    monkeypatch.setattr(
        batchmod,
        "grounded_sam2_to_visus_prediction_table",
        changed,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not exactly cover",
    ):
        batchmod.run_visus_grounded_sam2_protocol_batch(
            frozen,
            audit,
            plans,
            tmp_path / "batch",
            runtime=_FakeRuntime(),
        )


def test_run_rejects_prediction_intake_grid_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        audit,
        plans,
        _,
        frozen,
    ) = _protocol(tmp_path)

    original = batchmod.prepare_visus_dynamic_aoi_predictions

    def changed(*args, **kwargs):
        result = original(
            *args,
            **kwargs,
        )

        result.report["evaluation_timestamp_grid_generated"] = True

        return result

    monkeypatch.setattr(
        batchmod,
        "prepare_visus_dynamic_aoi_predictions",
        changed,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="generated an evaluation grid",
    ):
        batchmod.run_visus_grounded_sam2_protocol_batch(
            frozen,
            audit,
            plans,
            tmp_path / "batch",
            runtime=_FakeRuntime(),
        )


def test_validator_type_guard() -> None:
    with pytest.raises(
        TypeError,
        match="VisusProtocolBoundGroundedSAM2BatchRun",
    ):
        batchmod.validate_visus_protocol_bound_batch_run(object())


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "schema",
            "wrong",
            "schema drifted",
        ),
        (
            "status",
            "wrong",
            "status drifted",
        ),
        (
            "protocol_fingerprint_sha256",
            "0" * 64,
            "protocol identity drifted",
        ),
    ],
)
def test_validator_top_level_report_guards(
    tmp_path: Path,
    field: str,
    value: Any,
    match: str,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    batch.report[field] = value

    _resign_batch(batch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


def test_validator_fingerprint_object_guard(
    tmp_path: Path,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    batch.batch_fingerprint_sha256 = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint object drifted",
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


def test_validator_report_filename_guard(
    tmp_path: Path,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    changed = batch.report_path.parent / "wrong.json"

    changed.write_bytes(batch.report_path.read_bytes())

    batch.report_path = changed

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report filename drifted",
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


def test_validator_prediction_filename_guard(
    tmp_path: Path,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    changed = batch.prediction_path.parent / "wrong.csv"

    changed.write_bytes(batch.prediction_path.read_bytes())

    batch.prediction_path = changed

    with pytest.raises(
        BenchmarkIntegrityError,
        match="prediction filename drifted",
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


def test_validator_model_policy_guard(
    tmp_path: Path,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    batch.report["model"]["name"] = "wrong"

    _resign_batch(batch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="model policy drifted",
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


@pytest.mark.parametrize(
    "section",
    [
        "prediction_output",
        "execution",
        "prediction_intake",
    ],
)
def test_validator_missing_report_sections(
    tmp_path: Path,
    section: str,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    batch.report[section] = None

    _resign_batch(batch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report sections are missing",
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "stimulus_count",
            1,
            "stimulus count drifted",
        ),
        (
            "stimulus_ids",
            [],
            "stimulus order drifted",
        ),
        (
            "all_protocol_bindings_verified",
            False,
            "lost protocol-binding verification",
        ),
        (
            "all_frame_derivations_mechanically_verified",
            False,
            "lost frame-derivation verification",
        ),
    ],
)
def test_validator_execution_summary_guards(
    tmp_path: Path,
    field: str,
    value: Any,
    match: str,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    batch.report["execution"][field] = value

    _resign_batch(batch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


def test_validator_prediction_row_count_guard(
    tmp_path: Path,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    batch.report["prediction_output"]["row_count"] += 1

    _resign_batch(batch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="row count drifted",
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


def test_validator_prediction_track_count_guard(
    tmp_path: Path,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    batch.report["prediction_output"]["track_count"] += 1

    _resign_batch(batch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="track count drifted",
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


def test_validator_prediction_coverage_guard(
    tmp_path: Path,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    changed = batch.predictions.copy()

    changed.loc[
        changed["stimulus_id"] == "S01",
        "stimulus_id",
    ] = "WRONG"

    batch.predictions = changed

    output = batch.report["prediction_output"]

    output["table_fingerprint_sha256"] = batchmod.fingerprint_frame(changed)

    output["row_count"] = len(changed)

    output["track_count"] = int(
        changed[
            [
                "stimulus_id",
                "aoi_id",
            ]
        ]
        .drop_duplicates()
        .shape[0]
    )

    _resign_batch(batch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="coverage/order drifted",
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


@pytest.mark.parametrize(
    ("case", "match"),
    [
        (
            "not_list",
            "execution ledger drifted",
        ),
        (
            "length",
            "execution ledger drifted",
        ),
        (
            "ids",
            "execution identities drifted",
        ),
    ],
)
def test_validator_execution_ledger_guards(
    tmp_path: Path,
    case: str,
    match: str,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    execution = batch.report["execution"]

    if case == "not_list":
        execution["records"] = None

    elif case == "length":
        execution["records"] = execution["records"][:-1]

    elif case == "ids":
        execution["records"][0]["stimulus_id"] = "WRONG"

    _resign_batch(batch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


def test_validator_lineage_record_guard(
    tmp_path: Path,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    batch.report["execution"]["records"][0]["row_count"] += 1

    _resign_batch(batch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lineage drifted",
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


def test_validator_intake_summary_guard(
    tmp_path: Path,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    batch.report["prediction_intake"]["status"] = "wrong"

    _resign_batch(batch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="prediction-intake summary drifted",
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "input_table_fingerprint_sha256",
            "0" * 64,
            "not bound to the batch table",
        ),
        (
            "source_audit_report_fingerprint_sha256",
            "0" * 64,
            "source audit drifted",
        ),
        (
            "source_audit_spec_fingerprint_sha256",
            "0" * 64,
            "source specification drifted",
        ),
        (
            "source_manifest_fingerprint_sha256",
            "0" * 64,
            "source manifest drifted",
        ),
        (
            "stimulus_ids",
            [],
            "stimulus coverage drifted",
        ),
        (
            "row_count",
            -1,
            "row count drifted",
        ),
        (
            "complete_audited_stimulus_coverage_required",
            False,
            "lost complete-coverage enforcement",
        ),
        (
            "evaluation_timestamp_grid_generated",
            True,
            "cannot generate the evaluation grid",
        ),
    ],
)
def test_validator_prediction_intake_guards(
    tmp_path: Path,
    field: str,
    value: Any,
    match: str,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    batch.prediction_intake.report[field] = value

    _sync_intake_and_batch(batch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "name",
            "wrong",
            "model name drifted",
        ),
        (
            "version",
            "wrong",
            "model version drifted",
        ),
    ],
)
def test_validator_prediction_intake_model_guards(
    tmp_path: Path,
    field: str,
    value: str,
    match: str,
) -> None:
    batch, _, _, _, _ = _run(tmp_path)

    batch.prediction_intake.report["model"][field] = value

    _sync_intake_and_batch(batch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        batchmod.validate_visus_protocol_bound_batch_run(batch)
