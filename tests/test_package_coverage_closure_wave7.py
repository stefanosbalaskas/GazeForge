from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.dynamic_evaluation as dynamic_evaluation
import gazeforge.evaluation as evaluation
import gazeforge.evidence_details as evidence_details
import gazeforge.location_scale_bootstrap_monte_carlo as bootstrap_mc
import gazeforge.lund2013 as lund2013
import gazeforge.lund_benchmark as lund_benchmark
import gazeforge.sampling_sensitivity as sampling_sensitivity
import gazeforge.source_candidate_audit_template as audit_template
import gazeforge.visus_osnabrueck_derivative_recovery as visus_derivative
from gazeforge.aoi import AOI
from gazeforge.dynamic_aoi import DynamicAOIKeyframe
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.source_candidate_review import CandidateSourceReviewScaffold

# ======================================================================
# location_scale_bootstrap_monte_carlo.py
# Close the roundoff-sized negative residual clamp.
# ======================================================================


def test_bootstrap_mcse_clamps_roundoff_sized_negative_residual(
    monkeypatch,
):
    original_dot = bootstrap_mc.np.dot

    def controlled_dot(left, right):
        if np.asarray(left).shape == (3,) and np.asarray(right).shape == (3,):
            return 1.5 - 1e-15
        return original_dot(left, right)

    monkeypatch.setattr(
        bootstrap_mc.np,
        "dot",
        controlled_dot,
    )

    result = bootstrap_mc._jackknife_sd_mcse(np.array([0.0, 1.0, 2.0]))

    assert np.isfinite(result)
    assert result >= 0.0


# ======================================================================
# visus_osnabrueck_derivative_recovery.py
# Final residual is the _true fail-closed branch.
# ======================================================================


def test_visus_derivative_true_guard_rejects_false():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        visus_derivative._true(
            False,
            "coverage contract",
        )


# ======================================================================
# dynamic_evaluation.py
# ======================================================================


def _dynamic_frame(
    *,
    aoi_id: str = "A",
    label: str = "target",
    timestamp_ms: float = 0.0,
) -> DynamicAOIKeyframe:
    return DynamicAOIKeyframe(
        aoi_id=aoi_id,
        label=label,
        timestamp_ms=timestamp_ms,
        xmin=0.0,
        ymin=0.0,
        xmax=10.0,
        ymax=10.0,
    )


def test_dynamic_snapshot_rejects_nonfinite_timestamp():
    with pytest.raises(
        ValueError,
        match="timestamp_ms must be finite",
    ):
        dynamic_evaluation.dynamic_aoi_snapshot(
            [],
            np.nan,
        )


def test_dynamic_snapshot_rejects_negative_gap():
    with pytest.raises(
        ValueError,
        match="must be non-negative",
    ):
        dynamic_evaluation.dynamic_aoi_snapshot(
            [],
            0.0,
            max_interpolation_gap_ms=-1.0,
        )


def test_dynamic_evaluation_rejects_bad_iou():
    with pytest.raises(
        ValueError,
        match="min_iou",
    ):
        dynamic_evaluation.evaluate_dynamic_aoi_tracks(
            [],
            [],
            timestamps_ms=[0.0],
            min_iou=2.0,
        )


@pytest.mark.parametrize(
    "timestamps",
    [
        [],
        [[0.0]],
    ],
)
def test_dynamic_evaluation_requires_1d_grid(timestamps):
    with pytest.raises(
        ValueError,
        match="one-dimensional evaluation grid",
    ):
        dynamic_evaluation.evaluate_dynamic_aoi_tracks(
            [],
            [],
            timestamps_ms=timestamps,
        )


def test_dynamic_evaluation_requires_finite_grid():
    with pytest.raises(
        ValueError,
        match="finite one-dimensional",
    ):
        dynamic_evaluation.evaluate_dynamic_aoi_tracks(
            [],
            [],
            timestamps_ms=[0.0, np.nan],
        )


def test_dynamic_evaluation_rejects_duplicate_times():
    with pytest.raises(
        ValueError,
        match="must not contain duplicates",
    ):
        dynamic_evaluation.evaluate_dynamic_aoi_tracks(
            [],
            [],
            timestamps_ms=[0.0, 0.0],
        )


def test_dynamic_evaluation_requires_increasing_times():
    with pytest.raises(
        ValueError,
        match="strictly increasing",
    ):
        dynamic_evaluation.evaluate_dynamic_aoi_tracks(
            [],
            [],
            timestamps_ms=[10.0, 0.0],
        )


def test_dynamic_fixation_agreement_requires_columns():
    with pytest.raises(
        SchemaError,
        match="requires fixation columns",
    ):
        dynamic_evaluation.dynamic_fixation_assignment_agreement(
            pd.DataFrame({"x_px": [1.0]}),
            [],
            [],
        )


def test_dynamic_fixation_agreement_rejects_reserved_key():
    frame = pd.DataFrame(
        {
            "timestamp_ms": [0.0],
            "x_px": [1.0],
            "y_px": [1.0],
            "__gazeforge_fixation_index": [0],
        }
    )

    with pytest.raises(
        SchemaError,
        match="Reserved internal fixation key",
    ):
        dynamic_evaluation.dynamic_fixation_assignment_agreement(
            frame,
            [],
            [],
        )


def test_dynamic_report_includes_optional_agreement_and_matches(
    monkeypatch,
):
    result = dynamic_evaluation.DynamicAOIEvaluation(
        summary={"f1": 1.0},
        per_timestamp=pd.DataFrame(
            {
                "timestamp_ms": [0.0],
                "tp": [1],
            }
        ),
        matches=pd.DataFrame(
            {
                "timestamp_ms": [0.0],
                "status": ["matched"],
            }
        ),
    )

    observed = {}

    def fake_build_benchmark_report(
        *,
        benchmark,
        metrics,
        model,
        protocol,
    ):
        observed["benchmark"] = benchmark
        observed["metrics"] = metrics
        observed["model"] = model
        observed["protocol"] = protocol
        return {
            "metrics": metrics,
            "protocol": protocol,
        }

    monkeypatch.setattr(
        dynamic_evaluation,
        "build_benchmark_report",
        fake_build_benchmark_report,
    )

    report = dynamic_evaluation.build_dynamic_aoi_benchmark_report(
        result,
        benchmark=object(),
        fixation_agreement={
            "exact_agreement": 1.0,
        },
        include_matches=True,
    )

    assert report["metrics"]["fixation_assignment_agreement"]["exact_agreement"] == 1.0
    assert report["metrics"]["matches"][0]["status"] == "matched"


# ======================================================================
# evidence_details.py
# ======================================================================


def test_evidence_text_none():
    assert evidence_details._text(None) == "—"


def test_evidence_text_nonfinite():
    assert evidence_details._text(np.inf) == "—"


def test_evidence_text_large_float():
    assert evidence_details._text(123.456) == "123.5"


def test_evidence_table_empty():
    assert (
        evidence_details._table(
            [],
            [("x", "X")],
        )
        == ""
    )


def test_model_summary_rejects_nonmodel_rows():
    assert (
        evidence_details._model_summary(
            {
                "summary": [
                    {
                        "accuracy_mean": 1.0,
                    }
                ]
            }
        )
        == ""
    )


def test_paired_summary_rejects_irrelevant_metrics():
    assert (
        evidence_details._paired_summary(
            {
                "paired_model_difference_summary": [
                    {
                        "metric": "unrelated_metric",
                    }
                ]
            }
        )
        == ""
    )


def test_agreement_summary_skips_nonmapping_strata():
    markdown = evidence_details._agreement_summary(
        {
            "overall": {
                "n_aligned_samples": 10,
                "exact_agreement": 0.9,
                "cohen_kappa": 0.8,
            },
            "by_stimulus_type": {
                "image": "invalid",
            },
        }
    )

    assert "Human–human annotation agreement" in markdown
    assert "image" not in markdown


def test_report_detail_requires_benchmark_and_metrics():
    assert evidence_details.render_validated_report_detail_markdown({}) == ""


def test_report_detail_fallback_when_no_special_renderer():
    markdown = evidence_details.render_validated_report_detail_markdown(
        {
            "benchmark": {
                "name": "demo",
                "sampling_origin": "native",
                "reference_strength": "human",
            },
            "metrics": {},
            "report_fingerprint_sha256": "a" * 64,
        }
    )

    assert "no specialised public detail renderer" in markdown


# ======================================================================
# sampling_sensitivity.py
# ======================================================================


def _sensitivity_input() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": [
                "P1",
                "P2",
            ],
            "trial_id": [
                "T1",
                "T1",
            ],
            "event_label": [
                "fixation",
                "saccade",
            ],
        }
    )


def test_sensitivity_unique_values_cannot_be_empty():
    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        sampling_sensitivity._normalise_unique(
            [],
            name="demo",
            descending=False,
        )


def test_sensitivity_unique_values_must_be_finite():
    with pytest.raises(
        ValueError,
        match="must be finite",
    ):
        sampling_sensitivity._normalise_unique(
            [np.nan],
            name="demo",
            descending=False,
        )


def test_sensitivity_requires_dataframe():
    with pytest.raises(
        TypeError,
        match="pandas DataFrame",
    ):
        sampling_sensitivity.evaluate_sampling_purity_sensitivity(
            object(),
        )


def test_sensitivity_requires_columns():
    with pytest.raises(
        SchemaError,
        match="missing required columns",
    ):
        sampling_sensitivity.evaluate_sampling_purity_sensitivity(
            pd.DataFrame(),
            source_sampling_rate_hz=120.0,
        )


def test_sensitivity_requires_two_splits():
    with pytest.raises(
        ValueError,
        match="at least 2",
    ):
        sampling_sensitivity.evaluate_sampling_purity_sensitivity(
            _sensitivity_input(),
            source_sampling_rate_hz=120.0,
            n_splits=1,
        )


@pytest.mark.parametrize(
    "source_rate",
    [
        0.0,
        np.nan,
    ],
)
def test_sensitivity_requires_positive_source_rate(source_rate):
    with pytest.raises(
        ValueError,
        match="finite and positive",
    ):
        sampling_sensitivity.evaluate_sampling_purity_sensitivity(
            _sensitivity_input(),
            source_sampling_rate_hz=source_rate,
        )


def test_sensitivity_records_no_rows_after_exclusions(
    monkeypatch,
):
    sampled = pd.DataFrame(
        {
            "participant_id": ["P1"],
            "trial_id": ["T1"],
            "event_label": ["ambiguous"],
        }
    )

    monkeypatch.setattr(
        sampling_sensitivity,
        "resample_labeled_gaze",
        lambda *args, **kwargs: SimpleNamespace(
            data=sampled,
            report={
                "ambiguous_rows": 1,
                "ambiguous_fraction": 1.0,
                "mean_label_purity": 0.0,
            },
        ),
    )

    result = sampling_sensitivity.evaluate_sampling_purity_sensitivity(
        _sensitivity_input(),
        source_sampling_rate_hz=120.0,
        target_sampling_rates_hz=(60.0,),
        min_label_purities=(0.75,),
        n_splits=2,
    )

    assert result.settings.loc[0, "comparison_reason"] == "no_rows_after_label_exclusions"


def test_sensitivity_records_single_class_condition(
    monkeypatch,
):
    sampled = pd.DataFrame(
        {
            "participant_id": [
                "P1",
                "P2",
            ],
            "trial_id": [
                "T1",
                "T1",
            ],
            "event_label": [
                "fixation",
                "fixation",
            ],
        }
    )

    monkeypatch.setattr(
        sampling_sensitivity,
        "resample_labeled_gaze",
        lambda *args, **kwargs: SimpleNamespace(
            data=sampled,
            report={
                "ambiguous_rows": 0,
                "ambiguous_fraction": 0.0,
                "mean_label_purity": 1.0,
            },
        ),
    )

    result = sampling_sensitivity.evaluate_sampling_purity_sensitivity(
        _sensitivity_input(),
        source_sampling_rate_hz=120.0,
        target_sampling_rates_hz=(60.0,),
        min_label_purities=(0.75,),
        n_splits=2,
    )

    assert (
        result.settings.loc[0, "comparison_reason"] == "fewer_than_two_event_labels_after_filtering"
    )


# ======================================================================
# evaluation.py
# ======================================================================


def _aoi(
    *,
    aoi_id: str = "A",
    label: str = "target",
    xmin: float = 0.0,
    ymin: float = 0.0,
    xmax: float = 10.0,
    ymax: float = 10.0,
) -> AOI:
    return AOI(
        aoi_id=aoi_id,
        label=label,
        xmin=xmin,
        ymin=ymin,
        xmax=xmax,
        ymax=ymax,
    )


def test_pairwise_iou_produces_row():
    result = evaluation.pairwise_aoi_iou(
        [_aoi()],
        [_aoi(aoi_id="R")],
    )

    assert len(result) == 1
    assert result.loc[0, "iou"] == pytest.approx(1.0)


def test_match_aois_rejects_bad_threshold():
    with pytest.raises(
        ValueError,
        match="min_iou",
    ):
        evaluation.match_aois(
            [],
            [],
            min_iou=2.0,
        )


def test_match_aois_both_empty():
    result = evaluation.match_aois(
        [],
        [],
    )

    assert result.empty


def test_match_aois_predicted_only():
    result = evaluation.match_aois(
        [_aoi()],
        [],
    )

    assert list(result["status"]) == ["false_positive"]


def test_match_aois_reference_only():
    result = evaluation.match_aois(
        [],
        [_aoi()],
    )

    assert list(result["status"]) == ["false_negative"]


def test_fixation_agreement_requires_columns():
    with pytest.raises(
        SchemaError,
        match="missing columns",
    ):
        evaluation.fixation_assignment_agreement(
            pd.DataFrame(),
            pd.DataFrame(),
        )


def test_fixation_agreement_rejects_duplicate_keys():
    frame = pd.DataFrame(
        {
            "participant_id": ["P1", "P1"],
            "trial_id": ["T1", "T1"],
            "fixation_index": [1, 1],
            "aoi_label": ["A", "A"],
        }
    )

    with pytest.raises(
        SchemaError,
        match="duplicate fixation keys",
    ):
        evaluation.fixation_assignment_agreement(
            frame,
            frame,
        )


def test_fixation_agreement_requires_aligned_keys():
    predicted = pd.DataFrame(
        {
            "participant_id": ["P1"],
            "trial_id": ["T1"],
            "fixation_index": [1],
            "aoi_label": ["A"],
        }
    )
    reference = pd.DataFrame(
        {
            "participant_id": ["P2"],
            "trial_id": ["T1"],
            "fixation_index": [1],
            "aoi_label": ["A"],
        }
    )

    with pytest.raises(
        SchemaError,
        match="No aligned fixation keys",
    ):
        evaluation.fixation_assignment_agreement(
            predicted,
            reference,
        )


def test_aoi_boundary_sensitivity_can_drop_collapsed_aoi():
    fixations = pd.DataFrame(
        {
            "x_px": [5.0],
            "y_px": [5.0],
        }
    )

    result = evaluation.aoi_boundary_sensitivity(
        fixations,
        [_aoi()],
        perturbations_px=(-6.0,),
    )

    assert result.loc[0, "n_retained_aois"] == 0


def test_sample_label_agreement_requires_columns():
    with pytest.raises(
        SchemaError,
        match="missing columns",
    ):
        evaluation.sample_label_agreement(
            pd.DataFrame(),
            pd.DataFrame(),
        )


def test_sample_label_agreement_rejects_duplicates():
    frame = pd.DataFrame(
        {
            "participant_id": ["P1", "P1"],
            "trial_id": ["T1", "T1"],
            "timestamp_ms": [0.0, 0.0],
            "event_label": ["fixation", "fixation"],
        }
    )

    with pytest.raises(
        SchemaError,
        match="duplicate alignment keys",
    ):
        evaluation.sample_label_agreement(
            frame,
            frame,
        )


def test_sample_label_agreement_requires_overlap():
    left = pd.DataFrame(
        {
            "participant_id": ["P1"],
            "trial_id": ["T1"],
            "timestamp_ms": [0.0],
            "event_label": ["fixation"],
        }
    )
    right = pd.DataFrame(
        {
            "participant_id": ["P2"],
            "trial_id": ["T1"],
            "timestamp_ms": [0.0],
            "event_label": ["fixation"],
        }
    )

    with pytest.raises(
        SchemaError,
        match="No aligned samples",
    ):
        evaluation.sample_label_agreement(
            left,
            right,
        )


# ======================================================================
# source_candidate_audit_template.py
# ======================================================================


def _review_scaffold(
    *,
    dataset_key: str = "hollywood2em",
    source_review=None,
    files=(),
) -> CandidateSourceReviewScaffold:
    return CandidateSourceReviewScaffold(
        root=SimpleNamespace(),
        dataset_key=dataset_key,
        candidate_inventory_fingerprint_sha256="a" * 64,
        candidate_file_count=len(files),
        source_review=source_review or {},
        files=tuple(files),
    )


def test_audit_template_notes_must_be_list():
    scaffold = _review_scaffold(
        source_review={
            "notes": "wrong",
        }
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="notes must be a JSON list",
    ):
        audit_template._review_notes(scaffold)


def test_audit_template_requires_review_scaffold():
    with pytest.raises(
        TypeError,
        match="CandidateSourceReviewScaffold",
    ):
        audit_template._require_review_ready(object())


def test_audit_template_rejects_unknown_dataset():
    scaffold = _review_scaffold(
        dataset_key="unknown",
        source_review={
            "dataset_status": "template",
        },
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Unsupported candidate review dataset",
    ):
        audit_template._require_review_ready(scaffold)


def test_audit_template_must_remain_template_status():
    scaffold = _review_scaffold(
        source_review={
            "dataset_status": "empirical",
        }
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="dataset_status='template'",
    ):
        audit_template._require_review_ready(scaffold)


def test_hollywood_template_requires_included_arff():
    scaffold = _review_scaffold()

    with pytest.raises(
        BenchmarkIntegrityError,
        match="at least one reviewed included ARFF",
    ):
        audit_template._compile_hollywood2(
            scaffold,
            {
                "coordinate_unit": "pixels",
            },
        )


def test_giw_template_coordinate_unit_cannot_be_blank():
    scaffold = SimpleNamespace(
        candidate_inventory_fingerprint_sha256="a" * 64,
        files=[
            SimpleNamespace(
                include_in_audit=True,
                role="label",
                path="LabelData/L.mat",
                sha256="a" * 64,
                bytes=1,
                participant_id="P1",
                trial_id="T1",
                labeller_id=1,
                process_path="ProcessData/P.mat",
            ),
            SimpleNamespace(
                include_in_audit=True,
                role="process",
                path="ProcessData/P.mat",
                sha256="b" * 64,
                bytes=1,
            ),
        ],
    )

    review = {
        "notes": [],
        "source_authority_evidence": "reviewed",
        "analysis_use_evidence": "reviewed",
        "redistribution_evidence": "reviewed",
        "label_process_mapping_basis": "reviewed",
        "labeller_mapping_basis": "reviewed",
        "timestamp_sampling_basis": "reviewed",
        "coordinate_unit": "",
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="coordinate_unit must not be empty",
    ):
        audit_template._compile_gaze_in_wild(
            scaffold,
            review,
        )


def test_write_audit_template_requires_spec_type(tmp_path):
    with pytest.raises(
        TypeError,
        match="spec must be",
    ):
        audit_template.write_candidate_source_audit_template(
            object(),
            tmp_path / "template.json",
            candidate_root=tmp_path / "candidate",
        )


def test_write_audit_template_rejects_empirical_status(
    tmp_path,
    monkeypatch,
):
    class FakeSpec:
        dataset_status = "empirical"
        reuse_terms_verified = False
        analysis_use_permitted = False

    monkeypatch.setattr(
        audit_template,
        "Hollywood2SourceAuditSpec",
        FakeSpec,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="dataset_status='template'",
    ):
        audit_template.write_candidate_source_audit_template(
            FakeSpec(),
            tmp_path / "template.json",
            candidate_root=tmp_path / "candidate",
        )


def test_write_audit_template_rejects_permission_promotion(
    tmp_path,
    monkeypatch,
):
    class FakeSpec:
        dataset_status = "template"
        reuse_terms_verified = True
        analysis_use_permitted = False

    monkeypatch.setattr(
        audit_template,
        "Hollywood2SourceAuditSpec",
        FakeSpec,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot mark reuse terms",
    ):
        audit_template.write_candidate_source_audit_template(
            FakeSpec(),
            tmp_path / "template.json",
            candidate_root=tmp_path / "candidate",
        )


def test_write_audit_template_refuses_existing_target(
    tmp_path,
    monkeypatch,
):
    class FakeSpec:
        dataset_status = "template"
        reuse_terms_verified = False
        analysis_use_permitted = False

        def to_dict(self):
            return {
                "dataset_status": "template",
            }

    monkeypatch.setattr(
        audit_template,
        "Hollywood2SourceAuditSpec",
        FakeSpec,
    )

    root = tmp_path / "candidate"
    root.mkdir()

    target = tmp_path / "template.json"
    target.write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError):
        audit_template.write_candidate_source_audit_template(
            FakeSpec(),
            target,
            candidate_root=root,
            overwrite=False,
        )


# ======================================================================
# lund2013.py
# ======================================================================


def test_lund_mat_field_requires_field():
    array = np.zeros(
        (1, 1),
        dtype=[("other", object)],
    )

    with pytest.raises(
        SchemaError,
        match="missing field",
    ):
        lund2013._mat_field(
            array,
            "pos",
        )


def test_lund_numeric_flat_rejects_nonnumeric():
    with pytest.raises(
        SchemaError,
        match="non-numeric",
    ):
        lund2013._numeric_flat(object())


def test_lund_load_requires_existing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        lund2013.load_lund2013_mat(tmp_path / "missing.mat")


def test_lund_load_requires_etdata(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "P1_trial1_labelled_RA.mat"
    path.write_bytes(b"x")

    monkeypatch.setattr(
        lund2013,
        "loadmat",
        lambda path: {},
    )

    with pytest.raises(
        SchemaError,
        match="does not contain ETdata",
    ):
        lund2013.load_lund2013_mat(path)


def test_lund_load_requires_scalar_struct(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "P1_trial1_labelled_RA.mat"
    path.write_bytes(b"x")

    monkeypatch.setattr(
        lund2013,
        "loadmat",
        lambda path: {
            "ETdata": np.zeros(2),
        },
    )

    with pytest.raises(
        SchemaError,
        match="scalar MATLAB struct",
    ):
        lund2013.load_lund2013_mat(path)


def test_lund_directory_requires_existing_root(tmp_path):
    with pytest.raises(FileNotFoundError):
        lund2013.load_lund2013_directory(tmp_path / "missing")


def test_lund_directory_requires_matching_files(tmp_path):
    with pytest.raises(
        FileNotFoundError,
        match="No Lund2013 files matching",
    ):
        lund2013.load_lund2013_directory(tmp_path)


def test_lund_directory_rejects_inconsistent_sampling_rates(
    tmp_path,
    monkeypatch,
):
    first = tmp_path / "P1_trial1_labelled_RA.mat"
    second = tmp_path / "P2_trial1_labelled_RA.mat"
    first.write_bytes(b"x")
    second.write_bytes(b"x")

    def fake_load(path):
        rate = 100.0 if path == first else 200.0
        return SimpleNamespace(
            sampling_rate_hz=rate,
            data=pd.DataFrame(
                {
                    "participant_id": [
                        path.stem,
                    ],
                }
            ),
            screen_size_px=None,
            metadata={},
        )

    monkeypatch.setattr(
        lund2013,
        "load_lund2013_mat",
        fake_load,
    )

    with pytest.raises(
        SchemaError,
        match="inconsistent sampling rates",
    ):
        lund2013.load_lund2013_directory(tmp_path)


# ======================================================================
# lund_benchmark.py
# ======================================================================


def _lund_source(
    frame: pd.DataFrame,
    *,
    rate: float = 100.0,
):
    return SimpleNamespace(
        data=frame,
        sampling_rate_hz=rate,
        screen_size_px=None,
        metadata={},
    )


def test_lund_stimulus_counts_without_stimulus_column():
    frame = pd.DataFrame(
        {
            "participant_id": ["P1"],
            "trial_id": ["T1"],
        }
    )

    assert lund_benchmark._stimulus_counts(frame) == {}


def test_lund_prepare_native_rate_branch_then_missing_label(
    monkeypatch,
):
    monkeypatch.setattr(
        lund_benchmark,
        "validate_lund2013_source_manifest",
        lambda root: None,
    )
    monkeypatch.setattr(
        lund_benchmark,
        "load_lund2013_directory",
        lambda root, annotator="RA": _lund_source(
            pd.DataFrame(
                {
                    "participant_id": [
                        "P1",
                        "P2",
                    ],
                    "trial_id": [
                        "T1",
                        "T1",
                    ],
                }
            )
        ),
    )

    with pytest.raises(
        SchemaError,
        match="missing event_label",
    ):
        lund_benchmark.prepare_lund2013_benchmark(
            "unused",
            target_sampling_rate_hz=None,
        )


def test_lund_prepare_rejects_all_excluded_rows(
    monkeypatch,
):
    monkeypatch.setattr(
        lund_benchmark,
        "validate_lund2013_source_manifest",
        lambda root: None,
    )
    monkeypatch.setattr(
        lund_benchmark,
        "load_lund2013_directory",
        lambda root, annotator="RA": _lund_source(
            pd.DataFrame(
                {
                    "participant_id": [
                        "P1",
                        "P2",
                    ],
                    "trial_id": [
                        "T1",
                        "T1",
                    ],
                    "event_label": [
                        "ambiguous",
                        "ambiguous",
                    ],
                }
            )
        ),
    )

    with pytest.raises(
        SchemaError,
        match="excluded every benchmark row",
    ):
        lund_benchmark.prepare_lund2013_benchmark(
            "unused",
            target_sampling_rate_hz=None,
        )


def test_lund_prepare_requires_two_event_classes(
    monkeypatch,
):
    monkeypatch.setattr(
        lund_benchmark,
        "validate_lund2013_source_manifest",
        lambda root: None,
    )
    monkeypatch.setattr(
        lund_benchmark,
        "load_lund2013_directory",
        lambda root, annotator="RA": _lund_source(
            pd.DataFrame(
                {
                    "participant_id": [
                        "P1",
                        "P2",
                    ],
                    "trial_id": [
                        "T1",
                        "T1",
                    ],
                    "event_label": [
                        "fixation",
                        "fixation",
                    ],
                }
            )
        ),
    )

    with pytest.raises(
        SchemaError,
        match="fewer than two event classes",
    ):
        lund_benchmark.prepare_lund2013_benchmark(
            "unused",
            target_sampling_rate_hz=None,
        )


def test_lund_prepare_requires_two_participants(
    monkeypatch,
):
    monkeypatch.setattr(
        lund_benchmark,
        "validate_lund2013_source_manifest",
        lambda root: None,
    )
    monkeypatch.setattr(
        lund_benchmark,
        "load_lund2013_directory",
        lambda root, annotator="RA": _lund_source(
            pd.DataFrame(
                {
                    "participant_id": [
                        "P1",
                        "P1",
                    ],
                    "trial_id": [
                        "T1",
                        "T1",
                    ],
                    "event_label": [
                        "fixation",
                        "saccade",
                    ],
                }
            )
        ),
    )

    with pytest.raises(
        SchemaError,
        match="at least two participants",
    ):
        lund_benchmark.prepare_lund2013_benchmark(
            "unused",
            target_sampling_rate_hz=None,
        )


def test_lund_annotator_comparison_without_stimulus_column(
    monkeypatch,
):
    base = pd.DataFrame(
        {
            "participant_id": ["P1"],
            "trial_id": ["T1"],
            "timestamp_ms": [0.0],
            "event_label": ["fixation"],
        }
    )

    monkeypatch.setattr(
        lund_benchmark,
        "validate_lund2013_source_manifest",
        lambda root: None,
    )
    monkeypatch.setattr(
        lund_benchmark,
        "load_lund2013_directory",
        lambda root, annotator: _lund_source(base.copy()),
    )
    monkeypatch.setattr(
        lund_benchmark,
        "sample_label_agreement",
        lambda left, right: {
            "exact_agreement": 1.0,
        },
    )

    result = lund_benchmark.compare_lund2013_annotators("unused")

    assert result["by_stimulus_type"] == {}


def test_lund_event_benchmark_requires_two_folds(
    monkeypatch,
):
    prepared = SimpleNamespace(
        data=pd.DataFrame(
            {
                "participant_id": ["P1"],
            }
        ),
        preparation_report={
            "analysis_sampling_rate_hz": 100.0,
        },
    )

    monkeypatch.setattr(
        lund_benchmark,
        "prepare_lund2013_benchmark",
        lambda *args, **kwargs: prepared,
    )

    with pytest.raises(
        SchemaError,
        match="At least two participant folds",
    ):
        lund_benchmark.run_lund2013_event_benchmark(
            "unused",
            n_splits=5,
        )
