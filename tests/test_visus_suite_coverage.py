from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import gazeforge.visus_suite as suite
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_audit import (
    VisusSourceAuditSpec,
    VisusSourceFileRecord,
    audit_visus_source,
)
from gazeforge.visus_intake import prepare_visus_canonical_aoi_intake
from gazeforge.visus_prediction import prepare_visus_dynamic_aoi_predictions


def _write(root: Path, relative: str) -> tuple[str, int]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"fixture:{relative}\n", encoding="utf-8")
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest(), len(payload)


def _record(
    root: Path,
    *,
    path: str,
    role: str,
    stimulus_id: str,
    participant_id: str | None = None,
    annotation_stream_id: str | None = None,
) -> VisusSourceFileRecord:
    digest, size = _write(root, path)

    return VisusSourceFileRecord(
        path=path,
        sha256=digest,
        bytes=size,
        role=role,
        stimulus_id=stimulus_id,
        participant_id=participant_id,
        annotation_stream_id=annotation_stream_id,
    )


def _audit(root: Path, *, independent: bool):
    stimuli = [f"S{index:02d}" for index in range(1, 12)]

    files: list[VisusSourceFileRecord] = []

    for stimulus in stimuli:
        files.append(
            _record(
                root,
                path=f"video/{stimulus}.avi",
                role="video",
                stimulus_id=stimulus,
            )
        )

        for stream in (
            "annotator_a",
            "annotator_b",
        ):
            files.append(
                _record(
                    root,
                    path=f"aoi/{stimulus}-{stream}.xml",
                    role="aoi_annotation",
                    stimulus_id=stimulus,
                    annotation_stream_id=stream,
                )
            )

    for index in range(1, 26):
        participant = f"P{index:02d}"
        stimulus = stimuli[(index - 1) % len(stimuli)]

        files.append(
            _record(
                root,
                path=(f"gaze/{participant}-{stimulus}.tsv"),
                role="gaze",
                stimulus_id=stimulus,
                participant_id=participant,
            )
        )

    spec = VisusSourceAuditSpec(
        dataset_name="VISUS",
        dataset_version="coverage-fixture",
        source="https://example.invalid/visus",
        source_revision="fixture-snapshot",
        license="Reviewed fixture terms.",
        reuse_terms_source=("https://example.invalid/terms"),
        dataset_status="empirical",
        reuse_terms_verified=True,
        analysis_use_permitted=True,
        redistribution_status="restricted",
        stimulus_mapping_verified=True,
        stimulus_mapping_basis=("Fixture stimulus manifest."),
        participant_mapping_verified=True,
        participant_mapping_basis=("Fixture participant manifest."),
        coordinate_unit="pixels",
        coordinate_unit_verified=True,
        coordinate_verification_basis=("Fixture coordinate documentation."),
        timestamp_basis_verified=True,
        timestamp_verification_basis=("Fixture frame-time documentation."),
        independent_annotation_streams_verified=independent,
        independent_annotation_streams_basis=(
            "Fixture independent streams." if independent else ""
        ),
        files=files,
    )

    return audit_visus_source(root, spec)


def _reference_table() -> pd.DataFrame:
    rows = []

    for index in range(1, 12):
        stimulus = f"S{index:02d}"
        shift = float(index)

        for stream in (
            "annotator_a",
            "annotator_b",
        ):
            for frame_index, x_shift in (
                (1, 0.0),
                (3, 8.0),
            ):
                rows.append(
                    {
                        "source_path": (f"aoi/{stimulus}-{stream}.xml"),
                        "stimulus_id": stimulus,
                        "annotation_stream_id": stream,
                        "frame_index": frame_index,
                        "aoi_id": f"{stream}-person",
                        "label": "person",
                        "xmin": 10.0 + shift + x_shift,
                        "ymin": 20.0,
                        "xmax": 110.0 + shift + x_shift,
                        "ymax": 220.0,
                    }
                )

    return pd.DataFrame(rows)


def _prediction_table() -> pd.DataFrame:
    rows = []

    for index in range(1, 12):
        stimulus = f"S{index:02d}"
        shift = float(index)

        for frame_index, x_shift in (
            (1, 0.0),
            (3, 8.0),
        ):
            rows.append(
                {
                    "stimulus_id": stimulus,
                    "frame_index": frame_index,
                    "aoi_id": "model-person",
                    "label": "person",
                    "xmin": 10.0 + shift + x_shift,
                    "ymin": 20.0,
                    "xmax": 110.0 + shift + x_shift,
                    "ymax": 220.0,
                    "confidence": 0.95,
                }
            )

    return pd.DataFrame(rows)


def _inputs(
    root: Path,
    *,
    independent: bool,
):
    audit = _audit(
        root,
        independent=independent,
    )

    reference = prepare_visus_canonical_aoi_intake(
        audit,
        _reference_table(),
        extraction_basis=("Reviewed deterministic coverage fixture."),
        frame_index_base=1,
    )

    prediction = prepare_visus_dynamic_aoi_predictions(
        audit,
        _prediction_table(),
        model_name="fixture-detector",
        model_version="1.0.0",
        prediction_basis=("Reviewed deterministic fixture output."),
        prediction_coordinate_unit="pixels",
        frame_index_base=1,
        model_artifact_sha256="a" * 64,
    )

    timestamps = {
        f"S{index:02d}": [
            0.0,
            40.0,
            80.0,
        ]
        for index in range(1, 12)
    }

    return (
        audit,
        reference,
        prediction,
        timestamps,
    )


def _resign_report(
    report: dict[str, Any],
) -> None:
    body = {key: value for key, value in report.items() if key != "report_fingerprint_sha256"}

    report["report_fingerprint_sha256"] = benchmark_fingerprint(body)


IDENTITY = {
    "source_audit_report_fingerprint_sha256": ("a" * 64),
    "source_audit_spec_fingerprint_sha256": ("b" * 64),
    "source_manifest_fingerprint_sha256": ("c" * 64),
}


def _suite_protocol(
    *,
    independent: bool = False,
    include_hh: bool = False,
) -> dict[str, Any]:
    return {
        "reference_stream_id": "annotator_a",
        "model_name": "fixture-detector",
        "model_version": "1.0.0",
        "timestamp_grid_basis": "fixture-grid",
        "timestamp_grids": {
            "S01": "grid-fingerprint",
        },
        "independent_annotation_streams_verified": (independent),
        "human_human_agreement_included": (include_hh),
        "human_agreement_stream_ids": (
            [
                "annotator_a",
                "annotator_b",
            ]
            if include_hh
            else []
        ),
    }


def _reference_child() -> dict[str, Any]:
    return {
        **IDENTITY,
        "status": "verified-canonical-intake",
        "annotation_stream_ids": [
            "annotator_a",
            "annotator_b",
        ],
    }


def _prediction_child() -> dict[str, Any]:
    return {
        **IDENTITY,
        "status": "verified-prediction-intake",
        "evaluation_timestamp_grid_generated": False,
        "model": {
            "name": "fixture-detector",
            "version": "1.0.0",
        },
    }


def _model_child() -> dict[str, Any]:
    return {
        "protocol": {
            **IDENTITY,
            "reference_stream_id": "annotator_a",
            "timestamp_grid_explicit": True,
            "timestamp_grid_basis": "fixture-grid",
            "timestamp_grids": {
                "S01": "grid-fingerprint",
            },
            "human_human_agreement_claimed": False,
        },
        "model": {
            "name": "fixture-detector",
            "version": "1.0.0",
        },
    }


def _human_child() -> dict[str, Any]:
    return {
        "protocol": {
            **IDENTITY,
            "independent_annotation_streams_verified": True,
            "human_agreement_reference_not_ground_truth": True,
            "left_stream_id": "annotator_a",
            "right_stream_id": "annotator_b",
            "timestamp_grid_basis": "fixture-grid",
        }
    }


def _fingerprinted(
    report: dict[str, Any],
) -> dict[str, Any]:
    result = copy.deepcopy(report)
    _resign_report(result)
    return result


def _write_manifest(
    path: Path,
    manifest: dict[str, Any],
) -> None:
    body = {key: value for key, value in manifest.items() if key != "suite_fingerprint_sha256"}

    manifest["suite_fingerprint_sha256"] = benchmark_fingerprint(body)

    path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _manifest_fixture(
    root: Path,
) -> tuple[
    Path,
    dict[str, Any],
    dict[str, dict[str, Any]],
]:
    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    children = {
        "human_reference_intake": (_fingerprinted(_reference_child())),
        "model_prediction_intake": (_fingerprinted(_prediction_child())),
        "model_human_validation": (_fingerprinted(_model_child())),
    }

    filenames = {
        "human_reference_intake": ("reference.json"),
        "model_prediction_intake": ("prediction.json"),
        "model_human_validation": ("model.json"),
    }

    records = []

    for name, child in children.items():
        filename = filenames[name]

        (root / filename).write_text(
            json.dumps(child),
            encoding="utf-8",
        )

        records.append(
            {
                "name": name,
                "path": filename,
                "report_fingerprint_sha256": child["report_fingerprint_sha256"],
            }
        )

    manifest = {
        "suite": ("visus-dynamic-aoi-validation-v1"),
        "status": "complete",
        "source": {
            **IDENTITY,
        },
        "protocol": _suite_protocol(),
        "reports": records,
    }

    path = root / "visus-dynamic-aoi-suite-manifest.json"

    _write_manifest(
        path,
        manifest,
    )

    return (
        path,
        manifest,
        children,
    )


def test_report_fingerprint_success_and_guards() -> None:
    report = _fingerprinted(
        {
            "status": "ok",
        }
    )

    assert (
        len(
            suite._report_fingerprint(
                report,
                name="test",
            )
        )
        == 64
    )

    bad = {
        "status": "ok",
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing a valid fingerprint",
    ):
        suite._report_fingerprint(
            bad,
            name="test",
        )

    bad = {
        "status": "ok",
        "report_fingerprint_sha256": ("0" * 64),
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not revalidate",
    ):
        suite._report_fingerprint(
            bad,
            name="test",
        )


def test_audit_identity_type_and_status_guards(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        TypeError,
        match="VisusSourceAuditRun",
    ):
        suite._audit_identity(object())

    audit = _audit(
        tmp_path / "source",
        independent=False,
    )

    audit.report["status"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not verified",
    ):
        suite._audit_identity(audit)


def test_audit_identity_fingerprint_guards(
    tmp_path: Path,
) -> None:
    audit = _audit(
        tmp_path / "source",
        independent=False,
    )

    audit.report["report_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report fingerprint",
    ):
        suite._audit_identity(audit)

    audit = _audit(
        tmp_path / "source2",
        independent=False,
    )

    audit.report["spec_fingerprint_sha256"] = "0" * 64
    _resign_report(audit.report)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="specification fingerprint",
    ):
        suite._audit_identity(audit)

    audit = _audit(
        tmp_path / "source3",
        independent=False,
    )

    audit.report["inventory"]["manifest_fingerprint_sha256"] = "bad"
    _resign_report(audit.report)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="manifest fingerprint",
    ):
        suite._audit_identity(audit)


def test_child_source_identity_protocol_guard() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="protocol must be an object",
    ):
        suite._child_source_identity(
            {},
            benchmark_report=True,
        )

    assert (
        suite._child_source_identity(
            IDENTITY,
            benchmark_report=False,
        )
        == IDENTITY
    )


def test_verify_intake_type_guards(
    tmp_path: Path,
) -> None:
    (
        audit,
        reference,
        prediction,
        _,
    ) = _inputs(
        tmp_path,
        independent=False,
    )

    with pytest.raises(
        TypeError,
        match="reference_intake",
    ):
        suite._verify_intakes(
            audit,
            object(),
            prediction,
        )

    with pytest.raises(
        TypeError,
        match="prediction_intake",
    ):
        suite._verify_intakes(
            audit,
            reference,
            object(),
        )


@pytest.mark.parametrize(
    ("target", "mutation", "match"),
    [
        (
            "reference",
            (
                "status",
                "bad",
            ),
            "human-reference intake is not verified",
        ),
        (
            "prediction",
            (
                "status",
                "bad",
            ),
            "model-prediction intake is not verified",
        ),
        (
            "prediction",
            (
                "evaluation_timestamp_grid_generated",
                True,
            ),
            "must not generate",
        ),
        (
            "prediction",
            (
                "model",
                None,
            ),
            "missing model provenance",
        ),
    ],
)
def test_verify_intake_contract_guards(
    tmp_path: Path,
    target: str,
    mutation: tuple[str, Any],
    match: str,
) -> None:
    (
        audit,
        reference,
        prediction,
        _,
    ) = _inputs(
        tmp_path,
        independent=False,
    )

    selected = reference if target == "reference" else prediction

    key, value = mutation
    selected.report[key] = value
    _resign_report(selected.report)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        suite._verify_intakes(
            audit,
            reference,
            prediction,
        )


@pytest.mark.parametrize(
    "target",
    [
        "reference",
        "prediction",
    ],
)
def test_verify_intake_source_identity_guard(
    tmp_path: Path,
    target: str,
) -> None:
    (
        audit,
        reference,
        prediction,
        _,
    ) = _inputs(
        tmp_path,
        independent=False,
    )

    selected = reference if target == "reference" else prediction

    selected.report["source_manifest_fingerprint_sha256"] = "0" * 64
    _resign_report(selected.report)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity",
    ):
        suite._verify_intakes(
            audit,
            reference,
            prediction,
        )


@pytest.mark.parametrize(
    ("name", "version"),
    [
        ("", "1.0"),
        ("model", ""),
    ],
)
def test_verify_intake_model_identity_guard(
    tmp_path: Path,
    name: str,
    version: str,
) -> None:
    (
        audit,
        reference,
        prediction,
        _,
    ) = _inputs(
        tmp_path,
        independent=False,
    )

    prediction.report["model"]["name"] = name
    prediction.report["model"]["version"] = version

    _resign_report(prediction.report)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="model identity is incomplete",
    ):
        suite._verify_intakes(
            audit,
            reference,
            prediction,
        )


def test_target_paths_and_preflight(
    tmp_path: Path,
) -> None:
    without = suite._target_paths(
        tmp_path,
        include_human_agreement=False,
    )

    assert "human_human_agreement" not in without

    with_hh = suite._target_paths(
        tmp_path,
        include_human_agreement=True,
    )

    assert "human_human_agreement" in with_hh

    manifest = tmp_path / "visus-dynamic-aoi-suite-manifest.json"

    suite._preflight(
        with_hh,
        manifest,
        overwrite=True,
    )

    existing = with_hh["human_reference_intake"]
    existing.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    existing.write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        suite._preflight(
            with_hh,
            manifest,
            overwrite=False,
        )


@pytest.mark.parametrize(
    "relative",
    [
        "",
        "../escape.json",
    ],
)
def test_safe_child_path_rejects_unsafe(
    tmp_path: Path,
    relative: str,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="unsafe report path",
    ):
        suite._safe_child_path(
            tmp_path,
            relative,
        )


def test_safe_child_path_accepts_child(
    tmp_path: Path,
) -> None:
    result = suite._safe_child_path(
        tmp_path,
        "child.json",
    )

    assert result == (tmp_path / "child.json").resolve()


def test_manifest_path_directory_and_file(
    tmp_path: Path,
) -> None:
    tmp_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    assert suite._manifest_path(tmp_path).name == ("visus-dynamic-aoi-suite-manifest.json")

    explicit = tmp_path / "custom.json"

    assert suite._manifest_path(explicit) == explicit


def test_expected_report_names() -> None:
    assert suite._expected_report_names(
        {
            "human_human_agreement_included": False,
        }
    ) == {
        "human_reference_intake",
        "model_prediction_intake",
        "model_human_validation",
    }

    assert "human_human_agreement" in suite._expected_report_names(
        {
            "human_human_agreement_included": True,
        }
    )


def test_child_semantics_reference_guards() -> None:
    protocol = _suite_protocol()
    report = _reference_child()

    suite._validate_child_semantics(
        "human_reference_intake",
        report,
        source_identity=IDENTITY,
        protocol=protocol,
    )

    bad = copy.deepcopy(report)
    bad["status"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not verified",
    ):
        suite._validate_child_semantics(
            "human_reference_intake",
            bad,
            source_identity=IDENTITY,
            protocol=protocol,
        )

    bad = copy.deepcopy(report)
    bad["annotation_stream_ids"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="reference stream is absent",
    ):
        suite._validate_child_semantics(
            "human_reference_intake",
            bad,
            source_identity=IDENTITY,
            protocol=protocol,
        )


def test_child_semantics_prediction_guards() -> None:
    protocol = _suite_protocol()
    report = _prediction_child()

    suite._validate_child_semantics(
        "model_prediction_intake",
        report,
        source_identity=IDENTITY,
        protocol=protocol,
    )

    bad = copy.deepcopy(report)
    bad["status"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not verified",
    ):
        suite._validate_child_semantics(
            "model_prediction_intake",
            bad,
            source_identity=IDENTITY,
            protocol=protocol,
        )

    bad = copy.deepcopy(report)
    bad["evaluation_timestamp_grid_generated"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="improperly generated",
    ):
        suite._validate_child_semantics(
            "model_prediction_intake",
            bad,
            source_identity=IDENTITY,
            protocol=protocol,
        )

    bad = copy.deepcopy(report)
    bad["model"]["name"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="model identity mismatch",
    ):
        suite._validate_child_semantics(
            "model_prediction_intake",
            bad,
            source_identity=IDENTITY,
            protocol=protocol,
        )


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (
            (
                "reference_stream_id",
                "wrong",
            ),
            "reference stream mismatch",
        ),
        (
            (
                "timestamp_grid_explicit",
                False,
            ),
            "lacks an explicit grid",
        ),
        (
            (
                "timestamp_grid_basis",
                "wrong",
            ),
            "basis mismatch",
        ),
        (
            (
                "timestamp_grids",
                {},
            ),
            "fingerprints mismatch",
        ),
        (
            (
                "human_human_agreement_claimed",
                True,
            ),
            "invalid HH claim",
        ),
    ],
)
def test_child_semantics_model_human_guards(
    mutation: tuple[str, Any],
    match: str,
) -> None:
    protocol = _suite_protocol()
    report = _model_child()

    key, value = mutation
    report["protocol"][key] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        suite._validate_child_semantics(
            "model_human_validation",
            report,
            source_identity=IDENTITY,
            protocol=protocol,
        )


def test_child_semantics_model_human_model_guard() -> None:
    protocol = _suite_protocol()
    report = _model_child()

    report["model"]["version"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="model identity mismatch",
    ):
        suite._validate_child_semantics(
            "model_human_validation",
            report,
            source_identity=IDENTITY,
            protocol=protocol,
        )


@pytest.mark.parametrize(
    ("case", "match"),
    [
        (
            "suite_independence",
            "lacks suite independence proof",
        ),
        (
            "child_independence",
            "lacks independence proof",
        ),
        (
            "ground_truth",
            "not-ground-truth",
        ),
        (
            "pair",
            "stream pair mismatch",
        ),
        (
            "basis",
            "basis mismatch",
        ),
    ],
)
def test_child_semantics_human_agreement_guards(
    case: str,
    match: str,
) -> None:
    protocol = _suite_protocol(
        independent=True,
        include_hh=True,
    )
    report = _human_child()

    if case == "suite_independence":
        protocol["independent_annotation_streams_verified"] = False

    elif case == "child_independence":
        report["protocol"]["independent_annotation_streams_verified"] = False

    elif case == "ground_truth":
        report["protocol"]["human_agreement_reference_not_ground_truth"] = False

    elif case == "pair":
        report["protocol"]["right_stream_id"] = "wrong"

    elif case == "basis":
        report["protocol"]["timestamp_grid_basis"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        suite._validate_child_semantics(
            "human_human_agreement",
            report,
            source_identity=IDENTITY,
            protocol=protocol,
        )


def test_child_semantics_generic_identity_guard() -> None:
    report = _reference_child()

    report["source_manifest_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity mismatch",
    ):
        suite._validate_child_semantics(
            "human_reference_intake",
            report,
            source_identity=IDENTITY,
            protocol=_suite_protocol(),
        )


def test_manifest_file_level_guards(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        suite.validate_visus_dynamic_aoi_suite_manifest(missing)

    bad = tmp_path / "bad.json"
    bad.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not valid JSON",
    ):
        suite.validate_visus_dynamic_aoi_suite_manifest(bad)

    array = tmp_path / "array.json"
    array.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        suite.validate_visus_dynamic_aoi_suite_manifest(array)


@pytest.mark.parametrize(
    ("case", "match"),
    [
        (
            "missing",
            "missing fields",
        ),
        (
            "identity",
            "identity/status is invalid",
        ),
        (
            "fingerprint",
            "fingerprint mismatch",
        ),
        (
            "source_structure",
            "structure is invalid",
        ),
        (
            "protocol_structure",
            "structure is invalid",
        ),
        (
            "reports_structure",
            "structure is invalid",
        ),
        (
            "source_fp",
            "fingerprints are incomplete",
        ),
        (
            "record_type",
            "invalid report record",
        ),
        (
            "record_duplicate",
            "unique and complete",
        ),
        (
            "inventory",
            "report inventory mismatch",
        ),
        (
            "independence",
            "omits human-human agreement",
        ),
    ],
)
def test_manifest_structural_guards(
    tmp_path: Path,
    case: str,
    match: str,
) -> None:
    path, manifest, _ = _manifest_fixture(tmp_path / case)

    if case == "missing":
        manifest.pop("source")

    elif case == "identity":
        manifest["status"] = "bad"

    elif case == "fingerprint":
        _write_manifest(
            path,
            manifest,
        )
        manifest["suite_fingerprint_sha256"] = "0" * 64

        path.write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        with pytest.raises(
            BenchmarkIntegrityError,
            match=match,
        ):
            suite.validate_visus_dynamic_aoi_suite_manifest(
                path,
                verify_reports=False,
            )

        return

    elif case == "source_structure":
        manifest["source"] = []

    elif case == "protocol_structure":
        manifest["protocol"] = []

    elif case == "reports_structure":
        manifest["reports"] = {}

    elif case == "source_fp":
        manifest["source"]["source_manifest_fingerprint_sha256"] = "bad"

    elif case == "record_type":
        manifest["reports"][0] = "bad"

    elif case == "record_duplicate":
        manifest["reports"][1]["name"] = manifest["reports"][0]["name"]

    elif case == "inventory":
        manifest["reports"].pop()

    elif case == "independence":
        manifest["protocol"]["independent_annotation_streams_verified"] = True

    _write_manifest(
        path,
        manifest,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        suite.validate_visus_dynamic_aoi_suite_manifest(
            path,
            verify_reports=False,
        )


def test_manifest_verify_reports_false_success(
    tmp_path: Path,
) -> None:
    path, _, _ = _manifest_fixture(tmp_path)

    result = suite.validate_visus_dynamic_aoi_suite_manifest(
        path,
        verify_reports=False,
    )

    assert result["reports_verified"] is False

    assert result["report_count"] == 3


def test_manifest_verify_reports_success(
    tmp_path: Path,
) -> None:
    path, _, _ = _manifest_fixture(tmp_path)

    result = suite.validate_visus_dynamic_aoi_suite_manifest(
        path,
        verify_reports=True,
    )

    assert result["reports_verified"] is True


@pytest.mark.parametrize(
    ("case", "match"),
    [
        (
            "missing",
            "child report is missing",
        ),
        (
            "json",
            "child is invalid JSON",
        ),
        (
            "object",
            "child must be an object",
        ),
        (
            "manifest_fingerprint",
            "manifest/child fingerprint mismatch",
        ),
        (
            "semantics",
            "reference-intake child is not verified",
        ),
    ],
)
def test_manifest_child_guards(
    tmp_path: Path,
    case: str,
    match: str,
) -> None:
    path, manifest, children = _manifest_fixture(tmp_path / case)

    record = next(row for row in manifest["reports"] if row["name"] == "human_reference_intake")

    child_path = path.parent / record["path"]

    if case == "missing":
        child_path.unlink()

    elif case == "json":
        child_path.write_text(
            "{",
            encoding="utf-8",
        )

    elif case == "object":
        child_path.write_text(
            "[]",
            encoding="utf-8",
        )

    elif case == "manifest_fingerprint":
        record["report_fingerprint_sha256"] = "0" * 64
        _write_manifest(
            path,
            manifest,
        )

    elif case == "semantics":
        child = copy.deepcopy(children["human_reference_intake"])

        child["status"] = "bad"
        _resign_report(child)

        child_path.write_text(
            json.dumps(child),
            encoding="utf-8",
        )

        record["report_fingerprint_sha256"] = child["report_fingerprint_sha256"]

        _write_manifest(
            path,
            manifest,
        )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        suite.validate_visus_dynamic_aoi_suite_manifest(
            path,
            verify_reports=True,
        )


def test_suite_reference_stream_guards(
    tmp_path: Path,
) -> None:
    (
        audit,
        reference,
        prediction,
        timestamps,
    ) = _inputs(
        tmp_path / "source",
        independent=False,
    )

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        suite.run_visus_dynamic_aoi_validation_suite(
            audit,
            reference,
            prediction,
            timestamps,
            tmp_path / "empty",
            reference_stream_id=" ",
            timestamp_grid_basis="fixture",
            max_interpolation_gap_ms=100.0,
        )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="absent from canonical intake",
    ):
        suite.run_visus_dynamic_aoi_validation_suite(
            audit,
            reference,
            prediction,
            timestamps,
            tmp_path / "missing",
            reference_stream_id="missing",
            timestamp_grid_basis="fixture",
            max_interpolation_gap_ms=100.0,
        )


@pytest.mark.parametrize(
    ("pair", "match", "error"),
    [
        (
            (
                "annotator_a",
                "annotator_a",
            ),
            "distinct non-empty",
            ValueError,
        ),
        (
            (
                "",
                "annotator_b",
            ),
            "distinct non-empty",
            ValueError,
        ),
        (
            (
                "annotator_a",
                "missing",
            ),
            "absent from canonical intake",
            BenchmarkIntegrityError,
        ),
    ],
)
def test_suite_human_pair_guards(
    tmp_path: Path,
    pair: tuple[str, str],
    match: str,
    error: type[Exception],
) -> None:
    (
        audit,
        reference,
        prediction,
        timestamps,
    ) = _inputs(
        tmp_path / "source",
        independent=True,
    )

    with pytest.raises(
        error,
        match=match,
    ):
        suite.run_visus_dynamic_aoi_validation_suite(
            audit,
            reference,
            prediction,
            timestamps,
            tmp_path / "suite",
            reference_stream_id="annotator_a",
            timestamp_grid_basis="fixture",
            max_interpolation_gap_ms=100.0,
            human_agreement_streams=pair,
        )


def test_suite_preflight_blocks_existing_output(
    tmp_path: Path,
) -> None:
    (
        audit,
        reference,
        prediction,
        timestamps,
    ) = _inputs(
        tmp_path / "source",
        independent=False,
    )

    output = tmp_path / "suite"
    output.mkdir()

    (output / "visus-human-reference-intake.json").write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        suite.run_visus_dynamic_aoi_validation_suite(
            audit,
            reference,
            prediction,
            timestamps,
            output,
            reference_stream_id="annotator_a",
            timestamp_grid_basis="fixture",
            max_interpolation_gap_ms=100.0,
        )
