from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.gaze_in_wild_roadmap_sync as roadmap
import gazeforge.visus_intake as visus
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import (
    BenchmarkIntegrityError,
    SchemaError,
)
from gazeforge.visus_audit import (
    VisusSourceAuditSpec,
    VisusSourceFileRecord,
    audit_visus_source,
)

SYNC_EVIDENCE = Path("validation/evidence/gaze-in-wild/gaze-in-wild-roadmap-evidence-sync-v1.json")

RATE_LEDGER = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-processdata-processed-rate-ledger-v1.json"
)


# ============================================================
# VISUS FIXTURES
# ============================================================


def _write(
    root: Path,
    relative: str,
) -> tuple[str, int]:
    path = root / relative

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        f"fixture:{relative}\n",
        encoding="utf-8",
    )

    payload = path.read_bytes()

    return (
        hashlib.sha256(payload).hexdigest(),
        len(payload),
    )


def _visus_record(
    root: Path,
    *,
    path: str,
    role: str,
    stimulus_id: str,
    participant_id: str | None = None,
    annotation_stream_id: str | None = None,
):
    digest, size = _write(
        root,
        path,
    )

    return VisusSourceFileRecord(
        path=path,
        sha256=digest,
        bytes=size,
        role=role,
        stimulus_id=stimulus_id,
        participant_id=participant_id,
        annotation_stream_id=(annotation_stream_id),
    )


def _visus_audit(
    root: Path,
):
    stimuli = [
        f"S{index:02d}"
        for index in range(
            1,
            12,
        )
    ]

    files = []

    for stimulus in stimuli:
        files.append(
            _visus_record(
                root,
                path=(f"video/{stimulus}.avi"),
                role="video",
                stimulus_id=stimulus,
            )
        )

        files.append(
            _visus_record(
                root,
                path=(f"aoi/{stimulus}.xml"),
                role="aoi_annotation",
                stimulus_id=stimulus,
                annotation_stream_id=("published_curated"),
            )
        )

    for index in range(
        1,
        26,
    ):
        participant = f"P{index:02d}"

        stimulus = stimuli[(index - 1) % len(stimuli)]

        files.append(
            _visus_record(
                root,
                path=(f"gaze/{participant}-{stimulus}.tsv"),
                role="gaze",
                stimulus_id=stimulus,
                participant_id=participant,
            )
        )

    spec = VisusSourceAuditSpec(
        dataset_name="VISUS",
        dataset_version="wave-x",
        source=("https://example.invalid/visus"),
        source_revision="fixture",
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
        coordinate_verification_basis=("Fixture coordinate evidence."),
        timestamp_basis_verified=True,
        timestamp_verification_basis=("Fixture frame-time evidence."),
        files=files,
    )

    return audit_visus_source(
        root,
        spec,
    )


def _visus_table(
    *,
    confidence=True,
):
    rows = []

    for stimulus in (
        "S01",
        "S02",
    ):
        for frame, offset in (
            (
                1,
                0.0,
            ),
            (
                26,
                10.0,
            ),
        ):
            row = {
                "source_path": (f"aoi/{stimulus}.xml"),
                "stimulus_id": stimulus,
                "annotation_stream_id": ("published_curated"),
                "frame_index": frame,
                "aoi_id": "target",
                "label": "person",
                "xmin": 10.0 + offset,
                "ymin": 20.0,
                "xmax": 110.0 + offset,
                "ymax": 220.0,
            }

            if confidence:
                row["confidence"] = 0.9

            rows.append(row)

    return pd.DataFrame(rows)


def _restamp_audit_report(
    audit,
):
    audit.report["spec_fingerprint_sha256"] = benchmark_fingerprint(audit.spec.to_dict())

    body = {key: value for key, value in audit.report.items() if key != "report_fingerprint_sha256"}

    audit.report["report_fingerprint_sha256"] = benchmark_fingerprint(body)


# ============================================================
# VISUS _resolved
# ============================================================


@pytest.mark.parametrize(
    (
        "value",
        "expected",
    ),
    [
        (
            "reviewed",
            True,
        ),
        (
            " reviewed ",
            True,
        ),
        (
            "",
            False,
        ),
        (
            " ",
            False,
        ),
        (
            "REPLACE_ME",
            False,
        ),
        (
            "verify later",
            False,
        ),
    ],
)
def test_visus_resolved(
    value,
    expected,
):
    assert visus._resolved(value) is expected


# ============================================================
# VISUS AUDIT INTEGRITY
# ============================================================


def test_visus_integrity_type():
    with pytest.raises(
        TypeError,
        match="VisusSourceAuditRun",
    ):
        visus._verify_audit_integrity({})


def test_visus_integrity_status(
    tmp_path,
):
    audit = _visus_audit(tmp_path)

    audit.report["status"] = "invalid"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not verified",
    ):
        visus._verify_audit_integrity(audit)


def test_visus_integrity_report_fingerprint(
    tmp_path,
):
    audit = _visus_audit(tmp_path)

    audit.report["report_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report fingerprint",
    ):
        visus._verify_audit_integrity(audit)


def test_visus_integrity_short_report_fingerprint(
    tmp_path,
):
    audit = _visus_audit(tmp_path)

    audit.report["report_fingerprint_sha256"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report fingerprint",
    ):
        visus._verify_audit_integrity(audit)


def test_visus_integrity_spec_fingerprint(
    tmp_path,
):
    audit = _visus_audit(tmp_path)

    audit.report["spec_fingerprint_sha256"] = "0" * 64

    body = {key: value for key, value in audit.report.items() if key != "report_fingerprint_sha256"}

    audit.report["report_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="specification fingerprint",
    ):
        visus._verify_audit_integrity(audit)


def test_visus_integrity_manifest_fingerprint(
    tmp_path,
):
    audit = _visus_audit(tmp_path)

    audit.report["inventory"]["manifest_fingerprint_sha256"] = "0" * 64

    body = {key: value for key, value in audit.report.items() if key != "report_fingerprint_sha256"}

    audit.report["report_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source manifest fingerprint",
    ):
        visus._verify_audit_integrity(audit)


def test_visus_integrity_valid(
    tmp_path,
):
    audit = _visus_audit(tmp_path)

    visus._verify_audit_integrity(audit)


# ============================================================
# VISUS ANNOTATION MANIFEST
# ============================================================


def test_visus_annotation_manifest_none():
    audit = SimpleNamespace(
        files=[],
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="no AOI annotation files",
    ):
        visus._annotation_manifest(audit)


def test_visus_annotation_manifest_valid(
    tmp_path,
):
    audit = _visus_audit(tmp_path)

    manifest = visus._annotation_manifest(audit)

    assert set(manifest) == {
        f"aoi/S{index:02d}.xml"
        for index in range(
            1,
            12,
        )
    }

    assert len(manifest) == 11


# ============================================================
# VISUS NUMERIC


# ============================================================
# VISUS NUMERIC
# ============================================================


def test_visus_numeric_valid():
    table = pd.DataFrame(
        {
            "x": [
                "1",
                2,
            ]
        }
    )

    result = visus._numeric(
        table,
        "x",
    )

    assert result.tolist() == [
        1.0,
        2.0,
    ]


@pytest.mark.parametrize(
    "value",
    [
        "bad",
        np.nan,
        np.inf,
    ],
)
def test_visus_numeric_invalid(
    value,
):
    table = pd.DataFrame(
        {
            "x": [
                value,
            ]
        }
    )

    with pytest.raises(
        SchemaError,
        match="finite numeric",
    ):
        visus._numeric(
            table,
            "x",
        )


# ============================================================
# VISUS ROW VALIDATOR
# ============================================================


def _manifest(
    tmp_path,
):
    audit = _visus_audit(tmp_path)

    full = visus._annotation_manifest(audit)

    # Low-level _validate_rows tests deliberately exercise
    # only two audited AOI files. This keeps those tests
    # focused on visus_intake row contracts while the audit
    # fixture itself remains a valid empirical VISUS audit.
    wanted = (
        "aoi/S01.xml",
        "aoi/S02.xml",
    )

    return {path: full[path] for path in wanted}


def _validate_rows(
    table,
    manifest,
    *,
    frame_index_base=1,
    coordinate_unit="pixels",
    complete=True,
):
    return visus._validate_rows(
        table,
        manifest=manifest,
        frame_index_base=(frame_index_base),
        video_rate_hz=25.0,
        coordinate_unit=coordinate_unit,
        video_resolution_px=(
            1920,
            1080,
        ),
        require_complete_manifest_coverage=(complete),
    )


def test_visus_rows_missing_columns(
    tmp_path,
):
    table = _visus_table()

    table = table.drop(columns=["label"])

    with pytest.raises(
        SchemaError,
        match="missing columns",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
        )


def test_visus_rows_empty(
    tmp_path,
):
    table = _visus_table().iloc[0:0]

    with pytest.raises(
        SchemaError,
        match="cannot be empty",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
        )


@pytest.mark.parametrize(
    "column",
    [
        "source_path",
        "stimulus_id",
        "annotation_stream_id",
        "aoi_id",
        "label",
    ],
)
def test_visus_rows_empty_text(
    tmp_path,
    column,
):
    table = _visus_table()

    table.loc[
        table.index[0],
        column,
    ] = " "

    with pytest.raises(
        SchemaError,
        match="cannot contain empty",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
        )


def test_visus_rows_fractional_frame(
    tmp_path,
):
    table = _visus_table()

    table["frame_index"] = table["frame_index"].astype(float)

    table.loc[
        table.index[0],
        "frame_index",
    ] = 1.5

    with pytest.raises(
        SchemaError,
        match="must be integers",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
        )


def test_visus_rows_below_base(
    tmp_path,
):
    table = _visus_table()

    table.loc[
        table.index[0],
        "frame_index",
    ] = 0

    with pytest.raises(
        SchemaError,
        match="explicit base",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
        )


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        (
            "xmax",
            10.0,
        ),
        (
            "ymax",
            20.0,
        ),
    ],
)
def test_visus_rows_bad_geometry(
    tmp_path,
    field,
    value,
):
    table = _visus_table()

    table.loc[
        table.index[0],
        field,
    ] = value

    with pytest.raises(
        SchemaError,
        match="xmax > xmin and ymax > ymin",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
        )


def test_visus_rows_default_confidence(
    tmp_path,
):
    result = _validate_rows(
        _visus_table(confidence=False),
        _manifest(tmp_path),
    )

    assert result["confidence"].tolist() == [
        1.0,
        1.0,
        1.0,
        1.0,
    ]


@pytest.mark.parametrize(
    "value",
    [
        -0.01,
        1.01,
    ],
)
def test_visus_rows_confidence_range(
    tmp_path,
    value,
):
    table = _visus_table()

    table.loc[
        table.index[0],
        "confidence",
    ] = value

    with pytest.raises(
        SchemaError,
        match=r"\[0, 1\]",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
        )


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        (
            "xmin",
            -1.0,
        ),
        (
            "ymin",
            -1.0,
        ),
        (
            "xmax",
            2000.0,
        ),
        (
            "ymax",
            1200.0,
        ),
    ],
)
def test_visus_rows_pixel_bounds(
    tmp_path,
    field,
    value,
):
    table = _visus_table()

    table.loc[
        table.index[0],
        field,
    ] = value

    with pytest.raises(
        SchemaError,
        match="video resolution",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
        )


def test_visus_rows_nonpixel_skips_resolution(
    tmp_path,
):
    table = _visus_table()

    table.loc[
        table.index[0],
        "xmax",
    ] = 5000.0

    result = _validate_rows(
        table,
        _manifest(tmp_path),
        coordinate_unit="degrees",
    )

    assert (
        result.loc[
            0,
            "xmax",
        ]
        == 5000.0
    )


def test_visus_rows_unknown_source(
    tmp_path,
):
    table = _visus_table()

    table.loc[
        table.index[0],
        "source_path",
    ] = "aoi/UNKNOWN.xml"

    with pytest.raises(
        SchemaError,
        match="not an audited AOI file",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
            complete=False,
        )


def test_visus_rows_stimulus_mismatch(
    tmp_path,
):
    table = _visus_table()

    table.loc[
        table.index[0],
        "stimulus_id",
    ] = "S02"

    with pytest.raises(
        SchemaError,
        match="stimulus_id",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
        )


def test_visus_rows_stream_mismatch(
    tmp_path,
):
    table = _visus_table()

    table.loc[
        table.index[0],
        "annotation_stream_id",
    ] = "other"

    with pytest.raises(
        SchemaError,
        match="annotation_stream_id",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
        )


def test_visus_rows_missing_manifest_coverage(
    tmp_path,
):
    table = _visus_table()

    table = table.loc[table["stimulus_id"] != "S02"].copy()

    with pytest.raises(
        SchemaError,
        match="cover every audited AOI",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
        )


def test_visus_rows_partial_coverage_allowed(
    tmp_path,
):
    table = _visus_table()

    table = table.loc[table["stimulus_id"] != "S02"].copy()

    result = _validate_rows(
        table,
        _manifest(tmp_path),
        complete=False,
    )

    assert set(result["stimulus_id"]) == {"S01"}


def test_visus_rows_duplicate_identity(
    tmp_path,
):
    table = pd.concat(
        [
            _visus_table(),
            _visus_table().iloc[[0]],
        ],
        ignore_index=True,
    )

    with pytest.raises(
        SchemaError,
        match="duplicate",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
        )


def test_visus_rows_label_drift(
    tmp_path,
):
    table = _visus_table()

    table.loc[
        table.index[1],
        "label",
    ] = "vehicle"

    with pytest.raises(
        SchemaError,
        match="one semantic label",
    ):
        _validate_rows(
            table,
            _manifest(tmp_path),
        )


def test_visus_rows_timestamp_and_source(
    tmp_path,
):
    result = _validate_rows(
        _visus_table(),
        _manifest(tmp_path),
    )

    assert result["timestamp_ms"].min() == pytest.approx(0.0)

    assert result["timestamp_ms"].max() == pytest.approx(1000.0)

    assert set(result["source"]) == {"human-manual"}


# ============================================================
# VISUS KEYFRAMES
# ============================================================


def test_visus_to_keyframes(
    tmp_path,
):
    canonical = _validate_rows(
        _visus_table(),
        _manifest(tmp_path),
    )

    result = visus._to_keyframes(canonical)

    assert set(result) == {"published_curated"}

    assert set(result["published_curated"]) == {
        "S01",
        "S02",
    }

    first = result["published_curated"]["S01"][0]

    assert first.source == "human-manual"


# ============================================================
# VISUS PREPARE TOP-LEVEL GUARDS
# ============================================================


def test_visus_prepare_table_type(
    monkeypatch,
):
    monkeypatch.setattr(
        visus,
        "_verify_audit_integrity",
        lambda audit: None,
    )

    with pytest.raises(
        TypeError,
        match="pandas DataFrame",
    ):
        visus.prepare_visus_canonical_aoi_intake(
            object(),
            {},
            extraction_basis="reviewed",
            frame_index_base=1,
        )


@pytest.mark.parametrize(
    "basis",
    [
        "",
        "REPLACE_ME",
        "VERIFY LATER",
    ],
)
def test_visus_prepare_extraction_basis(
    monkeypatch,
    basis,
):
    monkeypatch.setattr(
        visus,
        "_verify_audit_integrity",
        lambda audit: None,
    )

    with pytest.raises(
        ValueError,
        match="extraction_basis",
    ):
        visus.prepare_visus_canonical_aoi_intake(
            object(),
            pd.DataFrame(),
            extraction_basis=basis,
            frame_index_base=1,
        )


@pytest.mark.parametrize(
    "base",
    [
        -1,
        2,
    ],
)
def test_visus_prepare_frame_base(
    monkeypatch,
    base,
):
    monkeypatch.setattr(
        visus,
        "_verify_audit_integrity",
        lambda audit: None,
    )

    with pytest.raises(
        ValueError,
        match="0 or 1",
    ):
        visus.prepare_visus_canonical_aoi_intake(
            object(),
            pd.DataFrame(),
            extraction_basis="reviewed",
            frame_index_base=base,
        )


def test_visus_prepare_timestamp_basis(
    monkeypatch,
):
    monkeypatch.setattr(
        visus,
        "_verify_audit_integrity",
        lambda audit: None,
    )

    fake = SimpleNamespace(
        spec=SimpleNamespace(
            timestamp_basis_verified=False,
            coordinate_unit_verified=True,
        )
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="timestamp/frame-time",
    ):
        visus.prepare_visus_canonical_aoi_intake(
            fake,
            pd.DataFrame(),
            extraction_basis="reviewed",
            frame_index_base=1,
        )


def test_visus_prepare_coordinate_basis(
    monkeypatch,
):
    monkeypatch.setattr(
        visus,
        "_verify_audit_integrity",
        lambda audit: None,
    )

    fake = SimpleNamespace(
        spec=SimpleNamespace(
            timestamp_basis_verified=True,
            coordinate_unit_verified=False,
        )
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="coordinate units",
    ):
        visus.prepare_visus_canonical_aoi_intake(
            fake,
            pd.DataFrame(),
            extraction_basis="reviewed",
            frame_index_base=1,
        )


@pytest.mark.parametrize(
    "rate",
    [
        0.0,
        -1.0,
        np.nan,
        np.inf,
    ],
)
def test_visus_prepare_video_rate(
    monkeypatch,
    rate,
):
    monkeypatch.setattr(
        visus,
        "_verify_audit_integrity",
        lambda audit: None,
    )

    fake = SimpleNamespace(
        spec=SimpleNamespace(
            timestamp_basis_verified=True,
            coordinate_unit_verified=True,
            published_video_frame_rate_hz=(rate),
        )
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="finite and positive",
    ):
        visus.prepare_visus_canonical_aoi_intake(
            fake,
            pd.DataFrame(),
            extraction_basis="reviewed",
            frame_index_base=1,
        )


def test_visus_prepare_success_partial(
    tmp_path,
):
    audit = _visus_audit(tmp_path)

    table = _visus_table()

    table = table.loc[table["stimulus_id"] == "S01"].copy()

    result = visus.prepare_visus_canonical_aoi_intake(
        audit,
        table,
        extraction_basis=("Reviewed fixture extraction."),
        frame_index_base=1,
        require_complete_manifest_coverage=False,
    )

    assert result.report["complete_annotation_manifest_coverage_required"] is False

    assert result.report["row_count"] == 2

    assert result.report["stimulus_ids"] == ["S01"]


# ============================================================
# ROADMAP FIXTURES
# ============================================================


def _load_json(
    path: Path,
):
    return json.loads(path.read_text(encoding="utf-8"))


def _rate_record():
    return _load_json(RATE_LEDGER)


def _sync_record():
    return _load_json(SYNC_EVIDENCE)


def _bypass_fingerprint(
    monkeypatch,
    expected,
):
    monkeypatch.setattr(
        roadmap,
        "evidence_fingerprint",
        lambda record: expected,
    )


# ============================================================
# ROADMAP LOW-LEVEL HELPERS
# ============================================================


def test_roadmap_canonical_bytes():
    assert roadmap._canonical_bytes(
        {
            "b": 2,
            "a": 1,
        }
    ) == roadmap._canonical_bytes(
        {
            "a": 1,
            "b": 2,
        }
    )


def test_roadmap_fingerprint_ignores_self():
    record = {
        "x": 1,
        "evidence_fingerprint_sha256": ("a" * 64),
    }

    first = roadmap.evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = "b" * 64

    assert roadmap.evidence_fingerprint(record) == first


def test_roadmap_load_mapping():
    record = {"x": 1}

    loaded, path = roadmap._load(
        record,
        "fixture",
    )

    assert loaded == record
    assert loaded is not record
    assert path is None


def test_roadmap_load_path_valid(
    tmp_path,
):
    path = tmp_path / "x.json"

    path.write_text(
        '{"x": 1}',
        encoding="utf-8",
    )

    loaded, observed_path = roadmap._load(
        path,
        "fixture",
    )

    assert loaded == {"x": 1}

    assert observed_path == path


@pytest.mark.parametrize(
    "payload",
    [
        b"{",
        b"\xff",
    ],
)
def test_roadmap_load_bad_json(
    tmp_path,
    payload,
):
    path = tmp_path / "x.json"

    path.write_bytes(payload)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        roadmap._load(
            path,
            "fixture",
        )


def test_roadmap_load_missing(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        roadmap._load(
            tmp_path / "missing.json",
            "fixture",
        )


def test_roadmap_load_nonobject(
    tmp_path,
):
    path = tmp_path / "x.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        roadmap._load(
            path,
            "fixture",
        )


def test_roadmap_mapping_missing():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        roadmap._mapping(
            {
                "x": [],
            },
            "x",
            "fixture",
        )


def test_roadmap_mapping_valid():
    value = roadmap._mapping(
        {
            "x": {
                "y": 1,
            }
        },
        "x",
        "fixture",
    )

    assert value == {"y": 1}


def test_roadmap_equal_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        roadmap._equal(
            1,
            2,
            "fixture",
        )


def test_roadmap_equal_success():
    roadmap._equal(
        1,
        1,
        "fixture",
    )


def test_roadmap_true_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        roadmap._true(
            False,
            "fixture",
        )


def test_roadmap_true_success():
    roadmap._true(
        True,
        "fixture",
    )


def test_roadmap_false_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        roadmap._false(
            True,
            "fixture",
        )


def test_roadmap_false_success():
    roadmap._false(
        False,
        "fixture",
    )


# ============================================================
# PROCESSED-RATE LEDGER IMMUTABLE HEADER
# ============================================================


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        (
            "record_type",
            "wrong",
        ),
        (
            "reviewed_on",
            "2026-01-01",
        ),
        (
            "columns",
            [],
        ),
        (
            "file_count",
            67,
        ),
        (
            "rate_semantics",
            "wrong",
        ),
        (
            "stored_rate_semantics",
            "wrong",
        ),
    ],
)
def test_rate_header_drift(
    monkeypatch,
    field,
    value,
):
    record = _rate_record()

    record[field] = value

    _bypass_fingerprint(
        monkeypatch,
        roadmap.RATE_LEDGER_FINGERPRINT,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


def test_rate_stored_fingerprint():
    record = _rate_record()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="stored rate-ledger fingerprint",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


def test_rate_recomputed_fingerprint(
    monkeypatch,
):
    record = _rate_record()

    monkeypatch.setattr(
        roadmap,
        "evidence_fingerprint",
        lambda value: "0" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="recomputed rate-ledger fingerprint",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


@pytest.mark.parametrize(
    "key",
    list(roadmap.EXPECTED_RATE_SOURCE_BINDING),
)
def test_rate_source_binding(
    monkeypatch,
    key,
):
    record = _rate_record()

    record["source_binding"][key] = "0" * 64

    _bypass_fingerprint(
        monkeypatch,
        roadmap.RATE_LEDGER_FINGERPRINT,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source binding",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


def test_rate_source_binding_missing(
    monkeypatch,
):
    record = _rate_record()

    record["source_binding"] = None

    _bypass_fingerprint(
        monkeypatch,
        roadmap.RATE_LEDGER_FINGERPRINT,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source_binding",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


def test_rate_required_true_boundary(
    monkeypatch,
):
    record = _rate_record()

    record["scientific_boundary"]["per_file_processed_timestamp_grid_rate_distribution_frozen"] = (
        False
    )

    _bypass_fingerprint(
        monkeypatch,
        roadmap.RATE_LEDGER_FINGERPRINT,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


@pytest.mark.parametrize(
    "key",
    [
        "acquisition_hardware_cadence_verified",
        "gp3_validity_claim_created",
        "new_model_performance_claim_created",
        ("participant_disjoint_model_validation_created"),
        "task_mapping_verified",
    ],
)
def test_rate_forbidden_boundaries(
    monkeypatch,
    key,
):
    record = _rate_record()

    record["scientific_boundary"][key] = True

    _bypass_fingerprint(
        monkeypatch,
        roadmap.RATE_LEDGER_FINGERPRINT,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


def test_rate_boundary_missing(
    monkeypatch,
):
    record = _rate_record()

    record["scientific_boundary"] = None

    _bypass_fingerprint(
        monkeypatch,
        roadmap.RATE_LEDGER_FINGERPRINT,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="scientific_boundary",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


# ============================================================
# PROCESSED-RATE ROW VALIDATION
# ============================================================


def _deep_rate(
    monkeypatch,
):
    record = copy.deepcopy(_rate_record())

    _bypass_fingerprint(
        monkeypatch,
        roadmap.RATE_LEDGER_FINGERPRINT,
    )

    return record


@pytest.mark.parametrize(
    "rows",
    [
        None,
        [],
    ],
)
def test_rate_rows_count(
    monkeypatch,
    rows,
):
    record = _deep_rate(monkeypatch)

    record["rows"] = rows

    with pytest.raises(
        BenchmarkIntegrityError,
        match="contain 68 rows",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


def test_rate_row_shape(
    monkeypatch,
):
    record = _deep_rate(monkeypatch)

    record["rows"][0] = [
        "bad",
    ]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="row shape drifted",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


def test_rate_row_name_type(
    monkeypatch,
):
    record = _deep_rate(monkeypatch)

    record["rows"][0][0] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file names are invalid",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


def test_rate_row_duplicate_name(
    monkeypatch,
):
    record = _deep_rate(monkeypatch)

    record["rows"][1][0] = record["rows"][0][0]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file names are invalid",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


@pytest.mark.parametrize(
    "digest",
    [
        None,
        "a" * 63,
        "G" * 64,
    ],
)
def test_rate_row_digest(
    monkeypatch,
    digest,
):
    record = _deep_rate(monkeypatch)

    record["rows"][0][1] = digest

    with pytest.raises(
        BenchmarkIntegrityError,
        match="SHA-256 identity",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


@pytest.mark.parametrize(
    "participant",
    [
        None,
        0,
        -1,
        1.5,
    ],
)
def test_rate_row_participant(
    monkeypatch,
    participant,
):
    record = _deep_rate(monkeypatch)

    record["rows"][0][2] = participant

    with pytest.raises(
        BenchmarkIntegrityError,
        match="participant identity",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


@pytest.mark.parametrize(
    "trial",
    [
        0,
        5,
        "1",
    ],
)
def test_rate_row_trial(
    monkeypatch,
    trial,
):
    record = _deep_rate(monkeypatch)

    record["rows"][0][3] = trial

    with pytest.raises(
        BenchmarkIntegrityError,
        match="trial identity",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


def test_rate_row_stored_rate(
    monkeypatch,
):
    record = _deep_rate(monkeypatch)

    record["rows"][0][4] = 120.0

    with pytest.raises(
        BenchmarkIntegrityError,
        match="stored processing rate",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


@pytest.mark.parametrize(
    "value",
    [
        "bad",
        None,
    ],
)
def test_rate_row_inferred_nonnumeric(
    monkeypatch,
    value,
):
    record = _deep_rate(monkeypatch)

    record["rows"][0][5] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be numeric",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


@pytest.mark.parametrize(
    "value",
    [
        np.nan,
        np.inf,
        299.0,
        301.0,
    ],
)
def test_rate_row_inferred_range(
    monkeypatch,
    value,
):
    record = _deep_rate(monkeypatch)

    record["rows"][0][5] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="timestamp-grid rate drifted",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


@pytest.mark.parametrize(
    "value",
    [
        None,
        0,
        1,
        1.5,
    ],
)
def test_rate_row_count(
    monkeypatch,
    value,
):
    record = _deep_rate(monkeypatch)

    record["rows"][0][6] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="timestamp count",
    ):
        roadmap.validate_gaze_in_wild_processed_rate_ledger(record)


def test_rate_mapping_success(
    monkeypatch,
):
    record = _deep_rate(monkeypatch)

    result = roadmap.validate_gaze_in_wild_processed_rate_ledger(record)

    assert result.path is None

    assert result.file_count == 68

    assert 299.98 < result.min_inferred_rate_hz < 300.01


# ============================================================
# REPOSITORY ROOT
# ============================================================


def test_roadmap_repository_root_explicit(
    tmp_path,
):
    explicit = tmp_path / "repo"

    assert (
        roadmap._repository_root(
            None,
            explicit,
        )
        == explicit
    )


def test_roadmap_repository_root_from_path():
    path = Path("a/b/c/d/e.json")

    assert (
        roadmap._repository_root(
            path,
            None,
        )
        == path.parents[3]
    )


def test_roadmap_repository_root_cwd():
    assert (
        roadmap._repository_root(
            None,
            None,
        )
        == Path.cwd()
    )


# ============================================================
# ROADMAP SYNC DEEP CONTRACT
# ============================================================


def _deep_sync(
    monkeypatch,
):
    record = copy.deepcopy(_sync_record())

    _bypass_fingerprint(
        monkeypatch,
        roadmap.SYNC_FINGERPRINT,
    )

    return record


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        (
            "record_type",
            "wrong",
        ),
        (
            "status",
            "wrong",
        ),
        (
            "reviewed_on",
            "2026-01-01",
        ),
        (
            "source_main_sha",
            "0" * 40,
        ),
    ],
)
def test_sync_header_drift(
    monkeypatch,
    field,
    value,
):
    record = _deep_sync(monkeypatch)

    record[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        roadmap.validate_gaze_in_wild_roadmap_sync(record)


def test_sync_stored_fingerprint():
    record = _sync_record()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="stored sync fingerprint",
    ):
        roadmap.validate_gaze_in_wild_roadmap_sync(record)


def test_sync_recomputed_fingerprint(
    monkeypatch,
):
    record = _sync_record()

    monkeypatch.setattr(
        roadmap,
        "evidence_fingerprint",
        lambda value: "0" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="recomputed sync fingerprint",
    ):
        roadmap.validate_gaze_in_wild_roadmap_sync(record)


@pytest.mark.parametrize(
    "field",
    [
        "upstream_evidence",
        "roadmap_completion",
        "scientific_boundary",
        "issue_wording",
    ],
)
def test_sync_sections_missing(
    monkeypatch,
    field,
):
    record = _deep_sync(monkeypatch)

    record[field] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        roadmap.validate_gaze_in_wild_roadmap_sync(record)


@pytest.mark.parametrize(
    (
        "section",
        "field",
        "value",
    ),
    [
        (
            "processed_rate_ledger",
            "path",
            "wrong.json",
        ),
        (
            "processed_rate_ledger",
            "evidence_fingerprint_sha256",
            "0" * 64,
        ),
        (
            "processed_rate_ledger",
            "file_count",
            67,
        ),
        (
            "processed_rate_ledger",
            "scope",
            "wrong",
        ),
        (
            "overlap_human_human_agreement",
            "path",
            "wrong.json",
        ),
        (
            "overlap_human_human_agreement",
            "evidence_fingerprint_sha256",
            "0" * 64,
        ),
        (
            "overlap_human_human_agreement",
            "recording_count",
            4,
        ),
        (
            "overlap_human_human_agreement",
            "labeller_pair_count",
            5,
        ),
        (
            "overlap_human_human_agreement",
            "scope",
            "wrong",
        ),
    ],
)
def test_sync_upstream_contract(
    monkeypatch,
    section,
    field,
    value,
):
    record = _deep_sync(monkeypatch)

    record["upstream_evidence"][section][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        roadmap.validate_gaze_in_wild_roadmap_sync(record)


@pytest.mark.parametrize(
    "field",
    [
        ("processed_timestamp_grid_rate_distribution_scoped_item_satisfied"),
        ("distributed_overlap_human_human_agreement_scoped_item_satisfied"),
    ],
)
def test_sync_completion_required_true(
    monkeypatch,
    field,
):
    record = _deep_sync(monkeypatch)

    record["roadmap_completion"][field] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        roadmap.validate_gaze_in_wild_roadmap_sync(record)


@pytest.mark.parametrize(
    "field",
    [
        ("authoritative_numeric_task_mapping_item_satisfied"),
        ("task_stratified_validation_item_satisfied"),
    ],
)
def test_sync_completion_required_false(
    monkeypatch,
    field,
):
    record = _deep_sync(monkeypatch)

    record["roadmap_completion"][field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        roadmap.validate_gaze_in_wild_roadmap_sync(record)


@pytest.mark.parametrize(
    "field",
    [
        "acquisition_hardware_cadence_verified",
        ("full_distributed_labeldata_hha_created"),
        "task_mapping_verified",
        "task_stratified_hha_created",
        ("task_stratified_model_validation_created"),
        "native_60hz_validity_claim_created",
        "gp3_validity_claim_created",
        "cross_dataset_validation_created",
        "quarantine_exit_authorized",
        "new_model_performance_claim_created",
    ],
)
def test_sync_boundaries(
    monkeypatch,
    field,
):
    record = _deep_sync(monkeypatch)

    record["scientific_boundary"][field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        roadmap.validate_gaze_in_wild_roadmap_sync(record)


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        (
            "processed_rate",
            "wrong",
        ),
        (
            "human_human_agreement",
            "wrong",
        ),
    ],
)
def test_sync_wording(
    monkeypatch,
    field,
    value,
):
    record = _deep_sync(monkeypatch)

    record["issue_wording"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="wording drifted",
    ):
        roadmap.validate_gaze_in_wild_roadmap_sync(record)


# ============================================================
# ROADMAP UPSTREAM VALIDATION
# ============================================================


def _patch_upstream_success(
    monkeypatch,
    *,
    recording_count=5,
    pair_count=6,
    overlap_verified=True,
    quarantine=False,
):
    rate = roadmap.GazeInWildProcessedRateLedger(
        path=None,
        fingerprint_sha256=(roadmap.RATE_LEDGER_FINGERPRINT),
        file_count=68,
        min_inferred_rate_hz=299.99,
        max_inferred_rate_hz=300.0,
    )

    hha = SimpleNamespace(
        overlap_hha_verified=(overlap_verified),
        quarantine_exit_authorized=(quarantine),
        recording_count=(recording_count),
        pair_count=pair_count,
    )

    monkeypatch.setattr(
        roadmap,
        "validate_gaze_in_wild_processed_rate_ledger",
        lambda path: rate,
    )

    monkeypatch.setattr(
        roadmap,
        "validate_gaze_in_wild_overlap_hha_evidence",
        lambda path: hha,
    )


@pytest.mark.parametrize(
    (
        "overlap_verified",
        "quarantine",
    ),
    [
        (
            False,
            False,
        ),
        (
            True,
            True,
        ),
    ],
)
def test_sync_hha_boundary(
    monkeypatch,
    tmp_path,
    overlap_verified,
    quarantine,
):
    record = _deep_sync(monkeypatch)

    _patch_upstream_success(
        monkeypatch,
        overlap_verified=(overlap_verified),
        quarantine=quarantine,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="upstream boundary drifted",
    ):
        roadmap.validate_gaze_in_wild_roadmap_sync(
            record,
            repository_root=tmp_path,
        )


def test_sync_hha_recording_count(
    monkeypatch,
    tmp_path,
):
    record = _deep_sync(monkeypatch)

    _patch_upstream_success(
        monkeypatch,
        recording_count=4,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="validated HHA recording count",
    ):
        roadmap.validate_gaze_in_wild_roadmap_sync(
            record,
            repository_root=tmp_path,
        )


def test_sync_hha_pair_count(
    monkeypatch,
    tmp_path,
):
    record = _deep_sync(monkeypatch)

    _patch_upstream_success(
        monkeypatch,
        pair_count=5,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="validated HHA pair count",
    ):
        roadmap.validate_gaze_in_wild_roadmap_sync(
            record,
            repository_root=tmp_path,
        )


def test_sync_mapping_success(
    monkeypatch,
    tmp_path,
):
    record = _deep_sync(monkeypatch)

    _patch_upstream_success(monkeypatch)

    result = roadmap.validate_gaze_in_wild_roadmap_sync(
        record,
        repository_root=tmp_path,
    )

    assert result.path is None

    assert result.processed_rate_file_count == 68

    assert result.overlap_hha_recording_count == 5

    assert result.overlap_hha_pair_count == 6
