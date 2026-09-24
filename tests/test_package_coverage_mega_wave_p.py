from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.hollywood2_audit as audit
import gazeforge.hollywood2_token_portability_v3_evidence as v3
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.schema import GazeFrame

V3_EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-source-token-numeric-portability-evidence-v3.json"
)


# ============================================================
# HOLLYWOOD2 AUDIT FIXTURES
# ============================================================


def _file_record(
    *,
    path="test/a.arff",
    sha256="a" * 64,
    bytes_=10,
    participant="P01",
    trial="T01",
):
    return audit.Hollywood2SourceFileRecord(
        path=path,
        sha256=sha256,
        bytes=bytes_,
        participant_id=participant,
        trial_id=trial,
    )


def _template_spec(**changes):
    values = {
        "dataset_name": "Hollywood2EM",
        "dataset_version": "test",
        "source": "https://example.invalid/source",
        "source_revision": "snapshot-1",
        "license": "Research use",
        "reuse_terms_source": ("https://example.invalid/terms"),
    }

    values.update(changes)

    return audit.Hollywood2SourceAuditSpec(**values)


def _empirical_spec(
    *,
    files=None,
    **changes,
):
    if files is None:
        files = [_file_record()]

    values = {
        "dataset_name": "Hollywood2EM",
        "dataset_version": "test",
        "source": "https://example.invalid/source",
        "source_revision": "snapshot-1",
        "license": "Research use",
        "reuse_terms_source": ("https://example.invalid/terms"),
        "dataset_status": "empirical",
        "reuse_terms_verified": True,
        "analysis_use_permitted": True,
        "redistribution_status": "restricted",
        "coordinate_unit": "pixels",
        "coordinate_unit_verified": True,
        "coordinate_verification_basis": ("Verified fixture pixels."),
        "participant_identity_mapping_verified": True,
        "participant_identity_mapping_basis": ("Verified fixture mapping."),
        "files": files,
    }

    values.update(changes)

    return audit.Hollywood2SourceAuditSpec(**values)


def _gaze_frame(
    *,
    x=(10.0, 20.0),
    order=(0, 1),
):
    frame = (
        pd.DataFrame(
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
                    2.0,
                ],
                "x_px": list(x),
                "y_px": [
                    30.0,
                    40.0,
                ],
                "validity": [
                    True,
                    True,
                ],
                "confidence": [
                    1.0,
                    0.9,
                ],
                "source_file": [
                    "test/a.arff",
                    "test/a.arff",
                ],
            }
        )
        .iloc[list(order)]
        .reset_index(drop=True)
    )

    return GazeFrame(
        data=frame,
        sampling_rate_hz=500.0,
        metadata={
            "annotator": "final",
        },
    )


def _write_source(
    root: Path,
    relative: str,
    payload: bytes,
):
    data_root = root / "ground_truth"

    path = data_root.joinpath(*Path(relative).parts)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_bytes(payload)

    return path


def _record_for_bytes(
    relative: str,
    payload: bytes,
    *,
    participant="P01",
    trial="T01",
):
    return audit.Hollywood2SourceFileRecord(
        path=relative,
        sha256=hashlib.sha256(payload).hexdigest(),
        bytes=len(payload),
        participant_id=participant,
        trial_id=trial,
    )


# ============================================================
# SOURCE-FILE RECORD VALIDATION
# ============================================================


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/absolute.arff",
        "../escape.arff",
        "a/../escape.arff",
    ],
)
def test_audit_record_path_safety(path):
    with pytest.raises(
        ValueError,
        match="safe relative POSIX paths",
    ):
        _file_record(path=path)


def test_audit_record_requires_arff():
    with pytest.raises(
        ValueError,
        match="must reference .arff",
    ):
        _file_record(path="test/a.csv")


def test_audit_record_accepts_uppercase_arff():
    record = _file_record(path="test/a.ARFF")

    assert record.path == "test/a.ARFF"


@pytest.mark.parametrize(
    "sha",
    [
        "",
        "a" * 63,
        "g" * 64,
        "A" * 63,
    ],
)
def test_audit_record_sha(sha):
    with pytest.raises(
        ValueError,
        match="64 hex",
    ):
        _file_record(sha256=sha)


def test_audit_record_sha_normalized():
    record = _file_record(sha256="A" * 64)

    assert record.sha256 == ("a" * 64)


@pytest.mark.parametrize(
    "size",
    [
        0,
        -1,
    ],
)
def test_audit_record_size(size):
    with pytest.raises(
        ValueError,
        match="byte size must be positive",
    ):
        _file_record(bytes_=size)


@pytest.mark.parametrize(
    "field",
    [
        "participant",
        "trial",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "__unresolved__",
        "unknown",
        "none",
        "nan",
    ],
)
def test_audit_record_identity(
    field,
    value,
):
    kwargs = {
        field: value,
    }

    with pytest.raises(
        ValueError,
        match="audited resolved identity",
    ):
        _file_record(**kwargs)


def test_audit_record_identity_stripped():
    record = _file_record(
        participant=" P01 ",
        trial=" T01 ",
    )

    assert record.participant_id == "P01"
    assert record.trial_id == "T01"


def test_audit_record_to_from_dict():
    record = _file_record()

    encoded = record.to_dict()

    restored = audit.Hollywood2SourceFileRecord.from_dict(encoded)

    assert restored.to_dict() == encoded


# ============================================================
# SOURCE-AUDIT SPEC CONTRACT
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
def test_audit_spec_required_strings(
    field,
):
    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        _template_spec(**{field: " "})


def test_audit_spec_dataset_identity():
    with pytest.raises(
        ValueError,
        match="must be 'Hollywood2EM'",
    ):
        _template_spec(dataset_name="Other")


@pytest.mark.parametrize(
    "status",
    [
        "",
        "verified",
        "pending",
    ],
)
def test_audit_spec_dataset_status(status):
    with pytest.raises(
        ValueError,
        match="template.*empirical",
    ):
        _template_spec(dataset_status=status)


def test_audit_spec_redistribution_normalized():
    spec = _template_spec(redistribution_status=(" Restricted "))

    assert spec.redistribution_status == "restricted"


def test_audit_spec_redistribution_invalid():
    with pytest.raises(
        ValueError,
        match="redistribution_status",
    ):
        _template_spec(redistribution_status="yes")


@pytest.mark.parametrize(
    "rate",
    [
        0,
        -1,
        np.nan,
        np.inf,
    ],
)
def test_audit_spec_sampling_rate(rate):
    with pytest.raises(
        ValueError,
        match="finite and positive",
    ):
        _template_spec(expected_sampling_rate_hz=rate)


@pytest.mark.parametrize(
    "value",
    [
        -0.1,
        1.0,
        2.0,
        np.nan,
    ],
)
def test_audit_spec_sampling_tolerance(
    value,
):
    with pytest.raises(
        ValueError,
        match=r"\[0, 1\)",
    ):
        _template_spec(sampling_rate_tolerance_fraction=(value))


def test_audit_spec_coordinate_unit():
    with pytest.raises(
        ValueError,
        match="verified pixels",
    ):
        _template_spec(coordinate_unit="degrees")


@pytest.mark.parametrize(
    "columns",
    [
        (),
        ("handlabeller_1",),
        ("handlabeller_final",),
        (
            "handlabeller_1",
            "handlabeller_final",
            "extra",
        ),
    ],
)
def test_audit_spec_annotation_columns(
    columns,
):
    with pytest.raises(
        ValueError,
        match="required_annotation_columns",
    ):
        _template_spec(required_annotation_columns=(columns))


def test_audit_spec_annotation_order_allowed():
    spec = _template_spec(
        required_annotation_columns=(
            " handlabeller_final ",
            " handlabeller_1 ",
        )
    )

    assert set(spec.required_annotation_columns) == {
        "handlabeller_1",
        "handlabeller_final",
    }


def test_audit_spec_converts_file_mapping():
    spec = _template_spec(files=[_file_record().to_dict()])

    assert isinstance(
        spec.files[0],
        audit.Hollywood2SourceFileRecord,
    )


def test_audit_spec_duplicate_path():
    first = _file_record(
        participant="P01",
        trial="T01",
    )

    second = _file_record(
        participant="P02",
        trial="T02",
    )

    with pytest.raises(
        ValueError,
        match="paths must be unique",
    ):
        _template_spec(
            files=[
                first,
                second,
            ]
        )


def test_audit_spec_duplicate_identity():
    first = _file_record(
        path="test/a.arff",
        participant="P01",
        trial="T01",
    )

    second = _file_record(
        path="test/b.arff",
        participant="P01",
        trial="T01",
    )

    with pytest.raises(
        ValueError,
        match="identities must be unique",
    ):
        _template_spec(
            files=[
                first,
                second,
            ]
        )


def test_audit_spec_notes_stringified():
    spec = _template_spec(
        notes=[
            "a",
            2,
            None,
        ]
    )

    assert spec.notes == [
        "a",
        "2",
        "None",
    ]


def test_audit_empirical_requires_manifest():
    with pytest.raises(
        ValueError,
        match="non-empty file manifest",
    ):
        _empirical_spec(files=[])


def test_audit_empirical_requires_reuse():
    with pytest.raises(
        ValueError,
        match="verified reuse terms",
    ):
        _empirical_spec(reuse_terms_verified=False)


def test_audit_empirical_requires_analysis_permission():
    with pytest.raises(
        ValueError,
        match="permission for analysis use",
    ):
        _empirical_spec(analysis_use_permitted=False)


@pytest.mark.parametrize(
    ("verified", "basis"),
    [
        (
            False,
            "documented",
        ),
        (
            True,
            "",
        ),
        (
            True,
            " ",
        ),
    ],
)
def test_audit_empirical_coordinate_basis(
    verified,
    basis,
):
    with pytest.raises(
        ValueError,
        match="coordinate-unit",
    ):
        _empirical_spec(
            coordinate_unit_verified=verified,
            coordinate_verification_basis=basis,
        )


@pytest.mark.parametrize(
    ("verified", "basis"),
    [
        (
            False,
            "documented",
        ),
        (
            True,
            "",
        ),
        (
            True,
            " ",
        ),
    ],
)
def test_audit_empirical_participant_basis(
    verified,
    basis,
):
    with pytest.raises(
        ValueError,
        match="participant-identity",
    ):
        _empirical_spec(
            participant_identity_mapping_verified=(verified),
            participant_identity_mapping_basis=(basis),
        )


def test_audit_spec_to_dict():
    spec = _template_spec(
        files=[_file_record()],
    )

    payload = spec.to_dict()

    assert isinstance(
        payload["required_annotation_columns"],
        list,
    )

    assert isinstance(
        payload["files"],
        list,
    )


def test_audit_spec_from_dict():
    payload = _template_spec(
        files=[_file_record()],
        notes=["note"],
    ).to_dict()

    restored = audit.Hollywood2SourceAuditSpec.from_dict(payload)

    assert restored.to_dict() == payload


# ============================================================
# SPEC LOADER + DATA ROOT
# ============================================================


def test_audit_load_spec_valid(
    tmp_path,
):
    payload = _template_spec().to_dict()

    path = tmp_path / "spec.json"

    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    loaded = audit.load_hollywood2_source_audit_spec(path)

    assert loaded.dataset_name == "Hollywood2EM"


def test_audit_load_spec_nonobject(
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
        audit.load_hollywood2_source_audit_spec(path)


def test_audit_data_root_nested(
    tmp_path,
):
    ground = tmp_path / "ground_truth"
    ground.mkdir()

    assert audit._data_root(tmp_path) == ground


def test_audit_data_root_direct(
    tmp_path,
):
    assert audit._data_root(tmp_path) == tmp_path


# ============================================================
# INVENTORY VERIFICATION
# ============================================================


def test_audit_inventory_exact(
    tmp_path,
):
    payload = b"@RELATION x\n"

    _write_source(
        tmp_path,
        "test/a.arff",
        payload,
    )

    spec = _empirical_spec(
        files=[
            _record_for_bytes(
                "test/a.arff",
                payload,
            )
        ]
    )

    report = audit._verify_inventory(
        tmp_path,
        spec,
    )

    assert report["file_count"] == 1

    assert report["exact_inventory_match"] is True

    assert len(report["source_manifest_fingerprint_sha256"]) == 64


def test_audit_inventory_missing(
    tmp_path,
):
    ground = tmp_path / "ground_truth"
    ground.mkdir()

    payload = b"x"

    spec = _empirical_spec(
        files=[
            _record_for_bytes(
                "test/a.arff",
                payload,
            )
        ]
    )

    with pytest.raises(
        SchemaError,
        match="inventory",
    ):
        audit._verify_inventory(
            tmp_path,
            spec,
        )


def test_audit_inventory_extra(
    tmp_path,
):
    payload = b"x"

    _write_source(
        tmp_path,
        "test/a.arff",
        payload,
    )

    _write_source(
        tmp_path,
        "test/extra.arff",
        b"extra",
    )

    spec = _empirical_spec(
        files=[
            _record_for_bytes(
                "test/a.arff",
                payload,
            )
        ]
    )

    with pytest.raises(
        SchemaError,
        match="inventory",
    ):
        audit._verify_inventory(
            tmp_path,
            spec,
        )


def test_audit_inventory_byte_size(
    tmp_path,
):
    payload = b"abc"

    _write_source(
        tmp_path,
        "test/a.arff",
        payload,
    )

    record = _record_for_bytes(
        "test/a.arff",
        payload,
    )

    record.bytes += 1

    spec = _empirical_spec(files=[record])

    with pytest.raises(
        SchemaError,
        match="byte-size mismatch",
    ):
        audit._verify_inventory(
            tmp_path,
            spec,
        )


def test_audit_inventory_sha(
    tmp_path,
):
    payload = b"abc"

    _write_source(
        tmp_path,
        "test/a.arff",
        payload,
    )

    record = _record_for_bytes(
        "test/a.arff",
        payload,
    )

    record.sha256 = "0" * 64

    spec = _empirical_spec(files=[record])

    with pytest.raises(
        SchemaError,
        match="SHA-256 mismatch",
    ):
        audit._verify_inventory(
            tmp_path,
            spec,
        )


# ============================================================
# IDENTITY PARSER
# ============================================================


def test_audit_identity_parser_valid():
    spec = _template_spec(files=[_file_record()])

    parser = audit._identity_parser(spec)

    assert parser(Path("test/a.arff")) == (
        "P01",
        "T01",
    )


def test_audit_identity_parser_missing():
    spec = _template_spec(files=[_file_record()])

    parser = audit._identity_parser(spec)

    with pytest.raises(
        SchemaError,
        match="has no entry",
    ):
        parser(Path("test/b.arff"))


# ============================================================
# ANNOTATION STREAM IDENTITY
# ============================================================


def test_audit_stream_identity_sort_safe():
    left = _gaze_frame(order=(0, 1))

    right = _gaze_frame(order=(1, 0))

    audit._verify_annotation_stream_identity(
        left,
        right,
    )


def test_audit_stream_identity_drift():
    left = _gaze_frame()

    right = _gaze_frame(x=(10.0, 99.0))

    with pytest.raises(
        SchemaError,
        match="identical gaze samples",
    ):
        audit._verify_annotation_stream_identity(
            left,
            right,
        )


# ============================================================
# AUDIT METADATA STAMP
# ============================================================


def test_audit_metadata_stamp():
    gaze = _gaze_frame()

    spec = _empirical_spec()

    stamped = audit._stamp_audit_metadata(
        gaze,
        spec=spec,
        report_fingerprint_sha256=("a" * 64),
        spec_fingerprint_sha256=("b" * 64),
        manifest_fingerprint_sha256=("c" * 64),
    )

    assert stamped is not gaze

    assert stamped.metadata["source_audit_status"] == "verified"

    assert stamped.metadata["source_revision"] == "snapshot-1"

    assert stamped.metadata["analysis_use_permitted"] is True

    assert stamped.metadata["redistribution_status"] == "restricted"


# ============================================================
# AUDIT ENTRY GUARDS
# ============================================================


def test_audit_source_spec_type(
    tmp_path,
):
    with pytest.raises(
        TypeError,
        match="Hollywood2SourceAuditSpec",
    ):
        audit.audit_hollywood2_source(
            tmp_path,
            {},
        )


def test_audit_source_template_refused(
    tmp_path,
):
    with pytest.raises(
        SchemaError,
        match="Template",
    ):
        audit.audit_hollywood2_source(
            tmp_path,
            _template_spec(),
        )


def test_audit_source_root_missing(
    tmp_path,
):
    missing = tmp_path / "missing"

    with pytest.raises(
        FileNotFoundError,
    ):
        audit.audit_hollywood2_source(
            missing,
            _empirical_spec(),
        )


# ============================================================
# AUDITED LOADER ALIASES WITHOUT SOURCE EXECUTION
# ============================================================


@pytest.mark.parametrize(
    "annotator",
    [
        "final",
        "expert",
        " FINAL ",
        "Expert",
    ],
)
def test_audit_loader_final_alias(
    monkeypatch,
    annotator,
):
    final = _gaze_frame()
    student = _gaze_frame()

    monkeypatch.setattr(
        audit,
        "audit_hollywood2_source",
        lambda root, spec: SimpleNamespace(
            final_annotations=final,
            student_annotations=student,
        ),
    )

    result = audit.load_audited_hollywood2_directory(
        "ignored",
        _empirical_spec(),
        annotator=annotator,
    )

    assert result is final


@pytest.mark.parametrize(
    "annotator",
    [
        "student",
        "novice",
        " STUDENT ",
        "Novice",
    ],
)
def test_audit_loader_student_alias(
    monkeypatch,
    annotator,
):
    final = _gaze_frame()
    student = _gaze_frame()

    monkeypatch.setattr(
        audit,
        "audit_hollywood2_source",
        lambda root, spec: SimpleNamespace(
            final_annotations=final,
            student_annotations=student,
        ),
    )

    result = audit.load_audited_hollywood2_directory(
        "ignored",
        _empirical_spec(),
        annotator=annotator,
    )

    assert result is student


def test_audit_loader_bad_alias(
    monkeypatch,
):
    monkeypatch.setattr(
        audit,
        "audit_hollywood2_source",
        lambda root, spec: SimpleNamespace(
            final_annotations=_gaze_frame(),
            student_annotations=_gaze_frame(),
        ),
    )

    with pytest.raises(
        ValueError,
        match="annotator",
    ):
        audit.load_audited_hollywood2_directory(
            "ignored",
            _empirical_spec(),
            annotator="other",
        )


# ============================================================
# V3 PORTABILITY HELPERS
# ============================================================


def _v3_record():
    return json.loads(V3_EVIDENCE.read_text(encoding="utf-8"))


def _allow_deep_v3_validation(
    monkeypatch,
):
    monkeypatch.setattr(
        v3,
        "portability_v3_evidence_fingerprint",
        lambda record: v3.PORTABILITY_V3_EVIDENCE_FINGERPRINT,
    )


def test_v3_fingerprint_ignores_stored():
    record = _v3_record()

    expected = v3.portability_v3_evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = "0" * 64

    assert v3.portability_v3_evidence_fingerprint(record) == expected


def test_v3_load_mapping_copy():
    record = _v3_record()

    loaded = v3._load_record(record)

    assert loaded == record
    assert loaded is not record


def test_v3_load_path():
    loaded = v3._load_record(V3_EVIDENCE)

    assert loaded["record_type"] == ("hollywood2-source-token-numeric-portability-evidence-v3")


def test_v3_contract_fields():
    contract = _v3_record()["migration"]["to_contract"]

    selected = v3._contract_fields(contract)

    assert set(selected) == {
        "method",
        "metric_float_decimal_places",
        "nonfinite_metric_floats_permitted",
        ("benchmark_model_protocol_numeric_values_rounded"),
    }


def test_v3_contract_fields_missing():
    contract = copy.deepcopy(_v3_record()["migration"]["to_contract"])

    contract.pop("method")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="contract metadata is incomplete",
    ):
        v3._contract_fields(contract)


# ============================================================
# V3 OUTER IMMUTABILITY GATES
# ============================================================


def test_v3_valid():
    record = v3.validate_hollywood2_source_token_portability_v3_evidence(V3_EVIDENCE)

    assert record["evidence_fingerprint_sha256"] == v3.PORTABILITY_V3_EVIDENCE_FINGERPRINT


def test_v3_record_type():
    record = _v3_record()
    record["record_type"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record type",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


def test_v3_status():
    record = _v3_record()
    record["status"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not verified",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


def test_v3_unreviewed_fingerprint():
    record = _v3_record()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint is not reviewed",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


def test_v3_content_drift():
    record = _v3_record()
    record["extra"] = "drift"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="content drifted",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


# ============================================================
# V3 MIGRATION CONTRACTS — DEEP BRANCH ISOLATION
# ============================================================


def test_v3_migration_missing(
    monkeypatch,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()
    record["migration"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="migration metadata is missing",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "from_contract",
        "to_contract",
    ],
)
def test_v3_contract_mapping_missing(
    monkeypatch,
    field,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    record["migration"][field] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="portability contracts are missing",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


def test_v3_before_contract_incomplete(
    monkeypatch,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    record["migration"]["from_contract"].pop("method")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="contract metadata is incomplete",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


def test_v3_after_contract_incomplete(
    monkeypatch,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    record["migration"]["to_contract"].pop("method")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="contract metadata is incomplete",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


def test_v3_before_contract_drift(
    monkeypatch,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    record["migration"]["from_contract"]["metric_float_decimal_places"] += 1

    with pytest.raises(
        BenchmarkIntegrityError,
        match="v2 contract drifted",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


def test_v3_after_contract_drift(
    monkeypatch,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    record["migration"]["to_contract"]["metric_float_decimal_places"] -= 1

    with pytest.raises(
        BenchmarkIntegrityError,
        match="v3 contract drifted",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


@pytest.mark.parametrize(
    (
        "side",
        "field",
        "message",
    ),
    [
        (
            "from_contract",
            ("canonical_source_report_fingerprint_sha256"),
            "v2 report identity drifted",
        ),
        (
            "from_contract",
            ("canonical_source_report_file_sha256"),
            "v2 report bytes drifted",
        ),
        (
            "from_contract",
            ("portability_evidence_fingerprint_sha256"),
            "v2 evidence identity drifted",
        ),
        (
            "to_contract",
            ("canonical_source_report_fingerprint_sha256"),
            "v3 report identity drifted",
        ),
        (
            "to_contract",
            ("canonical_source_report_file_sha256"),
            "v3 report bytes drifted",
        ),
    ],
)
def test_v3_report_binding_drift(
    monkeypatch,
    side,
    field,
    message,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    record["migration"][side][field] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


# ============================================================
# V3 HISTORICAL EVIDENCE
# ============================================================


def test_v3_historical_missing(
    monkeypatch,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()
    record["historical_evidence"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="historical evidence is missing",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        ("v1_frozen_summary_report_fingerprint_sha256"),
        ("v1_canonical_report_fingerprint_sha256"),
        ("v1_canonical_report_file_sha256"),
        "v1_evidence_rewritten",
        "v2_evidence_rewritten",
    ],
)
def test_v3_historical_drift(
    monkeypatch,
    field,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    original = record["historical_evidence"][field]

    record["historical_evidence"][field] = (
        not original
        if isinstance(
            original,
            bool,
        )
        else "0" * 64
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="historical evidence drifted",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


# ============================================================
# V3 PORTABILITY OBSERVATIONS
# ============================================================


def test_v3_observations_missing(
    monkeypatch,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    record["portability_observations"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="observations are missing",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "v2_live_binding_failure",
        "full_report_diagnostic",
    ],
)
def test_v3_observation_detail_missing(
    monkeypatch,
    field,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    record["portability_observations"][field] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="observation details are missing",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "workflow_run_id",
        "head_sha",
        "frozen_python_runtime_verified",
        "pinned_source_commit_verified",
        "empirical_compute_succeeded",
        "v2_exact_binding_failed",
        ("observed_v2_report_fingerprint_sha256"),
    ],
)
def test_v3_failed_v2_lineage(
    monkeypatch,
    field,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    original = record["portability_observations"]["v2_live_binding_failure"][field]

    record["portability_observations"]["v2_live_binding_failure"][field] = (
        not original
        if isinstance(
            original,
            bool,
        )
        else (
            original + 1
            if isinstance(
                original,
                int,
            )
            else "drift"
        )
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="v2 live-binding failure lineage drifted",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "workflow_run_id",
        "job_id",
        "head_sha",
        "artifact_id",
        "artifact_zip_sha256",
        "diagnostic_report_file_sha256",
        "diagnostic_content_fingerprint_sha256",
        "live_raw_report_file_sha256",
        "live_raw_report_fingerprint_sha256",
        "max_abs_raw_metric_delta",
        "max_abs_raw_metric_delta_path",
        ("highest_precision_with_exact_full_report_match"),
        ("precision_14_exact_full_report_match"),
        ("precision_13_exact_full_report_match"),
        ("precision_13_report_fingerprint_sha256"),
        ("precision_13_report_file_sha256"),
    ],
)
def test_v3_diagnostic_lineage(
    monkeypatch,
    field,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    diagnostic = record["portability_observations"]["full_report_diagnostic"]

    original = diagnostic[field]

    if isinstance(
        original,
        bool,
    ):
        diagnostic[field] = not original
    elif isinstance(
        original,
        int,
    ):
        diagnostic[field] = original + 1
    elif isinstance(
        original,
        float,
    ):
        diagnostic[field] = original + 1.0
    else:
        diagnostic[field] = "drift"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="full-report diagnostic lineage drifted",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


# ============================================================
# V3 REVIEWED ARTIFACTS
# ============================================================


def test_v3_reviewed_missing(
    monkeypatch,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    record["reviewed_source_verified_artifacts"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="reviewed source artifacts are missing",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


@pytest.mark.parametrize(
    "label",
    [
        "pre_merge",
        "exact_merge",
    ],
)
def test_v3_reviewed_lineage(
    monkeypatch,
    label,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    record["reviewed_source_verified_artifacts"][label]["artifact_id"] += 1

    with pytest.raises(
        BenchmarkIntegrityError,
        match=f"reviewed {label} artifact lineage drifted",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


def test_v3_replay_flag(
    monkeypatch,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    record["reviewed_source_verified_artifacts"][
        "v3_recanonicalized_reviewed_reports_byte_identical"
    ] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="replay is not verified",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


def test_v3_cross_worker_flag(
    monkeypatch,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    record["reviewed_source_verified_artifacts"]["v3_cross_worker_full_report_match_verified"] = (
        False
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cross-worker full-report match is not verified",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


# ============================================================
# V3 SCIENTIFIC BOUNDARY
# ============================================================


def test_v3_boundary_missing(
    monkeypatch,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()
    record["scientific_boundary"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="scientific boundary is missing",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "scientific_metrics_reestimated",
        "model_configuration_changed",
        "fold_assignment_changed",
        "source_rows_changed",
        "participant_identity_mapping_verified",
        "participant_disjoint_validation_created",
        "participant_generalization_claim",
        "cross_dataset_validation_created",
        "rights_status_changed",
        "raw_source_redistributed_by_gazeforge",
        "v1_evidence_rewritten",
        "v2_evidence_rewritten",
    ],
)
def test_v3_boundary_promotion(
    monkeypatch,
    field,
):
    _allow_deep_v3_validation(monkeypatch)

    record = _v3_record()

    record["scientific_boundary"][field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot promote",
    ):
        v3.validate_hollywood2_source_token_portability_v3_evidence(record)
