from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.lund_fetch as lund
import gazeforge.native_event as native
import gazeforge.native_suite as suite
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError

# ============================================================
# NATIVE EVENT
# ============================================================


def _native_spec(**changes):
    values = {
        "name": "fixture",
        "version": "1",
        "source": "fixture-source",
        "license": "test-only",
        "tracker_model": "fixture-tracker",
        "expected_sampling_rate_hz": 60.0,
    }
    values.update(changes)
    return native.NativeEventBenchmarkSpec(**values)


def _native_frame(
    *,
    participants=2,
    samples=8,
    labels=("fixation", "saccade"),
):
    rows = []
    step = 1000.0 / 60.0

    for p in range(participants):
        for i in range(samples):
            rows.append(
                {
                    "participant_id": f"P{p + 1}",
                    "trial_id": "T1",
                    "timestamp_ms": i * step,
                    "x_px": 100.0 + i,
                    "y_px": 200.0 + i,
                    "event_label": labels[i % len(labels)],
                }
            )

    return pd.DataFrame(rows)


@pytest.mark.parametrize(
    "field",
    ["name", "version", "source", "license", "tracker_model"],
)
def test_native_spec_empty_required_text(field):
    with pytest.raises(ValueError):
        _native_spec(**{field: ""})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"dataset_status": "other"},
        {"annotation_origin": "machine"},
        {"human_annotator_count": 0},
        {"expected_sampling_rate_hz": 0.0},
        {"expected_sampling_rate_hz": np.nan},
        {"sampling_rate_tolerance_fraction": -0.1},
        {"sampling_rate_tolerance_fraction": 1.0},
        {"sampling_rate_tolerance_fraction": np.nan},
    ],
)
def test_native_spec_invalid_contracts(kwargs):
    with pytest.raises(ValueError):
        _native_spec(**kwargs)


def test_native_spec_default_mapping_and_normalization():
    spec = _native_spec(
        analysis_excluded_labels=(" undefined ", " bad "),
        notes=[1, "two"],
    )

    assert spec.column_map == {key: key for key in native._REQUIRED_COLUMN_KEYS}
    assert spec.analysis_excluded_labels == (
        "undefined",
        "bad",
    )
    assert spec.notes == ["1", "two"]


def test_native_spec_from_dict_normalizes_containers():
    payload = _native_spec().to_dict()

    payload["analysis_excluded_labels"] = [
        "undefined",
    ]
    payload["notes"] = ["fixture"]
    payload["column_map"] = dict(payload["column_map"])

    spec = native.NativeEventBenchmarkSpec.from_dict(payload)

    assert spec.analysis_excluded_labels == ("undefined",)
    assert spec.notes == ["fixture"]


def test_native_spec_missing_mapping_key():
    mapping = {key: key for key in native._REQUIRED_COLUMN_KEYS if key != "event_label"}

    with pytest.raises(ValueError, match="missing required"):
        _native_spec(column_map=mapping)


def test_native_spec_duplicate_mapping_source():
    mapping = {key: "same" for key in native._REQUIRED_COLUMN_KEYS}

    with pytest.raises(ValueError, match="unique"):
        _native_spec(column_map=mapping)


def test_native_json_safe_records():
    frame = pd.DataFrame(
        {
            "x": [1.0, np.nan],
            "y": ["a", None],
        }
    )

    records = native._json_safe_records(frame)

    assert records[1]["x"] is None
    assert records[1]["y"] is None


def test_native_file_sha256(tmp_path):
    path = tmp_path / "fixture.bin"
    path.write_bytes(b"abc")

    assert native.file_sha256(path) == hashlib.sha256(b"abc").hexdigest()


def test_native_load_spec_valid(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text(
        json.dumps(_native_spec().to_dict()),
        encoding="utf-8",
    )

    loaded = native.load_native_event_spec(path)

    assert loaded.name == "fixture"


def test_native_load_spec_nonobject(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="one JSON object"):
        native.load_native_event_spec(path)


@pytest.mark.parametrize(
    ("suffix", "sep"),
    [
        (".csv", ","),
        (".tsv", "\t"),
        (".tab", "\t"),
    ],
)
def test_native_load_table_formats(tmp_path, suffix, sep):
    path = tmp_path / f"data{suffix}"

    _native_frame().to_csv(
        path,
        sep=sep,
        index=False,
    )

    loaded = native.load_native_event_table(path)

    assert len(loaded) == len(_native_frame())


def test_native_load_table_invalid_suffix(tmp_path):
    path = tmp_path / "data.txt"
    path.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="CSV or TSV"):
        native.load_native_event_table(path)


def test_native_standardize_wrong_type():
    with pytest.raises(SchemaError, match="pandas"):
        native._standardize_columns(
            [],
            _native_spec(),
        )


def test_native_standardize_missing_sources():
    with pytest.raises(SchemaError, match="source columns"):
        native._standardize_columns(
            pd.DataFrame({"x": [1]}),
            _native_spec(),
        )


def test_native_standardize_custom_mapping():
    spec = _native_spec(
        column_map={
            "participant_id": "p",
            "trial_id": "t",
            "timestamp_ms": "time",
            "x_px": "x",
            "y_px": "y",
            "event_label": "label",
        }
    )

    data = pd.DataFrame(
        {
            "p": ["P1"],
            "t": ["T1"],
            "time": [0.0],
            "x": [1.0],
            "y": [2.0],
            "label": ["fixation"],
        }
    )

    result = native._standardize_columns(data, spec)

    assert set(native._REQUIRED_COLUMN_KEYS).issubset(result.columns)


def test_native_standardize_mapping_collision():
    spec = _native_spec(
        column_map={
            "participant_id": "p",
            "trial_id": "t",
            "timestamp_ms": "time",
            "x_px": "x",
            "y_px": "y",
            "event_label": "label",
        }
    )

    data = pd.DataFrame(
        {
            "p": ["P1"],
            "t": ["T1"],
            "time": [0.0],
            "x": [1.0],
            "y": [2.0],
            "label": ["fixation"],
            "participant_id": ["collision"],
        }
    )

    with pytest.raises(SchemaError, match="duplicate canonical"):
        native._standardize_columns(data, spec)


def test_native_select_no_annotator_column():
    data = _native_frame()

    selected, annotator = native._select_annotator(
        data,
        annotator=None,
    )

    assert annotator is None
    assert selected.equals(data)


def test_native_select_requested_without_column():
    with pytest.raises(SchemaError, match="requested"):
        native._select_annotator(
            _native_frame(),
            annotator="A",
        )


def test_native_select_missing_annotator():
    data = _native_frame()
    data["annotator_id"] = "A"
    data.loc[0, "annotator_id"] = None

    with pytest.raises(SchemaError, match="missing"):
        native._select_annotator(
            data,
            annotator=None,
        )


def test_native_select_empty_annotator():
    data = _native_frame()
    data["annotator_id"] = "A"
    data.loc[0, "annotator_id"] = " "

    with pytest.raises(SchemaError, match="empty"):
        native._select_annotator(
            data,
            annotator=None,
        )


def test_native_select_multiple_requires_explicit():
    data = _native_frame()

    data["annotator_id"] = [
        "A",
        "B",
    ] * (len(data) // 2)

    with pytest.raises(SchemaError, match="Multiple annotation"):
        native._select_annotator(
            data,
            annotator=None,
        )


def test_native_select_unknown():
    data = _native_frame()
    data["annotator_id"] = "A"

    with pytest.raises(SchemaError, match="Unknown annotator"):
        native._select_annotator(
            data,
            annotator="B",
        )


def test_native_select_explicit_success():
    data = _native_frame()

    data["annotator_id"] = [
        "A",
        "B",
    ] * (len(data) // 2)

    selected, annotator = native._select_annotator(
        data,
        annotator="A",
    )

    assert annotator == "A"
    assert selected["annotator_id"].eq("A").all()


def test_native_group_sampling_too_few():
    data = pd.DataFrame(
        {
            "participant_id": ["P1"],
            "trial_id": ["T1"],
            "timestamp_ms": [0.0],
        }
    )

    with pytest.raises(SchemaError, match="at least two"):
        native._group_sampling_rates(data)


def test_native_group_sampling_no_positive_delta():
    data = pd.DataFrame(
        {
            "participant_id": ["P1", "P1"],
            "trial_id": ["T1", "T1"],
            "timestamp_ms": [1.0, 1.0],
        }
    )

    with pytest.raises(SchemaError, match="no positive"):
        native._group_sampling_rates(data)


def test_native_group_sampling_success():
    result = native._group_sampling_rates(_native_frame())

    assert len(result) == 2
    assert np.allclose(
        result["sampling_rate_hz"],
        60.0,
    )


def test_native_prepare_template_rejected():
    with pytest.raises(SchemaError, match="Template"):
        native.prepare_native_event_benchmark(
            _native_frame(),
            _native_spec(dataset_status="template"),
        )


def test_native_prepare_missing_ids():
    data = _native_frame()
    data.loc[0, "participant_id"] = None

    with pytest.raises(SchemaError, match="participant_id"):
        native.prepare_native_event_benchmark(
            data,
            _native_spec(),
        )


def test_native_prepare_missing_label():
    data = _native_frame()
    data.loc[0, "event_label"] = None

    with pytest.raises(SchemaError, match="missing"):
        native.prepare_native_event_benchmark(
            data,
            _native_spec(),
        )


def test_native_prepare_empty_label():
    data = _native_frame()
    data.loc[0, "event_label"] = " "

    with pytest.raises(SchemaError, match="empty"):
        native.prepare_native_event_benchmark(
            data,
            _native_spec(),
        )


def test_native_prepare_duplicate_key():
    data = _native_frame()

    data = pd.concat(
        [data, data.iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(SchemaError, match="duplicate"):
        native.prepare_native_event_benchmark(
            data,
            _native_spec(),
        )


def test_native_prepare_rate_mismatch():
    with pytest.raises(SchemaError, match="sampling-rate verification"):
        native.prepare_native_event_benchmark(
            _native_frame(),
            _native_spec(
                expected_sampling_rate_hz=120.0,
                sampling_rate_tolerance_fraction=0.01,
            ),
        )


def test_native_prepare_all_excluded():
    with pytest.raises(SchemaError, match="removed every"):
        native.prepare_native_event_benchmark(
            _native_frame(labels=("undefined",)),
            _native_spec(),
        )


def test_native_prepare_one_class():
    with pytest.raises(SchemaError, match="at least two retained"):
        native.prepare_native_event_benchmark(
            _native_frame(labels=("fixation",)),
            _native_spec(
                analysis_excluded_labels=(),
            ),
        )


def test_native_prepare_one_participant():
    with pytest.raises(SchemaError, match="at least two participants"):
        native.prepare_native_event_benchmark(
            _native_frame(
                participants=1,
            ),
            _native_spec(),
        )


@pytest.mark.parametrize(
    ("origin", "strength"),
    [
        ("expert-manual", "expert-human-reference"),
        ("human-manual", "human-reference"),
    ],
)
def test_native_prepare_success_reference_strength(
    origin,
    strength,
):
    prepared = native.prepare_native_event_benchmark(
        _native_frame(),
        _native_spec(
            annotation_origin=origin,
        ),
        source_file_name="native.csv",
        source_file_sha256="a" * 64,
    )

    assert prepared.dataset_card.reference_strength == strength
    assert prepared.preparation_report["native_rate_verified"] is True
    assert prepared.preparation_report["source_file_name"] == "native.csv"


def test_native_run_threshold_guard():
    data = _native_frame()
    spec = _native_spec()

    with pytest.raises(ValueError, match="exactly one"):
        native.run_native_event_benchmark(
            data,
            spec,
        )

    with pytest.raises(ValueError, match="exactly one"):
        native.run_native_event_benchmark(
            data,
            spec,
            ivt_velocity_threshold_deg_s=30.0,
            ivt_velocity_threshold_px_s=700.0,
        )


def test_native_run_angular_geometry_guard():
    with pytest.raises(SchemaError, match="geometry"):
        native.run_native_event_benchmark(
            _native_frame(),
            _native_spec(),
            ivt_velocity_threshold_deg_s=30.0,
        )


def test_native_run_fold_guard():
    with pytest.raises(SchemaError, match="two participant folds"):
        native.run_native_event_benchmark(
            _native_frame(),
            _native_spec(),
            n_splits=1,
            ivt_velocity_threshold_px_s=700.0,
        )


def test_native_run_success_without_real_models(monkeypatch):
    data = _native_frame()
    spec = _native_spec()

    comparison = SimpleNamespace(
        summary=pd.DataFrame([{"model": "fixture", "accuracy": 0.8}]),
        fold_metrics=pd.DataFrame(
            [
                {
                    "fold": 0,
                    "model": "fixture",
                    "accuracy": 0.8,
                }
            ]
        ),
        design={
            "models": ["fixture"],
            "fixture": True,
        },
    )

    paired = SimpleNamespace(
        summary=pd.DataFrame([{"metric": "accuracy", "mean_difference": 0.0}]),
        deltas=pd.DataFrame([{"fold": 0, "metric": "accuracy", "difference": 0.0}]),
        design={"fixture": True},
    )

    monkeypatch.setattr(
        native,
        "compare_event_models_grouped",
        lambda *args, **kwargs: comparison,
    )

    monkeypatch.setattr(
        native,
        "paired_model_metric_differences",
        lambda *args, **kwargs: paired,
    )

    run = native.run_native_event_benchmark(
        data,
        spec,
        n_splits=2,
        ivt_velocity_threshold_px_s=700.0,
        n_estimators=2,
    )

    assert run.prepared.preparation_report["native_rate_verified"] is True

    assert run.report["protocol"]["native_intake"]["native_rate_verified"] is True


def test_native_file_benchmark_wrapper(monkeypatch, tmp_path):
    data_path = tmp_path / "native.csv"
    spec_path = tmp_path / "spec.json"

    _native_frame().to_csv(
        data_path,
        index=False,
    )

    spec_path.write_text(
        json.dumps(_native_spec().to_dict()),
        encoding="utf-8",
    )

    captured = {}

    def fake_run(data, spec, **kwargs):
        captured["rows"] = len(data)
        captured["name"] = spec.name
        captured.update(kwargs)
        return "sentinel"

    monkeypatch.setattr(
        native,
        "run_native_event_benchmark",
        fake_run,
    )

    result = native.run_native_event_file_benchmark(
        data_path,
        spec_path,
        ivt_velocity_threshold_px_s=700.0,
    )

    assert result == "sentinel"
    assert captured["rows"] == len(_native_frame())
    assert captured["source_file_name"] == "native.csv"
    assert len(captured["source_file_sha256"]) == 64


# ============================================================
# LUND FETCH
# ============================================================


def _entry(name, payload=b"payload", **changes):
    result = {
        "name": name,
        "type": "file",
        "sha": lund._git_blob_sha1(payload),
        "size": len(payload),
        "download_url": ("https://raw.githubusercontent.com/example/repo/pinned/" + name),
    }
    result.update(changes)
    return result


def _write_manifest(root, body):
    fingerprint = lund._manifest_fingerprint(body)

    payload = {
        **body,
        "manifest_fingerprint_sha256": fingerprint,
    }

    path = root / lund._MANIFEST_NAME

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return path, payload


@pytest.mark.parametrize(
    ("annotators", "families"),
    [
        (("BAD",), ("dots",)),
        (("RA",), ("bad",)),
        ((), ("dots",)),
        (("RA",), ()),
    ],
)
def test_lund_validate_selection_failures(
    annotators,
    families,
):
    with pytest.raises(ValueError):
        lund._validate_selection(
            annotators,
            families,
        )


def test_lund_validate_selection_success():
    lund._validate_selection(
        ("RA", "MN"),
        ("dots", "img"),
    )


def test_lund_git_blob_sha_is_deterministic():
    assert lund._git_blob_sha1(b"abc") == lund._git_blob_sha1(b"abc")


def test_lund_manifest_fingerprint_order_independent():
    assert lund._manifest_fingerprint({"b": 2, "a": 1}) == lund._manifest_fingerprint(
        {"a": 1, "b": 2}
    )


def test_lund_family_entries_reject_nonlist(monkeypatch):
    monkeypatch.setattr(
        lund,
        "_request_json",
        lambda url: {"bad": True},
    )

    with pytest.raises(BenchmarkIntegrityError, match="Unexpected GitHub"):
        lund._family_entries("dots")


def test_lund_family_entries_filters_nonmapping(monkeypatch):
    monkeypatch.setattr(
        lund,
        "_request_json",
        lambda url: [
            {"name": "a"},
            "bad",
            1,
        ],
    )

    assert lund._family_entries("dots") == [{"name": "a"}]


def test_lund_selected_entries_filters_noise(monkeypatch):
    ra = _entry(
        "P01_labelled_RA.mat",
        b"ra",
    )

    entries = [
        {"name": "directory", "type": "dir"},
        {
            "name": "readme.txt",
            "type": "file",
        },
        _entry(
            "P01_labelled_MN.mat",
            b"mn",
        ),
        ra,
    ]

    monkeypatch.setattr(
        lund,
        "_family_entries",
        lambda family: entries,
    )

    selected = lund._selected_entries(
        annotators=("RA",),
        stimulus_families=("dots",),
    )

    assert selected == [("dots", ra)]


def test_lund_selected_entries_none(monkeypatch):
    monkeypatch.setattr(
        lund,
        "_family_entries",
        lambda family: [],
    )

    with pytest.raises(BenchmarkIntegrityError, match="No labelled"):
        lund._selected_entries(
            annotators=("RA",),
            stimulus_families=("dots",),
        )


def test_lund_verified_payload_missing_url():
    entry = {
        "name": "x.mat",
        "sha": "a",
        "size": 1,
        "download_url": None,
    }

    with pytest.raises(BenchmarkIntegrityError, match="download_url"):
        lund._verified_payload(entry)


def test_lund_verified_payload_sha_mismatch():
    entry = _entry(
        "x.mat",
        b"expected",
    )

    with pytest.raises(BenchmarkIntegrityError, match="SHA mismatch"):
        lund._verified_payload(
            entry,
            existing=b"wrong",
        )


def test_lund_verified_payload_size_mismatch():
    payload = b"expected"

    entry = _entry(
        "x.mat",
        payload,
        size=len(payload) + 1,
    )

    with pytest.raises(BenchmarkIntegrityError, match="byte-size"):
        lund._verified_payload(
            entry,
            existing=payload,
        )


def test_lund_verified_payload_download(monkeypatch):
    payload = b"expected"
    entry = _entry("x.mat", payload)

    monkeypatch.setattr(
        lund,
        "_request_bytes",
        lambda url: payload,
    )

    assert lund._verified_payload(entry) == payload


def test_lund_manifest_summary():
    manifest = {
        "repository": "r",
        "commit": "c",
        "data_path": "d",
        "annotators": ["RA"],
        "stimulus_families": ["dots"],
        "file_count": 1,
        "manifest_fingerprint_sha256": "a" * 64,
    }

    summary = lund._manifest_summary(manifest)

    assert summary["files_verified_at_run"] is True


def test_lund_manifest_optional(tmp_path):
    assert lund.validate_lund2013_source_manifest(tmp_path) is None


def test_lund_manifest_invalid_json(tmp_path):
    path = tmp_path / lund._MANIFEST_NAME
    path.write_text("{", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="valid JSON"):
        lund.validate_lund2013_source_manifest(tmp_path)


def test_lund_manifest_nonobject(tmp_path):
    path = tmp_path / lund._MANIFEST_NAME
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="JSON object"):
        lund.validate_lund2013_source_manifest(tmp_path)


def test_lund_manifest_missing_fields(tmp_path):
    body = {
        "dataset": "Lund2013",
    }

    path = tmp_path / lund._MANIFEST_NAME
    path.write_text(
        json.dumps(body),
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="missing fields"):
        lund.validate_lund2013_source_manifest(tmp_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("dataset", "Other", "dataset"),
        ("repository", "Other", "repository"),
        ("commit", "0" * 40, "commit"),
        ("data_path", "Other", "data path"),
    ],
)
def test_lund_manifest_identity_guards(
    tmp_path,
    field,
    value,
    message,
):
    body = {
        "dataset": "Lund2013",
        "repository": lund.LUND2013_REPOSITORY,
        "commit": lund.LUND2013_COMMIT,
        "data_path": lund.LUND2013_DATA_PATH,
        "file_count": 0,
        "files": [],
    }

    body[field] = value
    _write_manifest(tmp_path, body)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        lund.validate_lund2013_source_manifest(tmp_path)


def test_lund_manifest_files_not_list(tmp_path):
    body = {
        "dataset": "Lund2013",
        "repository": lund.LUND2013_REPOSITORY,
        "commit": lund.LUND2013_COMMIT,
        "data_path": lund.LUND2013_DATA_PATH,
        "file_count": 0,
        "files": {},
    }

    _write_manifest(tmp_path, body)

    with pytest.raises(BenchmarkIntegrityError, match="files must be a list"):
        lund.validate_lund2013_source_manifest(tmp_path)


def test_lund_manifest_count_mismatch(tmp_path):
    body = {
        "dataset": "Lund2013",
        "repository": lund.LUND2013_REPOSITORY,
        "commit": lund.LUND2013_COMMIT,
        "data_path": lund.LUND2013_DATA_PATH,
        "file_count": 1,
        "files": [],
    }

    _write_manifest(tmp_path, body)

    with pytest.raises(BenchmarkIntegrityError, match="file_count"):
        lund.validate_lund2013_source_manifest(tmp_path)


def test_lund_manifest_invalid_row(tmp_path):
    body = {
        "dataset": "Lund2013",
        "repository": lund.LUND2013_REPOSITORY,
        "commit": lund.LUND2013_COMMIT,
        "data_path": lund.LUND2013_DATA_PATH,
        "file_count": 1,
        "files": ["bad"],
    }

    _write_manifest(tmp_path, body)

    with pytest.raises(BenchmarkIntegrityError, match="invalid file row"):
        lund.validate_lund2013_source_manifest(tmp_path)


@pytest.mark.parametrize(
    "relative",
    [
        "",
        "../escape.mat",
        "/absolute.mat",
    ],
)
def test_lund_manifest_unsafe_path(tmp_path, relative):
    body = {
        "dataset": "Lund2013",
        "repository": lund.LUND2013_REPOSITORY,
        "commit": lund.LUND2013_COMMIT,
        "data_path": lund.LUND2013_DATA_PATH,
        "file_count": 1,
        "files": [
            {
                "relative_path": relative,
                "size_bytes": 1,
                "git_blob_sha1": "a",
            }
        ],
    }

    _write_manifest(tmp_path, body)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="unsafe path|escapes the checkout",
    ):
        lund.validate_lund2013_source_manifest(tmp_path)


def test_lund_manifest_missing_local_file(tmp_path):
    body = {
        "dataset": "Lund2013",
        "repository": lund.LUND2013_REPOSITORY,
        "commit": lund.LUND2013_COMMIT,
        "data_path": lund.LUND2013_DATA_PATH,
        "file_count": 1,
        "files": [
            {
                "relative_path": "dots/a.mat",
                "size_bytes": 1,
                "git_blob_sha1": "a",
            }
        ],
    }

    _write_manifest(tmp_path, body)

    with pytest.raises(BenchmarkIntegrityError, match="missing"):
        lund.validate_lund2013_source_manifest(tmp_path)


def test_lund_manifest_size_mismatch(tmp_path):
    target = tmp_path / "dots" / "a.mat"
    target.parent.mkdir()
    target.write_bytes(b"abc")

    body = {
        "dataset": "Lund2013",
        "repository": lund.LUND2013_REPOSITORY,
        "commit": lund.LUND2013_COMMIT,
        "data_path": lund.LUND2013_DATA_PATH,
        "file_count": 1,
        "files": [
            {
                "relative_path": "dots/a.mat",
                "size_bytes": 999,
                "git_blob_sha1": lund._git_blob_sha1(b"abc"),
            }
        ],
    }

    _write_manifest(tmp_path, body)

    with pytest.raises(BenchmarkIntegrityError, match="byte-size"):
        lund.validate_lund2013_source_manifest(tmp_path)


def test_lund_manifest_sha_mismatch(tmp_path):
    target = tmp_path / "dots" / "a.mat"
    target.parent.mkdir()
    target.write_bytes(b"abc")

    body = {
        "dataset": "Lund2013",
        "repository": lund.LUND2013_REPOSITORY,
        "commit": lund.LUND2013_COMMIT,
        "data_path": lund.LUND2013_DATA_PATH,
        "file_count": 1,
        "files": [
            {
                "relative_path": "dots/a.mat",
                "size_bytes": 3,
                "git_blob_sha1": "0" * 40,
            }
        ],
    }

    _write_manifest(tmp_path, body)

    with pytest.raises(BenchmarkIntegrityError, match="Git blob SHA"):
        lund.validate_lund2013_source_manifest(tmp_path)


def test_lund_manifest_verify_files_false(tmp_path):
    body = {
        "dataset": "Lund2013",
        "repository": lund.LUND2013_REPOSITORY,
        "commit": lund.LUND2013_COMMIT,
        "data_path": lund.LUND2013_DATA_PATH,
        "annotators": ["RA"],
        "stimulus_families": ["dots"],
        "file_count": 1,
        "files": [
            {
                "relative_path": "missing.mat",
                "size_bytes": 10,
                "git_blob_sha1": "0" * 40,
            }
        ],
    }

    _, manifest = _write_manifest(
        tmp_path,
        body,
    )

    result = lund.validate_lund2013_source_manifest(
        tmp_path,
        verify_files=False,
    )

    assert result["file_count"] == 1
    assert result["manifest_fingerprint_sha256"] == manifest["manifest_fingerprint_sha256"]


def test_lund_fetch_normalizes_selection(monkeypatch, tmp_path):
    payload = b"fixture"

    entry = _entry(
        "P01_labelled_RA.mat",
        payload,
    )

    captured = {}

    def selected(*, annotators, stimulus_families):
        captured["annotators"] = annotators
        captured["stimulus_families"] = stimulus_families
        return [("dots", entry)]

    monkeypatch.setattr(
        lund,
        "_selected_entries",
        selected,
    )

    monkeypatch.setattr(
        lund,
        "_request_bytes",
        lambda url: payload,
    )

    result = lund.fetch_lund2013_dataset(
        tmp_path,
        annotators=("ra", "RA"),
        stimulus_families=("DOTS", "dots"),
    )

    assert captured["annotators"] == ("RA",)
    assert captured["stimulus_families"] == ("dots",)
    assert len(result.files) == 1


# ============================================================
# NATIVE SUITE
# ============================================================


def _child_report(
    *,
    kind,
    source_name="native.csv",
    source_sha="a" * 64,
    spec_fp="b" * 64,
    marker="x",
):
    if kind == "agreement":
        protocol = {
            "source_file_name": source_name,
            "source_file_sha256": source_sha,
            "spec_fingerprint_sha256": spec_fp,
        }
    else:
        protocol = {
            "native_intake": {
                "source_file_name": source_name,
                "source_file_sha256": source_sha,
                "spec_fingerprint_sha256": spec_fp,
            }
        }

    body = {
        "benchmark": {"name": marker},
        "model": {"name": marker},
        "protocol": protocol,
        "metrics": {"marker": marker},
    }

    return {
        **body,
        "report_fingerprint_sha256": benchmark_fingerprint(body),
    }


def _valid_suite_manifest():
    reports = {
        "human_agreement": _child_report(
            kind="agreement",
            marker="agreement",
        ),
        "primary_annotator_model": _child_report(
            kind="model",
            marker="primary",
        ),
        "annotator_sensitivity_model": _child_report(
            kind="model",
            marker="sensitivity",
        ),
    }

    records = [
        {
            "name": name,
            "path": f"{name}.json",
            "report_fingerprint_sha256": report["report_fingerprint_sha256"],
        }
        for name, report in reports.items()
    ]

    body = {
        "suite": suite._SUITE_NAME,
        "status": "complete",
        "source": {
            "data_file_name": "native.csv",
            "data_file_sha256": "a" * 64,
            "spec_file_name": "spec.json",
            "spec_fingerprint_sha256": "b" * 64,
        },
        "protocol": {"fixture": True},
        "reports": records,
    }

    manifest = {
        **body,
        "suite_fingerprint_sha256": benchmark_fingerprint(body),
    }

    return reports, manifest


def _write_suite(tmp_path, *, write_children=True):
    reports, manifest = _valid_suite_manifest()

    root = tmp_path / "suite"
    root.mkdir()

    if write_children:
        for record in manifest["reports"]:
            report = reports[record["name"]]

            (root / record["path"]).write_text(
                json.dumps(
                    report,
                    indent=2,
                ),
                encoding="utf-8",
            )

    manifest_path = root / suite._SUITE_MANIFEST_NAME

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    return root, reports, manifest


def test_suite_target_paths(tmp_path):
    paths = suite._target_paths(tmp_path)

    assert set(paths) == suite._SUITE_REPORT_NAMES


def test_suite_preflight_overwrite_ignores_existing(tmp_path):
    paths = suite._target_paths(tmp_path)
    manifest = tmp_path / suite._SUITE_MANIFEST_NAME

    tmp_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    next(iter(paths.values())).write_text(
        "{}",
        encoding="utf-8",
    )

    suite._preflight_targets(
        paths,
        manifest,
        overwrite=True,
    )


def test_suite_preflight_existing_rejected(tmp_path):
    paths = suite._target_paths(tmp_path)
    manifest = tmp_path / suite._SUITE_MANIFEST_NAME

    tmp_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    next(iter(paths.values())).write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError, match="already exists"):
        suite._preflight_targets(
            paths,
            manifest,
            overwrite=False,
        )


def test_suite_child_missing_fingerprint():
    with pytest.raises(BenchmarkIntegrityError, match="missing"):
        suite._validate_child_report(
            "x",
            {},
        )


def test_suite_child_fingerprint_mismatch():
    report = _child_report(
        kind="agreement",
    )

    report["metrics"]["marker"] = "changed"

    with pytest.raises(BenchmarkIntegrityError, match="mismatch"):
        suite._validate_child_report(
            "x",
            report,
        )


def test_suite_child_identity_protocol_type():
    with pytest.raises(BenchmarkIntegrityError, match="protocol"):
        suite._child_identity(
            {"protocol": None},
            kind="agreement",
        )


def test_suite_child_identity_agreement():
    report = _child_report(
        kind="agreement",
    )

    identity = suite._child_identity(
        report,
        kind="agreement",
    )

    assert identity["source_file_name"] == "native.csv"


def test_suite_child_identity_missing_native_intake():
    report = _child_report(
        kind="model",
    )

    report["protocol"] = {}

    with pytest.raises(BenchmarkIntegrityError, match="native_intake"):
        suite._child_identity(
            report,
            kind="model",
        )


def test_suite_shared_identity_mismatch():
    reports = {
        "human_agreement": _child_report(
            kind="agreement",
            source_name="wrong.csv",
        ),
        "primary_annotator_model": _child_report(
            kind="model",
        ),
        "annotator_sensitivity_model": _child_report(
            kind="model",
        ),
    }

    with pytest.raises(BenchmarkIntegrityError, match="does not share"):
        suite._assert_shared_identity(
            reports,
            expected_source_file_name="native.csv",
            expected_source_file_sha256="a" * 64,
            expected_spec_fingerprint_sha256="b" * 64,
        )


def test_suite_manifest_path_directory_and_file(tmp_path):
    root = tmp_path / "suite"
    root.mkdir()

    expected = root / suite._SUITE_MANIFEST_NAME

    assert suite._manifest_path(root) == expected
    assert suite._manifest_path(expected) == expected


@pytest.mark.parametrize(
    "relative",
    [
        "",
        "../escape.json",
        "/absolute.json",
    ],
)
def test_suite_safe_child_path_invalid(tmp_path, relative):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="unsafe|escapes the suite directory",
    ):
        suite._safe_child_path(
            tmp_path,
            relative,
        )


def test_suite_safe_child_path_valid(tmp_path):
    path = suite._safe_child_path(
        tmp_path,
        "child.json",
    )

    assert path == (tmp_path / "child.json").resolve()


def test_suite_manifest_source_wrong_type():
    with pytest.raises(BenchmarkIntegrityError, match="object"):
        suite._validate_manifest_source(None)


@pytest.mark.parametrize(
    "field",
    [
        "data_file_name",
        "data_file_sha256",
        "spec_file_name",
        "spec_fingerprint_sha256",
    ],
)
def test_suite_manifest_source_missing_field(field):
    source = {
        "data_file_name": "native.csv",
        "data_file_sha256": "a" * 64,
        "spec_file_name": "spec.json",
        "spec_fingerprint_sha256": "b" * 64,
    }

    source[field] = ""

    with pytest.raises(BenchmarkIntegrityError, match=field):
        suite._validate_manifest_source(source)


def test_suite_validate_missing_manifest(tmp_path):
    with pytest.raises(FileNotFoundError):
        suite.validate_native_event_suite_manifest(tmp_path)


def test_suite_validate_invalid_json(tmp_path):
    path = tmp_path / suite._SUITE_MANIFEST_NAME
    path.write_text("{", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="valid JSON"):
        suite.validate_native_event_suite_manifest(path)


def test_suite_validate_nonobject(tmp_path):
    path = tmp_path / suite._SUITE_MANIFEST_NAME
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="JSON object"):
        suite.validate_native_event_suite_manifest(path)


def test_suite_validate_missing_required(tmp_path):
    path = tmp_path / suite._SUITE_MANIFEST_NAME
    path.write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="missing required"):
        suite.validate_native_event_suite_manifest(path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("suite", "bad"),
        ("status", "pending"),
    ],
)
def test_suite_validate_identity_status(
    tmp_path,
    field,
    value,
):
    _, manifest = _valid_suite_manifest()

    manifest[field] = value

    body = {key: val for key, val in manifest.items() if key != "suite_fingerprint_sha256"}

    manifest["suite_fingerprint_sha256"] = benchmark_fingerprint(body)

    path = tmp_path / suite._SUITE_MANIFEST_NAME
    path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError):
        suite.validate_native_event_suite_manifest(
            path,
            verify_reports=False,
        )


def test_suite_validate_missing_fingerprint(tmp_path):
    _, manifest = _valid_suite_manifest()
    manifest["suite_fingerprint_sha256"] = ""

    path = tmp_path / suite._SUITE_MANIFEST_NAME
    path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="fingerprint is missing"):
        suite.validate_native_event_suite_manifest(
            path,
            verify_reports=False,
        )


def test_suite_validate_fingerprint_mismatch(tmp_path):
    _, manifest = _valid_suite_manifest()
    manifest["protocol"]["changed"] = True

    path = tmp_path / suite._SUITE_MANIFEST_NAME
    path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="fingerprint mismatch"):
        suite.validate_native_event_suite_manifest(
            path,
            verify_reports=False,
        )


def test_suite_validate_protocol_type(tmp_path):
    _, manifest = _valid_suite_manifest()
    manifest["protocol"] = []

    body = {key: val for key, val in manifest.items() if key != "suite_fingerprint_sha256"}

    manifest["suite_fingerprint_sha256"] = benchmark_fingerprint(body)

    path = tmp_path / suite._SUITE_MANIFEST_NAME
    path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="protocol"):
        suite.validate_native_event_suite_manifest(
            path,
            verify_reports=False,
        )


def test_suite_validate_reports_type(tmp_path):
    _, manifest = _valid_suite_manifest()
    manifest["reports"] = {}

    body = {key: val for key, val in manifest.items() if key != "suite_fingerprint_sha256"}

    manifest["suite_fingerprint_sha256"] = benchmark_fingerprint(body)

    path = tmp_path / suite._SUITE_MANIFEST_NAME
    path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="reports must be a list"):
        suite.validate_native_event_suite_manifest(
            path,
            verify_reports=False,
        )


def test_suite_validate_invalid_report_row(tmp_path):
    _, manifest = _valid_suite_manifest()

    manifest["reports"] = ["bad"]

    body = {key: val for key, val in manifest.items() if key != "suite_fingerprint_sha256"}

    manifest["suite_fingerprint_sha256"] = benchmark_fingerprint(body)

    path = tmp_path / suite._SUITE_MANIFEST_NAME
    path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="invalid report row"):
        suite.validate_native_event_suite_manifest(
            path,
            verify_reports=False,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_name",
        "empty_name",
        "duplicate_path",
        "empty_path",
        "missing_fingerprint",
    ],
)
def test_suite_validate_report_row_contracts(
    tmp_path,
    mutation,
):
    _, manifest = _valid_suite_manifest()

    if mutation == "duplicate_name":
        manifest["reports"][1]["name"] = manifest["reports"][0]["name"]
    elif mutation == "empty_name":
        manifest["reports"][0]["name"] = ""
    elif mutation == "duplicate_path":
        manifest["reports"][1]["path"] = manifest["reports"][0]["path"]
    elif mutation == "empty_path":
        manifest["reports"][0]["path"] = ""
    else:
        manifest["reports"][0]["report_fingerprint_sha256"] = ""

    body = {key: val for key, val in manifest.items() if key != "suite_fingerprint_sha256"}

    manifest["suite_fingerprint_sha256"] = benchmark_fingerprint(body)

    path = tmp_path / suite._SUITE_MANIFEST_NAME
    path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError):
        suite.validate_native_event_suite_manifest(
            path,
            verify_reports=False,
        )


def test_suite_validate_inventory_mismatch(tmp_path):
    _, manifest = _valid_suite_manifest()

    manifest["reports"] = manifest["reports"][:-1]

    body = {key: val for key, val in manifest.items() if key != "suite_fingerprint_sha256"}

    manifest["suite_fingerprint_sha256"] = benchmark_fingerprint(body)

    path = tmp_path / suite._SUITE_MANIFEST_NAME
    path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="required tranche"):
        suite.validate_native_event_suite_manifest(
            path,
            verify_reports=False,
        )


def test_suite_validate_success_without_children(tmp_path):
    root, _, manifest = _write_suite(
        tmp_path,
        write_children=False,
    )

    result = suite.validate_native_event_suite_manifest(
        root,
        verify_reports=False,
    )

    assert result["report_count"] == 3
    assert result["reports_verified"] is False
    assert result["suite_fingerprint_sha256"] == manifest["suite_fingerprint_sha256"]


def test_suite_validate_missing_child(tmp_path):
    root, _, _ = _write_suite(
        tmp_path,
        write_children=False,
    )

    with pytest.raises(BenchmarkIntegrityError, match="child report is missing"):
        suite.validate_native_event_suite_manifest(
            root,
            verify_reports=True,
        )


def test_suite_validate_bad_child_json(tmp_path):
    root, _, manifest = _write_suite(
        tmp_path,
        write_children=False,
    )

    first = manifest["reports"][0]
    (root / first["path"]).write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="invalid JSON"):
        suite.validate_native_event_suite_manifest(
            root,
            verify_reports=True,
        )


def test_suite_validate_child_nonobject(tmp_path):
    root, _, manifest = _write_suite(
        tmp_path,
        write_children=False,
    )

    first = manifest["reports"][0]
    (root / first["path"]).write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="must be an object"):
        suite.validate_native_event_suite_manifest(
            root,
            verify_reports=True,
        )


def test_suite_validate_success_with_children(tmp_path):
    root, _, _ = _write_suite(
        tmp_path,
        write_children=True,
    )

    result = suite.validate_native_event_suite_manifest(
        root,
        verify_reports=True,
    )

    assert result["report_count"] == 3
    assert result["reports_verified"] is True


def test_suite_run_input_guards(tmp_path):
    with pytest.raises(ValueError, match="non-empty"):
        suite.run_native_event_validation_suite(
            "data.csv",
            "spec.json",
            tmp_path / "out",
            primary_annotator="",
            sensitivity_annotator="B",
            ivt_velocity_threshold_px_s=700.0,
        )

    with pytest.raises(ValueError, match="distinct"):
        suite.run_native_event_validation_suite(
            "data.csv",
            "spec.json",
            tmp_path / "out",
            primary_annotator="A",
            sensitivity_annotator="A",
            ivt_velocity_threshold_px_s=700.0,
        )

    with pytest.raises(ValueError, match="exactly one"):
        suite.run_native_event_validation_suite(
            "data.csv",
            "spec.json",
            tmp_path / "out",
            primary_annotator="A",
            sensitivity_annotator="B",
        )


def test_suite_run_success_without_models(monkeypatch, tmp_path):
    data_path = tmp_path / "native.csv"
    spec_path = tmp_path / "spec.json"
    output = tmp_path / "out"

    data_path.write_text(
        "participant_id\nP1\n",
        encoding="utf-8",
    )

    spec = _native_spec()

    spec_path.write_text(
        json.dumps(spec.to_dict()),
        encoding="utf-8",
    )

    source_sha = native.file_sha256(data_path)

    spec_fp = benchmark_fingerprint(spec.to_dict())

    agreement = _child_report(
        kind="agreement",
        source_name=data_path.name,
        source_sha=source_sha,
        spec_fp=spec_fp,
        marker="agreement",
    )

    primary = _child_report(
        kind="model",
        source_name=data_path.name,
        source_sha=source_sha,
        spec_fp=spec_fp,
        marker="primary",
    )

    sensitivity = _child_report(
        kind="model",
        source_name=data_path.name,
        source_sha=source_sha,
        spec_fp=spec_fp,
        marker="sensitivity",
    )

    monkeypatch.setattr(
        suite,
        "load_native_event_spec",
        lambda path: spec,
    )

    monkeypatch.setattr(
        suite,
        "load_native_event_table",
        lambda path: pd.DataFrame({"dummy": [1]}),
    )

    monkeypatch.setattr(
        suite,
        "run_native_event_annotator_agreement",
        lambda *args, **kwargs: SimpleNamespace(report=agreement),
    )

    def fake_model(
        data,
        model_spec,
        *,
        annotator,
        **kwargs,
    ):
        del data, model_spec, kwargs

        return SimpleNamespace(report=(primary if annotator == "A" else sensitivity))

    monkeypatch.setattr(
        suite,
        "run_native_event_benchmark",
        fake_model,
    )

    def fake_freeze(report, path, overwrite=False):
        del overwrite

        Path(path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        Path(path).write_text(
            json.dumps(
                report,
                indent=2,
            ),
            encoding="utf-8",
        )

        return Path(path)

    monkeypatch.setattr(
        suite,
        "freeze_benchmark_report",
        fake_freeze,
    )

    run = suite.run_native_event_validation_suite(
        data_path,
        spec_path,
        output,
        primary_annotator="A",
        sensitivity_annotator="B",
        n_splits=2,
        ivt_velocity_threshold_px_s=700.0,
        n_estimators=2,
        hidden_layer_sizes=(4,),
        temporal_max_iter=2,
    )

    assert run.manifest_path.is_file()
    assert run.manifest["status"] == "complete"
    assert len(run.reports) == 3
