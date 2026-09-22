from __future__ import annotations

import json

import pytest
from test_visus_audit import _fixture

from gazeforge import visus_audit as audit
from gazeforge.exceptions import BenchmarkIntegrityError


def _rebuild(spec, **changes):
    values = spec.to_dict()
    values["files"] = spec.files
    values.update(changes)
    return audit.VisusSourceAuditSpec(**values)


# ============================================================
# SMALL HELPERS
# ============================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("resolved", True),
        (" https://example.invalid ", True),
        ("", False),
        ("   ", False),
        ("REPLACE_ME", False),
        ("verify-this", False),
    ],
)
def test_resolved_contract(value, expected):
    assert audit._resolved(value) is expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "../secret.tsv",
        "/absolute/file.tsv",
    ],
)
def test_safe_relative_path_rejects_unsafe(value):
    with pytest.raises(ValueError, match="safe non-empty relative"):
        audit._safe_relative_path(value)


def test_safe_relative_path_normalizes_windows_separator():
    assert audit._safe_relative_path(r"gaze\P01-S01.tsv") == "gaze/P01-S01.tsv"


# ============================================================
# FILE RECORD CONTRACT
# ============================================================


def _record(**changes):
    values = {
        "path": "other/data.bin",
        "sha256": "A" * 64,
        "bytes": 1,
        "role": "other",
    }
    values.update(changes)
    return audit.VisusSourceFileRecord(**values)


def test_record_normalizes_digest_and_role():
    record = _record(role=" OTHER ")
    assert record.sha256 == "a" * 64
    assert record.role == "other"


@pytest.mark.parametrize(
    "digest",
    [
        "a" * 63,
        "g" * 64,
    ],
)
def test_record_requires_valid_sha256(digest):
    with pytest.raises(ValueError, match="64 hex digits"):
        _record(sha256=digest)


def test_record_requires_positive_bytes():
    with pytest.raises(ValueError, match="byte sizes must be positive"):
        _record(bytes=0)


def test_record_rejects_unknown_role():
    with pytest.raises(ValueError, match="file role"):
        _record(role="mystery")


@pytest.mark.parametrize(
    ("role", "path", "message"),
    [
        ("video", "video/S01.txt", "video file suffix"),
        ("gaze", "gaze/P01-S01.csv", "TSV"),
        ("aoi_annotation", "aoi/S01.txt", "XML"),
    ],
)
def test_record_role_suffix_guards(role, path, message):
    kwargs = {
        "role": role,
        "path": path,
        "stimulus_id": "S01",
    }

    if role == "gaze":
        kwargs["participant_id"] = "P01"

    if role == "aoi_annotation":
        kwargs["annotation_stream_id"] = "curated"

    with pytest.raises(ValueError, match=message):
        _record(**kwargs)


@pytest.mark.parametrize(
    "role",
    [
        "video",
        "gaze",
        "aoi_annotation",
    ],
)
def test_record_requires_stimulus_for_scientific_roles(role):
    kwargs = {
        "role": role,
        "path": {
            "video": "video/S01.avi",
            "gaze": "gaze/P01-S01.tsv",
            "aoi_annotation": "aoi/S01.xml",
        }[role],
    }

    if role == "gaze":
        kwargs["participant_id"] = "P01"

    if role == "aoi_annotation":
        kwargs["annotation_stream_id"] = "curated"

    with pytest.raises(ValueError, match="stimulus_id"):
        _record(**kwargs)


def test_record_gaze_requires_participant():
    with pytest.raises(ValueError, match="participant_id"):
        _record(
            role="gaze",
            path="gaze/P01-S01.tsv",
            stimulus_id="S01",
        )


def test_record_annotation_requires_stream():
    with pytest.raises(ValueError, match="annotation_stream_id"):
        _record(
            role="aoi_annotation",
            path="aoi/S01.xml",
            stimulus_id="S01",
        )


def test_record_nonannotation_rejects_stream_id():
    with pytest.raises(ValueError, match="only valid for AOI"):
        _record(
            annotation_stream_id="not-allowed",
        )


def test_record_optional_identity_fields_are_trimmed():
    record = _record(
        participant_id=" P01 ",
        participant_group=" A ",
    )
    assert record.participant_id == "P01"
    assert record.participant_group == "A"


# ============================================================
# SPEC BASIC CONTRACT
# ============================================================


def _template(**changes):
    values = {
        "dataset_name": "VISUS",
        "dataset_version": "template-v1",
        "source": "https://example.invalid/visus",
        "source_revision": "revision",
        "license": "terms",
        "reuse_terms_source": "https://example.invalid/terms",
        "dataset_status": "template",
    }
    values.update(changes)
    return audit.VisusSourceAuditSpec(**values)


def test_spec_requires_visus_name():
    with pytest.raises(ValueError, match="dataset_name='VISUS'"):
        _template(dataset_name="Other")


def test_spec_status_guard():
    with pytest.raises(ValueError, match="template.*empirical"):
        _template(dataset_status="unknown")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("published_eye_sampling_rate_hz", 0, "eye_sampling"),
        ("published_video_frame_rate_hz", 0, "video_frame"),
    ],
)
def test_spec_requires_positive_rates(field, value, message):
    with pytest.raises(ValueError, match=message):
        _template(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("published_video_resolution_px", (1920,)),
        ("published_video_resolution_px", (1920, 0)),
        ("published_display_resolution_px", (0, 1200)),
    ],
)
def test_spec_resolution_guard(field, value):
    with pytest.raises(ValueError, match="positive width and height"):
        _template(**{field: value})


def test_spec_resolution_normalizes_to_int_tuple():
    spec = _template(
        published_video_resolution_px=(1920.0, 1080.0),
        published_display_resolution_px=(1920.0, 1200.0),
    )
    assert spec.published_video_resolution_px == (1920, 1080)
    assert spec.published_display_resolution_px == (1920, 1200)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("published_stimulus_count", 10, "must be 11"),
        ("published_participant_count", 24, "must be 25"),
        ("annotation_process_contributor_count", 1, "two human contributors"),
        ("annotation_format", "   ", "annotation_format cannot be empty"),
    ],
)
def test_spec_published_contract_guards(field, value, message):
    with pytest.raises(ValueError, match=message):
        _template(**{field: value})


def test_spec_rejects_duplicate_paths():
    first = _record(path="same.bin")
    second = _record(path="same.bin")

    with pytest.raises(ValueError, match="paths must be unique"):
        _template(files=[first, second])


def test_spec_rejects_duplicate_annotation_identity():
    first = _record(
        path="aoi/a.xml",
        role="aoi_annotation",
        stimulus_id="S01",
        annotation_stream_id="stream",
    )
    second = _record(
        path="aoi/b.xml",
        role="aoi_annotation",
        stimulus_id="S01",
        annotation_stream_id="stream",
    )

    with pytest.raises(ValueError, match="cannot duplicate"):
        _template(files=[first, second])


# ============================================================
# INDEPENDENT STREAM CLAIM
# ============================================================


def test_independent_stream_claim_requires_basis():
    with pytest.raises(ValueError, match="require an evidence basis"):
        _template(
            independent_annotation_streams_verified=True,
            independent_annotation_streams_basis="VERIFY",
        )


def test_independent_stream_claim_requires_two_streams():
    only = _record(
        path="aoi/S01.xml",
        role="aoi_annotation",
        stimulus_id="S01",
        annotation_stream_id="one",
    )

    with pytest.raises(ValueError, match="at least two"):
        _template(
            files=[only],
            independent_annotation_streams_verified=True,
            independent_annotation_streams_basis="Reviewed evidence.",
        )


def test_independent_stream_claim_can_be_disabled():
    spec = _template(
        independent_annotation_streams_verified=False,
        independent_annotation_streams_basis="",
    )
    assert spec.independent_annotation_streams_verified is False


# ============================================================
# EMPIRICAL PROVENANCE CONTRACT
# ============================================================


@pytest.fixture
def empirical(tmp_path):
    return _fixture(tmp_path / "valid")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dataset_version", "REPLACE_ME"),
        ("source", "VERIFY_SOURCE"),
        ("source_revision", ""),
        ("license", "VERIFY"),
        ("reuse_terms_source", "REPLACE"),
    ],
)
def test_empirical_requires_resolved_text(empirical, field, value):
    with pytest.raises(ValueError, match="resolved fields"):
        _rebuild(empirical, **{field: value})


def test_empirical_requires_files(empirical):
    with pytest.raises(ValueError, match="non-empty exact file manifest"):
        _rebuild(empirical, files=[])


@pytest.mark.parametrize(
    ("reuse", "analysis"),
    [
        (False, True),
        (True, False),
    ],
)
def test_empirical_requires_reuse_and_analysis_permission(empirical, reuse, analysis):
    with pytest.raises(ValueError, match="reviewed reuse terms"):
        _rebuild(
            empirical,
            reuse_terms_verified=reuse,
            analysis_use_permitted=analysis,
        )


@pytest.mark.parametrize(
    ("verified", "basis"),
    [
        (False, "Valid basis"),
        (True, "VERIFY"),
    ],
)
def test_empirical_requires_stimulus_mapping(empirical, verified, basis):
    with pytest.raises(ValueError, match="verified stimulus mapping"):
        _rebuild(
            empirical,
            stimulus_mapping_verified=verified,
            stimulus_mapping_basis=basis,
        )


@pytest.mark.parametrize(
    ("verified", "basis"),
    [
        (False, "Valid basis"),
        (True, "REPLACE"),
    ],
)
def test_empirical_requires_participant_mapping(empirical, verified, basis):
    with pytest.raises(ValueError, match="participant mapping"):
        _rebuild(
            empirical,
            participant_mapping_verified=verified,
            participant_mapping_basis=basis,
        )


@pytest.mark.parametrize(
    ("verified", "unit", "basis"),
    [
        (False, "pixels", "Valid basis"),
        (True, "unverified", "Valid basis"),
        (True, "pixels", "VERIFY"),
    ],
)
def test_empirical_requires_coordinate_basis(empirical, verified, unit, basis):
    with pytest.raises(ValueError, match="coordinate basis"):
        _rebuild(
            empirical,
            coordinate_unit_verified=verified,
            coordinate_unit=unit,
            coordinate_verification_basis=basis,
        )


@pytest.mark.parametrize(
    ("verified", "basis"),
    [
        (False, "Valid basis"),
        (True, "VERIFY"),
    ],
)
def test_empirical_requires_timestamp_basis(empirical, verified, basis):
    with pytest.raises(ValueError, match="timestamp/frame-time basis"):
        _rebuild(
            empirical,
            timestamp_basis_verified=verified,
            timestamp_verification_basis=basis,
        )


# ============================================================
# EMPIRICAL COVERAGE CONTRACT
# ============================================================


def test_empirical_requires_all_video_stimuli(empirical):
    files = [
        record
        for record in empirical.files
        if not (record.role == "video" and record.stimulus_id == "S11")
    ]

    with pytest.raises(ValueError, match="11 manifested video"):
        _rebuild(empirical, files=files)


def test_empirical_requires_aoi_video_identity_match(empirical):
    files = [
        record
        for record in empirical.files
        if not (record.role == "aoi_annotation" and record.stimulus_id == "S11")
    ]

    with pytest.raises(ValueError, match="AOI annotation manifest"):
        _rebuild(empirical, files=files)


def test_empirical_requires_gaze_video_identity_match(empirical):
    files = [
        record
        for record in empirical.files
        if not (record.role == "gaze" and record.stimulus_id == "S01")
    ]

    with pytest.raises(ValueError, match="gaze manifest must cover"):
        _rebuild(empirical, files=files)


def test_empirical_requires_exact_participant_count(empirical):
    files = list(empirical.files)

    index = next(
        i
        for i, record in enumerate(files)
        if record.role == "gaze" and record.participant_id == "P25"
    )

    old = files[index]

    files[index] = audit.VisusSourceFileRecord(
        path=old.path,
        sha256=old.sha256,
        bytes=old.bytes,
        role=old.role,
        stimulus_id=old.stimulus_id,
        participant_id="P01",
        participant_group=old.participant_group,
    )

    with pytest.raises(ValueError, match="exactly 25 participant"):
        _rebuild(empirical, files=files)


# ============================================================
# SPEC LOADER
# ============================================================


def test_load_spec_requires_object(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="one JSON object"):
        audit.load_visus_source_audit_spec(path)


def test_load_spec_requires_file_list(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text(
        json.dumps(
            {
                "dataset_name": "VISUS",
                "dataset_version": "v1",
                "source": "source",
                "source_revision": "rev",
                "license": "terms",
                "reuse_terms_source": "terms",
                "dataset_status": "template",
                "files": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="JSON list"):
        audit.load_visus_source_audit_spec(path)


def test_load_spec_defaults_when_resolution_fields_absent(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text(
        json.dumps(
            {
                "dataset_name": "VISUS",
                "dataset_version": "v1",
                "source": "source",
                "source_revision": "rev",
                "license": "terms",
                "reuse_terms_source": "terms",
                "dataset_status": "template",
                "files": [],
            }
        ),
        encoding="utf-8",
    )

    spec = audit.load_visus_source_audit_spec(path)

    assert spec.published_video_resolution_px == (1920, 1080)
    assert spec.published_display_resolution_px == (1920, 1200)


def test_load_spec_converts_resolutions_and_records(tmp_path):
    path = tmp_path / "spec.json"

    path.write_text(
        json.dumps(
            {
                "dataset_name": "VISUS",
                "dataset_version": "v1",
                "source": "source",
                "source_revision": "rev",
                "license": "terms",
                "reuse_terms_source": "terms",
                "dataset_status": "template",
                "published_video_resolution_px": [640, 480],
                "published_display_resolution_px": [800, 600],
                "files": [
                    {
                        "path": "misc/file.bin",
                        "sha256": "a" * 64,
                        "bytes": 1,
                        "role": "other",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    spec = audit.load_visus_source_audit_spec(path)

    assert spec.published_video_resolution_px == (640, 480)
    assert spec.published_display_resolution_px == (800, 600)
    assert len(spec.files) == 1


# ============================================================
# INVENTORY
# ============================================================


def test_inventory_rejects_missing_manifest_file(tmp_path):
    root = tmp_path / "case"
    spec = _fixture(root)

    missing = root / spec.files[0].path
    missing.unlink()

    with pytest.raises(BenchmarkIntegrityError, match="exact audited manifest"):
        audit._inventory(root, spec)


def test_inventory_rejects_byte_size_drift(tmp_path):
    root = tmp_path / "case"
    spec = _fixture(root)

    target = root / spec.files[0].path
    target.write_bytes(target.read_bytes() + b"x")

    with pytest.raises(BenchmarkIntegrityError, match="byte-size mismatch"):
        audit._inventory(root, spec)


def test_inventory_rejects_same_size_sha_drift(tmp_path):
    root = tmp_path / "case"
    spec = _fixture(root)

    target = root / spec.files[0].path
    payload = bytearray(target.read_bytes())

    payload[0] = ord("X") if payload[0] != ord("X") else ord("Y")

    target.write_bytes(bytes(payload))

    with pytest.raises(BenchmarkIntegrityError, match="SHA-256 mismatch"):
        audit._inventory(root, spec)


# ============================================================
# STREAM SUMMARY
# ============================================================


def test_annotation_stream_summary_empty():
    summary, minimum = audit._annotation_stream_summary([])
    assert summary == {}
    assert minimum == 0


def test_streams_by_stimulus_skips_nonannotations():
    records = [
        _record(
            path="misc/file.bin",
            role="other",
        ),
        _record(
            path="aoi/S01.xml",
            role="aoi_annotation",
            stimulus_id="S01",
            annotation_stream_id="curated",
        ),
    ]

    observed = audit._streams_by_stimulus(records)

    assert observed == {"S01": {"curated"}}


# ============================================================
# AUDIT RUNNER GUARDS
# ============================================================


def test_audit_runner_type_guard(tmp_path):
    with pytest.raises(TypeError, match="VisusSourceAuditSpec"):
        audit.audit_visus_source(
            tmp_path,
            object(),
        )


def test_audit_runner_requires_existing_directory(tmp_path):
    spec = _fixture(tmp_path / "source")

    with pytest.raises(FileNotFoundError, match="does not exist"):
        audit.audit_visus_source(
            tmp_path / "missing",
            spec,
        )


def test_audit_runner_handles_other_role_without_identity(tmp_path):
    root = tmp_path / "case"
    spec = _fixture(root)

    path = root / "misc" / "README.bin"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"x")

    other = audit.VisusSourceFileRecord(
        path="misc/README.bin",
        sha256=audit._sha256(path),
        bytes=1,
        role="other",
    )

    spec = _rebuild(
        spec,
        files=[
            *spec.files,
            other,
        ],
    )

    run = audit.audit_visus_source(
        root,
        spec,
    )

    assert run.report["inventory"]["role_counts"]["other"] == 1
    assert run.report["identity"]["stimulus_count"] == 11
