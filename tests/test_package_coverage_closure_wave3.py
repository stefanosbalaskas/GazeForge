from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import gazeforge.gaze_in_wild_copy_rights_roadmap_sync as giw_copy
import gazeforge.gaze_in_wild_current_listing_evidence as giw_listing
import gazeforge.gaze_in_wild_distribution_evidence as giw_distribution
import gazeforge.gaze_in_wild_explicit_task_mapping_certificate as giw_task_certificate
import gazeforge.gaze_in_wild_participant_validation_roadmap_sync as giw_participant_roadmap
import gazeforge.gaze_in_wild_supplementary_evidence as giw_supplement
import gazeforge.hollywood2_annotation_provenance as h2_annotation
import gazeforge.hollywood2_coordinate_metadata as h2_coordinate
import gazeforge.hollywood2_copy_rights_roadmap_sync as h2_copy
import gazeforge.hollywood2_gin_accessible_host_evidence as h2_access
import gazeforge.hollywood2_gin_rights_model_exhaustion as h2_gin_rights
import gazeforge.hollywood2_history_evidence as h2_history
import gazeforge.hollywood2_original_subject_metadata_evidence as h2_original
import gazeforge.hollywood2_participant_cardinality_evidence as h2_cardinality
import gazeforge.hollywood2_participant_crosswalk_exhaustion as h2_crosswalk
import gazeforge.hollywood2_token_validation as h2_token
import gazeforge.quality_gating as quality
import gazeforge.resampling as resampling
import gazeforge.schema as schema
from gazeforge.exceptions import BenchmarkIntegrityError

AUTH_PATH = Path("validation/governance/hollywood2-source-token-analysis-authorization-v1.json")

H2_COPY_PATH = Path(
    "validation/evidence/hollywood2/hollywood2-copy-rights-roadmap-sync-evidence-v1.json"
)

H2_GIN_RIGHTS_PATH = Path(
    "validation/evidence/hollywood2/hollywood2-gin-rights-model-exhaustion-evidence-v1.json"
)


def _write_array(path: Path) -> Path:
    path.write_text("[]\n", encoding="utf-8")
    return path


# ======================================================================
# quality_gating.py -- final scalar-group branch
# ======================================================================


def test_motion_quality_summary_handles_intentionally_ungrouped_stream():
    frame = pd.DataFrame(
        {
            "quality_modality": ["pupil", "pupil"],
            "quality_weight": [1.0, 0.5],
            "quality_state": ["clean", "downweighted"],
        }
    )

    summary = quality.summarize_motion_quality(
        frame,
        group_cols=(),
    )

    assert len(summary) == 1
    assert summary.loc[0, "quality_modality"] == "pupil"
    assert summary.loc[0, "n_samples"] == 2
    assert summary.loc[0, "effective_weight_sum"] == pytest.approx(1.5)


# ======================================================================
# resampling.py -- remaining branch-only paths
# ======================================================================


def test_interpolation_exercises_exact_left_only_tolerance_path():
    result = resampling._interpolate_with_gap_limit(
        np.array([0.0, 10.0, 20.0]),
        np.array([0.0, 1.0, 2.0]),
        np.array([10.0 + 5e-10]),
        max_gap_ms=20.0,
    )

    assert result[0] == pytest.approx(1.0)


def test_interpolation_refuses_interpolation_across_excessive_gap():
    result = resampling._interpolate_with_gap_limit(
        np.array([0.0, 10.0]),
        np.array([0.0, 10.0]),
        np.array([5.0]),
        max_gap_ms=1.0,
    )

    assert np.isnan(result[0])


def test_majority_window_handles_no_finite_source_timestamps():
    labels, purity, counts, ambiguous = resampling._majority_label_window(
        np.array([np.nan]),
        np.array(["fixation"], dtype=object),
        np.array([0.0]),
        target_period_ms=10.0,
        min_label_purity=0.75,
        ambiguous_label="ambiguous",
    )

    assert labels == ["ambiguous"]
    assert np.isnan(purity[0])
    assert counts[0] == 0
    assert bool(ambiguous[0]) is True


# ======================================================================
# schema.py -- final branch-only paths
# ======================================================================


def test_sampling_rate_skips_singleton_group_before_valid_group():
    frame = pd.DataFrame(
        {
            "participant_id": ["P1", "P2", "P2"],
            "trial_id": ["T1", "T2", "T2"],
            "timestamp_ms": [0.0, 0.0, 10.0],
        }
    )

    assert schema.infer_sampling_rate_hz(frame) == pytest.approx(100.0)


def test_canonicalize_gaze_can_preserve_input_order_when_sort_disabled():
    frame = pd.DataFrame(
        {
            "participant_id": ["P1", "P1"],
            "trial_id": ["T1", "T1"],
            "timestamp_ms": [10.0, 0.0],
            "x_px": [2.0, 1.0],
            "y_px": [4.0, 3.0],
        }
    )

    result = schema.canonicalize_gaze(
        frame,
        sampling_rate_hz=60.0,
        sort=False,
    )

    assert result.data["timestamp_ms"].tolist() == [10.0, 0.0]


# ======================================================================
# hollywood2_token_validation.py -- optional notes false branch
# ======================================================================


def test_hollywood2_authorization_notes_are_genuinely_optional(tmp_path):
    payload = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    payload.pop("notes", None)
    payload["authorization_fingerprint_sha256"] = h2_token.authorization_fingerprint(payload)

    path = tmp_path / "authorization-without-notes.json"
    path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    authorization = h2_token.load_hollywood2_source_token_analysis_authorization(path)

    assert authorization.notes == ()


# ======================================================================
# Shared fail-closed JSON loading contracts
# ======================================================================


_SIMPLE_LOADERS = (
    giw_listing._load,
    giw_distribution._load,
    giw_supplement._load,
    giw_task_certificate._load,
    h2_annotation._load,
    h2_copy._load,
    h2_access._load,
    h2_gin_rights._load,
    h2_original._load,
    h2_cardinality._load,
    h2_crosswalk._load,
)


@pytest.mark.parametrize("loader", _SIMPLE_LOADERS)
def test_evidence_loaders_fail_closed_on_missing_file(
    loader,
    tmp_path,
):
    with pytest.raises(BenchmarkIntegrityError):
        loader(tmp_path / "missing.json")


@pytest.mark.parametrize("loader", _SIMPLE_LOADERS)
def test_evidence_loaders_reject_nonobject_json(
    loader,
    tmp_path,
):
    path = _write_array(tmp_path / "array.json")

    with pytest.raises(BenchmarkIntegrityError):
        loader(path)


def test_giw_copy_loader_fail_closed_paths(tmp_path):
    with pytest.raises(BenchmarkIntegrityError):
        giw_copy._load(
            tmp_path / "missing.json",
            "copy-rights evidence",
        )

    with pytest.raises(BenchmarkIntegrityError):
        giw_copy._load(
            _write_array(tmp_path / "array.json"),
            "copy-rights evidence",
        )


def test_giw_participant_roadmap_loader_fail_closed_paths(tmp_path):
    with pytest.raises(BenchmarkIntegrityError):
        giw_participant_roadmap._load(
            tmp_path / "missing.json",
            "participant roadmap evidence",
        )

    with pytest.raises(BenchmarkIntegrityError):
        giw_participant_roadmap._load(
            _write_array(tmp_path / "array.json"),
            "participant roadmap evidence",
        )


def test_hollywood2_history_loader_fail_closed_paths(tmp_path):
    with pytest.raises(BenchmarkIntegrityError):
        h2_history._load_mapping(
            tmp_path / "missing.json",
            label="history evidence",
        )

    with pytest.raises(BenchmarkIntegrityError):
        h2_history._load_mapping(
            _write_array(tmp_path / "array.json"),
            label="history evidence",
        )


# ======================================================================
# Missing mapping/object fail-closed contracts
# ======================================================================


_MAPPING_GUARDS = (
    giw_listing._mapping,
    giw_copy._mapping,
    giw_participant_roadmap._mapping,
    giw_distribution._mapping,
    giw_supplement._mapping,
    h2_annotation._mapping,
    h2_copy._mapping,
    h2_access._map,
    h2_gin_rights._mapping,
    h2_history._mapping,
    h2_original._map,
    h2_cardinality._mapping,
    h2_crosswalk._mapping,
)


@pytest.mark.parametrize("guard", _MAPPING_GUARDS)
def test_evidence_mapping_guards_fail_closed(guard):
    with pytest.raises(BenchmarkIntegrityError):
        guard({}, "required_section")


# ======================================================================
# Equality / boolean non-promotion guards
# ======================================================================


_EQUALITY_GUARDS = (
    giw_listing._equal,
    giw_copy._equal,
    giw_participant_roadmap._equal,
    giw_distribution._equal,
    giw_supplement._equal,
    h2_annotation._equal,
    h2_copy._equal,
    h2_access._eq,
    h2_gin_rights._equal,
    h2_history._equal,
    h2_original._eq,
    h2_cardinality._eq,
    h2_crosswalk._equal,
)


@pytest.mark.parametrize("guard", _EQUALITY_GUARDS)
def test_evidence_equality_guards_detect_drift(guard):
    with pytest.raises(BenchmarkIntegrityError):
        guard("actual", "expected", "test field")


_TRUE_GUARDS = (
    giw_listing._true,
    giw_distribution._true,
    giw_supplement._true,
    h2_annotation._true,
    h2_copy._true,
    h2_access._must_true,
    h2_gin_rights._true,
    h2_history._true,
    h2_original._must_true,
    h2_cardinality._true,
    h2_crosswalk._true,
)


@pytest.mark.parametrize("guard", _TRUE_GUARDS)
def test_evidence_true_guards_reject_false(guard):
    with pytest.raises(BenchmarkIntegrityError):
        guard(False, "required positive evidence")


_FALSE_GUARDS = (
    giw_listing._false,
    giw_distribution._false,
    giw_supplement._false,
    h2_annotation._false,
    h2_copy._false,
    h2_access._must_false,
    h2_gin_rights._false,
    h2_history._false,
    h2_original._must_false,
    h2_cardinality._false,
    h2_crosswalk._false,
)


@pytest.mark.parametrize("guard", _FALSE_GUARDS)
def test_evidence_false_guards_reject_claim_promotion(guard):
    with pytest.raises(BenchmarkIntegrityError):
        guard(True, "prohibited promotion")


# ======================================================================
# GIW roadmap root-resolution branches
# ======================================================================


def test_giw_copy_roadmap_repository_root_explicit_and_fallback(
    tmp_path,
    monkeypatch,
):
    explicit = giw_copy._repository_root(
        None,
        tmp_path,
    )
    assert explicit == tmp_path

    monkeypatch.chdir(tmp_path)
    fallback = giw_copy._repository_root(
        None,
        None,
    )
    assert fallback == tmp_path


def test_giw_participant_roadmap_repository_root_explicit_and_fallback(
    tmp_path,
    monkeypatch,
):
    explicit = giw_participant_roadmap._repository_root(
        None,
        tmp_path,
    )
    assert explicit == tmp_path

    monkeypatch.chdir(tmp_path)
    fallback = giw_participant_roadmap._repository_root(
        None,
        None,
    )
    assert fallback == tmp_path


# ======================================================================
# GIW current-listing primitive guards
# ======================================================================


def test_current_listing_true_guard_rejects_missing_positive_evidence():
    with pytest.raises(BenchmarkIntegrityError):
        giw_listing._true(
            False,
            "first-party listing verification",
        )


def test_current_listing_false_guard_rejects_promotion():
    with pytest.raises(BenchmarkIntegrityError):
        giw_listing._false(
            True,
            "dataset rights",
        )


# ======================================================================
# Hollywood2 coordinate-metadata residual branches
# ======================================================================


def test_coordinate_header_byte_limit_is_enforced(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "oversize.arff"
    path.write_bytes(b"@relation too_long\n@data\n")

    monkeypatch.setattr(
        h2_coordinate,
        "HEADER_BYTE_LIMIT",
        4,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="header exceeded",
    ):
        h2_coordinate._read_header(path)


def test_coordinate_metadata_value_preserves_non_numeric_text():
    assert h2_coordinate._metadata_value("not-a-number") == "not-a-number"


def test_coordinate_metadata_rejects_non_arff_file(tmp_path):
    path = tmp_path / "header.txt"
    path.write_text("@data\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"\.arff"):
        h2_coordinate.inspect_hollywood2_arff_header(path)


def test_coordinate_probe_requires_at_least_one_arff(tmp_path):
    with pytest.raises(FileNotFoundError, match="No Hollywood2 ARFF"):
        h2_coordinate.build_hollywood2_coordinate_metadata_probe(tmp_path)


def test_coordinate_probe_tracks_required_schema_without_author_metadata(
    tmp_path,
):
    path = tmp_path / "example.arff"
    path.write_text(
        "\n".join(
            [
                "@relation gaze_labels",
                "@attribute time numeric",
                "@attribute x numeric",
                "@attribute y numeric",
                "@attribute confidence numeric",
                "@attribute handlabeller_1 string",
                "@attribute handlabeller_final string",
                "@data",
                "",
            ]
        ),
        encoding="utf-8",
    )

    record = h2_coordinate.build_hollywood2_coordinate_metadata_probe(tmp_path)

    assert record["record_type"] == h2_coordinate.RECORD_TYPE


# ======================================================================
# Real frozen-record negative behavioral contracts
# ======================================================================


def test_hollywood2_copy_rights_rejects_interpretation_count_drift():
    record = json.loads(H2_COPY_PATH.read_text(encoding="utf-8"))
    record["interpretation"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="four interpretation",
    ):
        h2_copy.validate_hollywood2_copy_rights_roadmap_sync(record)


def test_hollywood2_gin_rights_requires_six_claim_limits():
    record = json.loads(H2_GIN_RIGHTS_PATH.read_text(encoding="utf-8"))
    record["claim_limits"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="six claim limits",
    ):
        h2_gin_rights.validate_hollywood2_gin_rights_model_exhaustion(record)


def test_hollywood2_gin_rights_requires_next_action():
    record = json.loads(H2_GIN_RIGHTS_PATH.read_text(encoding="utf-8"))
    record["next_required_action"] = ""

    with pytest.raises(
        BenchmarkIntegrityError,
        match="next action",
    ):
        h2_gin_rights.validate_hollywood2_gin_rights_model_exhaustion(record)


# ======================================================================
# Explicit task-mapping certificate digest guard
# ======================================================================


@pytest.mark.parametrize(
    "value",
    [
        "",
        "abc",
        "A" * 64,
        "g" * 64,
    ],
)
def test_explicit_task_certificate_rejects_invalid_sha256(value):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="lowercase SHA-256",
    ):
        giw_task_certificate._require_sha256(
            value,
            label="test digest",
        )
