import json

import numpy as np
from scipy.io import savemat

from gazeforge import (
    compare_lund2013_annotators,
    lund_fetch,
    prepare_lund2013_benchmark,
    run_lund2013_event_benchmark,
)


def _write_recording(path, *, phase=0.0, annotator_offset=0):
    n = 400
    pos = np.zeros((n, 6), dtype=float)
    t = np.arange(n, dtype=float)
    pos[:, 3] = 500 + 0.2 * t + phase
    pos[:, 4] = 300 + 8 * np.sin(t / 15.0 + phase)
    labels = np.where((np.arange(n) + annotator_offset) % 200 < 150, 1, 2)
    pos[:, 5] = labels
    savemat(
        path,
        {
            "ETdata": {
                "pos": pos,
                "sampFreq": np.array([[500.0]]),
                "screenRes": np.array([[1920.0, 1080.0]]),
                "screenDim": np.array([[530.0, 300.0]]),
                "viewDist": np.array([[650.0]]),
            }
        },
    )


def _benchmark_tree(tmp_path):
    image_dir = tmp_path / "img"
    image_dir.mkdir()
    for index, participant in enumerate(("P01", "P02", "P03")):
        _write_recording(
            image_dir / f"{participant}_img_scene_labelled_RA.mat",
            phase=float(index),
        )
        _write_recording(
            image_dir / f"{participant}_img_scene_labelled_MN.mat",
            phase=float(index),
            annotator_offset=2,
        )
    return tmp_path


def _write_source_manifest(root):
    records = []
    for path in sorted(root.rglob("*.mat")):
        payload = path.read_bytes()
        annotator = "RA" if path.name.endswith("_RA.mat") else "MN"
        records.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "stimulus_family": "img",
                "annotator": annotator,
                "git_blob_sha1": lund_fetch._git_blob_sha1(payload),
                "size_bytes": len(payload),
            }
        )
    body = {
        "dataset": "Lund2013",
        "repository": lund_fetch.LUND2013_REPOSITORY,
        "commit": lund_fetch.LUND2013_COMMIT,
        "data_path": lund_fetch.LUND2013_DATA_PATH,
        "repository_license": "GPL-3.0",
        "bundled_by_gazeforge": False,
        "annotators": ["RA", "MN"],
        "stimulus_families": ["img"],
        "file_count": len(records),
        "files": records,
    }
    fingerprint = lund_fetch._manifest_fingerprint(body)
    manifest = {**body, "manifest_fingerprint_sha256": fingerprint}
    (root / "_gazeforge_source_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return fingerprint


def test_prepare_lund2013_benchmark_records_60hz_provenance(tmp_path):
    root = _benchmark_tree(tmp_path)
    prepared = prepare_lund2013_benchmark(
        root,
        annotator="RA",
        target_sampling_rate_hz=60,
        min_label_purity=0.75,
    )
    assert prepared.dataset_card.name == "Lund2013"
    assert prepared.dataset_card.split_unit == "participant_id"
    assert prepared.preparation_report["source_manifest"] is None
    assert prepared.preparation_report["source_sampling_rate_hz"] == 500
    assert prepared.preparation_report["analysis_sampling_rate_hz"] == 60
    assert prepared.data["participant_id"].nunique() == 3
    assert set(prepared.data["stimulus_type"]) == {"image"}
    assert set(prepared.data["annotator"]) == {"RA"}
    counts = prepared.preparation_report["stimulus_type_counts"]["image"]
    assert counts["participants"] == 3
    assert counts["trials"] == 3
    assert counts["rows"] == len(prepared.data)


def test_lund2013_annotator_agreement_runs_native_and_resampled(tmp_path):
    root = _benchmark_tree(tmp_path)
    native = compare_lund2013_annotators(root)
    low_rate = compare_lund2013_annotators(root, target_sampling_rate_hz=60)
    assert native["overall"]["n_aligned_samples"] > low_rate["overall"]["n_aligned_samples"]
    assert -1 <= native["overall"]["cohen_kappa"] <= 1
    assert "image" in low_rate["by_stimulus_type"]
    assert native["source_manifest"] is None


def test_lund2013_event_benchmark_builds_fingerprinted_report(tmp_path):
    root = _benchmark_tree(tmp_path)
    source_fingerprint = _write_source_manifest(root)
    run = run_lund2013_event_benchmark(
        root,
        annotator="RA",
        target_sampling_rate_hz=60,
        n_splits=2,
        n_estimators=10,
        context_radius_ms=20,
        hidden_layer_sizes=(4,),
        temporal_solver="lbfgs",
        temporal_max_iter=100,
    )
    assert set(run.comparison.summary["model"]) == {"I-VT", "RandomForest", "ContextMLP"}
    assert set(run.stimulus_type_performance.summary["stratum"]) == {"image"}
    assert set(run.stimulus_type_performance.summary["model"]) == {
        "I-VT",
        "RandomForest",
        "ContextMLP",
    }
    pairs = set(
        run.paired_model_differences.summary[["model_a", "model_b"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )
    assert pairs == {
        ("I-VT", "RandomForest"),
        ("I-VT", "ContextMLP"),
        ("RandomForest", "ContextMLP"),
    }
    assert run.report["benchmark"]["name"] == "Lund2013"
    assert len(run.report["report_fingerprint_sha256"]) == 64
    preparation = run.report["protocol"]["preparation"]
    source_manifest = preparation["source_manifest"]
    assert source_manifest["manifest_fingerprint_sha256"] == source_fingerprint
    assert source_manifest["commit"] == lund_fetch.LUND2013_COMMIT
    assert source_manifest["files_verified_at_run"] is True
    design = run.report["protocol"]["comparison_design"]
    assert design["group_col"] == "participant_id"
    assert design["ivt_velocity_unit"] == "deg/s"
    assert design["ivt_velocity_threshold_deg_s"] == 45.0
    assert design["ivt_velocity_threshold_px_s"] is None
    paired_design = run.report["protocol"]["paired_model_difference_design"]
    assert paired_design["inferential_p_values"] is False
    assert paired_design["confidence_intervals"] is False
    assert paired_design["folds_treated_as_independent_replicates"] is False
    paired_rows = run.report["metrics"]["paired_model_difference_summary"]
    assert {row["metric"] for row in paired_rows} >= {"accuracy", "macro_f1", "event_f1"}
    stimulus_design = run.report["protocol"]["stimulus_type_design"]
    assert stimulus_design["stratify_col"] == "stimulus_type"
    assert stimulus_design["models_refit_by_stratum"] is False
    family_rows = run.report["metrics"]["stimulus_type_summary"]
    assert {row["stratum"] for row in family_rows} == {"image"}
    assert {row["model"] for row in family_rows} == {
        "I-VT",
        "RandomForest",
        "ContextMLP",
    }
