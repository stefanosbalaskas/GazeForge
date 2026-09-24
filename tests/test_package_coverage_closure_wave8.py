from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.event_evaluation as event_eval
import gazeforge.evidence_details as evidence_details
import gazeforge.lund2013 as lund2013
import gazeforge.source_audit_lineage as lineage
import gazeforge.source_candidate_cli as source_cli
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError

# =====================================================================
# evidence_details.py
# Close the genuine false side of the optional by-stimulus renderer.
# =====================================================================


def test_evidence_agreement_without_stimulus_mapping():
    rendered = evidence_details._agreement_summary(
        {
            "overall": {
                "n_aligned_samples": 10,
                "exact_agreement": 0.9,
                "cohen_kappa": 0.8,
            },
            "by_stimulus_type": None,
        }
    )

    assert "Human–human annotation agreement" in rendered
    assert "overall" in rendered


# =====================================================================
# event_evaluation.py
# =====================================================================


def _sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": ["P1", "P1"],
            "trial_id": ["T1", "T1"],
            "timestamp_ms": [0.0, 10.0],
            "event_label": ["fixation", "fixation"],
            "predicted_event": ["fixation", "fixation"],
        }
    )


def _event_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": ["P1"],
            "trial_id": ["T1"],
            "event_index": [0],
            "event_label": ["fixation"],
            "start_ms": [0.0],
            "end_ms": [10.0],
            "duration_ms": [10.0],
        }
    )


def test_event_normalise_missing_label():
    assert event_eval._normalise_label(None) == "unlabelled"


@pytest.mark.parametrize("rate", [0.0, np.nan])
def test_event_rate_must_be_positive_finite(rate):
    with pytest.raises(
        ValueError,
        match="finite and positive",
    ):
        event_eval._validate_rate(rate)


def test_event_segmentation_requires_group_columns():
    with pytest.raises(
        ValueError,
        match="at least one grouping column",
    ):
        event_eval.samples_to_event_intervals(
            _sample_frame(),
            group_cols=(),
            sampling_rate_hz=100.0,
        )


def test_event_segmentation_requires_columns():
    with pytest.raises(
        SchemaError,
        match="requires columns",
    ):
        event_eval.samples_to_event_intervals(
            pd.DataFrame(),
            sampling_rate_hz=100.0,
        )


def test_event_segmentation_rejects_missing_group_ids():
    frame = _sample_frame()
    frame.loc[0, "participant_id"] = None

    with pytest.raises(
        SchemaError,
        match="group identifiers cannot be missing",
    ):
        event_eval.samples_to_event_intervals(
            frame,
            sampling_rate_hz=100.0,
        )


def test_event_segmentation_rejects_bad_gap_factor():
    with pytest.raises(
        ValueError,
        match="max_gap_factor",
    ):
        event_eval.samples_to_event_intervals(
            _sample_frame(),
            sampling_rate_hz=100.0,
            max_gap_factor=0.5,
        )


def test_event_segmentation_rejects_nonfinite_timestamp():
    frame = _sample_frame()
    frame.loc[1, "timestamp_ms"] = np.nan

    with pytest.raises(
        SchemaError,
        match="timestamps must be finite",
    ):
        event_eval.samples_to_event_intervals(
            frame,
            sampling_rate_hz=100.0,
        )


def test_event_segmentation_requires_increasing_timestamp():
    frame = _sample_frame()
    frame["timestamp_ms"] = [10.0, 0.0]

    with pytest.raises(
        SchemaError,
        match="strictly increasing timestamps",
    ):
        event_eval.samples_to_event_intervals(
            frame,
            sampling_rate_hz=100.0,
        )


def test_temporal_iou_rejects_nonfinite_bounds():
    with pytest.raises(
        ValueError,
        match="bounds must be finite",
    ):
        event_eval.temporal_event_iou(
            0.0,
            np.inf,
            0.0,
            10.0,
        )


def test_temporal_iou_rejects_nonpositive_interval():
    with pytest.raises(
        ValueError,
        match="end must be greater than start",
    ):
        event_eval.temporal_event_iou(
            10.0,
            10.0,
            0.0,
            10.0,
        )


def test_event_frame_requires_columns():
    with pytest.raises(
        SchemaError,
        match="missing columns",
    ):
        event_eval._validate_event_frame(
            pd.DataFrame(),
            name="demo",
            group_cols=("participant_id", "trial_id"),
            label_col="event_label",
        )


def test_event_frame_rejects_missing_group_identifier():
    frame = _event_frame()
    frame.loc[0, "participant_id"] = None

    with pytest.raises(
        SchemaError,
        match="group identifiers cannot be missing",
    ):
        event_eval._validate_event_frame(
            frame,
            name="demo",
            group_cols=("participant_id", "trial_id"),
            label_col="event_label",
        )


def test_event_frame_rejects_duplicate_keys():
    frame = pd.concat(
        [_event_frame(), _event_frame()],
        ignore_index=True,
    )

    with pytest.raises(
        SchemaError,
        match="duplicate event keys",
    ):
        event_eval._validate_event_frame(
            frame,
            name="demo",
            group_cols=("participant_id", "trial_id"),
            label_col="event_label",
        )


def test_event_frame_rejects_nonfinite_bounds():
    frame = _event_frame()
    frame.loc[0, "start_ms"] = np.nan

    with pytest.raises(
        SchemaError,
        match="bounds must be finite",
    ):
        event_eval._validate_event_frame(
            frame,
            name="demo",
            group_cols=("participant_id", "trial_id"),
            label_col="event_label",
        )


def test_event_frame_requires_end_after_start():
    frame = _event_frame()
    frame.loc[0, "end_ms"] = 0.0

    with pytest.raises(
        SchemaError,
        match="end_ms > start_ms",
    ):
        event_eval._validate_event_frame(
            frame,
            name="demo",
            group_cols=("participant_id", "trial_id"),
            label_col="event_label",
        )


def test_event_frame_rejects_overlap_within_group():
    frame = pd.DataFrame(
        {
            "participant_id": ["P1", "P1"],
            "trial_id": ["T1", "T1"],
            "event_index": [0, 1],
            "event_label": ["fixation", "saccade"],
            "start_ms": [0.0, 5.0],
            "end_ms": [10.0, 15.0],
            "duration_ms": [10.0, 10.0],
        }
    )

    with pytest.raises(
        SchemaError,
        match="cannot overlap",
    ):
        event_eval._validate_event_frame(
            frame,
            name="demo",
            group_cols=("participant_id", "trial_id"),
            label_col="event_label",
        )


def test_component_assignment_handles_already_unified_edge():
    selected = event_eval._component_assignments(
        [
            (0, 0, 0.75),
            (0, 0, 0.50),
        ]
    )

    assert selected


def test_match_event_intervals_rejects_bad_threshold():
    frame = _event_frame()

    with pytest.raises(
        ValueError,
        match="min_iou",
    ):
        event_eval.match_event_intervals(
            frame,
            frame,
            min_iou=2.0,
        )


def test_sample_event_evaluation_requires_truth_column():
    frame = _sample_frame().drop(columns=["event_label"])

    with pytest.raises(
        SchemaError,
        match="Missing event-evaluation label column",
    ):
        event_eval.evaluate_sample_event_predictions(
            frame,
            sampling_rate_hz=100.0,
        )


def test_sample_event_evaluation_requires_prediction_column():
    frame = _sample_frame().drop(columns=["predicted_event"])

    with pytest.raises(
        SchemaError,
        match="Missing event-evaluation label column",
    ):
        event_eval.evaluate_sample_event_predictions(
            frame,
            sampling_rate_hz=100.0,
        )


# =====================================================================
# lund2013.py
# =====================================================================


def _etdata(
    *,
    pos=None,
    samp_freq=100.0,
    screen_res=(1920.0, 1080.0),
    screen_dim=None,
    view_dist=None,
):
    fields = [
        ("pos", object),
        ("sampFreq", object),
        ("screenRes", object),
    ]

    if screen_dim is not None:
        fields.append(("screenDim", object))

    if view_dist is not None:
        fields.append(("viewDist", object))

    value = np.empty(
        (1, 1),
        dtype=np.dtype(fields),
    )

    if pos is None:
        pos = np.array(
            [
                [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
                [0.0, 0.0, 0.0, 1.0, 1.0, 2.0],
            ],
            dtype=float,
        )

    value["pos"][0, 0] = np.asarray(pos)
    value["sampFreq"][0, 0] = np.asarray([samp_freq])
    value["screenRes"][0, 0] = np.asarray(screen_res)

    if screen_dim is not None:
        value["screenDim"][0, 0] = np.asarray(screen_dim)

    if view_dist is not None:
        value["viewDist"][0, 0] = np.asarray(view_dist)

    return value


def test_lund_metadata_video_branch():
    result = lund2013._infer_file_metadata(Path("P01_video_scene_labelled_RA.mat"))

    assert result["stimulus_type"] == "video"
    assert result["annotator"] == "RA"


def test_lund_rejects_short_position_matrix(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "P01_trial1_labelled_RA.mat"
    path.write_bytes(b"x")

    monkeypatch.setattr(
        lund2013,
        "loadmat",
        lambda _: {
            "ETdata": _etdata(
                pos=np.zeros((2, 5)),
            )
        },
    )

    with pytest.raises(
        SchemaError,
        match="at least six columns",
    ):
        lund2013.load_lund2013_mat(path)


def test_lund_rejects_nonpositive_sampling_rate(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "P01_trial1_labelled_RA.mat"
    path.write_bytes(b"x")

    monkeypatch.setattr(
        lund2013,
        "loadmat",
        lambda _: {
            "ETdata": _etdata(
                samp_freq=0.0,
            )
        },
    )

    with pytest.raises(
        SchemaError,
        match="positive sampling rate",
    ):
        lund2013.load_lund2013_mat(path)


def test_lund_can_preserve_zero_coordinate_pair(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "P01_trial1_labelled_RA.mat"
    path.write_bytes(b"x")

    monkeypatch.setattr(
        lund2013,
        "loadmat",
        lambda _: {"ETdata": _etdata()},
    )

    result = lund2013.load_lund2013_mat(
        path,
        zero_pair_is_missing=False,
    )

    assert result.data.loc[0, "x_px"] == 0.0
    assert result.data.loc[0, "y_px"] == 0.0
    assert result.metadata["visual_angle_geometry_available"] is False


def test_lund_invalid_screen_resolution_remains_unverified(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "P01_trial1_labelled_RA.mat"
    path.write_bytes(b"x")

    monkeypatch.setattr(
        lund2013,
        "loadmat",
        lambda _: {
            "ETdata": _etdata(
                screen_res=(-1.0, -1.0),
            )
        },
    )

    result = lund2013.load_lund2013_mat(path)

    assert result.screen_size_px is None
    assert result.metadata["visual_angle_geometry_available"] is False


def test_lund_geometry_available_branch(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "P01_img_scene_labelled_RA.mat"
    path.write_bytes(b"x")

    monkeypatch.setattr(
        lund2013,
        "loadmat",
        lambda _: {
            "ETdata": _etdata(
                screen_dim=(530.0, 300.0),
                view_dist=(600.0,),
            )
        },
    )

    result = lund2013.load_lund2013_mat(path)

    assert result.metadata["visual_angle_geometry_available"] is True
    assert "screen_width_physical" in result.data


# =====================================================================
# source_candidate_cli.py
# Real CLI misuse/error routing without touching source files.
# =====================================================================


def test_source_cli_rejects_giw_lineage_args_for_hollywood_apply(
    monkeypatch,
):
    monkeypatch.setattr(
        source_cli,
        "_load_audit_spec",
        lambda path, dataset: object(),
    )
    monkeypatch.setattr(
        source_cli,
        "validate_candidate_source_audit_authorization",
        lambda *args, **kwargs: object(),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot be used for Hollywood2EM",
    ):
        source_cli.main(
            [
                "authorization-apply",
                "--dataset",
                "hollywood2em",
                "--template",
                "template.json",
                "--authorization",
                "authorization.json",
                "--root",
                ".",
                "--quarantine-exit",
                "exit.json",
                "--output",
                "out.json",
            ]
        )


def test_source_cli_rejects_giw_lineage_args_for_hollywood_receipt(
    monkeypatch,
):
    monkeypatch.setattr(
        source_cli,
        "_load_audit_spec",
        lambda path, dataset: object(),
    )
    monkeypatch.setattr(
        source_cli,
        "validate_candidate_source_audit_authorization",
        lambda *args, **kwargs: object(),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot be used for Hollywood2EM",
    ):
        source_cli.main(
            [
                "lineage",
                "--dataset",
                "hollywood2em",
                "--template",
                "template.json",
                "--authorization",
                "authorization.json",
                "--audit-report",
                "audit.json",
                "--root",
                ".",
                "--inventory",
                "inventory.json",
                "--output",
                "out.json",
            ]
        )


def test_source_cli_giw_lineage_validates_exit_path(
    monkeypatch,
    capsys,
):
    class FakeGIWSpec:
        pass

    class Result:
        def to_dict(self):
            return {
                "record_type": "demo",
            }

    template = FakeGIWSpec()
    marker = object()

    monkeypatch.setattr(
        source_cli,
        "GazeInWildSourceAuditSpec",
        FakeGIWSpec,
    )
    monkeypatch.setattr(
        source_cli,
        "_load_audit_spec",
        lambda path, dataset: template,
    )
    monkeypatch.setattr(
        source_cli,
        "validate_candidate_source_audit_authorization",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        source_cli,
        "_validated_giw_exit_for_args",
        lambda args, spec: marker,
    )
    monkeypatch.setattr(
        source_cli,
        "_load_json_object",
        lambda *args, **kwargs: {},
    )

    observed = {}

    def fake_build(
        template_spec,
        authorization,
        audit_report,
        *,
        gaze_in_wild_quarantine_exit=None,
    ):
        observed["exit"] = gaze_in_wild_quarantine_exit
        return Result()

    monkeypatch.setattr(
        source_cli,
        "build_source_audit_lineage_receipt",
        fake_build,
    )
    monkeypatch.setattr(
        source_cli,
        "write_source_audit_lineage_receipt",
        lambda *args, **kwargs: None,
    )

    code = source_cli.main(
        [
            "lineage",
            "--dataset",
            "gaze-in-the-wild",
            "--template",
            "template.json",
            "--authorization",
            "authorization.json",
            "--audit-report",
            "audit.json",
            "--root",
            ".",
            "--quarantine-exit",
            "exit.json",
            "--recovery-review",
            "review.json",
            "--inventory",
            "inventory.json",
            "--output",
            "out.json",
        ]
    )

    assert code == 0
    assert observed["exit"] is marker
    assert '"record_type": "demo"' in capsys.readouterr().out


# =====================================================================
# source_audit_lineage.py
# =====================================================================


def _digest(char: str = "a") -> str:
    return char * 64


def _receipt() -> lineage.SourceAuditLineageReceipt:
    return lineage.SourceAuditLineageReceipt(
        dataset_key="hollywood2em",
        audit_template_fingerprint_sha256=_digest("a"),
        authorization_fingerprint_sha256=_digest("b"),
        authorized_spec_fingerprint_sha256=_digest("c"),
        audit_report_fingerprint_sha256=_digest("d"),
        source_manifest_fingerprints_sha256={
            "source": _digest("e"),
        },
        source_revision="reviewed-revision",
    )


def _fake_spec():
    return SimpleNamespace(
        dataset_name="Demo",
        dataset_version="1",
        source="source",
        source_revision="revision",
        license="license",
        reuse_terms_source="terms",
        redistribution_status="unknown",
        coordinate_unit="pixels",
        to_dict=lambda: {
            "dataset_name": "Demo",
        },
    )


def _common_report(spec):
    body = {
        "audit": "Hollywood2EM-source-audit",
        "status": "verified",
        "spec_fingerprint_sha256": (lineage.benchmark_fingerprint(spec.to_dict())),
        "dataset": {
            "name": spec.dataset_name,
            "version": spec.dataset_version,
            "source": spec.source,
            "source_revision": spec.source_revision,
            "license": spec.license,
        },
        "reuse": {
            "terms_source": spec.reuse_terms_source,
            "terms_verified": True,
            "analysis_use_permitted": True,
            "redistribution_status": (spec.redistribution_status),
        },
        "coordinates": {
            "verified": True,
            "unit": spec.coordinate_unit,
        },
    }

    body["report_fingerprint_sha256"] = lineage.benchmark_fingerprint(body)
    return body


def _inventory():
    files = [
        {
            "path": "a",
            "sha256": _digest("1"),
        }
    ]

    return {
        "exact_inventory_match": True,
        "files": files,
        "file_count": len(files),
        "source_manifest_fingerprint_sha256": (lineage.benchmark_fingerprint(files)),
        "manifest_fingerprint_sha256": (lineage.benchmark_fingerprint(files)),
    }


def test_lineage_from_dict_wraps_constructor_error():
    payload = _receipt().to_dict()
    payload["source_revision"] = ""

    body = dict(payload)
    body.pop(
        "receipt_fingerprint_sha256",
        None,
    )
    payload["receipt_fingerprint_sha256"] = lineage.benchmark_fingerprint(body)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="receipt is invalid",
    ):
        lineage.SourceAuditLineageReceipt.from_dict(payload)


def test_lineage_common_report_requires_verified_audit():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="verified source-audit report",
    ):
        lineage._validate_common_report(
            {
                "audit": "wrong",
                "status": "failed",
            },
            authorized_spec=_fake_spec(),
            dataset_key="hollywood2em",
        )


def test_lineage_common_report_requires_reuse_permission():
    spec = _fake_spec()
    report = _common_report(spec)
    report["reuse"]["analysis_use_permitted"] = False

    body = dict(report)
    body.pop(
        "report_fingerprint_sha256",
        None,
    )
    report["report_fingerprint_sha256"] = lineage.benchmark_fingerprint(body)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="permitted analysis use",
    ):
        lineage._validate_common_report(
            report,
            authorized_spec=spec,
            dataset_key="hollywood2em",
        )


def test_lineage_common_report_requires_verified_coordinates():
    spec = _fake_spec()
    report = _common_report(spec)
    report["coordinates"]["verified"] = False

    body = dict(report)
    body.pop(
        "report_fingerprint_sha256",
        None,
    )
    report["report_fingerprint_sha256"] = lineage.benchmark_fingerprint(body)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="verified coordinate units",
    ):
        lineage._validate_common_report(
            report,
            authorized_spec=spec,
            dataset_key="hollywood2em",
        )


def test_lineage_hollywood_requires_identity_mapping():
    report = {
        "source_inventory": _inventory(),
        "annotations": {
            "same_underlying_gaze_verified": True,
        },
        "participant_identity": {
            "verified": False,
        },
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="participant identity mapping",
    ):
        lineage._manifest_fingerprints(
            report,
            dataset_key="hollywood2em",
            authorized_spec=_fake_spec(),
        )


def test_lineage_hollywood_requires_native_sampling():
    report = {
        "source_inventory": _inventory(),
        "annotations": {
            "same_underlying_gaze_verified": True,
        },
        "participant_identity": {
            "verified": True,
        },
        "sampling": {
            "sampling_origin": "derived",
        },
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sampling must remain native",
    ):
        lineage._manifest_fingerprints(
            report,
            dataset_key="hollywood2em",
            authorized_spec=_fake_spec(),
        )


def test_lineage_hollywood_invalid_observed_rate(
    monkeypatch,
):
    class FakeHollywoodSpec:
        expected_sampling_rate_hz = 500.0
        sampling_rate_tolerance_fraction = 0.05

    monkeypatch.setattr(
        lineage,
        "Hollywood2SourceAuditSpec",
        FakeHollywoodSpec,
    )

    report = {
        "source_inventory": _inventory(),
        "annotations": {
            "same_underlying_gaze_verified": True,
        },
        "participant_identity": {
            "verified": True,
        },
        "sampling": {
            "sampling_origin": "native",
            "expected_sampling_rate_hz": 500.0,
            "tolerance_fraction": 0.05,
            "observed_sampling_rate_hz": "bad",
        },
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="observed sampling rate is missing or invalid",
    ):
        lineage._manifest_fingerprints(
            report,
            dataset_key="hollywood2em",
            authorized_spec=FakeHollywoodSpec(),
        )


def test_lineage_hollywood_rejects_out_of_tolerance_rate(
    monkeypatch,
):
    class FakeHollywoodSpec:
        expected_sampling_rate_hz = 500.0
        sampling_rate_tolerance_fraction = 0.05

    monkeypatch.setattr(
        lineage,
        "Hollywood2SourceAuditSpec",
        FakeHollywoodSpec,
    )

    report = {
        "source_inventory": _inventory(),
        "annotations": {
            "same_underlying_gaze_verified": True,
        },
        "participant_identity": {
            "verified": True,
        },
        "sampling": {
            "sampling_origin": "native",
            "expected_sampling_rate_hz": 500.0,
            "tolerance_fraction": 0.05,
            "observed_sampling_rate_hz": 600.0,
        },
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="outside the authorized contract",
    ):
        lineage._manifest_fingerprints(
            report,
            dataset_key="hollywood2em",
            authorized_spec=FakeHollywoodSpec(),
        )


def test_lineage_giw_requires_identity_mapping():
    report = {
        "label_inventory": _inventory(),
        "process_inventory": _inventory(),
        "identity": {
            "participant_mapping_verified": False,
        },
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="verified participant mapping",
    ):
        lineage._manifest_fingerprints(
            report,
            dataset_key="gaze-in-the-wild",
            authorized_spec=_fake_spec(),
        )


def test_lineage_giw_requires_timestamp_sampling_source():
    report = {
        "label_inventory": _inventory(),
        "process_inventory": _inventory(),
        "identity": {
            "participant_mapping_verified": True,
        },
        "sampling": {
            "source": "wrong",
        },
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="timestamp-inferred file cadence",
    ):
        lineage._manifest_fingerprints(
            report,
            dataset_key="gaze-in-the-wild",
            authorized_spec=_fake_spec(),
        )


def test_lineage_build_requires_template_status(
    monkeypatch,
):
    class FakeSpec:
        dataset_status = "empirical"

    monkeypatch.setattr(
        lineage,
        "Hollywood2SourceAuditSpec",
        FakeSpec,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="dataset_status='template'",
    ):
        lineage.build_source_audit_lineage_receipt(
            FakeSpec(),
            object(),
            {},
        )


def test_lineage_build_requires_authorization_type(
    monkeypatch,
):
    class FakeSpec:
        dataset_status = "template"

    monkeypatch.setattr(
        lineage,
        "Hollywood2SourceAuditSpec",
        FakeSpec,
    )

    with pytest.raises(
        TypeError,
        match="CandidateSourceAuditAuthorization",
    ):
        lineage.build_source_audit_lineage_receipt(
            FakeSpec(),
            object(),
            {},
        )


def test_lineage_build_requires_audit_mapping(
    monkeypatch,
):
    class FakeSpec:
        dataset_status = "template"

    class FakeAuthorization:
        decision = "authorized"

    monkeypatch.setattr(
        lineage,
        "Hollywood2SourceAuditSpec",
        FakeSpec,
    )
    monkeypatch.setattr(
        lineage,
        "CandidateSourceAuditAuthorization",
        FakeAuthorization,
    )

    with pytest.raises(
        TypeError,
        match="audit_report must be a mapping",
    ):
        lineage.build_source_audit_lineage_receipt(
            FakeSpec(),
            FakeAuthorization(),
            object(),
        )


def test_lineage_writer_refuses_existing_target(
    tmp_path,
):
    root = tmp_path / "candidate"
    root.mkdir()

    target = tmp_path / "receipt.json"
    target.write_text(
        "already exists",
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError):
        lineage.write_source_audit_lineage_receipt(
            _receipt(),
            target,
            candidate_root=root,
        )


def test_lineage_loader_requires_file(
    tmp_path,
):
    with pytest.raises(FileNotFoundError):
        lineage.load_source_audit_lineage_receipt(tmp_path / "missing.json")


def test_lineage_loader_rejects_nonobject_json(
    tmp_path,
):
    path = tmp_path / "receipt.json"
    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        lineage.load_source_audit_lineage_receipt(path)
