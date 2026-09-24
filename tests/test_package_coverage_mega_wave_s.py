from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import gazeforge.gaze_in_wild_audit as audit
import gazeforge.source_candidate_authorization as auth
from gazeforge.exceptions import (
    BenchmarkIntegrityError,
    SchemaError,
)
from gazeforge.hollywood2_audit import (
    Hollywood2SourceAuditSpec,
    Hollywood2SourceFileRecord,
)
from gazeforge.schema import GazeFrame

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


# ============================================================
# SHARED FIXTURES
# ============================================================


def _process_record(
    *,
    path="process.mat",
    digest=SHA_B,
    bytes_=10,
):
    return audit.GazeInWildProcessFileRecord(
        path=path,
        sha256=digest,
        bytes=bytes_,
    )


def _label_record(
    *,
    path="label.mat",
    digest=SHA_A,
    bytes_=10,
    participant="P01",
    trial="T01",
    labeller=1,
    process_path="process.mat",
):
    return audit.GazeInWildLabelFileRecord(
        path=path,
        sha256=digest,
        bytes=bytes_,
        participant_id=participant,
        trial_id=trial,
        labeller_id=labeller,
        process_path=process_path,
    )


def _giw_template(
    *,
    coordinate_unit="pixels",
    label_files=None,
    process_files=None,
    **changes,
):
    if process_files is None:
        process_files = [_process_record()]

    if label_files is None:
        label_files = [_label_record()]

    values = {
        "dataset_name": "Gaze-in-the-Wild",
        "dataset_version": "reviewed-version",
        "source": "reviewed-source",
        "source_revision": "reviewed-revision",
        "license": "reviewed terms",
        "reuse_terms_source": "reviewed terms source",
        "dataset_status": "template",
        "participant_mapping_basis": ("reviewed participant mapping"),
        "coordinate_unit": coordinate_unit,
        "coordinate_verification_basis": ("reviewed coordinate evidence"),
        "label_files": label_files,
        "process_files": process_files,
        "notes": ["reviewed template"],
    }

    values.update(changes)

    return audit.GazeInWildSourceAuditSpec(**values)


def _giw_empirical(
    **changes,
):
    values = {
        "dataset_status": "empirical",
        "reuse_terms_verified": True,
        "analysis_use_permitted": True,
        "redistribution_status": "restricted",
        "participant_mapping_verified": True,
        "coordinate_unit_verified": True,
    }

    values.update(changes)

    return _giw_template(**values)


def _hollywood_template():
    return Hollywood2SourceAuditSpec(
        dataset_name="Hollywood2EM",
        dataset_version="reviewed-version",
        source="reviewed-source",
        source_revision="reviewed-revision",
        license="reviewed terms",
        reuse_terms_source="reviewed terms source",
        dataset_status="template",
        coordinate_unit="pixels",
        coordinate_verification_basis=("reviewed coordinate evidence"),
        participant_identity_mapping_basis=("reviewed participant mapping"),
        files=[
            Hollywood2SourceFileRecord(
                path="P01_T01.arff",
                sha256=SHA_A,
                bytes=10,
                participant_id="P01",
                trial_id="T01",
            )
        ],
    )


def _authorization(
    spec,
    *,
    decision="authorized",
    pixel_kinematics_compatible=False,
    redistribution_status="restricted",
    **changes,
):
    dataset_key = (
        "hollywood2em"
        if isinstance(
            spec,
            Hollywood2SourceAuditSpec,
        )
        else "gaze-in-the-wild"
    )

    values = {
        "dataset_key": dataset_key,
        ("audit_template_fingerprint_sha256"): (auth.source_audit_template_fingerprint(spec)),
        "decision": decision,
        "reviewer": "reviewer",
        "reviewed_at": "2026-09-24",
        "source_authority_verified": True,
        "source_authority_evidence": ("source reviewed"),
        "reuse_terms_verified": True,
        "reuse_terms_evidence": ("reuse reviewed"),
        "analysis_use_permitted": True,
        "analysis_use_evidence": ("analysis reviewed"),
        "redistribution_status": (redistribution_status),
        "redistribution_evidence": ("redistribution reviewed"),
        "coordinate_unit_verified": True,
        ("coordinate_verification_evidence"): "coordinates reviewed",
        "participant_mapping_verified": True,
        "participant_mapping_evidence": ("mapping reviewed"),
        "sampling_contract_reviewed": True,
        "sampling_contract_evidence": ("sampling reviewed"),
        "annotation_contract_reviewed": True,
        "annotation_contract_evidence": ("annotation reviewed"),
        "pixel_kinematics_compatible": (pixel_kinematics_compatible),
        "authorization_basis": ("all gates independently reviewed"),
    }

    values.update(changes)

    return auth.CandidateSourceAuditAuthorization(**values)


def _gaze_frame(
    *,
    x=(1.0, 2.0),
    labeller=1,
    sampling_rate=120.0,
):
    return GazeFrame(
        data=pd.DataFrame(
            {
                "participant_id": [
                    "P01",
                    "P01",
                ],
                "trial_id": [
                    "T01",
                    "T01",
                ],
                "timestamp_ms": [
                    0.0,
                    10.0,
                ],
                "x_px": list(x),
                "y_px": [
                    3.0,
                    4.0,
                ],
                "validity": [
                    True,
                    True,
                ],
                "confidence": [
                    1.0,
                    0.9,
                ],
            }
        ),
        sampling_rate_hz=sampling_rate,
        metadata={
            "labeller_id": labeller,
        },
    )


# ============================================================
# GIW PATH / SHA / IDENTITY HELPERS
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/absolute.mat",
        "../escape.mat",
        "x/../escape.mat",
    ],
)
def test_audit_safe_mat_path_rejects(
    value,
):
    with pytest.raises(
        ValueError,
        match="safe relative POSIX path",
    ):
        audit._safe_mat_path(
            value,
            field_name="fixture",
        )


def test_audit_safe_mat_requires_mat():
    with pytest.raises(
        ValueError,
        match="must reference a .mat",
    ):
        audit._safe_mat_path(
            "x.csv",
            field_name="fixture",
        )


def test_audit_safe_mat_normalizes():
    assert (
        audit._safe_mat_path(
            "a/b.MAT",
            field_name="fixture",
        )
        == "a/b.MAT"
    )


@pytest.mark.parametrize(
    "digest",
    [
        "",
        "a" * 63,
        "g" * 64,
    ],
)
def test_audit_sha_rejects(
    digest,
):
    with pytest.raises(
        ValueError,
        match="64 hexadecimal",
    ):
        audit._sha256(
            digest,
            field_name="fixture",
        )


def test_audit_sha_lowercases():
    assert (
        audit._sha256(
            "A" * 64,
            field_name="fixture",
        )
        == SHA_A
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "unknown",
        "none",
        "nan",
        "__unresolved__",
    ],
)
def test_audit_resolved_rejects(
    value,
):
    with pytest.raises(
        ValueError,
        match="audited resolved identity",
    ):
        audit._resolved(
            value,
            field_name="fixture",
        )


def test_audit_resolved_strips():
    assert (
        audit._resolved(
            " P01 ",
            field_name="fixture",
        )
        == "P01"
    )


# ============================================================
# GIW FILE RECORDS
# ============================================================


@pytest.mark.parametrize(
    "bytes_",
    [
        0,
        -1,
    ],
)
def test_process_record_bytes(
    bytes_,
):
    with pytest.raises(
        ValueError,
        match="positive",
    ):
        _process_record(bytes_=bytes_)


def test_process_record_roundtrip():
    record = _process_record()

    assert (
        audit.GazeInWildProcessFileRecord.from_dict(record.to_dict()).to_dict() == record.to_dict()
    )


@pytest.mark.parametrize(
    "bytes_",
    [
        0,
        -1,
    ],
)
def test_label_record_bytes(
    bytes_,
):
    with pytest.raises(
        ValueError,
        match="positive",
    ):
        _label_record(bytes_=bytes_)


@pytest.mark.parametrize(
    "labeller",
    [
        0,
        -1,
    ],
)
def test_label_record_labeller(
    labeller,
):
    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        _label_record(labeller=labeller)


def test_label_record_roundtrip():
    record = _label_record()

    restored = audit.GazeInWildLabelFileRecord.from_dict(record.to_dict())

    assert restored.to_dict() == record.to_dict()


# ============================================================
# GIW SPEC GENERAL VALIDATION
# ============================================================


@pytest.mark.parametrize(
    "field",
    [
        "dataset_name",
        "dataset_version",
        "source",
        "source_revision",
        "license",
        "reuse_terms_source",
    ],
)
def test_giw_spec_required_strings(
    field,
):
    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        _giw_template(**{field: " "})


def test_giw_spec_dataset_name():
    with pytest.raises(
        ValueError,
        match="must be 'Gaze-in-the-Wild'",
    ):
        _giw_template(dataset_name="Other")


@pytest.mark.parametrize(
    "value",
    [
        "",
        "verified",
        "pending",
    ],
)
def test_giw_spec_status(
    value,
):
    with pytest.raises(
        ValueError,
        match="template.*empirical",
    ):
        _giw_template(dataset_status=value)


@pytest.mark.parametrize(
    "value",
    [
        "yes",
        "no",
        "",
    ],
)
def test_giw_spec_redistribution(
    value,
):
    with pytest.raises(
        ValueError,
        match="redistribution_status",
    ):
        _giw_template(redistribution_status=value)


def test_giw_spec_redistribution_normalized():
    spec = _giw_template(redistribution_status=" Restricted ")

    assert spec.redistribution_status == "restricted"


@pytest.mark.parametrize(
    "value",
    [
        -0.1,
        1.1,
        np.nan,
        np.inf,
    ],
)
def test_giw_spec_confidence_threshold(
    value,
):
    with pytest.raises(
        ValueError,
        match=r"\[0, 1\]",
    ):
        _giw_template(confidence_threshold=value)


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        np.nan,
        np.inf,
    ],
)
def test_giw_spec_hardware_rate(
    value,
):
    with pytest.raises(
        ValueError,
        match="finite and positive",
    ):
        _giw_template(published_hardware_sampling_rate_hz=(value))


def test_giw_spec_coordinate_empty():
    with pytest.raises(
        ValueError,
        match="coordinate_unit must not be empty",
    ):
        _giw_template(coordinate_unit=" ")


def test_giw_spec_converts_mappings():
    spec = _giw_template(
        label_files=[_label_record().to_dict()],
        process_files=[_process_record().to_dict()],
        notes=[
            1,
            None,
        ],
    )

    assert isinstance(
        spec.label_files[0],
        audit.GazeInWildLabelFileRecord,
    )

    assert isinstance(
        spec.process_files[0],
        audit.GazeInWildProcessFileRecord,
    )

    assert spec.notes == [
        "1",
        "None",
    ]


def test_giw_duplicate_label_paths():
    process = _process_record()

    labels = [
        _label_record(
            participant="P01",
            trial="T01",
            labeller=1,
        ),
        _label_record(
            participant="P02",
            trial="T02",
            labeller=2,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="label manifest paths must be unique",
    ):
        _giw_template(
            label_files=labels,
            process_files=[process],
        )


def test_giw_duplicate_process_paths():
    with pytest.raises(
        ValueError,
        match="process manifest paths must be unique",
    ):
        _giw_template(
            process_files=[
                _process_record(),
                _process_record(),
            ]
        )


def test_giw_duplicate_identity():
    with pytest.raises(
        ValueError,
        match="identities must be unique",
    ):
        _giw_template(
            label_files=[
                _label_record(
                    path="a.mat",
                ),
                _label_record(
                    path="b.mat",
                    digest=SHA_C,
                ),
            ]
        )


def test_giw_missing_process_record():
    with pytest.raises(
        ValueError,
        match="missing",
    ):
        _giw_template(label_files=[_label_record(process_path="missing.mat")])


def test_giw_trial_process_mismatch():
    processes = [
        _process_record(
            path="a.mat",
        ),
        _process_record(
            path="b.mat",
            digest=SHA_C,
        ),
    ]

    labels = [
        _label_record(
            path="l1.mat",
            process_path="a.mat",
            labeller=1,
        ),
        _label_record(
            path="l2.mat",
            digest=SHA_C,
            process_path="b.mat",
            labeller=2,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="same ProcessData file",
    ):
        _giw_template(
            label_files=labels,
            process_files=processes,
        )


# ============================================================
# EMPIRICAL SPEC FAIL-CLOSED GATES
# ============================================================


def test_giw_empirical_requires_manifests():
    with pytest.raises(
        ValueError,
        match="non-empty label and process",
    ):
        _giw_empirical(
            label_files=[],
            process_files=[],
        )


def test_giw_empirical_requires_reuse():
    with pytest.raises(
        ValueError,
        match="verified reuse terms",
    ):
        _giw_empirical(reuse_terms_verified=False)


def test_giw_empirical_requires_analysis():
    with pytest.raises(
        ValueError,
        match="permission for analysis use",
    ):
        _giw_empirical(analysis_use_permitted=False)


@pytest.mark.parametrize(
    (
        "verified",
        "basis",
    ),
    [
        (
            False,
            "reviewed",
        ),
        (
            True,
            "",
        ),
    ],
)
def test_giw_empirical_requires_mapping(
    verified,
    basis,
):
    with pytest.raises(
        ValueError,
        match="participant/task identity mapping",
    ):
        _giw_empirical(
            participant_mapping_verified=verified,
            participant_mapping_basis=basis,
        )


@pytest.mark.parametrize(
    (
        "verified",
        "unit",
    ),
    [
        (
            False,
            "pixels",
        ),
        (
            True,
            "unverified",
        ),
    ],
)
def test_giw_empirical_requires_coordinate(
    verified,
    unit,
):
    with pytest.raises(
        ValueError,
        match="coordinate unit",
    ):
        _giw_empirical(
            coordinate_unit_verified=verified,
            coordinate_unit=unit,
        )


def test_giw_empirical_requires_coordinate_basis():
    with pytest.raises(
        ValueError,
        match="coordinate-unit verification basis",
    ):
        _giw_empirical(coordinate_verification_basis="")


def test_giw_pixel_kinematics_requires_pixels():
    with pytest.raises(
        ValueError,
        match="only be true",
    ):
        _giw_empirical(
            coordinate_unit="degrees",
            pixel_kinematics_compatible=True,
        )


def test_giw_spec_roundtrip():
    spec = _giw_template()

    restored = audit.GazeInWildSourceAuditSpec.from_dict(spec.to_dict())

    assert restored.to_dict() == spec.to_dict()


# ============================================================
# GIW SPEC LOADER
# ============================================================


def test_giw_loader_nonobject(
    tmp_path,
):
    path = tmp_path / "spec.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="one JSON object",
    ):
        audit.load_gaze_in_wild_source_audit_spec(path)


def test_giw_loader_valid(
    tmp_path,
):
    spec = _giw_template()

    path = tmp_path / "spec.json"

    path.write_text(
        json.dumps(spec.to_dict()),
        encoding="utf-8",
    )

    loaded = audit.load_gaze_in_wild_source_audit_spec(path)

    assert loaded.to_dict() == spec.to_dict()


# ============================================================
# INVENTORY
# ============================================================


def _write_inventory_file(
    root: Path,
    relative: str,
    payload: bytes,
):
    path = root.joinpath(*Path(relative).parts)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_bytes(payload)

    return path


def _process_from_bytes(
    relative,
    payload,
):
    return audit.GazeInWildProcessFileRecord(
        path=relative,
        sha256=hashlib.sha256(payload).hexdigest(),
        bytes=len(payload),
    )


def test_giw_inventory_exact(
    tmp_path,
):
    payload = b"fixture"

    _write_inventory_file(
        tmp_path,
        "a.mat",
        payload,
    )

    record = _process_from_bytes(
        "a.mat",
        payload,
    )

    result = audit._inventory(
        tmp_path,
        [record],
        label="process",
    )

    assert result["file_count"] == 1

    assert result["exact_inventory_match"] is True


def test_giw_inventory_missing_file(
    tmp_path,
):
    with pytest.raises(
        SchemaError,
        match="inventory",
    ):
        audit._inventory(
            tmp_path,
            [_process_record(path="missing.mat")],
            label="process",
        )


def test_giw_inventory_extra(
    tmp_path,
):
    _write_inventory_file(
        tmp_path,
        "extra.mat",
        b"x",
    )

    with pytest.raises(
        SchemaError,
        match="inventory",
    ):
        audit._inventory(
            tmp_path,
            [],
            label="process",
        )


def test_giw_inventory_size_mismatch(
    tmp_path,
):
    payload = b"abc"

    _write_inventory_file(
        tmp_path,
        "a.mat",
        payload,
    )

    record = _process_from_bytes(
        "a.mat",
        payload,
    )

    record.bytes += 1

    with pytest.raises(
        SchemaError,
        match="byte-size mismatch",
    ):
        audit._inventory(
            tmp_path,
            [record],
            label="process",
        )


def test_giw_inventory_sha_mismatch(
    tmp_path,
):
    payload = b"abc"

    _write_inventory_file(
        tmp_path,
        "a.mat",
        payload,
    )

    record = _process_from_bytes(
        "a.mat",
        payload,
    )

    record.sha256 = "0" * 64

    with pytest.raises(
        SchemaError,
        match="SHA-256 mismatch",
    ):
        audit._inventory(
            tmp_path,
            [record],
            label="process",
        )


# ============================================================
# GAZE IDENTITY + METADATA
# ============================================================


def test_giw_same_underlying_true():
    assert audit._same_underlying_gaze(
        _gaze_frame(),
        _gaze_frame(),
    )


def test_giw_same_underlying_false():
    assert not audit._same_underlying_gaze(
        _gaze_frame(),
        _gaze_frame(
            x=(
                1.0,
                99.0,
            )
        ),
    )


def test_giw_stamp_metadata():
    gaze = _gaze_frame()
    spec = _giw_empirical()

    stamped = audit._stamp_metadata(
        gaze,
        spec=spec,
        report_fingerprint="a" * 64,
        spec_fingerprint="b" * 64,
        label_manifest_fingerprint=("c" * 64),
        process_manifest_fingerprint=("d" * 64),
    )

    assert stamped is not gaze

    assert stamped.metadata["source_audit_status"] == "verified"

    assert stamped.metadata["analysis_use_permitted"] is True

    assert stamped.metadata["coordinate_source_unit"] == "pixels"


# ============================================================
# AUDIT EXECUTION GUARDS WITHOUT MATLAB LOADING
# ============================================================


def test_giw_audit_type(
    tmp_path,
):
    with pytest.raises(
        TypeError,
        match="GazeInWildSourceAuditSpec",
    ):
        audit.audit_gaze_in_wild_source(
            tmp_path,
            tmp_path,
            {},
        )


def test_giw_audit_template_refused(
    tmp_path,
):
    with pytest.raises(
        SchemaError,
        match="Template",
    ):
        audit.audit_gaze_in_wild_source(
            tmp_path,
            tmp_path,
            _giw_template(),
        )


def test_giw_audit_label_root_missing(
    tmp_path,
):
    process_root = tmp_path / "process"

    process_root.mkdir()

    with pytest.raises(
        FileNotFoundError,
    ):
        audit.audit_gaze_in_wild_source(
            tmp_path / "missing",
            process_root,
            _giw_empirical(),
        )


def test_giw_audit_process_root_missing(
    tmp_path,
):
    label_root = tmp_path / "labels"

    label_root.mkdir()

    with pytest.raises(
        FileNotFoundError,
    ):
        audit.audit_gaze_in_wild_source(
            label_root,
            tmp_path / "missing",
            _giw_empirical(),
        )


def test_giw_audit_labeller_mismatch(
    monkeypatch,
    tmp_path,
):
    label_root = tmp_path / "labels"

    process_root = tmp_path / "process"

    label_root.mkdir()
    process_root.mkdir()

    label_payload = b"label"
    process_payload = b"process"

    (label_root / "label.mat").write_bytes(label_payload)

    (process_root / "process.mat").write_bytes(process_payload)

    spec = _giw_empirical(
        label_files=[
            _label_record(
                digest=hashlib.sha256(label_payload).hexdigest(),
                bytes_=len(label_payload),
            )
        ],
        process_files=[
            _process_record(
                digest=hashlib.sha256(process_payload).hexdigest(),
                bytes_=len(process_payload),
            )
        ],
    )

    monkeypatch.setattr(
        audit,
        "load_gaze_in_wild_mat",
        lambda *args, **kwargs: _gaze_frame(labeller=99),
    )

    with pytest.raises(
        SchemaError,
        match="labeller mismatch",
    ):
        audit.audit_gaze_in_wild_source(
            label_root,
            process_root,
            spec,
        )


# ============================================================
# AUDIT RUN HELPERS
# ============================================================


def _synthetic_run():
    spec = _giw_empirical()

    first = audit.GazeInWildAuditedFile(
        record=_label_record(
            path="b.mat",
            participant="P02",
            trial="T02",
            labeller=2,
        ),
        gaze=_gaze_frame(labeller=2),
    )

    second = audit.GazeInWildAuditedFile(
        record=_label_record(
            path="a.mat",
            participant="P01",
            trial="T01",
            labeller=1,
        ),
        gaze=_gaze_frame(labeller=1),
    )

    report = {
        "sampling": {
            "files": [
                {
                    "path": "b.mat",
                    "participant_id": "P02",
                    "trial_id": "T02",
                    "labeller_id": 2,
                    "observed_sampling_rate_hz": 100.0,
                },
                {
                    "path": "a.mat",
                    "participant_id": "P01",
                    "trial_id": "T01",
                    "labeller_id": 1,
                    "observed_sampling_rate_hz": 120.0,
                },
            ]
        }
    }

    return audit.GazeInWildSourceAuditRun(
        spec=spec,
        files=[
            first,
            second,
        ],
        report=report,
    )


def test_giw_group_type():
    with pytest.raises(
        TypeError,
        match="GazeInWildSourceAuditRun",
    ):
        audit.audited_gaze_in_wild_files_by_labeller({})


def test_giw_group_sorted():
    grouped = audit.audited_gaze_in_wild_files_by_labeller(_synthetic_run())

    assert list(grouped) == [
        1,
        2,
    ]


def test_giw_sampling_table_type():
    with pytest.raises(
        TypeError,
        match="GazeInWildSourceAuditRun",
    ):
        audit.gaze_in_wild_sampling_rate_table({})


def test_giw_sampling_table_sorted():
    table = audit.gaze_in_wild_sampling_rate_table(_synthetic_run())

    assert table["participant_id"].tolist() == [
        "P01",
        "P02",
    ]


# ============================================================
# AUTHORIZATION CLASS CONTRACT
# ============================================================


@pytest.mark.parametrize(
    "dataset_key",
    [
        "",
        "other",
    ],
)
def test_auth_dataset_key(
    dataset_key,
):
    with pytest.raises(
        ValueError,
        match="Unsupported",
    ):
        auth.CandidateSourceAuditAuthorization(
            dataset_key=dataset_key,
            audit_template_fingerprint_sha256=(SHA_A),
        )


def test_auth_dataset_normalized():
    value = auth.CandidateSourceAuditAuthorization(
        dataset_key=" Hollywood2EM ",
        audit_template_fingerprint_sha256=(SHA_A.upper()),
    )

    assert value.dataset_key == "hollywood2em"

    assert value.audit_template_fingerprint_sha256 == SHA_A


@pytest.mark.parametrize(
    "digest",
    [
        "",
        "a" * 63,
        "g" * 64,
    ],
)
def test_auth_fingerprint(
    digest,
):
    with pytest.raises(
        ValueError,
        match="64 hexadecimal",
    ):
        auth.CandidateSourceAuditAuthorization(
            dataset_key="hollywood2em",
            audit_template_fingerprint_sha256=(digest),
        )


@pytest.mark.parametrize(
    "decision",
    [
        "",
        "approved",
        "yes",
    ],
)
def test_auth_decision(
    decision,
):
    with pytest.raises(
        ValueError,
        match="pending.*authorized.*denied",
    ):
        auth.CandidateSourceAuditAuthorization(
            dataset_key="hollywood2em",
            audit_template_fingerprint_sha256=(SHA_A),
            decision=decision,
        )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "allowed",
    ],
)
def test_auth_redistribution(
    value,
):
    with pytest.raises(
        ValueError,
        match="redistribution_status",
    ):
        auth.CandidateSourceAuditAuthorization(
            dataset_key="hollywood2em",
            audit_template_fingerprint_sha256=(SHA_A),
            redistribution_status=value,
        )


@pytest.mark.parametrize(
    "field",
    [
        "source_authority_verified",
        "reuse_terms_verified",
        "analysis_use_permitted",
        "coordinate_unit_verified",
        "participant_mapping_verified",
        "sampling_contract_reviewed",
        "annotation_contract_reviewed",
        "pixel_kinematics_compatible",
    ],
)
def test_auth_boolean_fields(
    field,
):
    with pytest.raises(
        ValueError,
        match="must be boolean",
    ):
        auth.CandidateSourceAuditAuthorization(
            dataset_key="gaze-in-the-wild",
            audit_template_fingerprint_sha256=(SHA_A),
            **{field: 1},
        )


def test_auth_notes_tuple():
    value = auth.CandidateSourceAuditAuthorization(
        dataset_key="hollywood2em",
        audit_template_fingerprint_sha256=(SHA_A),
        notes=[
            1,
            None,
        ],
    )

    assert value.notes == (
        "1",
        "None",
    )


def test_auth_hollywood_pixel_control():
    with pytest.raises(
        ValueError,
        match="only an authorization control",
    ):
        auth.CandidateSourceAuditAuthorization(
            dataset_key="hollywood2em",
            audit_template_fingerprint_sha256=(SHA_A),
            pixel_kinematics_compatible=True,
        )


@pytest.mark.parametrize(
    "field",
    [
        "reviewer",
        "reviewed_at",
        "authorization_basis",
    ],
)
def test_auth_denied_requires_review_fields(
    field,
):
    values = {
        "dataset_key": "hollywood2em",
        ("audit_template_fingerprint_sha256"): SHA_A,
        "decision": "denied",
        "reviewer": "reviewer",
        "reviewed_at": "2026-09-24",
        "authorization_basis": "basis",
    }

    values[field] = "REVIEW_REQUIRED"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="require reviewed",
    ):
        auth.CandidateSourceAuditAuthorization(**values)


# ============================================================
# AUTHORIZATION RECORD SERIALIZATION
# ============================================================


def test_auth_to_dict_boundary():
    value = auth.CandidateSourceAuditAuthorization(
        dataset_key="hollywood2em",
        audit_template_fingerprint_sha256=(SHA_A),
    )

    payload = value.to_dict()

    assert payload["record_type"] == ("candidate-source-audit-authorization-v1")

    assert payload["scientific_boundary"]["manual_authorization_required"] is True

    assert isinstance(
        payload["notes"],
        list,
    )


def test_auth_from_dict_record_type():
    payload = auth.CandidateSourceAuditAuthorization(
        dataset_key="hollywood2em",
        audit_template_fingerprint_sha256=(SHA_A),
    ).to_dict()

    payload["record_type"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record_type",
    ):
        auth.CandidateSourceAuditAuthorization.from_dict(payload)


def test_auth_from_dict_boundary():
    payload = auth.CandidateSourceAuditAuthorization(
        dataset_key="hollywood2em",
        audit_template_fingerprint_sha256=(SHA_A),
    ).to_dict()

    payload["scientific_boundary"]["empirical_evidence_created"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="manual gate",
    ):
        auth.CandidateSourceAuditAuthorization.from_dict(payload)


def test_auth_from_dict_notes():
    payload = auth.CandidateSourceAuditAuthorization(
        dataset_key="hollywood2em",
        audit_template_fingerprint_sha256=(SHA_A),
    ).to_dict()

    payload["notes"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="JSON list",
    ):
        auth.CandidateSourceAuditAuthorization.from_dict(payload)


def test_auth_from_dict_wraps_value_error():
    payload = auth.CandidateSourceAuditAuthorization(
        dataset_key="hollywood2em",
        audit_template_fingerprint_sha256=(SHA_A),
    ).to_dict()

    payload["dataset_key"] = "other"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record is invalid",
    ):
        auth.CandidateSourceAuditAuthorization.from_dict(payload)


# ============================================================
# AUTHORIZATION INTERNAL HELPERS
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "review_required",
        "unknown",
        "none",
        "nan",
    ],
)
def test_auth_resolved_text(
    value,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="require reviewed",
    ):
        auth._require_resolved_text(
            value,
            field_name="fixture",
        )


def test_auth_resolved_text_valid():
    assert (
        auth._require_resolved_text(
            " reviewed ",
            field_name="fixture",
        )
        == "reviewed"
    )


def test_auth_dataset_key_hollywood():
    assert auth._dataset_key(_hollywood_template()) == "hollywood2em"


def test_auth_dataset_key_giw():
    assert auth._dataset_key(_giw_template()) == "gaze-in-the-wild"


def test_auth_dataset_key_type():
    with pytest.raises(
        TypeError,
        match="Hollywood2SourceAuditSpec",
    ):
        auth._dataset_key({})


def test_auth_template_fingerprint():
    spec = _giw_template()

    assert auth.source_audit_template_fingerprint(spec) == auth.source_audit_template_fingerprint(
        spec
    )


# ============================================================
# AUTHORIZATION BUILD
# ============================================================


def test_auth_build_hollywood():
    spec = _hollywood_template()

    value = auth.build_candidate_source_audit_authorization(spec)

    assert value.dataset_key == "hollywood2em"

    assert value.decision == "pending"


def test_auth_build_giw():
    spec = _giw_template()

    value = auth.build_candidate_source_audit_authorization(spec)

    assert value.dataset_key == "gaze-in-the-wild"


def test_auth_build_refuses_empirical():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="dataset_status='template'",
    ):
        auth.build_candidate_source_audit_authorization(_giw_empirical())


# ============================================================
# AUTHORIZATION WRITER / LOADER
# ============================================================


def test_auth_writer_type(
    tmp_path,
):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    with pytest.raises(
        TypeError,
        match="CandidateSourceAuditAuthorization",
    ):
        auth.write_candidate_source_audit_authorization(
            {},
            tmp_path / "out.json",
            candidate_root=candidate,
        )


def test_auth_writer_inside_candidate(
    tmp_path,
):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    value = auth.build_candidate_source_audit_authorization(_hollywood_template())

    with pytest.raises(
        BenchmarkIntegrityError,
        match="outside the candidate source tree",
    ):
        auth.write_candidate_source_audit_authorization(
            value,
            candidate / "auth.json",
            candidate_root=candidate,
        )


def test_auth_writer_root_itself(
    tmp_path,
):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    value = auth.build_candidate_source_audit_authorization(_hollywood_template())

    with pytest.raises(
        BenchmarkIntegrityError,
        match="outside the candidate source tree",
    ):
        auth.write_candidate_source_audit_authorization(
            value,
            candidate,
            candidate_root=candidate,
        )


def test_auth_writer_exists(
    tmp_path,
):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    target = tmp_path / "auth.json"

    target.write_text(
        "{}",
        encoding="utf-8",
    )

    value = auth.build_candidate_source_audit_authorization(_hollywood_template())

    with pytest.raises(
        FileExistsError,
    ):
        auth.write_candidate_source_audit_authorization(
            value,
            target,
            candidate_root=candidate,
        )


def test_auth_writer_overwrite(
    tmp_path,
):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    target = tmp_path / "auth.json"

    target.write_text(
        "{}",
        encoding="utf-8",
    )

    value = auth.build_candidate_source_audit_authorization(_hollywood_template())

    written = auth.write_candidate_source_audit_authorization(
        value,
        target,
        candidate_root=candidate,
        overwrite=True,
    )

    assert written == target


def test_auth_loader_missing(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError,
    ):
        auth.load_candidate_source_audit_authorization(tmp_path / "missing.json")


def test_auth_loader_bad_json(
    tmp_path,
):
    path = tmp_path / "bad.json"

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        auth.load_candidate_source_audit_authorization(path)


def test_auth_loader_bad_utf8(
    tmp_path,
):
    path = tmp_path / "bad.json"

    path.write_bytes(b"\xff\xfe")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        auth.load_candidate_source_audit_authorization(path)


def test_auth_loader_nonobject(
    tmp_path,
):
    path = tmp_path / "bad.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        auth.load_candidate_source_audit_authorization(path)


def test_auth_loader_valid(
    tmp_path,
):
    value = auth.build_candidate_source_audit_authorization(_hollywood_template())

    path = tmp_path / "auth.json"

    path.write_text(
        json.dumps(value.to_dict()),
        encoding="utf-8",
    )

    loaded = auth.load_candidate_source_audit_authorization(path)

    assert loaded == value


# ============================================================
# AUTHORIZATION BINDING
# ============================================================


def test_auth_binding_requires_template():
    spec = _giw_empirical()

    value = _authorization(_giw_template())

    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-empirical template",
    ):
        auth._validate_authorization_binding(
            spec,
            value,
        )


def test_auth_binding_dataset_identity():
    spec = _giw_template()

    hollywood_auth = auth.CandidateSourceAuditAuthorization(
        dataset_key="hollywood2em",
        audit_template_fingerprint_sha256=(auth.source_audit_template_fingerprint(spec)),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="dataset identity",
    ):
        auth._validate_authorization_binding(
            spec,
            hollywood_auth,
        )


def test_auth_binding_fingerprint():
    spec = _giw_template()

    value = auth.CandidateSourceAuditAuthorization(
        dataset_key="gaze-in-the-wild",
        audit_template_fingerprint_sha256=(SHA_A),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exact audit-template fingerprint",
    ):
        auth._validate_authorization_binding(
            spec,
            value,
        )


def test_auth_binding_pixel_unit():
    spec = _giw_template(coordinate_unit="degrees")

    value = auth.CandidateSourceAuditAuthorization(
        dataset_key="gaze-in-the-wild",
        audit_template_fingerprint_sha256=(auth.source_audit_template_fingerprint(spec)),
        pixel_kinematics_compatible=True,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="verified pixel units",
    ):
        auth._validate_authorization_binding(
            spec,
            value,
        )


# ============================================================
# AUTHORIZATION MATERIALIZATION — SAFE HOLLYWOOD PATH
# ============================================================


def test_auth_materialize_type():
    spec = _hollywood_template()

    with pytest.raises(
        TypeError,
        match="CandidateSourceAuditAuthorization",
    ):
        auth.authorize_candidate_source_audit_template(
            spec,
            {},
        )


@pytest.mark.parametrize(
    "decision",
    [
        "pending",
        "denied",
    ],
)
def test_auth_materialize_requires_authorized(
    decision,
):
    spec = _hollywood_template()

    if decision == "pending":
        value = auth.build_candidate_source_audit_authorization(spec)
    else:
        value = auth.CandidateSourceAuditAuthorization(
            dataset_key="hollywood2em",
            audit_template_fingerprint_sha256=(auth.source_audit_template_fingerprint(spec)),
            decision="denied",
            reviewer="reviewer",
            reviewed_at="2026-09-24",
            authorization_basis="denied",
        )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="decision='authorized'",
    ):
        auth.authorize_candidate_source_audit_template(
            spec,
            value,
        )


def test_auth_materialize_hollywood():
    spec = _hollywood_template()

    empirical = auth.authorize_candidate_source_audit_template(
        spec,
        _authorization(spec),
    )

    assert empirical.dataset_status == "empirical"

    assert empirical.reuse_terms_verified

    assert empirical.analysis_use_permitted

    assert empirical.participant_identity_mapping_verified


# ============================================================
# AUTHORIZED SPEC WRITER
# ============================================================


def test_authorized_writer_type():
    with pytest.raises(
        TypeError,
    ):
        auth.write_authorized_source_audit_spec(
            {},
            "out.json",
            candidate_root="candidate",
        )


def test_authorized_writer_requires_empirical(
    tmp_path,
):
    candidate = tmp_path / "candidate"
    candidate.mkdir()

    with pytest.raises(
        BenchmarkIntegrityError,
        match="dataset_status='empirical'",
    ):
        auth.write_authorized_source_audit_spec(
            _hollywood_template(),
            tmp_path / "out.json",
            candidate_root=candidate,
        )


def test_authorized_writer_inside_tree(
    tmp_path,
):
    template = _hollywood_template()

    empirical = auth.authorize_candidate_source_audit_template(
        template,
        _authorization(template),
    )

    candidate = tmp_path / "candidate"
    candidate.mkdir()

    with pytest.raises(
        BenchmarkIntegrityError,
        match="outside the candidate source tree",
    ):
        auth.write_authorized_source_audit_spec(
            empirical,
            candidate / "spec.json",
            candidate_root=candidate,
        )


def test_authorized_writer_exists(
    tmp_path,
):
    template = _hollywood_template()

    empirical = auth.authorize_candidate_source_audit_template(
        template,
        _authorization(template),
    )

    candidate = tmp_path / "candidate"
    candidate.mkdir()

    target = tmp_path / "spec.json"

    target.write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
    ):
        auth.write_authorized_source_audit_spec(
            empirical,
            target,
            candidate_root=candidate,
        )


def test_authorized_writer_overwrite(
    tmp_path,
):
    template = _hollywood_template()

    empirical = auth.authorize_candidate_source_audit_template(
        template,
        _authorization(template),
    )

    candidate = tmp_path / "candidate"
    candidate.mkdir()

    target = tmp_path / "spec.json"

    target.write_text(
        "{}",
        encoding="utf-8",
    )

    written = auth.write_authorized_source_audit_spec(
        empirical,
        target,
        candidate_root=candidate,
        overwrite=True,
    )

    assert written == target

    payload = json.loads(target.read_text(encoding="utf-8"))

    assert payload["dataset_status"] == "empirical"
