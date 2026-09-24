from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.cross_dataset as cross
import gazeforge.dynamic_aoi as dynamic
from gazeforge.exceptions import SchemaError
from gazeforge.schema import GazeFrame

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


# ============================================================
# CROSS-DATASET FIXTURES
# ============================================================


def _gaze(
    name: str,
    *,
    sampling_rate_hz: float = 60.0,
    verified: bool = True,
    resolved: bool = True,
    include_event: bool = True,
    data_id: str | None = None,
    metadata_source: str | None = None,
    labels: tuple[str, ...] = (
        "fixation",
        "saccade",
        "pursuit",
    ),
) -> GazeFrame:
    rows = []

    participants = ("P1", "P2") if resolved else ("__unresolved__",)

    dataset_id = name if data_id is None else data_id

    dt = 1000.0 / sampling_rate_hz

    for participant in participants:
        for index in range(6):
            row = {
                "participant_id": participant,
                "trial_id": (f"{participant}_trial"),
                "timestamp_ms": (index * dt),
                "x_px": (100.0 + 10.0 * index),
                "y_px": (200.0 + index),
                "dataset_id": (dataset_id),
                "source_file": (f"{participant}.fixture"),
            }

            if include_event:
                row["event_label"] = labels[index % len(labels)]

            rows.append(row)

    return GazeFrame(
        data=pd.DataFrame(rows),
        sampling_rate_hz=(sampling_rate_hz),
        metadata={
            "source_dataset": (name if metadata_source is None else metadata_source),
            ("participant_identity_resolved"): resolved,
            "coordinate_source_unit": ("pixels" if verified else "unverified"),
            "coordinate_unit_verified": (verified),
        },
    )


# ============================================================
# DATASET IDENTITY
# ============================================================


def test_cross_identity_fallback_name():
    gaze = SimpleNamespace(
        data=pd.DataFrame({"x": [1]}),
        metadata={},
    )

    assert (
        cross._dataset_identity(
            "Fixture",
            gaze,
        )
        == "Fixture"
    )


def test_cross_identity_from_data():
    gaze = SimpleNamespace(
        data=pd.DataFrame(
            {
                "dataset_id": [
                    "DataSet",
                    "DataSet",
                ]
            }
        ),
        metadata={},
    )

    assert (
        cross._dataset_identity(
            "alias",
            gaze,
        )
        == "DataSet"
    )


def test_cross_identity_multiple_data_ids():
    gaze = SimpleNamespace(
        data=pd.DataFrame(
            {
                "dataset_id": [
                    "A",
                    "B",
                ]
            }
        ),
        metadata={},
    )

    with pytest.raises(
        SchemaError,
        match="multiple dataset_id",
    ):
        cross._dataset_identity(
            "fixture",
            gaze,
        )


def test_cross_identity_metadata_conflict():
    gaze = SimpleNamespace(
        data=pd.DataFrame({"dataset_id": ["Data"]}),
        metadata={
            "source_dataset": "Metadata",
        },
    )

    with pytest.raises(
        SchemaError,
        match="identity conflict",
    ):
        cross._dataset_identity(
            "fixture",
            gaze,
        )


# ============================================================
# PARTICIPANT IDENTITY
# ============================================================


def test_cross_participant_column_required():
    gaze = SimpleNamespace(
        data=pd.DataFrame({"x": [1]}),
        metadata={},
    )

    with pytest.raises(
        SchemaError,
        match="no participant_id",
    ):
        cross._require_resolved_participants(
            "fixture",
            gaze,
        )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "__unresolved__",
        "unknown",
        "none",
        "nan",
    ],
)
def test_cross_unresolved_participant_values(
    value,
):
    gaze = SimpleNamespace(
        data=pd.DataFrame({"participant_id": [value]}),
        metadata={},
    )

    with pytest.raises(
        SchemaError,
        match="fully resolved",
    ):
        cross._require_resolved_participants(
            "fixture",
            gaze,
        )


def test_cross_metadata_unresolved():
    gaze = SimpleNamespace(
        data=pd.DataFrame({"participant_id": ["P01"]}),
        metadata={
            ("participant_identity_resolved"): False,
        },
    )

    with pytest.raises(
        SchemaError,
        match="fully resolved",
    ):
        cross._require_resolved_participants(
            "fixture",
            gaze,
        )


def test_cross_resolved_participant_success():
    gaze = SimpleNamespace(
        data=pd.DataFrame(
            {
                "participant_id": [
                    "P01",
                    "P02",
                ]
            }
        ),
        metadata={
            ("participant_identity_resolved"): True,
        },
    )

    cross._require_resolved_participants(
        "fixture",
        gaze,
    )


# ============================================================
# COORDINATE EVIDENCE
# ============================================================


def test_cross_coordinate_metadata():
    gaze = SimpleNamespace(
        metadata={
            "source_dataset": "Other",
            "coordinate_source_unit": ("degrees"),
            "coordinate_unit_verified": (True),
        }
    )

    assert cross._coordinate_evidence(gaze) == (
        "degrees",
        True,
        "dataset metadata",
    )


def test_cross_coordinate_lund_fallback():
    gaze = SimpleNamespace(
        metadata={
            "source_dataset": ("Lund2013"),
            "coordinate_source_unit": ("unverified"),
            "coordinate_unit_verified": (False),
        }
    )

    assert cross._coordinate_evidence(gaze) == (
        "pixels",
        True,
        ("Lund2013 adapter/source convention"),
    )


def test_cross_coordinate_required():
    gaze = SimpleNamespace(
        metadata={
            "source_dataset": "Other",
            "coordinate_source_unit": ("unverified"),
            "coordinate_unit_verified": (False),
        }
    )

    with pytest.raises(
        SchemaError,
        match="verified coordinate unit",
    ):
        cross._require_verified_coordinates(
            "Other",
            gaze,
        )


# ============================================================
# SHA + SOURCE AUDIT
# ============================================================


@pytest.mark.parametrize(
    (
        "value",
        "expected",
    ),
    [
        (
            SHA_A,
            True,
        ),
        (
            "A" * 64,
            True,
        ),
        (
            "a" * 63,
            False,
        ),
        (
            "g" * 64,
            False,
        ),
        (
            None,
            False,
        ),
    ],
)
def test_cross_is_sha256(
    value,
    expected,
):
    assert cross._is_sha256(value) is expected


def _hollywood_metadata():
    return {
        "source_audit_status": ("verified"),
        ("source_audit_report_fingerprint_sha256"): SHA_A,
        ("source_audit_spec_fingerprint_sha256"): SHA_B,
        ("source_manifest_fingerprint_sha256"): SHA_C,
        "reuse_terms_verified": True,
        "analysis_use_permitted": True,
    }


def test_cross_source_audit_non_hollywood():
    gaze = SimpleNamespace(metadata={})

    assert (
        cross._require_source_audit(
            "Lund2013",
            gaze,
            None,
        )
        is None
    )


def test_cross_source_audit_status():
    metadata = _hollywood_metadata()

    metadata["source_audit_status"] = "template"

    gaze = SimpleNamespace(metadata=metadata)

    with pytest.raises(
        SchemaError,
        match="reviewed source-audit",
    ):
        cross._require_source_audit(
            "Hollywood2EM",
            gaze,
            object(),
        )


def test_cross_source_audit_fingerprint():
    metadata = _hollywood_metadata()

    metadata[("source_manifest_fingerprint_sha256")] = "bad"

    gaze = SimpleNamespace(metadata=metadata)

    with pytest.raises(
        SchemaError,
        match="incomplete or malformed",
    ):
        cross._require_source_audit(
            "Hollywood2EM",
            gaze,
            object(),
        )


def test_cross_source_audit_reuse_terms():
    metadata = _hollywood_metadata()

    metadata["reuse_terms_verified"] = False

    gaze = SimpleNamespace(metadata=metadata)

    with pytest.raises(
        SchemaError,
        match="reuse terms",
    ):
        cross._require_source_audit(
            "Hollywood2EM",
            gaze,
            object(),
        )


def test_cross_source_audit_permission():
    metadata = _hollywood_metadata()

    metadata["analysis_use_permitted"] = False

    gaze = SimpleNamespace(metadata=metadata)

    with pytest.raises(
        SchemaError,
        match="analysis-use permission",
    ):
        cross._require_source_audit(
            "Hollywood2EM",
            gaze,
            object(),
        )


def test_cross_source_audit_lineage_required():
    gaze = SimpleNamespace(metadata=_hollywood_metadata())

    with pytest.raises(
        SchemaError,
        match="lineage receipt",
    ):
        cross._require_source_audit(
            "Hollywood2EM",
            gaze,
            None,
        )


def test_cross_source_audit_success(
    monkeypatch,
):
    gaze = SimpleNamespace(metadata=_hollywood_metadata())

    monkeypatch.setattr(
        cross,
        ("validate_hollywood2_gaze_lineage"),
        lambda gaze, lineage: SHA_A,
    )

    assert (
        cross._require_source_audit(
            "Hollywood2EM",
            gaze,
            object(),
        )
        == SHA_A
    )


# ============================================================
# LABEL NORMALIZATION
# ============================================================


@pytest.mark.parametrize(
    (
        "value",
        "expected",
    ),
    [
        (
            " FIXATION ",
            "fixation",
        ),
        (
            "smooth_pursuit",
            "pursuit",
        ),
        (
            "Smooth_Pursuit",
            "pursuit",
        ),
        (
            10,
            "10",
        ),
    ],
)
def test_cross_normalise_label(
    value,
    expected,
):
    assert cross._normalise_label(value) == expected


# ============================================================
# PREPARATION INPUT GUARDS
# ============================================================


def test_cross_prepare_two_datasets():
    with pytest.raises(
        ValueError,
        match="At least two datasets",
    ):
        cross.prepare_cross_dataset_event_benchmark({"A": _gaze("A")})


@pytest.mark.parametrize(
    "rate",
    [
        0,
        -1,
        np.nan,
        np.inf,
    ],
)
def test_cross_prepare_target_rate(
    rate,
):
    with pytest.raises(
        ValueError,
        match="finite and positive",
    ):
        cross.prepare_cross_dataset_event_benchmark(
            {
                "A": _gaze("A"),
                "B": _gaze("B"),
            },
            target_sampling_rate_hz=rate,
            require_source_audits=False,
        )


def test_cross_prepare_label_inventory():
    with pytest.raises(
        ValueError,
        match="at least two distinct labels",
    ):
        cross.prepare_cross_dataset_event_benchmark(
            {
                "A": _gaze("A"),
                "B": _gaze("B"),
            },
            common_labels=(
                "fixation",
                " FIXATION ",
            ),
            require_source_audits=False,
        )


def test_cross_prepare_dataset_type():
    with pytest.raises(
        TypeError,
        match="must be a GazeFrame",
    ):
        cross.prepare_cross_dataset_event_benchmark(
            {
                "A": object(),
                "B": _gaze("B"),
            },
            require_source_audits=False,
        )


def test_cross_prepare_duplicate_identity():
    first = _gaze(
        "A",
        data_id="Same",
        metadata_source="Same",
    )

    second = _gaze(
        "B",
        data_id="Same",
        metadata_source="Same",
    )

    with pytest.raises(
        SchemaError,
        match="Duplicate dataset identity",
    ):
        cross.prepare_cross_dataset_event_benchmark(
            {
                "A": first,
                "B": second,
            },
            require_source_audits=False,
        )


def test_cross_prepare_missing_event_label():
    with pytest.raises(
        SchemaError,
        match="no event_label",
    ):
        cross.prepare_cross_dataset_event_benchmark(
            {
                "A": _gaze(
                    "A",
                    include_event=False,
                ),
                "B": _gaze("B"),
            },
            require_source_audits=False,
        )


def test_cross_prepare_native_path():
    prepared = cross.prepare_cross_dataset_event_benchmark(
        {
            "A": _gaze(
                "A",
                sampling_rate_hz=60,
            ),
            "B": _gaze(
                "B",
                sampling_rate_hz=60,
            ),
        },
        target_sampling_rate_hz=60,
        require_source_audits=False,
    )

    assert prepared.data["benchmark_label_ambiguous"].eq(False).all()

    assert (
        set(prepared.data["sampling_rate_hz"])
        if "sampling_rate_hz" in prepared.data.columns
        else True
    )

    assert all(
        item["sampling_origin_at_analysis"] == "native"
        for item in prepared.dataset_reports.values()
    )


def test_cross_prepare_upsampling_refused():
    with pytest.raises(
        ValueError,
        match="will not upsample",
    ):
        cross.prepare_cross_dataset_event_benchmark(
            {
                "A": _gaze(
                    "A",
                    sampling_rate_hz=60,
                ),
                "B": _gaze(
                    "B",
                    sampling_rate_hz=60,
                ),
            },
            target_sampling_rate_hz=120,
            require_source_audits=False,
        )


def test_cross_prepare_missing_common_label():
    with pytest.raises(
        SchemaError,
        match="missing required common labels",
    ):
        cross.prepare_cross_dataset_event_benchmark(
            {
                "A": _gaze(
                    "A",
                    labels=(
                        "fixation",
                        "saccade",
                    ),
                ),
                "B": _gaze("B"),
            },
            target_sampling_rate_hz=60,
            require_source_audits=False,
        )


def test_cross_prepare_empty_after_filter():
    with pytest.raises(
        SchemaError,
        match="no rows after label harmonisation",
    ):
        cross.prepare_cross_dataset_event_benchmark(
            {
                "A": _gaze(
                    "A",
                    labels=(
                        "fixation",
                        "saccade",
                    ),
                ),
                "B": _gaze(
                    "B",
                    labels=(
                        "fixation",
                        "saccade",
                    ),
                ),
            },
            target_sampling_rate_hz=60,
            common_labels=(
                "blink",
                "microsaccade",
            ),
            require_all_common_labels=False,
            require_source_audits=False,
        )


def test_cross_prepare_optional_guards_disabled():
    prepared = cross.prepare_cross_dataset_event_benchmark(
        {
            "A": _gaze(
                "A",
                verified=False,
                resolved=False,
            ),
            "B": _gaze(
                "B",
                verified=False,
                resolved=False,
            ),
        },
        target_sampling_rate_hz=60,
        require_resolved_participants=False,
        require_verified_coordinates=False,
        require_source_audits=False,
    )

    assert prepared.design["require_resolved_participants"] is False

    assert prepared.design["require_verified_coordinates"] is False


def test_cross_prepare_lineage_column(
    monkeypatch,
):
    monkeypatch.setattr(
        cross,
        "_require_source_audit",
        lambda name, gaze, lineage: SHA_A if name == "A" else None,
    )

    prepared = cross.prepare_cross_dataset_event_benchmark(
        {
            "A": _gaze("A"),
            "B": _gaze("B"),
        },
        target_sampling_rate_hz=60,
        source_audit_lineages={
            "A": object(),
        },
        require_source_audits=True,
    )

    rows = prepared.data.loc[prepared.data["dataset_id"] == "A"]

    assert rows[("source_audit_lineage_receipt_fingerprint_sha256")].eq(SHA_A).all()


# ============================================================
# VALIDATION SUMMARY
# ============================================================


def _predictions(
    *,
    probabilities: bool,
):
    frame = pd.DataFrame(
        {
            "held_out_dataset": [
                "A",
                "A",
                "B",
                "B",
            ],
            "event_label": [
                "fixation",
                "saccade",
                "fixation",
                "saccade",
            ],
            "predicted_event": [
                "fixation",
                "fixation",
                "fixation",
                "saccade",
            ],
        }
    )

    if probabilities:
        frame["p_event_fixation"] = [
            0.9,
            0.6,
            0.8,
            0.1,
        ]

        frame["p_event_saccade"] = [
            0.1,
            0.4,
            0.2,
            0.9,
        ]

    return frame


def _patch_event_evaluation(
    monkeypatch,
):
    monkeypatch.setattr(
        cross,
        "evaluate_sample_event_predictions",
        lambda *args, **kwargs: SimpleNamespace(
            summary={
                "precision": 0.8,
                "recall": 0.75,
                "f1": 0.77,
                "mean_matched_iou": 0.7,
                ("mean_abs_onset_error_ms"): 3.0,
                ("mean_abs_offset_error_ms"): 4.0,
                ("mean_abs_duration_error_ms"): 5.0,
            }
        ),
    )

    monkeypatch.setattr(
        cross,
        "evaluate_event_calibration",
        lambda *args, **kwargs: {
            "multiclass_brier_score": 0.12,
            ("expected_calibration_error"): 0.08,
        },
    )


def test_cross_validation_summary_without_probs(
    monkeypatch,
):
    _patch_event_evaluation(monkeypatch)

    result = SimpleNamespace(predictions=_predictions(probabilities=False))

    rows = cross._validation_summary(
        "Model",
        result,
        label_col="event_label",
        calibration_bins=4,
        sampling_rate_hz=60.0,
        event_min_iou=0.5,
        event_excluded_labels=(),
    )

    assert len(rows) == 2

    assert np.isnan(rows[0]["multiclass_brier_score"])

    assert rows[0]["event_f1"] == pytest.approx(0.77)


def test_cross_validation_summary_with_probs(
    monkeypatch,
):
    _patch_event_evaluation(monkeypatch)

    result = SimpleNamespace(predictions=_predictions(probabilities=True))

    rows = cross._validation_summary(
        "Model",
        result,
        label_col="event_label",
        calibration_bins=4,
        sampling_rate_hz=60.0,
        event_min_iou=0.5,
        event_excluded_labels=(),
    )

    assert len(rows) == 2

    assert rows[0]["multiclass_brier_score"] == pytest.approx(0.12)

    assert rows[0]["expected_calibration_error"] == pytest.approx(0.08)


# ============================================================
# RUN CROSS-DATASET VALIDATION
# ============================================================


def _prepared_validation(
    *,
    dataset_count=2,
):
    datasets = [
        "A",
        "B",
    ][:dataset_count]

    data = []

    for dataset in datasets:
        data.extend(
            [
                {
                    "dataset_id": dataset,
                    "participant_id": (f"{dataset}::P1"),
                    "event_label": ("fixation"),
                },
                {
                    "dataset_id": dataset,
                    "participant_id": (f"{dataset}::P2"),
                    "event_label": ("saccade"),
                },
            ]
        )

    return cross.CrossDatasetEventPrepared(
        data=pd.DataFrame(data),
        dataset_reports={dataset: {"fixture": True} for dataset in datasets},
        design={
            "target_sampling_rate_hz": 60.0,
        },
    )


def test_cross_run_type():
    with pytest.raises(
        TypeError,
        match="CrossDatasetEventPrepared",
    ):
        cross.run_cross_dataset_event_validation(object())


def test_cross_run_dataset_count():
    with pytest.raises(
        ValueError,
        match="At least two datasets",
    ):
        cross.run_cross_dataset_event_validation(_prepared_validation(dataset_count=1))


def test_cross_run_calibration_bins():
    with pytest.raises(
        ValueError,
        match="at least 2",
    ):
        cross.run_cross_dataset_event_validation(
            _prepared_validation(),
            calibration_bins=1,
        )


@pytest.mark.parametrize(
    "value",
    [
        -0.01,
        1.01,
    ],
)
def test_cross_run_event_iou(
    value,
):
    with pytest.raises(
        ValueError,
        match=r"\[0, 1\]",
    ):
        cross.run_cross_dataset_event_validation(
            _prepared_validation(),
            event_min_iou=value,
        )


def test_cross_run_wrapper_without_model_fitting(
    monkeypatch,
):
    _patch_event_evaluation(monkeypatch)

    predictions = _predictions(probabilities=True)

    rf = SimpleNamespace(predictions=predictions.copy())

    context = SimpleNamespace(predictions=predictions.copy())

    rf_calls = []
    context_calls = []

    def fake_rf(
        data,
        **kwargs,
    ):
        rf_calls.append(kwargs)

        return rf

    def fake_context(
        data,
        **kwargs,
    ):
        context_calls.append(kwargs)

        return context

    monkeypatch.setattr(
        cross,
        "dataset_holdout_event_validate",
        fake_rf,
    )

    monkeypatch.setattr(
        cross,
        ("dataset_holdout_context_event_validate"),
        fake_context,
    )

    result = cross.run_cross_dataset_event_validation(
        _prepared_validation(),
        random_state=11,
        n_estimators=7,
        context_radius_ms=20,
        rolling_window_ms=40,
        hidden_layer_sizes=(8,),
        temporal_solver="lbfgs",
        temporal_max_iter=50,
        calibration_bins=4,
        event_min_iou=0.4,
        event_excluded_labels=("ambiguous",),
    )

    assert result.random_forest is rf
    assert result.context_mlp is context

    assert set(result.summary["model"]) == {
        "RandomForest",
        "ContextMLP",
    }

    assert len(result.report_fingerprint_sha256) == 64

    assert result.design["validation_design"] == "leave_one_dataset_out"

    assert result.design["event_interval_convention"] == "half_open_[start,end)"

    assert rf_calls[0]["n_estimators"] == 7

    assert context_calls[0]["solver"] == "lbfgs"


# ============================================================
# DYNAMIC AOI KEYFRAME CONTRACT
# ============================================================


def _keyframe(
    aoi_id="a",
    *,
    label="target",
    timestamp=0.0,
    xmin=0.0,
    ymin=0.0,
    xmax=100.0,
    ymax=100.0,
    confidence=1.0,
    source="manual",
    model_name="tracker",
    model_version="1",
):
    return dynamic.DynamicAOIKeyframe(
        aoi_id=aoi_id,
        label=label,
        timestamp_ms=timestamp,
        xmin=xmin,
        ymin=ymin,
        xmax=xmax,
        ymax=ymax,
        confidence=confidence,
        source=source,
        model_name=model_name,
        model_version=model_version,
    )


@pytest.mark.parametrize(
    "timestamp",
    [
        np.nan,
        np.inf,
        -np.inf,
    ],
)
def test_dynamic_keyframe_timestamp(
    timestamp,
):
    with pytest.raises(
        ValueError,
        match="timestamp_ms must be finite",
    ):
        _keyframe(timestamp=timestamp)


@pytest.mark.parametrize(
    (
        "xmin",
        "ymin",
        "xmax",
        "ymax",
    ),
    [
        (
            0,
            0,
            0,
            10,
        ),
        (
            0,
            0,
            10,
            0,
        ),
        (
            10,
            0,
            5,
            10,
        ),
    ],
)
def test_dynamic_keyframe_bounds(
    xmin,
    ymin,
    xmax,
    ymax,
):
    with pytest.raises(
        ValueError,
        match="xmax > xmin",
    ):
        _keyframe(
            xmin=xmin,
            ymin=ymin,
            xmax=xmax,
            ymax=ymax,
        )


@pytest.mark.parametrize(
    "confidence",
    [
        -0.01,
        1.01,
    ],
)
def test_dynamic_keyframe_confidence(
    confidence,
):
    with pytest.raises(
        ValueError,
        match="between 0 and 1",
    ):
        _keyframe(confidence=confidence)


# ============================================================
# PROVIDER + DETECTION
# ============================================================


def test_dynamic_callable_provider():
    calls = []

    def tracker(
        stimulus,
        labels,
    ):
        calls.append(
            (
                stimulus,
                tuple(labels),
            )
        )

        return iter([_keyframe()])

    provider = dynamic.CallableDynamicAOIProvider(
        tracker,
        model_name="custom",
        model_version="2",
    )

    result = provider.track(
        "stimulus",
        ["target"],
    )

    assert len(result) == 1

    assert calls == [
        (
            "stimulus",
            ("target",),
        )
    ]


def test_dynamic_detect_requires_labels():
    provider = SimpleNamespace(track=lambda *args: [])

    with pytest.raises(
        ValueError,
        match="At least one semantic label",
    ):
        dynamic.detect_dynamic_aois(
            object(),
            labels=[],
            provider=provider,
        )


@pytest.mark.parametrize(
    "value",
    [
        -0.01,
        1.01,
    ],
)
def test_dynamic_detect_confidence_guard(
    value,
):
    provider = SimpleNamespace(track=lambda *args: [])

    with pytest.raises(
        ValueError,
        match=r"\[0, 1\]",
    ):
        dynamic.detect_dynamic_aois(
            object(),
            labels=["target"],
            provider=provider,
            min_confidence=value,
        )


def test_dynamic_detect_threshold():
    provider = SimpleNamespace(
        track=lambda *args: [
            _keyframe(
                aoi_id="low",
                confidence=0.2,
            ),
            _keyframe(
                aoi_id="high",
                confidence=0.9,
            ),
        ]
    )

    result = dynamic.detect_dynamic_aois(
        object(),
        labels=["target"],
        provider=provider,
        min_confidence=0.5,
    )

    assert [item.aoi_id for item in result] == ["high"]


# ============================================================
# FRAME CONVERSION
# ============================================================


def test_dynamic_to_frame():
    frame = dynamic.dynamic_aois_to_frame([_keyframe()])

    assert (
        frame.loc[
            0,
            "aoi_id",
        ]
        == "a"
    )

    assert (
        frame.loc[
            0,
            "model_name",
        ]
        == "tracker"
    )


def test_dynamic_from_frame_missing():
    with pytest.raises(
        SchemaError,
        match="missing columns",
    ):
        dynamic.dynamic_aois_from_frame(pd.DataFrame({"aoi_id": ["a"]}))


def test_dynamic_from_frame_duplicate():
    frame = pd.DataFrame(
        {
            "aoi_id": [
                "a",
                "a",
            ],
            "label": [
                "target",
                "target",
            ],
            "timestamp_ms": [
                0,
                0,
            ],
            "xmin": [
                0,
                0,
            ],
            "ymin": [
                0,
                0,
            ],
            "xmax": [
                10,
                10,
            ],
            "ymax": [
                10,
                10,
            ],
        }
    )

    with pytest.raises(
        SchemaError,
        match="duplicate",
    ):
        dynamic.dynamic_aois_from_frame(frame)


def test_dynamic_from_frame_defaults_and_nan():
    frame = pd.DataFrame(
        {
            "aoi_id": ["a"],
            "label": ["target"],
            "timestamp_ms": [0],
            "xmin": [0],
            "ymin": [0],
            "xmax": [10],
            "ymax": [10],
            "confidence": [np.nan],
            "source": [np.nan],
            "model_name": [np.nan],
            "model_version": [np.nan],
        }
    )

    result = dynamic.dynamic_aois_from_frame(
        frame,
        default_source="reviewed",
    )

    item = result[0]

    assert item.confidence == 1.0
    assert item.source == "reviewed"
    assert item.model_name is None
    assert item.model_version is None


def test_dynamic_from_frame_optional_absent():
    frame = pd.DataFrame(
        {
            "aoi_id": ["a"],
            "label": ["target"],
            "timestamp_ms": [0],
            "xmin": [0],
            "ymin": [0],
            "xmax": [10],
            "ymax": [10],
        }
    )

    result = dynamic.dynamic_aois_from_frame(frame)

    assert result[0].confidence == 1.0
    assert result[0].source == "manual"


# ============================================================
# SORTED TRACK
# ============================================================


def test_dynamic_sorted_track_empty():
    assert dynamic._sorted_track([]) == []


def test_dynamic_sorted_track_multiple_ids():
    with pytest.raises(
        ValueError,
        match="exactly one AOI track",
    ):
        dynamic._sorted_track(
            [
                _keyframe("a"),
                _keyframe(
                    "b",
                    timestamp=100,
                ),
            ]
        )


def test_dynamic_sorted_track_duplicate_times():
    with pytest.raises(
        ValueError,
        match="duplicate keyframe timestamps",
    ):
        dynamic._sorted_track(
            [
                _keyframe(timestamp=0),
                _keyframe(timestamp=0),
            ]
        )


def test_dynamic_sorted_track_label_drift():
    with pytest.raises(
        ValueError,
        match="one semantic label",
    ):
        dynamic._sorted_track(
            [
                _keyframe(
                    label="one",
                    timestamp=0,
                ),
                _keyframe(
                    label="two",
                    timestamp=100,
                ),
            ]
        )


def test_dynamic_sorted_track_orders():
    result = dynamic._sorted_track(
        [
            _keyframe(timestamp=100),
            _keyframe(timestamp=0),
        ]
    )

    assert [item.timestamp_ms for item in result] == [
        0,
        100,
    ]


# ============================================================
# INTERPOLATION
# ============================================================


def _track(
    *,
    model_change=False,
):
    return [
        _keyframe(
            timestamp=0,
            xmin=0,
            xmax=100,
            confidence=0.5,
            model_name="A",
            model_version="1",
        ),
        _keyframe(
            timestamp=100,
            xmin=100,
            xmax=200,
            confidence=1.0,
            model_name=("B" if model_change else "A"),
            model_version=("2" if model_change else "1"),
        ),
    ]


def test_dynamic_interpolate_negative_gap():
    with pytest.raises(
        ValueError,
        match="non-negative",
    ):
        dynamic.interpolate_dynamic_aoi(
            _track(),
            50,
            max_gap_ms=-1,
        )


@pytest.mark.parametrize(
    "timestamp",
    [
        np.nan,
        np.inf,
        -np.inf,
    ],
)
def test_dynamic_interpolate_nonfinite(
    timestamp,
):
    assert (
        dynamic.interpolate_dynamic_aoi(
            _track(),
            timestamp,
        )
        is None
    )


def test_dynamic_interpolate_empty():
    assert (
        dynamic.interpolate_dynamic_aoi(
            [],
            10,
        )
        is None
    )


def test_dynamic_interpolate_exact():
    result = dynamic.interpolate_dynamic_aoi(
        _track(),
        0,
    )

    assert result is not None
    assert result.source == "manual"
    assert result.timestamp_ms == 0


@pytest.mark.parametrize(
    "timestamp",
    [
        -1,
        101,
    ],
)
def test_dynamic_interpolate_no_extrapolation(
    timestamp,
):
    assert (
        dynamic.interpolate_dynamic_aoi(
            _track(),
            timestamp,
        )
        is None
    )


def test_dynamic_interpolate_large_gap():
    assert (
        dynamic.interpolate_dynamic_aoi(
            _track(),
            50,
            max_gap_ms=99,
        )
        is None
    )


def test_dynamic_interpolate_geometry():
    result = dynamic.interpolate_dynamic_aoi(
        _track(),
        50,
        max_gap_ms=100,
    )

    assert result is not None
    assert result.xmin == pytest.approx(50)
    assert result.xmax == pytest.approx(150)
    assert result.confidence == pytest.approx(0.75)
    assert result.source == "interpolated"
    assert result.model_name == "A"
    assert result.model_version == "1"


def test_dynamic_interpolate_model_drift():
    result = dynamic.interpolate_dynamic_aoi(
        _track(model_change=True),
        50,
        max_gap_ms=100,
    )

    assert result is not None
    assert result.model_name is None
    assert result.model_version is None


# ============================================================
# MAPPING
# ============================================================


def _overlap_tracks():
    return [
        _keyframe(
            aoi_id="large",
            timestamp=0,
            xmin=0,
            ymin=0,
            xmax=100,
            ymax=100,
            confidence=0.8,
        ),
        _keyframe(
            aoi_id="small",
            timestamp=0,
            xmin=20,
            ymin=20,
            xmax=60,
            ymax=60,
            confidence=0.9,
        ),
    ]


def _one_fixation(
    *,
    timestamp=0,
    x=30,
    y=30,
):
    return pd.DataFrame(
        {
            "timestamp_ms": [timestamp],
            "x_px": [x],
            "y_px": [y],
        }
    )


def test_dynamic_mapping_missing_columns():
    with pytest.raises(
        SchemaError,
        match="requires fixation columns",
    ):
        dynamic.map_fixations_to_dynamic_aois(
            pd.DataFrame({"timestamp_ms": [0]}),
            _overlap_tracks(),
        )


def test_dynamic_mapping_overlap_rule():
    with pytest.raises(
        ValueError,
        match="overlap_rule",
    ):
        dynamic.map_fixations_to_dynamic_aois(
            _one_fixation(),
            _overlap_tracks(),
            overlap_rule="other",
        )


def test_dynamic_mapping_highest_confidence():
    result = dynamic.map_fixations_to_dynamic_aois(
        _one_fixation(),
        _overlap_tracks(),
        overlap_rule=("highest_confidence"),
    )

    assert (
        result.loc[
            0,
            "aoi_id",
        ]
        == "small"
    )


def test_dynamic_mapping_highest_confidence_tie_area():
    tracks = [
        _keyframe(
            aoi_id="large",
            xmax=100,
            ymax=100,
            confidence=0.9,
        ),
        _keyframe(
            aoi_id="small",
            xmin=20,
            ymin=20,
            xmax=60,
            ymax=60,
            confidence=0.9,
        ),
    ]

    result = dynamic.map_fixations_to_dynamic_aois(
        _one_fixation(),
        tracks,
        overlap_rule=("highest_confidence"),
    )

    assert (
        result.loc[
            0,
            "aoi_id",
        ]
        == "small"
    )


def test_dynamic_mapping_smallest_area():
    result = dynamic.map_fixations_to_dynamic_aois(
        _one_fixation(),
        _overlap_tracks(),
        overlap_rule="smallest_area",
    )

    assert (
        result.loc[
            0,
            "aoi_id",
        ]
        == "small"
    )


def test_dynamic_mapping_first():
    result = dynamic.map_fixations_to_dynamic_aois(
        _one_fixation(),
        _overlap_tracks(),
        overlap_rule="first",
    )

    assert (
        result.loc[
            0,
            "aoi_id",
        ]
        == "large"
    )


@pytest.mark.parametrize(
    (
        "timestamp",
        "x",
        "y",
    ),
    [
        (
            "bad",
            30,
            30,
        ),
        (
            0,
            "bad",
            30,
        ),
        (
            0,
            30,
            "bad",
        ),
        (
            1000,
            30,
            30,
        ),
        (
            0,
            500,
            500,
        ),
    ],
)
def test_dynamic_mapping_unassigned(
    timestamp,
    x,
    y,
):
    result = dynamic.map_fixations_to_dynamic_aois(
        _one_fixation(
            timestamp=timestamp,
            x=x,
            y=y,
        ),
        _overlap_tracks(),
    )

    assert pd.isna(
        result.loc[
            0,
            "aoi_id",
        ]
    )

    assert pd.isna(
        result.loc[
            0,
            "aoi_confidence",
        ]
    )

    assert pd.isna(
        result.loc[
            0,
            ("aoi_geometry_timestamp_ms"),
        ]
    )


def test_dynamic_mapping_custom_columns():
    frame = pd.DataFrame(
        {
            "time": [0],
            "gx": [30],
            "gy": [30],
        }
    )

    result = dynamic.map_fixations_to_dynamic_aois(
        frame,
        _overlap_tracks(),
        timestamp_col="time",
        x_col="gx",
        y_col="gy",
    )

    assert (
        result.loc[
            0,
            "aoi_id",
        ]
        == "small"
    )


def test_dynamic_mapping_audit_trail():
    class Recorder:
        def __init__(self):
            self.calls = []

        def add(
            self,
            **kwargs,
        ):
            self.calls.append(kwargs)

    trail = Recorder()

    source = _one_fixation()

    result = dynamic.map_fixations_to_dynamic_aois(
        source,
        _overlap_tracks(),
        trail=trail,
    )

    assert len(trail.calls) == 1

    call = trail.calls[0]

    assert call["operation"] == ("map_fixations_to_dynamic_aois")

    assert call["parameters"]["n_keyframes"] == 2

    assert call["parameters"]["n_tracks"] == 2

    pd.testing.assert_frame_equal(
        call["input_data"],
        source,
    )

    pd.testing.assert_frame_equal(
        call["output_data"],
        result,
    )
