from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.dashboard as dashboard
import gazeforge.location_scale_refit_residual_calibration as refit
import gazeforge.location_scale_residual_calibration as residual
import gazeforge.video_frame_derivation as video
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError

# ============================================================
# SHARED HELPERS
# ============================================================


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resign(payload: dict) -> dict:
    body = {key: value for key, value in payload.items() if key != "certificate_fingerprint_sha256"}
    payload["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    return payload


def _summary(module) -> pd.DataFrame:
    frame = pd.DataFrame(
        [
            {
                "metric": metric,
                "observed": 0.0,
                "simulation_mean": 0.0,
                "envelope_lower": -1.0,
                "envelope_upper": 1.0,
                "simulation_percentile": 0.5,
                "outside_envelope": False,
            }
            for metric in module._METRIC_ORDER
        ]
    )
    return frame.loc[:, list(module._SUMMARY_COLUMNS)]


# ============================================================
# VIDEO FRAME DERIVATION
# ============================================================


class FakeExtractor:
    def __init__(self, artifact: Path):
        self.artifact = artifact

    def identify(self):
        return video.FrameExtractorIdentity(
            name="ffmpeg",
            version="fixture-1",
            artifact_path=str(self.artifact),
            artifact_sha256=_sha(self.artifact),
        )

    def extract(
        self,
        source_video,
        output_dir,
        *,
        frame_index_base,
        jpeg_quality,
    ):
        del source_video, jpeg_quality

        for offset in range(2):
            index = frame_index_base + offset
            (output_dir / f"{index:06d}.jpg").write_bytes(b"jpeg" + bytes([offset]))

        return video.FrameExtractionExecution(
            argv=("ffmpeg", "fixture"),
            returncode=0,
            stdout="ok",
            stderr="",
        )


def _video_fixture(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")

    artifact = tmp_path / "ffmpeg"
    artifact.write_bytes(b"binary")

    extractor = FakeExtractor(artifact)
    identity = extractor.identify()

    config = video.VideoFrameDerivationConfig(
        source_video_path=source,
        source_video_sha256=_sha(source),
        output_dir=tmp_path / "frames",
        expected_extractor_name=identity.name,
        expected_extractor_version=identity.version,
        expected_extractor_sha256=identity.artifact_sha256,
        frame_index_base=0,
        jpeg_quality=2,
    )

    run = video.derive_video_frames(
        config,
        extractor=extractor,
    )

    return run, source, artifact


def _resign_video(run, report):
    body = {key: value for key, value in report.items() if key != "report_fingerprint_sha256"}

    report["report_fingerprint_sha256"] = benchmark_fingerprint(body)

    return video.VideoFrameDerivationRun(
        source_video_path=run.source_video_path,
        frame_dir=run.frame_dir,
        report=report,
    )


@pytest.mark.parametrize(
    "value",
    ["", "VERIFY", "replace-me"],
)
def test_video_resolved_invalid(value):
    with pytest.raises(ValueError):
        video._resolved(value, label="fixture")


def test_video_resolved_valid():
    assert video._resolved(" ffmpeg ", label="x") == "ffmpeg"


@pytest.mark.parametrize(
    "value",
    ["x", "a" * 63, "a" * 65, "g" * 64],
)
def test_video_sha_invalid(value):
    with pytest.raises(ValueError):
        video._sha256(value, label="fixture")


def test_video_sha_normalizes():
    assert video._sha256("A" * 64, label="x") == "a" * 64


def test_video_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        video._file_sha256(
            tmp_path / "missing",
            label="fixture",
        )


def test_video_file_empty(tmp_path):
    path = tmp_path / "empty"
    path.write_bytes(b"")

    with pytest.raises(BenchmarkIntegrityError):
        video._file_sha256(path, label="fixture")


def test_video_config_wrong_type():
    with pytest.raises(TypeError):
        video._validate_config(object())


def test_video_output_is_file(tmp_path):
    path = tmp_path / "frames"
    path.write_text("x", encoding="utf-8")

    with pytest.raises(SchemaError):
        video._prepare_empty_output_dir(path)


def test_video_output_nonempty(tmp_path):
    path = tmp_path / "frames"
    path.mkdir()
    (path / "x").write_text("x", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError):
        video._prepare_empty_output_dir(path)


def test_video_manifest_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        video._frame_manifest(
            tmp_path / "missing",
            frame_index_base=0,
        )


def test_video_manifest_empty(tmp_path):
    path = tmp_path / "frames"
    path.mkdir()

    with pytest.raises(BenchmarkIntegrityError):
        video._frame_manifest(path, frame_index_base=0)


def test_video_manifest_nonjpeg(tmp_path):
    path = tmp_path / "frames"
    path.mkdir()
    (path / "000000.png").write_bytes(b"x")

    with pytest.raises(SchemaError, match="non-JPEG"):
        video._frame_manifest(path, frame_index_base=0)


def test_video_manifest_bad_stem(tmp_path):
    path = tmp_path / "frames"
    path.mkdir()
    (path / "frame.jpg").write_bytes(b"x")

    with pytest.raises(SchemaError, match="integer"):
        video._frame_manifest(path, frame_index_base=0)


def test_video_manifest_duplicate_index(tmp_path):
    path = tmp_path / "frames"
    path.mkdir()
    (path / "0.jpg").write_bytes(b"x")
    (path / "00.jpeg").write_bytes(b"y")

    with pytest.raises(SchemaError, match="unique"):
        video._frame_manifest(path, frame_index_base=0)


def test_video_manifest_gap(tmp_path):
    path = tmp_path / "frames"
    path.mkdir()
    (path / "000000.jpg").write_bytes(b"x")
    (path / "000002.jpg").write_bytes(b"y")

    with pytest.raises(SchemaError, match="contiguous"):
        video._frame_manifest(path, frame_index_base=0)


def test_video_identity_wrong_type():
    with pytest.raises(TypeError):
        video._validate_identity(
            object(),
            expected_name="ffmpeg",
            expected_version="1",
            expected_sha256="a" * 64,
        )


def test_video_identity_name_mismatch(tmp_path):
    artifact = tmp_path / "ffmpeg"
    artifact.write_bytes(b"x")

    identity = video.FrameExtractorIdentity(
        name="other",
        version="1",
        artifact_path=str(artifact),
        artifact_sha256=_sha(artifact),
    )

    with pytest.raises(BenchmarkIntegrityError, match="name mismatch"):
        video._validate_identity(
            identity,
            expected_name="ffmpeg",
            expected_version="1",
            expected_sha256=_sha(artifact),
        )


def test_video_identity_version_mismatch(tmp_path):
    artifact = tmp_path / "ffmpeg"
    artifact.write_bytes(b"x")

    identity = video.FrameExtractorIdentity(
        name="ffmpeg",
        version="wrong",
        artifact_path=str(artifact),
        artifact_sha256=_sha(artifact),
    )

    with pytest.raises(BenchmarkIntegrityError, match="version"):
        video._validate_identity(
            identity,
            expected_name="ffmpeg",
            expected_version="1",
            expected_sha256=_sha(artifact),
        )


def test_video_identity_declared_sha_mismatch(tmp_path):
    artifact = tmp_path / "ffmpeg"
    artifact.write_bytes(b"x")

    identity = video.FrameExtractorIdentity(
        name="ffmpeg",
        version="1",
        artifact_path=str(artifact),
        artifact_sha256="0" * 64,
    )

    with pytest.raises(BenchmarkIntegrityError, match="declared SHA"):
        video._validate_identity(
            identity,
            expected_name="ffmpeg",
            expected_version="1",
            expected_sha256=_sha(artifact),
        )


def test_ffmpeg_identification_nonzero(tmp_path, monkeypatch):
    binary = tmp_path / "ffmpeg"
    binary.write_bytes(b"x")

    monkeypatch.setattr(
        video.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="bad",
        ),
    )

    with pytest.raises(BenchmarkIntegrityError, match="non-zero"):
        video.FFmpegJPEGFrameExtractor(binary).identify()


def test_ffmpeg_identification_empty_output(tmp_path, monkeypatch):
    binary = tmp_path / "ffmpeg"
    binary.write_bytes(b"x")

    monkeypatch.setattr(
        video.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="",
        ),
    )

    with pytest.raises(BenchmarkIntegrityError, match="empty"):
        video.FFmpegJPEGFrameExtractor(binary).identify()


def test_video_validation_wrong_type():
    with pytest.raises(TypeError):
        video.validate_video_frame_derivation_run(object())


def test_video_validation_missing_fingerprint(tmp_path):
    run, _, _ = _video_fixture(tmp_path)

    report = deepcopy(run.report)
    report.pop("report_fingerprint_sha256")

    broken = video.VideoFrameDerivationRun(
        source_video_path=run.source_video_path,
        frame_dir=run.frame_dir,
        report=report,
    )

    with pytest.raises(BenchmarkIntegrityError, match="fingerprint is missing"):
        video.validate_video_frame_derivation_run(broken)


def test_video_validation_mechanical_flag(tmp_path):
    run, _, _ = _video_fixture(tmp_path)

    report = deepcopy(run.report)
    report["frame_derivation_mechanically_verified"] = False

    with pytest.raises(BenchmarkIntegrityError, match="mechanically verified"):
        video.validate_video_frame_derivation_run(_resign_video(run, report))


@pytest.mark.parametrize(
    "field",
    [
        "empirical_performance_claim_created",
        "dataset_source_authority_implied",
        "dataset_rights_implied",
        "raw_source_redistribution_authorized",
    ],
)
def test_video_validation_forbidden_claim(tmp_path, field):
    run, _, _ = _video_fixture(tmp_path)

    report = deepcopy(run.report)
    report[field] = True

    with pytest.raises(BenchmarkIntegrityError, match=field):
        video.validate_video_frame_derivation_run(_resign_video(run, report))


def test_video_validation_missing_source(tmp_path):
    run, _, _ = _video_fixture(tmp_path)

    report = deepcopy(run.report)
    report["source_video"] = None

    with pytest.raises(BenchmarkIntegrityError, match="source-video metadata"):
        video.validate_video_frame_derivation_run(_resign_video(run, report))


def test_video_validation_source_path(tmp_path):
    run, source, _ = _video_fixture(tmp_path)

    other = tmp_path / "other.mp4"
    other.write_bytes(source.read_bytes())

    report = deepcopy(run.report)
    report["source_video"]["path"] = str(other)

    with pytest.raises(BenchmarkIntegrityError, match="path binding"):
        video.validate_video_frame_derivation_run(_resign_video(run, report))


def test_video_validation_source_bytes(tmp_path):
    run, source, _ = _video_fixture(tmp_path)

    source.write_bytes(b"changed")

    with pytest.raises(BenchmarkIntegrityError, match="source-video bytes"):
        video.validate_video_frame_derivation_run(run)


def test_video_validation_missing_extractor(tmp_path):
    run, _, _ = _video_fixture(tmp_path)

    report = deepcopy(run.report)
    report["extractor"] = None

    with pytest.raises(BenchmarkIntegrityError, match="extractor metadata"):
        video.validate_video_frame_derivation_run(_resign_video(run, report))


def test_video_validation_missing_frames(tmp_path):
    run, _, _ = _video_fixture(tmp_path)

    report = deepcopy(run.report)
    report["frames"] = None

    with pytest.raises(BenchmarkIntegrityError, match="frame metadata"):
        video.validate_video_frame_derivation_run(_resign_video(run, report))


def test_video_validation_frame_directory(tmp_path):
    run, _, _ = _video_fixture(tmp_path)

    other = tmp_path / "other"
    other.mkdir()

    report = deepcopy(run.report)
    report["frames"]["directory"] = str(other)

    with pytest.raises(BenchmarkIntegrityError, match="output-directory"):
        video.validate_video_frame_derivation_run(_resign_video(run, report))


def test_video_validation_manifest_fingerprint(tmp_path):
    run, _, _ = _video_fixture(tmp_path)

    report = deepcopy(run.report)
    report["frames"]["manifest_fingerprint_sha256"] = "0" * 64

    with pytest.raises(BenchmarkIntegrityError, match="manifest fingerprint"):
        video.validate_video_frame_derivation_run(_resign_video(run, report))


# ============================================================
# DASHBOARD
# ============================================================


def _dashboard_report():
    body = {
        "benchmark": {
            "name": "fixture",
            "version": "1",
            "source": "fixture",
            "validation_scope": "fixture-scope",
            "annotation_origin": "expert-manual",
            "sampling_origin": "native",
            "reference_strength": "human-reference",
            "sampling_rates_hz": [60.0],
        },
        "model": {"name": "model"},
        "protocol": {},
        "metrics": {},
    }

    return {
        **body,
        "report_fingerprint_sha256": benchmark_fingerprint(body),
    }


def test_dashboard_report_wrong_type():
    with pytest.raises(BenchmarkIntegrityError):
        dashboard.validate_frozen_benchmark_report([])


def test_dashboard_report_missing_fields():
    with pytest.raises(BenchmarkIntegrityError, match="missing required"):
        dashboard.validate_frozen_benchmark_report({})


def test_dashboard_benchmark_not_mapping():
    report = _dashboard_report()
    report["benchmark"] = "bad"

    body = {key: report[key] for key in dashboard._REPORT_BODY_KEYS}

    report["report_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(BenchmarkIntegrityError, match="metadata"):
        dashboard.validate_frozen_benchmark_report(report)


def test_dashboard_load_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        dashboard.load_frozen_benchmark_report(tmp_path / "missing.json")


def test_dashboard_load_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="Invalid benchmark JSON"):
        dashboard.load_frozen_benchmark_report(path)


def test_dashboard_discovery_missing_root(tmp_path):
    with pytest.raises(FileNotFoundError):
        dashboard.discover_frozen_benchmark_reports(tmp_path / "missing")


def test_dashboard_discovery_skips_noise(tmp_path):
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    (tmp_path / "list.json").write_text("[]", encoding="utf-8")

    assert dashboard.discover_frozen_benchmark_reports(tmp_path) == ()


def test_dashboard_nonrecursive_manifest(tmp_path):
    path = tmp_path / "native-event-suite-manifest.json"
    path.write_text("{}", encoding="utf-8")

    assert dashboard.discover_native_event_suite_manifests(
        tmp_path,
        recursive=False,
    ) == (path,)


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        (None, ""),
        ("bad", ""),
        ({"models": ["A", "B"]}, "A, B"),
        ({"models": "A"}, "A"),
        ({"name": "M"}, "M"),
        ({"model": "M"}, "M"),
        ({"type": "M"}, "M"),
        ({}, ""),
    ],
)
def test_dashboard_model_names(metadata, expected):
    assert dashboard._model_names(metadata) == expected


def test_dashboard_suite_source_variants():
    assert (
        dashboard._suite_source_fingerprint(
            {
                "source_manifest": {
                    "manifest_fingerprint_sha256": "a" * 64,
                }
            }
        )
        == "a" * 64
    )

    assert (
        dashboard._suite_source_fingerprint(
            {
                "source": {
                    "source_manifest_fingerprint_sha256": "b" * 64,
                }
            }
        )
        == "b" * 64
    )

    assert dashboard._suite_source_fingerprint({}) == ""


def test_dashboard_cross_dataset_unrelated():
    assert dashboard._cross_dataset_dashboard_signal(_dashboard_report()) is False


@pytest.mark.parametrize(
    "kind",
    ["name", "scope", "schema", "design"],
)
def test_dashboard_partial_cross_dataset_signal(kind):
    report = _dashboard_report()

    if kind == "name":
        report["benchmark"]["name"] = dashboard.CROSS_DATASET_BENCHMARK_NAME
    elif kind == "scope":
        report["benchmark"]["validation_scope"] = dashboard.CROSS_DATASET_VALIDATION_SCOPE
    elif kind == "schema":
        report["protocol"]["evidence_schema"] = dashboard.CROSS_DATASET_EVIDENCE_SCHEMA
    else:
        report["protocol"]["validation_design"] = {"validation_design": "leave_one_dataset_out"}

    with pytest.raises(BenchmarkIntegrityError):
        dashboard._cross_dataset_dashboard_signal(report)


def test_dashboard_native_model_missing_intake():
    report = _dashboard_report()
    report["benchmark"]["validation_scope"] = dashboard._NATIVE_MODEL_SCOPE

    with pytest.raises(BenchmarkIntegrityError, match="missing native_intake"):
        dashboard._native_dashboard_child_names(report)


def test_dashboard_native_model_valid():
    report = _dashboard_report()
    report["benchmark"]["validation_scope"] = dashboard._NATIVE_MODEL_SCOPE
    report["protocol"]["native_intake"] = {}

    assert dashboard._native_dashboard_child_names(report) == dashboard._NATIVE_MODEL_CHILDREN


def test_dashboard_native_agreement_wrong_intake():
    report = _dashboard_report()
    report["benchmark"]["validation_scope"] = dashboard._NATIVE_AGREEMENT_SCOPE
    report["protocol"]["native_intake"] = {}

    with pytest.raises(BenchmarkIntegrityError, match="model-only"):
        dashboard._native_dashboard_child_names(report)


def test_dashboard_native_agreement_valid():
    report = _dashboard_report()
    report["benchmark"]["validation_scope"] = dashboard._NATIVE_AGREEMENT_SCOPE

    assert dashboard._native_dashboard_child_names(report) == frozenset({"human_agreement"})


def test_dashboard_native_wrong_scope():
    report = _dashboard_report()
    report["protocol"]["native_intake"] = {}

    with pytest.raises(BenchmarkIntegrityError, match="disagrees"):
        dashboard._native_dashboard_child_names(report)


def test_dashboard_visus_unrelated():
    assert dashboard._visus_dashboard_child_name(_dashboard_report()) is None


def test_dashboard_visus_unknown_schema():
    report = _dashboard_report()
    report["benchmark"]["name"] = "VISUS-fixture"

    with pytest.raises(BenchmarkIntegrityError, match="known review-gated"):
        dashboard._visus_dashboard_child_name(report)


def test_dashboard_visus_scope_mismatch():
    report = _dashboard_report()
    report["benchmark"]["name"] = "VISUS-fixture"
    report["protocol"]["evaluation_type"] = "visus-audited-model-human-dynamic-aoi"
    report["benchmark"]["validation_scope"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="known review-gated child schema",
    ):
        dashboard._visus_dashboard_child_name(report)


def test_dashboard_visus_valid():
    report = _dashboard_report()
    report["benchmark"]["name"] = "VISUS-fixture"
    report["protocol"]["evaluation_type"] = "visus-audited-model-human-dynamic-aoi"
    report["benchmark"]["validation_scope"] = "audited-source-model-human-dynamic-aoi"

    assert dashboard._visus_dashboard_child_name(report) == "model_human_validation"


def test_dashboard_native_requires_manifest(tmp_path):
    report = _dashboard_report()
    report["benchmark"]["validation_scope"] = dashboard._NATIVE_MODEL_SCOPE
    report["protocol"]["native_intake"] = {}

    with pytest.raises(BenchmarkIntegrityError, match="manifest is missing"):
        dashboard._validate_native_report_for_dashboard(
            tmp_path / "report.json",
            report,
        )


def test_dashboard_visus_requires_manifest(tmp_path):
    report = _dashboard_report()
    report["benchmark"]["name"] = "VISUS-fixture"
    report["protocol"]["evaluation_type"] = "visus-audited-model-human-dynamic-aoi"
    report["benchmark"]["validation_scope"] = "audited-source-model-human-dynamic-aoi"

    with pytest.raises(BenchmarkIntegrityError, match="manifest is missing"):
        dashboard._validate_visus_report_for_dashboard(
            tmp_path / "report.json",
            report,
        )


def test_dashboard_markdown_helpers():
    assert dashboard._escape_markdown_cell("a|b\nc") == "a\\|b c"

    rendered = dashboard._markdown_table(
        pd.DataFrame(
            {
                "a": ["x|y"],
                "b": [1],
            }
        )
    )

    assert "x\\|y" in rendered


# ============================================================
# RESIDUAL CALIBRATION
# ============================================================


@pytest.mark.parametrize(
    "value",
    [None, "", "g" * 64, "a" * 63, "a" * 65],
)
def test_residual_invalid_sha(value):
    assert residual._is_sha256_hex(value) is False


def test_residual_moments_too_short():
    with pytest.raises(SchemaError, match="at least two"):
        residual._safe_standardized_moments(np.array([1.0]))


def test_residual_moments_zero_dispersion():
    with pytest.raises(SchemaError, match="dispersion"):
        residual._safe_standardized_moments(np.ones(4))


def test_residual_group_empty():
    with pytest.raises(SchemaError, match="empty group"):
        residual._group_metric_arrays(
            np.array([1.0, 2.0]),
            np.array([0, 0]),
            2,
        )


def test_residual_group_bad_second_moment():
    with pytest.raises(SchemaError, match="second moments"):
        residual._group_metric_arrays(
            np.zeros(2),
            np.array([0, 0]),
            1,
        )


@pytest.mark.parametrize(
    "z",
    [
        np.array([[1.0, 2.0]]),
        np.array([1.0]),
        np.array([1.0, np.nan]),
    ],
)
def test_residual_metrics_bad_vector(z):
    with pytest.raises(SchemaError, match="finite one-dimensional"):
        residual._residual_metrics(
            z,
            np.array([0, 1]),
            2,
            tail_threshold=1.96,
        )


def test_residual_summary_wrong_type():
    with pytest.raises(SchemaError):
        residual._canonical_summary([])


def test_residual_summary_columns():
    frame = _summary(residual).drop(columns=["simulation_mean"])

    with pytest.raises(SchemaError, match="columns"):
        residual._canonical_summary(frame)


def test_residual_summary_length():
    frame = _summary(residual).iloc[:-1]

    with pytest.raises(SchemaError, match="inventory"):
        residual._canonical_summary(frame)


def test_residual_summary_order():
    frame = _summary(residual).iloc[::-1].reset_index(drop=True)

    with pytest.raises(SchemaError, match="order"):
        residual._canonical_summary(frame)


def test_residual_summary_nonfinite():
    frame = _summary(residual)
    frame.loc[0, "observed"] = np.nan

    with pytest.raises(SchemaError, match="non-finite"):
        residual._canonical_summary(frame)


def test_residual_summary_bounds():
    frame = _summary(residual)
    frame.loc[0, "envelope_lower"] = 2.0

    with pytest.raises(SchemaError, match="bounds"):
        residual._canonical_summary(frame)


def test_residual_summary_percentile():
    frame = _summary(residual)
    frame.loc[0, "simulation_percentile"] = 2.0

    with pytest.raises(SchemaError, match="percentiles"):
        residual._canonical_summary(frame)


def test_residual_summary_flag_type():
    frame = _summary(residual)
    frame["outside_envelope"] = frame["outside_envelope"].astype(object)
    frame.at[0, "outside_envelope"] = "false"

    with pytest.raises(SchemaError, match="boolean"):
        residual._canonical_summary(frame)


def test_residual_summary_flag_contradiction():
    frame = _summary(residual)
    frame.at[0, "outside_envelope"] = True

    with pytest.raises(SchemaError, match="contradict"):
        residual._canonical_summary(frame)


def _residual_certificate():
    spec = residual.LocationScaleResidualCalibrationSpec(
        n_simulations=50,
        seed=1,
        envelope_level=0.90,
        max_simulated_residual_draws=100_000,
    )

    summary = _summary(residual)

    summary_fp = residual._summary_fingerprint(summary)

    diagnostic = residual._diagnostic_identity_payload(
        spec=spec,
        model_family="independent_location_scale",
        model_fingerprint="1" * 64,
        base_model_certificate_fingerprint="2" * 64,
        input_fingerprint="3" * 64,
        n_obs=10,
        n_groups=2,
        residuals_fingerprint="4" * 64,
        summary_fingerprint=summary_fp,
    )

    body = {
        "schema": residual._CERTIFICATE_SCHEMA,
        "diagnostic": diagnostic,
        "diagnostic_fingerprint_sha256": benchmark_fingerprint(diagnostic),
        "summary": summary.to_dict(orient="records"),
        "claim_boundary": dict(residual._CLAIM_BOUNDARY),
    }

    return {
        **body,
        "certificate_fingerprint_sha256": benchmark_fingerprint(body),
    }


def test_residual_certificate_valid():
    residual.validate_location_scale_residual_calibration_certificate(_residual_certificate())


def test_residual_certificate_type():
    with pytest.raises(TypeError):
        residual.validate_location_scale_residual_calibration_certificate([])


def test_residual_certificate_schema():
    cert = _residual_certificate()
    cert["schema"] = "bad"
    _resign(cert)

    with pytest.raises(SchemaError, match="schema"):
        residual.validate_location_scale_residual_calibration_certificate(cert)


def test_residual_certificate_claim():
    cert = _residual_certificate()
    cert["claim_boundary"]["global_model_adequacy_established"] = True
    _resign(cert)

    with pytest.raises(SchemaError, match="claim boundary"):
        residual.validate_location_scale_residual_calibration_certificate(cert)


def test_residual_certificate_diagnostic_schema():
    cert = _residual_certificate()
    cert["diagnostic"]["schema"] = "bad"
    _resign(cert)

    with pytest.raises(SchemaError, match="identity"):
        residual.validate_location_scale_residual_calibration_certificate(cert)


def test_residual_certificate_spec():
    cert = _residual_certificate()
    cert["diagnostic"]["spec"]["n_simulations"] = 1
    _resign(cert)

    with pytest.raises(SchemaError, match="invalid spec"):
        residual.validate_location_scale_residual_calibration_certificate(cert)


def test_residual_certificate_family():
    cert = _residual_certificate()
    cert["diagnostic"]["model_family"] = "bad"
    _resign(cert)

    with pytest.raises(SchemaError, match="model family"):
        residual.validate_location_scale_residual_calibration_certificate(cert)


def test_residual_certificate_hash():
    cert = _residual_certificate()
    cert["diagnostic"]["input_fingerprint_sha256"] = "bad"
    _resign(cert)

    with pytest.raises(SchemaError, match="input_fingerprint"):
        residual.validate_location_scale_residual_calibration_certificate(cert)


@pytest.mark.parametrize(
    ("n_obs", "n_groups"),
    [
        (1, 1),
        (10, 1),
        (2, 3),
        (True, 2),
    ],
)
def test_residual_certificate_counts(n_obs, n_groups):
    cert = _residual_certificate()
    cert["diagnostic"]["n_obs"] = n_obs
    cert["diagnostic"]["n_groups"] = n_groups
    _resign(cert)

    with pytest.raises(SchemaError, match="counts"):
        residual.validate_location_scale_residual_calibration_certificate(cert)


def test_residual_certificate_budget():
    cert = _residual_certificate()
    cert["diagnostic"]["n_obs"] = 10_000
    _resign(cert)

    with pytest.raises(SchemaError, match="simulation budget"):
        residual.validate_location_scale_residual_calibration_certificate(cert)


def test_residual_certificate_summary_type():
    cert = _residual_certificate()
    cert["summary"] = {}
    _resign(cert)

    with pytest.raises(SchemaError, match="summary"):
        residual.validate_location_scale_residual_calibration_certificate(cert)


def test_residual_certificate_metric_inventory():
    cert = _residual_certificate()
    cert["summary"][0]["metric"] = "wrong"
    _resign(cert)

    with pytest.raises(SchemaError, match="metric inventory"):
        residual.validate_location_scale_residual_calibration_certificate(cert)


def test_residual_certificate_summary_fp():
    cert = _residual_certificate()
    cert["summary"][0]["observed"] = 0.4
    _resign(cert)

    with pytest.raises(SchemaError, match="summary fingerprint"):
        residual.validate_location_scale_residual_calibration_certificate(cert)


def test_residual_certificate_diagnostic_fp():
    cert = _residual_certificate()
    cert["diagnostic_fingerprint_sha256"] = "0" * 64
    _resign(cert)

    with pytest.raises(SchemaError, match="diagnostic fingerprint"):
        residual.validate_location_scale_residual_calibration_certificate(cert)


# ============================================================
# REFIT RESIDUAL CALIBRATION
# ============================================================


def _ledger():
    return [
        {
            "simulation_index": index,
            "model_fingerprint_sha256": "1" * 64,
            "model_certificate_fingerprint_sha256": "2" * 64,
            "standardized_residuals_fingerprint_sha256": "3" * 64,
        }
        for index in range(2)
    ]


def test_refit_unknown_result():
    with pytest.raises(TypeError, match="supported"):
        refit._fit_function_for_result(object())


def test_refit_ledger_container():
    with pytest.raises(SchemaError, match="length"):
        refit._canonical_refit_ledger(
            {},
            n_simulations=2,
        )


def test_refit_ledger_length():
    with pytest.raises(SchemaError, match="length"):
        refit._canonical_refit_ledger(
            _ledger()[:1],
            n_simulations=2,
        )


def test_refit_ledger_index():
    rows = _ledger()
    rows[0]["simulation_index"] = 1

    with pytest.raises(SchemaError, match="indices"):
        refit._canonical_refit_ledger(
            rows,
            n_simulations=2,
        )


def test_refit_ledger_boolean_index():
    rows = _ledger()
    rows[0]["simulation_index"] = False

    with pytest.raises(SchemaError, match="indices"):
        refit._canonical_refit_ledger(
            rows,
            n_simulations=2,
        )


def test_refit_ledger_hash():
    rows = _ledger()
    rows[0]["model_fingerprint_sha256"] = "bad"

    with pytest.raises(SchemaError, match="model_fingerprint"):
        refit._canonical_refit_ledger(
            rows,
            n_simulations=2,
        )


def _refit_certificate():
    spec = refit.LocationScaleRefitResidualCalibrationSpec(
        n_simulations=2,
        seed=1,
        envelope_level=0.90,
        max_refit_rows=1_000,
    )

    summary = _summary(refit)
    summary_fp = refit._summary_fingerprint(summary)

    ledger = _ledger()

    ledger_fp = refit._refit_ledger_fingerprint(
        ledger,
        n_simulations=2,
    )

    diagnostic = refit._diagnostic_identity_payload(
        spec=spec,
        model_family="independent_location_scale",
        model_fingerprint="1" * 64,
        base_model_certificate_fingerprint="2" * 64,
        input_fingerprint="3" * 64,
        n_obs=10,
        n_groups=2,
        observed_residuals_fingerprint="4" * 64,
        refit_ledger_fingerprint=ledger_fp,
        summary_fingerprint=summary_fp,
    )

    body = {
        "schema": refit._CERTIFICATE_SCHEMA,
        "diagnostic": diagnostic,
        "diagnostic_fingerprint_sha256": benchmark_fingerprint(diagnostic),
        "summary": summary.to_dict(orient="records"),
        "refit_ledger": ledger,
        "claim_boundary": dict(refit._CLAIM_BOUNDARY),
    }

    return {
        **body,
        "certificate_fingerprint_sha256": benchmark_fingerprint(body),
    }


def test_refit_certificate_valid():
    refit.validate_location_scale_refit_residual_calibration_certificate(_refit_certificate())


def test_refit_certificate_type():
    with pytest.raises(TypeError):
        refit.validate_location_scale_refit_residual_calibration_certificate([])


def test_refit_certificate_schema():
    cert = _refit_certificate()
    cert["schema"] = "bad"
    _resign(cert)

    with pytest.raises(SchemaError, match="schema"):
        refit.validate_location_scale_refit_residual_calibration_certificate(cert)


def test_refit_certificate_claim():
    cert = _refit_certificate()
    cert["claim_boundary"]["parameter_estimation_uncertainty_quantified"] = True
    _resign(cert)

    with pytest.raises(SchemaError, match="claim boundary"):
        refit.validate_location_scale_refit_residual_calibration_certificate(cert)


def test_refit_certificate_identity_schema():
    cert = _refit_certificate()
    cert["diagnostic"]["schema"] = "bad"
    _resign(cert)

    with pytest.raises(SchemaError, match="identity"):
        refit.validate_location_scale_refit_residual_calibration_certificate(cert)


def test_refit_certificate_spec():
    cert = _refit_certificate()
    cert["diagnostic"]["spec"]["n_simulations"] = 1
    _resign(cert)

    with pytest.raises(SchemaError, match="invalid spec"):
        refit.validate_location_scale_refit_residual_calibration_certificate(cert)


def test_refit_certificate_family():
    cert = _refit_certificate()
    cert["diagnostic"]["model_family"] = "bad"
    _resign(cert)

    with pytest.raises(SchemaError, match="model family"):
        refit.validate_location_scale_refit_residual_calibration_certificate(cert)


def test_refit_certificate_hash():
    cert = _refit_certificate()
    cert["diagnostic"]["summary_fingerprint_sha256"] = "bad"
    _resign(cert)

    with pytest.raises(SchemaError, match="summary_fingerprint"):
        refit.validate_location_scale_refit_residual_calibration_certificate(cert)


@pytest.mark.parametrize(
    ("n_obs", "n_groups"),
    [
        (1, 1),
        (10, 1),
        (2, 3),
        (True, 2),
    ],
)
def test_refit_certificate_counts(n_obs, n_groups):
    cert = _refit_certificate()
    cert["diagnostic"]["n_obs"] = n_obs
    cert["diagnostic"]["n_groups"] = n_groups
    _resign(cert)

    with pytest.raises(SchemaError, match="counts"):
        refit.validate_location_scale_refit_residual_calibration_certificate(cert)


def test_refit_certificate_budget():
    cert = _refit_certificate()
    cert["diagnostic"]["n_obs"] = 600
    _resign(cert)

    with pytest.raises(SchemaError, match="resource budget"):
        refit.validate_location_scale_refit_residual_calibration_certificate(cert)


def test_refit_certificate_ledger_fp():
    cert = _refit_certificate()
    cert["refit_ledger"][0]["model_fingerprint_sha256"] = "f" * 64
    _resign(cert)

    with pytest.raises(SchemaError, match="ledger fingerprint"):
        refit.validate_location_scale_refit_residual_calibration_certificate(cert)


def test_refit_certificate_metric_inventory():
    cert = _refit_certificate()
    cert["summary"][0]["metric"] = "wrong"
    _resign(cert)

    with pytest.raises(SchemaError, match="metric inventory"):
        refit.validate_location_scale_refit_residual_calibration_certificate(cert)


def test_refit_certificate_columns():
    cert = _refit_certificate()
    cert["summary"][0]["extra"] = 1
    _resign(cert)

    with pytest.raises(SchemaError, match="columns"):
        refit.validate_location_scale_refit_residual_calibration_certificate(cert)


def test_refit_certificate_summary_fp():
    cert = _refit_certificate()
    cert["summary"][0]["observed"] = 0.5
    _resign(cert)

    with pytest.raises(SchemaError, match="summary fingerprint"):
        refit.validate_location_scale_refit_residual_calibration_certificate(cert)


def test_refit_certificate_diagnostic_fp():
    cert = _refit_certificate()
    cert["diagnostic_fingerprint_sha256"] = "0" * 64
    _resign(cert)

    with pytest.raises(SchemaError, match="diagnostic fingerprint"):
        refit.validate_location_scale_refit_residual_calibration_certificate(cert)
