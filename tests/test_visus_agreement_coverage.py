from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest
from test_visus_agreement import _audit, _inputs

from gazeforge import visus_agreement as agreement
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    root = tmp_path_factory.mktemp("visus-agreement-coverage")
    audit = _audit(root)
    left, right, timestamps, fixations = _inputs()

    return {
        "audit": audit,
        "left": left,
        "right": right,
        "timestamps": timestamps,
        "fixations": fixations,
    }


def _resign_report(audit):
    body = {key: value for key, value in audit.report.items() if key != "report_fingerprint_sha256"}
    audit.report["report_fingerprint_sha256"] = benchmark_fingerprint(body)


# ============================================================
# AUDIT INTEGRITY
# ============================================================


def test_verify_audit_type_guard():
    with pytest.raises(TypeError, match="VisusSourceAuditRun"):
        agreement._verify_audit(object())


def test_verify_audit_status_guard(case):
    audit = copy.deepcopy(case["audit"])
    audit.report["status"] = "invalid"

    with pytest.raises(BenchmarkIntegrityError, match="not verified"):
        agreement._verify_audit(audit)


def test_verify_audit_spec_fingerprint_guard(case):
    audit = copy.deepcopy(case["audit"])
    audit.report["spec_fingerprint_sha256"] = "0" * 64
    _resign_report(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="specification fingerprint does not revalidate",
    ):
        agreement._verify_audit(audit)


def test_verify_audit_manifest_fingerprint_guard(case):
    audit = copy.deepcopy(case["audit"])
    audit.report["inventory"]["manifest_fingerprint_sha256"] = "0" * 64
    _resign_report(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="manifest fingerprint does not revalidate",
    ):
        agreement._verify_audit(audit)


# ============================================================
# INDEPENDENCE + STIMULUS CONTRACTS
# ============================================================


def test_require_independence_spec_guard(case):
    audit = copy.deepcopy(case["audit"])
    object.__setattr__(
        audit.spec,
        "independent_annotation_streams_verified",
        False,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not verify independent annotation streams",
    ):
        agreement._require_independence(audit)


def test_audited_stimuli_requires_nonempty_identity(case):
    audit = copy.deepcopy(case["audit"])
    audit.report["identity"]["stimulus_ids"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="no verified stimulus identities",
    ):
        agreement._audited_stimuli(audit)


def test_require_exact_keys_rejects_missing_and_extra():
    with pytest.raises(
        SchemaError,
        match="must exactly cover",
    ) as exc:
        agreement._require_exact_keys(
            {
                "S01": object(),
                "EXTRA": object(),
            },
            ["S01", "S02"],
            name="fixture mapping",
        )

    message = str(exc.value)
    assert "S02" in message
    assert "EXTRA" in message


# ============================================================
# STREAM CONTRACTS
# ============================================================


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("", "annotator_b"),
        ("annotator_a", ""),
        ("   ", "annotator_b"),
    ],
)
def test_require_streams_rejects_empty_identifiers(case, left, right):
    audit = case["audit"]
    stimuli = agreement._audited_stimuli(audit)

    with pytest.raises(
        ValueError,
        match="identifiers cannot be empty",
    ):
        agreement._require_streams(
            audit,
            stimuli,
            left_stream_id=left,
            right_stream_id=right,
        )


def test_require_streams_requires_both_streams_for_every_stimulus(case):
    audit = copy.deepcopy(case["audit"])
    stimuli = agreement._audited_stimuli(audit)

    first = stimuli[0]
    audit.report["annotation_provenance"]["streams_by_stimulus"][first] = ["annotator_a"]

    with pytest.raises(
        SchemaError,
        match="must both be manifested",
    ):
        agreement._require_streams(
            audit,
            stimuli,
            left_stream_id="annotator_a",
            right_stream_id="annotator_b",
        )


# ============================================================
# KEYFRAME CONTRACTS
# ============================================================


def test_keyframes_rejects_empty_sequence():
    with pytest.raises(
        SchemaError,
        match="has no keyframes",
    ):
        agreement._keyframes(
            [],
            stream_id="annotator_a",
            stimulus_id="S01",
        )


def test_keyframes_rejects_wrong_object_type():
    with pytest.raises(
        TypeError,
        match="DynamicAOIKeyframe",
    ):
        agreement._keyframes(
            [object()],
            stream_id="annotator_a",
            stimulus_id="S01",
        )


# ============================================================
# TIMESTAMP GRID CONTRACTS
# ============================================================


@pytest.mark.parametrize(
    "values",
    [
        [],
        [0.0, np.nan, 100.0],
        [[0.0, 50.0], [100.0, 150.0]],
    ],
)
def test_grid_rejects_nonfinite_empty_or_nonvector(values):
    with pytest.raises(
        ValueError,
        match="finite and one-dimensional",
    ):
        agreement._grid(
            values,
            stimulus_id="S01",
        )


@pytest.mark.parametrize(
    "values",
    [
        [0.0, 50.0, 50.0],
        [0.0, 100.0, 50.0],
    ],
)
def test_grid_requires_unique_increasing_values(values):
    with pytest.raises(
        ValueError,
        match="unique and increasing",
    ):
        agreement._grid(
            values,
            stimulus_id="S01",
        )


# ============================================================
# FIXATION TABLE CONTRACTS
# ============================================================


def test_fixation_agreement_requires_columns():
    frame = pd.DataFrame(
        {
            "timestamp_ms": [0.0],
        }
    )

    with pytest.raises(
        SchemaError,
        match="missing columns",
    ):
        agreement._fixation_agreement(
            {"S01": frame},
            {"S01": []},
            {"S01": []},
            stimuli=["S01"],
            max_interpolation_gap_ms=100.0,
            overlap_rule="highest_confidence",
        )


def test_fixation_agreement_rejects_empty_table():
    frame = pd.DataFrame(
        columns=[
            "timestamp_ms",
            "x_px",
            "y_px",
        ]
    )

    with pytest.raises(
        SchemaError,
        match="is empty",
    ):
        agreement._fixation_agreement(
            {"S01": frame},
            {"S01": []},
            {"S01": []},
            stimuli=["S01"],
            max_interpolation_gap_ms=100.0,
            overlap_rule="highest_confidence",
        )


# ============================================================
# RUNNER PARAMETER CONTRACTS
# ============================================================


def _run(case, **overrides):
    kwargs = {
        "audit": case["audit"],
        "left_by_stimulus": case["left"],
        "right_by_stimulus": case["right"],
        "timestamps_by_stimulus": case["timestamps"],
        "left_stream_id": "annotator_a",
        "right_stream_id": "annotator_b",
        "timestamp_grid_basis": "fixture video frame timestamps",
        "max_interpolation_gap_ms": 100.0,
    }
    kwargs.update(overrides)
    return agreement.run_visus_dynamic_aoi_human_agreement(**kwargs)


def test_runner_requires_timestamp_grid_basis(case):
    with pytest.raises(
        ValueError,
        match="timestamp_grid_basis cannot be empty",
    ):
        _run(
            case,
            timestamp_grid_basis="   ",
        )


@pytest.mark.parametrize(
    "gap",
    [
        -1.0,
        np.inf,
        np.nan,
    ],
)
def test_runner_requires_valid_interpolation_gap(case, gap):
    with pytest.raises(
        ValueError,
        match="finite and non-negative",
    ):
        _run(
            case,
            max_interpolation_gap_ms=gap,
        )


@pytest.mark.parametrize(
    "threshold",
    [
        -0.01,
        1.01,
        np.inf,
        np.nan,
    ],
)
def test_runner_requires_valid_iou_threshold(case, threshold):
    with pytest.raises(
        ValueError,
        match=r"finite and in \[0, 1\]",
    ):
        _run(
            case,
            min_iou=threshold,
        )


def test_runner_fixation_assignment_requires_pixel_coordinates(case):
    audit = copy.deepcopy(case["audit"])

    object.__setattr__(
        audit.spec,
        "coordinate_unit",
        "normalized",
    )

    audit.report["spec_fingerprint_sha256"] = benchmark_fingerprint(audit.spec.to_dict())
    _resign_report(audit)

    with pytest.raises(
        SchemaError,
        match="requires audited pixel coordinates",
    ):
        agreement.run_visus_dynamic_aoi_human_agreement(
            audit,
            left_by_stimulus=case["left"],
            right_by_stimulus=case["right"],
            timestamps_by_stimulus=case["timestamps"],
            fixations_by_stimulus=case["fixations"],
            left_stream_id="annotator_a",
            right_stream_id="annotator_b",
            timestamp_grid_basis="fixture video frame timestamps",
            max_interpolation_gap_ms=100.0,
        )


# ============================================================
# OPTIONAL-BRANCH SUCCESS CONTRACT
# ============================================================


def test_runner_without_fixations_or_match_export(case):
    run = _run(
        case,
        fixations_by_stimulus=None,
        include_matches=False,
    )

    assert run.fixation_assignment is None
    assert run.matches.empty
    assert "matches" not in run.report["metrics"]

    assert run.report["protocol"]["fixation_assignment_enabled"] is False

    assert set(run.directional_summary["direction"]) == {
        "left_to_right",
        "right_to_left",
    }
