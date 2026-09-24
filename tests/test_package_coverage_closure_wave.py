from __future__ import annotations

import importlib
import importlib.metadata
import json
import runpy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import gazeforge
import gazeforge._certificate_schema as cert
import gazeforge._features as features
import gazeforge.benchmarks as benchmarks
import gazeforge.downstream_lineage as downstream
import gazeforge.evidence_cards as cards
import gazeforge.gaze_in_wild_authoritative_task_mapping_exhaustion as giw_mapping
import gazeforge.geometry as geometry
import gazeforge.hollywood2_original_subject_metadata as h2meta
import gazeforge.model_cards as model_cards
import gazeforge.provenance as provenance
import gazeforge.source_resolution_cli as source_cli
import gazeforge.source_resolution_discovery as discovery
import gazeforge.visus_source_resolution as visus_source_resolution
import gazeforge.visus_source_resolution_cli as visus_cli
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError

# ---------------------------------------------------------------------------
# package metadata fallback
# ---------------------------------------------------------------------------


def test_package_version_fallback_and_restore(monkeypatch):
    real_version = importlib.metadata.version

    def missing(_name):
        raise importlib.metadata.PackageNotFoundError("gazeforge")

    monkeypatch.setattr(importlib.metadata, "version", missing)
    reloaded = importlib.reload(gazeforge)
    assert reloaded.__version__ == "0+unknown"

    monkeypatch.setattr(importlib.metadata, "version", real_version)
    restored = importlib.reload(gazeforge)
    assert restored.__version__ != "0+unknown"


# ---------------------------------------------------------------------------
# certificate schema
# ---------------------------------------------------------------------------


def test_certificate_exact_mapping_contracts():
    assert cert.require_exact_mapping_keys(
        {"a": 1},
        {"a"},
        context="demo",
    ) == {"a": 1}

    with pytest.raises(SchemaError, match="must be a mapping"):
        cert.require_exact_mapping_keys([], {"a"}, context="demo")

    with pytest.raises(SchemaError, match="missing fields"):
        cert.require_exact_mapping_keys({}, {"a"}, context="demo")

    with pytest.raises(SchemaError, match="unexpected fields"):
        cert.require_exact_mapping_keys(
            {"a": 1, "b": 2},
            {"a"},
            context="demo",
        )

    with pytest.raises(SchemaError, match="missing fields"):
        cert.require_exact_mapping_keys(
            {"b": 2},
            {"a"},
            context="demo",
        )


def test_certificate_optimizer_contracts():
    good = {
        "converged": True,
        "status": 0,
        "message": "ok",
        "iterations": 2,
    }
    assert cert.require_canonical_optimizer(good, context="demo") is good

    bad = dict(good)
    bad["converged"] = False
    with pytest.raises(SchemaError, match="Only converged"):
        cert.require_canonical_optimizer(bad, context="demo")

    for status in (True, "0", 1.2):
        bad = dict(good)
        bad["status"] = status
        with pytest.raises(SchemaError, match="status must be an integer"):
            cert.require_canonical_optimizer(bad, context="demo")

    for iterations in (True, "2", -1):
        bad = dict(good)
        bad["iterations"] = iterations
        with pytest.raises(SchemaError, match="non-negative integer"):
            cert.require_canonical_optimizer(bad, context="demo")

    bad = dict(good)
    bad["message"] = 123
    with pytest.raises(SchemaError, match="message must be a string"):
        cert.require_canonical_optimizer(bad, context="demo")


def test_certificate_finite_json_number_contracts():
    cert.require_finite_json_numbers([0, 1, -2, 1.25], context="demo")

    for bad in (True, "1", None):
        with pytest.raises(SchemaError, match="canonical JSON numbers"):
            cert.require_finite_json_numbers([bad], context="demo")

    for bad in (float("inf"), float("-inf"), float("nan")):
        with pytest.raises(SchemaError, match="non-finite"):
            cert.require_finite_json_numbers([bad], context="demo")


# ---------------------------------------------------------------------------
# sample features
# ---------------------------------------------------------------------------


def test_kinematic_features_missing_columns():
    with pytest.raises(SchemaError, match="Missing columns"):
        features.kinematic_features(pd.DataFrame({"participant_id": ["P1"]}))


def test_kinematic_features_sampling_fallback_without_pupil():
    frame = pd.DataFrame(
        {
            "participant_id": ["P1", "P1", "P1"],
            "timestamp_ms": [0.0, 0.0, 20.0],
            "x_px": [0.0, 1.0, 3.0],
            "y_px": [0.0, 0.0, 0.0],
        }
    )

    result = features.kinematic_features(
        frame,
        sampling_rate_hz=100.0,
        group_cols=("participant_id",),
    )

    assert result["dt_ms"].tolist() == pytest.approx([10.0, 10.0, 20.0])
    assert result["pupil"].isna().all()
    assert result["pupil_missing"].eq(1.0).all()
    assert np.isfinite(result.loc[1, "velocity_px_s"])


def test_kinematic_features_without_sampling_fallback_and_with_pupil():
    frame = pd.DataFrame(
        {
            "participant_id": ["P1", "P1"],
            "trial_id": ["T1", "T1"],
            "timestamp_ms": [0.0, 0.0],
            "x_px": [0.0, 1.0],
            "y_px": [0.0, 0.0],
            "pupil": ["3.0", "bad"],
        }
    )

    result = features.kinematic_features(frame)

    assert result.loc[0, "pupil"] == pytest.approx(3.0)
    assert np.isnan(result.loc[1, "pupil"])
    assert result["velocity_px_s"].isna().all()


# ---------------------------------------------------------------------------
# benchmark card/report/freeze contracts
# ---------------------------------------------------------------------------


def _card(**kwargs):
    values = {
        "name": "demo",
        "version": "1",
        "source": "synthetic",
        "license": "MIT",
        "task": "event-validation",
    }
    values.update(kwargs)
    return benchmarks.BenchmarkDatasetCard(**values)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("annotation_origin", "invalid", "Unknown annotation_origin"),
        ("sampling_origin", "invalid", "Unknown sampling_origin"),
        ("reference_strength", "invalid", "Unknown reference_strength"),
    ],
)
def test_benchmark_card_rejects_unknown_categories(field, value, match):
    with pytest.raises(ValueError, match=match):
        _card(**{field: value})


def test_benchmark_card_rejects_invalid_human_count():
    with pytest.raises(ValueError, match="non-negative"):
        _card(human_annotator_count=-1)


def test_benchmark_card_rejects_algorithm_as_human_reference():
    with pytest.raises(
        ValueError,
        match="Algorithm-generated annotations",
    ):
        _card(
            annotation_origin="research-algorithm",
            sampling_origin="native",
            reference_strength="human-reference",
        )


def test_benchmark_card_rejects_synthetic_empirical_reference():
    with pytest.raises(
        ValueError,
        match="Synthetic sampling cannot support",
    ):
        _card(
            annotation_origin="synthetic",
            sampling_origin="synthetic",
            reference_strength="human-reference",
        )


def test_benchmark_card_requires_synthetic_origins_for_known_truth():
    with pytest.raises(
        ValueError,
        match="Synthetic known truth requires",
    ):
        _card(
            annotation_origin="human-manual",
            sampling_origin="native",
            reference_strength="synthetic-known-truth",
        )


def test_benchmark_card_properties_and_serialization():
    human = _card(
        annotation_origin="expert-manual",
        sampling_origin="native",
        reference_strength="expert-human-reference",
        human_annotator_count=2,
    )
    assert human.is_human_reference is True
    assert human.is_native_human_reference is True
    assert human.is_synthetic_known_truth_reference is False
    assert human.to_dict()["human_annotator_count"] == 2

    synthetic = _card(
        annotation_origin="synthetic",
        sampling_origin="synthetic",
        reference_strength="synthetic-known-truth",
    )
    assert synthetic.is_human_reference is False
    assert synthetic.is_native_human_reference is False
    assert synthetic.is_synthetic_known_truth_reference is True


def test_benchmark_report_fingerprint_and_freeze(tmp_path):
    card = _card()
    report = benchmarks.build_benchmark_report(
        benchmark=card,
        metrics={"score": 0.5},
    )

    assert report["model"] == {}
    assert report["protocol"] == {}
    assert len(report["report_fingerprint_sha256"]) == 64

    assert benchmarks.canonical_json({"path": Path("demo")}) == '{"path":"demo"}'

    target = tmp_path / "nested" / "report.json"
    result = benchmarks.freeze_benchmark_report(report, target)
    assert result == target
    assert (
        json.loads(target.read_text(encoding="utf-8"))["report_fingerprint_sha256"]
        == report["report_fingerprint_sha256"]
    )

    with pytest.raises(FileExistsError):
        benchmarks.freeze_benchmark_report(report, target)

    benchmarks.freeze_benchmark_report(
        {**report, "extra": True},
        target,
        overwrite=True,
    )
    assert json.loads(target.read_text(encoding="utf-8"))["extra"] is True


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("physical_extent", "pixel_extent", "viewing_distance"),
    [
        (0.0, 1920.0, 650.0),
        (530.0, 0.0, 650.0),
        (530.0, 1920.0, 0.0),
        (-1.0, 1920.0, 650.0),
    ],
)
def test_visual_angle_rejects_nonpositive_geometry(
    physical_extent,
    pixel_extent,
    viewing_distance,
):
    with pytest.raises(ValueError, match="must be positive"):
        geometry.pixels_to_visual_angle_deg(
            [1.0, 2.0],
            physical_extent=physical_extent,
            pixel_extent=pixel_extent,
            viewing_distance=viewing_distance,
        )


def _geometry_frame():
    return pd.DataFrame(
        {
            "participant_id": ["P1", "P1", "P1"],
            "trial_id": ["T1", "T1", "T1"],
            "timestamp_ms": [0.0, 0.0, 20.0],
            "x_px": [100.0, 101.0, 103.0],
            "y_px": [100.0, 100.0, 101.0],
            "screen_width_px": [1920.0] * 3,
            "screen_height_px": [1080.0] * 3,
            "screen_width_physical": [530.0] * 3,
            "screen_height_physical": [300.0] * 3,
            "view_distance_physical": [650.0] * 3,
        }
    )


def test_angular_features_missing_geometry_column():
    frame = _geometry_frame().drop(columns=["screen_width_px"])
    with pytest.raises(SchemaError, match="missing columns"):
        geometry.angular_kinematic_features(frame)


def test_angular_features_single_group_and_sampling_fallback():
    frame = _geometry_frame()

    result = geometry.angular_kinematic_features(
        frame,
        sampling_rate_hz=100.0,
        group_cols=("participant_id",),
    )

    assert result["dt_ms"].tolist() == pytest.approx([10.0, 10.0, 20.0])
    assert np.isnan(result.loc[0, "angular_displacement_deg"])
    assert np.isfinite(result.loc[1, "angular_velocity_deg_s"])


def test_angular_features_without_sampling_fallback():
    frame = _geometry_frame()
    frame["timestamp_ms"] = [0.0, 10.0, 20.0]

    result = geometry.angular_kinematic_features(
        frame,
        group_cols=("participant_id", "trial_id"),
    )

    assert np.isnan(result.loc[0, "dt_ms"])
    assert result.loc[1, "dt_ms"] == pytest.approx(10.0)


def test_angular_features_reject_nonfinite_geometry():
    frame = _geometry_frame()
    frame["view_distance_physical"] = np.nan

    with pytest.raises(
        SchemaError,
        match="one positive invariant",
    ):
        geometry.angular_kinematic_features(frame)


# ---------------------------------------------------------------------------
# model cards and provenance
# ---------------------------------------------------------------------------


def test_model_card_defaults_and_json():
    card = model_cards.ModelCard(
        name="m",
        version="1",
        task="classification",
        intended_use="testing",
        metadata={"path": Path("demo")},
    )

    payload = card.to_dict()
    assert payload["training_data"] == "unspecified"
    assert payload["ethical_constraints"]

    text = card.to_json(indent=0)
    assert '"name": "m"' in text
    assert '"path": "demo"' in text


def test_provenance_fingerprints_and_audit_trail():
    before = pd.DataFrame({"x": [1, 2]})
    after = pd.DataFrame({"x": [1, 3]})

    before_fp = provenance.fingerprint_frame(before)
    after_fp = provenance.fingerprint_frame(after)

    assert before_fp != after_fp
    assert len(before_fp) == 64

    trail = provenance.AuditTrail()
    assert trail.to_frame().empty
    assert json.loads(trail.to_json()) == []

    record = trail.add(
        operation="transform",
        input_data=before,
        output_data=after,
    )
    assert record.parameters == {}
    assert record.warnings == []
    assert record.to_dict()["operation"] == "transform"

    second = trail.add(
        operation="model",
        input_data=after,
        output_data=after,
        parameters={"rate": 60},
        model_name="demo",
        model_version="1",
        warnings=["warning"],
    )

    assert second.parameters == {"rate": 60}
    assert second.warnings == ["warning"]
    assert len(trail.to_frame()) == 2
    assert len(json.loads(trail.to_json(indent=0))) == 2


# ---------------------------------------------------------------------------
# source-resolution discovery
# ---------------------------------------------------------------------------


def test_source_resolution_discovery_rejects_missing_and_empty_dirs(tmp_path):
    with pytest.raises(NotADirectoryError):
        discovery.discover_source_resolution_paths(tmp_path / "missing")

    empty = tmp_path / "empty"
    empty.mkdir()

    with pytest.raises(
        BenchmarkIntegrityError,
        match="No source-resolution checkpoints",
    ):
        discovery.discover_source_resolution_paths(empty)


def test_source_resolution_discovery_rejects_directory_symlink_semantics(
    tmp_path,
    monkeypatch,
):
    directory = tmp_path / "checkpoints"
    directory.mkdir()

    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: self == directory,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="symbolic-link directories",
    ):
        discovery.discover_source_resolution_paths(directory)


def test_source_resolution_discovery_rejects_candidate_symlink_semantics(
    tmp_path,
    monkeypatch,
):
    directory = tmp_path / "checkpoints"
    directory.mkdir()
    candidate = directory / "x-source-resolution-test.json"
    candidate.write_text(
        '{"record_type":"source-resolution-status-v1"}',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: self == candidate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="symbolic links",
    ):
        discovery.discover_source_resolution_paths(directory)


def test_source_resolution_discovery_rejects_nonregular_candidate(
    tmp_path,
    monkeypatch,
):
    directory = tmp_path / "checkpoints"
    directory.mkdir()
    candidate = directory / "x-source-resolution-test.json"
    candidate.write_text(
        '{"record_type":"source-resolution-status-v1"}',
        encoding="utf-8",
    )

    original = Path.is_file
    monkeypatch.setattr(
        Path,
        "is_file",
        lambda self: False if self == candidate else original(self),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not a regular file",
    ):
        discovery.discover_source_resolution_paths(directory)


@pytest.mark.parametrize(
    ("raw", "match"),
    [
        (b"{", "not valid UTF-8 JSON"),
        (b"\xff", "not valid UTF-8 JSON"),
        (b"[]", "must be a JSON object"),
        (b'{"record_type":"wrong"}', "must use record_type"),
    ],
)
def test_source_resolution_discovery_rejects_bad_candidate_payloads(
    tmp_path,
    raw,
    match,
):
    directory = tmp_path / "checkpoints"
    directory.mkdir()
    candidate = directory / "x-source-resolution-test.json"
    candidate.write_bytes(raw)

    with pytest.raises(BenchmarkIntegrityError, match=match):
        discovery.discover_source_resolution_paths(directory)


def test_source_resolution_directory_delegates_valid_candidate(
    tmp_path,
    monkeypatch,
):
    directory = tmp_path / "checkpoints"
    directory.mkdir()
    candidate = directory / "x-source-resolution-test.json"
    candidate.write_text(
        '{"record_type":"source-resolution-status-v1"}',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        discovery,
        "validate_source_resolution_records",
        lambda paths: {
            "paths": [str(path) for path in paths],
            "ok": True,
        },
    )

    result = discovery.validate_source_resolution_directory(directory)

    assert result["ok"] is True
    assert result["paths"] == [str(candidate)]


# ---------------------------------------------------------------------------
# source-resolution CLI
# ---------------------------------------------------------------------------


def test_source_resolution_cli_rejects_invalid_mode_combinations():
    with pytest.raises(SystemExit) as exc:
        source_cli.main([])
    assert exc.value.code == 2

    with pytest.raises(SystemExit) as exc:
        source_cli.main(
            [
                "record.json",
                "--directory",
                "records",
            ]
        )
    assert exc.value.code == 2

    with pytest.raises(SystemExit) as exc:
        source_cli.main(
            [
                "record.json",
                "--lock",
                "lock.json",
            ]
        )
    assert exc.value.code == 2


def test_source_resolution_cli_explicit_paths(monkeypatch, capsys):
    monkeypatch.setattr(
        source_cli,
        "validate_source_resolution_records",
        lambda paths: {
            "mode": "paths",
            "count": len(paths),
        },
    )

    assert source_cli.main(["a.json", "b.json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload == {"count": 2, "mode": "paths"}


def test_source_resolution_cli_directory(monkeypatch, capsys):
    monkeypatch.setattr(
        source_cli,
        "validate_source_resolution_directory",
        lambda path: {
            "mode": "directory",
            "path": str(path),
        },
    )

    assert source_cli.main(["--directory", "records"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "directory"


def test_source_resolution_cli_directory_and_lock(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        source_cli,
        "validate_source_resolution_directory",
        lambda path: {"bundle": str(path)},
    )
    monkeypatch.setattr(
        source_cli,
        "validate_source_resolution_bundle_lock",
        lambda lock, directory: {
            "lock": str(lock),
            "directory": str(directory),
        },
    )

    assert (
        source_cli.main(
            [
                "--directory",
                "records",
                "--lock",
                "lock.json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["validation_bundle"]["bundle"] == "records"
    assert payload["bundle_lock"]["lock"] == "lock.json"


def test_source_resolution_cli_module_entrypoint(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["gazeforge-source-resolution"],
    )

    with pytest.raises(SystemExit) as exc:
        runpy.run_module(
            "gazeforge.source_resolution_cli",
            run_name="__main__",
        )

    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# VISUS source-resolution CLI
# ---------------------------------------------------------------------------


def test_visus_source_resolution_cli(monkeypatch, capsys):
    monkeypatch.setattr(
        visus_cli,
        "validate_visus_source_resolution_record",
        lambda path: {
            "ok": True,
            "path": str(path),
        },
    )

    assert visus_cli.main(["record.json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": True,
        "path": "record.json",
    }


def test_visus_source_resolution_cli_module_entrypoint(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        visus_source_resolution,
        "validate_visus_source_resolution_record",
        lambda path: {
            "ok": True,
            "path": str(path),
        },
    )

    path = tmp_path / "record.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "gazeforge-visus-source-resolution",
            str(path),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        runpy.run_module(
            "gazeforge.visus_source_resolution_cli",
            run_name="__main__",
        )

    assert exc.value.code == 0


# ---------------------------------------------------------------------------
# Hollywood2 public metadata parser
# ---------------------------------------------------------------------------


def test_hollywood2_metadata_page_summary_nonbytes_body():
    result = h2meta._page_summary(
        {
            "http_status": 200,
            "body": "not-bytes",
        },
        base_url=h2meta.DESCRIPTION_URL,
    )

    assert result["normalized_text_length"] == 0
    assert result["links"] == []


def test_hollywood2_description_and_license_markers():
    description_html = b"""
    <html><body>
    16 human volunteers.
    The active group and free-viewing group were used.
    12 active subjects and 4 free viewing subjects.
    The active action recognition task was used.
    Free-viewing participants were not required to solve any specific task.
    Data were sampled at 500 Hz.
    <a href="data.zip">Hollywood-2 gaze data</a>
    <a href="README.txt">README</a>
    </body></html>
    """

    license_html = b"""
    <html><body>
    Academic use only.
    A limited, non-exclusive, non-assignable, non-transferable licence.
    Request from an academic address.
    Do not sub-license or transfer.
    Seek prior written permission.
    </body></html>
    """

    description = h2meta.summarize_description(
        {
            "http_status": 200,
            "body": description_html,
        }
    )
    license_summary = h2meta.summarize_license(
        {
            "http_status": 200,
            "body": license_html,
        }
    )

    assert all(description["markers"].values())
    assert all(license_summary["markers"].values())

    assert description["hollywood2_data_links"][0]["resolved_url"].endswith("/eyetracking/data.zip")

    record = h2meta.build_probe_record(
        {
            "http_status": 200,
            "body": description_html,
        },
        {
            "http_status": 200,
            "body": license_html,
        },
        data_link_head={"http_status": 302},
    )

    assert record["rights_boundary"]["public_license_page_observed"] is True
    assert record["rights_boundary"]["dataset_use_authorized_by_this_probe"] is False
    assert record["mapping_boundary"]["participant_identity_mapping_verified"] is False

    assert h2meta.probe_fingerprint(record) == record["probe_fingerprint_sha256"]


def test_hollywood2_html_parser_ignores_nonanchors():
    parser = h2meta._HTMLSummaryParser()
    parser.feed('<div>plain</div><a>missing href</a><a href="/x"> X </a>')

    assert parser.text_parts
    assert parser.links == [
        {
            "href": "/x",
            "text": "X",
        }
    ]


def test_hollywood2_canonical_bytes_and_hash_are_stable():
    left = h2meta.canonical_bytes({"b": 2, "a": "é"})
    right = h2meta.canonical_bytes({"a": "é", "b": 2})

    assert left == right
    assert len(h2meta.sha256_bytes(left)) == 64


# ---------------------------------------------------------------------------
# Gaze-in-the-Wild task-mapping exhaustion loaders
# ---------------------------------------------------------------------------


def test_giw_task_mapping_helpers_fail_closed():
    assert len(giw_mapping._canonical_sha256({"a": 1})) == 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="demo",
    ):
        giw_mapping._require(False, "demo")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="field must be an object",
    ):
        giw_mapping._mapping(
            {"field": []},
            "field",
        )


def test_giw_task_mapping_loader_rejects_missing_and_malformed(
    tmp_path,
):
    missing = tmp_path / "missing.json"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load GIW task-mapping exhaustion evidence",
    ):
        giw_mapping.load_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(missing)

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load GIW task-mapping exhaustion evidence",
    ):
        giw_mapping.load_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(malformed)

    nonmapping = tmp_path / "list.json"
    nonmapping.write_text("[]", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        giw_mapping.load_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(nonmapping)


def test_giw_task_mapping_bound_upstream_missing_fails_closed(
    tmp_path,
):
    evidence = tmp_path / "one" / "two" / "three" / "evidence.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("{}", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load bound GIW upstream evidence",
    ):
        giw_mapping._validate_bound_upstream_files(evidence)


# ---------------------------------------------------------------------------
# downstream lineage fingerprint normalization
# ---------------------------------------------------------------------------


def test_downstream_fingerprint_normalization_contracts():
    fp = "A" * 64

    assert downstream._normalise_fingerprints(
        {"source": fp},
        field_name="demo",
    ) == {
        "source": "a" * 64,
    }

    with pytest.raises(
        TypeError,
        match="must be a mapping",
    ):
        downstream._normalise_fingerprints(
            [],
            field_name="demo",
        )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="invalid SHA-256",
    ):
        downstream._normalise_fingerprints(
            {"source": "abc"},
            field_name="demo",
        )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="invalid SHA-256",
    ):
        downstream._normalise_fingerprints(
            {"source": "z" * 64},
            field_name="demo",
        )


# ---------------------------------------------------------------------------
# evidence-card helper branches
# ---------------------------------------------------------------------------


def test_evidence_card_text_helpers():
    assert cards._text(None) == ""
    assert cards._text(pd.NA) == ""
    assert cards._text(float("nan")) == ""
    assert cards._text("  hello  ") == "hello"

    # pd.isna(list) returns an array; _text intentionally catches
    # its ambiguous truth-value error and falls back to str().
    assert cards._text([1, 2]) == "[1, 2]"

    assert cards._html("<x>") == "&lt;x&gt;"
    assert cards._short_fingerprint("abcdef") == "abcdef"

    assert cards._fact("Label", None) == ""
    assert "Label" in cards._fact("Label", "value")

    assert cards._fingerprint("FP", None) == ""
    assert "<code>abcdef</code>" in cards._fingerprint(
        "FP",
        "abcdef",
    )


def test_evidence_card_review_facts_without_and_with_review():
    empty = pd.Series(dtype=object)
    assert cards._review_facts(empty) == ("", "")

    row = pd.Series(
        {
            "scientific_review_fingerprint_sha256": "a" * 64,
            "scientific_review_reviewer": "Reviewer",
            "scientific_reviewed_at": "2026-09-22",
            "scientific_review_scope": "scope",
        }
    )

    facts, provenance_html = cards._review_facts(row)

    assert "Reviewer" in facts
    assert "2026-09-22" in facts
    assert "Review fingerprint" in provenance_html


def test_evidence_card_insertion_contracts():
    original = "# Report\n"

    assert (
        cards._insert_cards_before_table(
            original,
            "## Missing\n",
            "",
        )
        == original
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="expected section heading",
    ):
        cards._insert_cards_before_table(
            original,
            "## Missing\n",
            "<cards>",
        )

    no_table = "# Report\n\n## Section\n\nNo table\n"
    with pytest.raises(
        BenchmarkIntegrityError,
        match="provenance table",
    ):
        cards._insert_cards_before_table(
            no_table,
            "## Section\n\n",
            "<cards>",
        )

    markdown = "# Report\n\n## Section\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"

    rendered = cards._insert_cards_before_table(
        markdown,
        "## Section\n\n",
        "<cards>",
    )

    assert "<cards>" in rendered
    assert rendered.index("<cards>") < rendered.index("| A | B |")
