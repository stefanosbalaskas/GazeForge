from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import gazeforge.evidence_status as status
import gazeforge.gaze_in_wild_recovery as recovery
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError

# ============================================================
# SHARED HELPERS
# ============================================================


def _write_json(
    path: Path,
    payload,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _git_blob_sha1(
    raw: bytes,
):
    return hashlib.sha1(
        (f"blob {len(raw)}\0").encode("ascii") + raw,
        usedforsecurity=False,
    ).hexdigest()


# ============================================================
# GIW RECOVERY FIXTURES
# ============================================================


def _candidate_tree(
    tmp_path: Path,
):
    root = tmp_path / "candidate"

    (root / "ProcessData").mkdir(parents=True)

    (root / "LabelData").mkdir(parents=True)

    (root / "ProcessData" / "PrIdx_1_TrIdx_1.mat").write_bytes(b"process-copy")

    (root / "LabelData" / "LabellerIdx_7_PrIdx_1_TrIdx_1.mat").write_bytes(b"label-copy")

    (root / "README").write_text(
        "unverified candidate\n",
        encoding="utf-8",
    )

    return root


def _review(
    root: Path,
    *,
    kind=("candidate_original_layout_unverified"),
):
    return recovery.build_gaze_in_wild_recovery_candidate_review(
        root,
        candidate_kind=kind,
        provenance_source=("synthetic recovery lead"),
        provenance_note=("Review-only candidate."),
    )


def _refingerprint_recovery(
    record,
):
    record["record_fingerprint_sha256"] = recovery.recovery_candidate_record_fingerprint(record)


# ============================================================
# GIW RECOVERY HASH + INVENTORY HELPERS
# ============================================================


def test_recovery_canonical_bytes():
    assert recovery._canonical_bytes(
        {
            "b": 2,
            "a": 1,
        }
    ) == recovery._canonical_bytes(
        {
            "a": 1,
            "b": 2,
        }
    )


def test_recovery_sha256_file(
    tmp_path,
):
    path = tmp_path / "x.bin"
    path.write_bytes(b"abc")

    assert recovery._sha256_file(path) == hashlib.sha256(b"abc").hexdigest()


def test_recovery_tree_fingerprint():
    files = [
        {
            "path": "a",
            "bytes": 1,
            "sha256": "a" * 64,
            "role": "unclassified",
        }
    ]

    assert (
        recovery._tree_fingerprint(files)
        == hashlib.sha256(recovery._canonical_bytes(files)).hexdigest()
    )


def test_recovery_record_fingerprint_ignores_stored():
    record = {
        "x": 1,
        "record_fingerprint_sha256": ("a" * 64),
    }

    first = recovery.recovery_candidate_record_fingerprint(record)

    record["record_fingerprint_sha256"] = "b" * 64

    assert recovery.recovery_candidate_record_fingerprint(record) == first


def test_recovery_check_root_missing(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="existing directory",
    ):
        recovery._check_root(tmp_path / "missing")


def test_recovery_check_root_file(
    tmp_path,
):
    path = tmp_path / "file"
    path.write_text(
        "x",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="existing directory",
    ):
        recovery._check_root(path)


def test_recovery_inventory_extensions(
    tmp_path,
):
    root = tmp_path / "candidate"
    root.mkdir()

    (root / "A.MAT").write_bytes(b"a")

    (root / "README").write_bytes(b"b")

    nested = root / "nested"
    nested.mkdir()

    files, extensions = recovery._inventory(root)

    assert [item["path"] for item in files] == [
        "A.MAT",
        "README",
    ]

    assert extensions == {
        ".mat": 1,
        "<none>": 1,
    }

    assert all(item["role"] == "unclassified" for item in files)


# ============================================================
# GIW BUILD CONTRACT
# ============================================================


@pytest.mark.parametrize(
    "kind",
    sorted(recovery._ALLOWED_CANDIDATE_KINDS),
)
def test_recovery_build_all_allowed_kinds(
    tmp_path,
    kind,
):
    root = _candidate_tree(tmp_path)

    record = _review(
        root,
        kind=kind,
    )

    assert record["candidate_kind"] == kind


def test_recovery_build_kind_normalized(
    tmp_path,
):
    root = _candidate_tree(tmp_path)

    record = recovery.build_gaze_in_wild_recovery_candidate_review(
        root,
        candidate_kind=(" UNKNOWN_RECOVERED_COPY "),
        provenance_source=" source ",
        provenance_note=" note ",
    )

    assert record["candidate_kind"] == "unknown_recovered_copy"

    assert record["provenance"]["source"] == "source"


@pytest.mark.parametrize(
    (
        "source",
        "note",
    ),
    [
        (
            "",
            "note",
        ),
        (
            "source",
            "",
        ),
        (
            " ",
            "note",
        ),
        (
            "source",
            " ",
        ),
    ],
)
def test_recovery_build_provenance_required(
    tmp_path,
    source,
    note,
):
    root = _candidate_tree(tmp_path)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="explicit provenance",
    ):
        recovery.build_gaze_in_wild_recovery_candidate_review(
            root,
            candidate_kind=("unknown_recovered_copy"),
            provenance_source=source,
            provenance_note=note,
        )


# ============================================================
# GIW LOAD
# ============================================================


def test_recovery_load_mapping_copy(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    loaded, path = recovery._load(record)

    assert loaded == record
    assert loaded is not record
    assert path is None


def test_recovery_load_json_path(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    path = tmp_path / "review.json"
    _write_json(
        path,
        record,
    )

    loaded, observed_path = recovery._load(path)

    assert loaded == record
    assert observed_path == path


def test_recovery_load_missing(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        recovery._load(tmp_path / "missing.json")


def test_recovery_load_bad_json(
    tmp_path,
):
    path = tmp_path / "bad.json"

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        recovery._load(path)


def test_recovery_load_nonobject(
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
        recovery._load(path)


# ============================================================
# GIW RECORD VALIDATOR — IDENTITY
# ============================================================


@pytest.mark.parametrize(
    (
        "field",
        "value",
        "message",
    ),
    [
        (
            "record_type",
            "bad",
            "record_type drifted",
        ),
        (
            "candidate_status",
            "verified",
            "remain quarantined",
        ),
        (
            "dataset",
            "Other",
            "dataset identity drifted",
        ),
        (
            "candidate_kind",
            "authoritative",
            "kind is invalid",
        ),
    ],
)
def test_recovery_identity_guards(
    tmp_path,
    field,
    value,
    message,
):
    record = _review(_candidate_tree(tmp_path))

    record[field] = value

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


@pytest.mark.parametrize(
    (
        "field",
        "value",
        "message",
    ),
    [
        (
            "source",
            "",
            "source is unresolved",
        ),
        (
            "note",
            " ",
            "note is unresolved",
        ),
        (
            "authority_status",
            "verified",
            "must remain unverified",
        ),
        (
            "rights_status",
            "resolved",
            "must remain unresolved",
        ),
    ],
)
def test_recovery_provenance_guards(
    tmp_path,
    field,
    value,
    message,
):
    record = _review(_candidate_tree(tmp_path))

    record["provenance"][field] = value

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_provenance_missing(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["provenance"] = None

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="provenance is missing",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


# ============================================================
# GIW INVENTORY VALIDATOR
# ============================================================


def test_recovery_inventory_missing(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["inventory"] = None

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="inventory is missing",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


@pytest.mark.parametrize(
    "files",
    [
        None,
        [],
    ],
)
def test_recovery_files_required(
    tmp_path,
    files,
):
    record = _review(_candidate_tree(tmp_path))

    record["inventory"]["files"] = files

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must contain files",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_file_entry_mapping(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["inventory"]["files"][0] = "bad"

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="entries must be mappings",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/absolute.mat",
        "../escape.mat",
        "x/../escape.mat",
    ],
)
def test_recovery_file_path(
    tmp_path,
    path,
):
    record = _review(_candidate_tree(tmp_path))

    record["inventory"]["files"][0]["path"] = path

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="path is unsafe",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


@pytest.mark.parametrize(
    "size",
    [
        -1,
        1.5,
        "1",
        None,
    ],
)
def test_recovery_file_size(
    tmp_path,
    size,
):
    record = _review(_candidate_tree(tmp_path))

    record["inventory"]["files"][0]["bytes"] = size

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="byte size is invalid",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


@pytest.mark.parametrize(
    "digest",
    [
        "",
        "a" * 63,
        "g" * 64,
        "A" * 64,
    ],
)
def test_recovery_file_sha(
    tmp_path,
    digest,
):
    record = _review(_candidate_tree(tmp_path))

    record["inventory"]["files"][0]["sha256"] = digest

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="SHA-256 is invalid",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_file_role(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["inventory"]["files"][0]["role"] = "process_data"

    record["inventory"]["tree_fingerprint_sha256"] = recovery._tree_fingerprint(
        [dict(item) for item in record["inventory"]["files"]]
    )

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="roles must remain unclassified",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_unsorted_paths(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["inventory"]["files"] = list(reversed(record["inventory"]["files"]))

    record["inventory"]["tree_fingerprint_sha256"] = recovery._tree_fingerprint(
        [dict(item) for item in record["inventory"]["files"]]
    )

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sorted and unique",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_duplicate_paths(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    duplicate = copy.deepcopy(record["inventory"]["files"][0])

    record["inventory"]["files"] = [
        duplicate,
        copy.deepcopy(duplicate),
    ]

    record["inventory"]["tree_fingerprint_sha256"] = recovery._tree_fingerprint(
        record["inventory"]["files"]
    )

    record["inventory"]["file_count"] = 2

    record["inventory"]["total_bytes"] = duplicate["bytes"] * 2

    suffix = Path(duplicate["path"]).suffix.lower() or "<none>"

    record["inventory"]["extension_counts"] = {suffix: 2}

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sorted and unique",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_file_count_drift(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["inventory"]["file_count"] += 1

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file count drifted",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_total_bytes_drift(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["inventory"]["total_bytes"] += 1

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="total byte count drifted",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_extension_drift(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["inventory"]["extension_counts"] = {".mat": 999}

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="extension inventory drifted",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_tree_fingerprint_drift(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["inventory"]["tree_fingerprint_sha256"] = "0" * 64

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="tree fingerprint drifted",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


# ============================================================
# GIW POLICY + FINAL RECORD GATES
# ============================================================


def test_recovery_policy_missing(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["interpretation_policy"] = None

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="policy is missing",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_policy_unclassified_gate(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["interpretation_policy"]["all_file_roles_are_unclassified"] = False

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must stay unclassified",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


@pytest.mark.parametrize(
    "field",
    [
        "filename_identity_inference_permitted",
        "matlab_schema_inference_permitted",
        "license_inference_permitted",
        ("candidate_can_materialize_empirical_audit_spec"),
    ],
)
def test_recovery_policy_false_gates(
    tmp_path,
    field,
):
    record = _review(_candidate_tree(tmp_path))

    record["interpretation_policy"][field] = True

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must keep",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_scientific_boundary_exact(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["scientific_boundary"]["analysis_use_authorized"] = True

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot be promoted",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_claim_limit(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["claim_limit"] = "promoted"

    _refingerprint_recovery(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="claim limit drifted",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_record_fp(
    tmp_path,
):
    record = _review(_candidate_tree(tmp_path))

    record["record_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record fingerprint drifted",
    ):
        recovery.validate_gaze_in_wild_recovery_candidate_review(record)


def test_recovery_validate_path_preserved(
    tmp_path,
):
    root = _candidate_tree(tmp_path)

    record = _review(root)

    path = tmp_path / "review.json"

    _write_json(
        path,
        record,
    )

    validated = recovery.validate_gaze_in_wild_recovery_candidate_review(path)

    assert validated.path == path


# ============================================================
# GIW VERIFY + WRITE
# ============================================================


def test_recovery_verify_extension_mismatch(
    monkeypatch,
    tmp_path,
):
    root = _candidate_tree(tmp_path)

    record = _review(root)

    expected_files = copy.deepcopy(record["inventory"]["files"])

    monkeypatch.setattr(
        recovery,
        "_inventory",
        lambda resolved: (
            expected_files,
            {
                ".fake": 1,
            },
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="extension inventory no longer matches",
    ):
        recovery.verify_gaze_in_wild_recovery_candidate_tree(
            root,
            record,
        )


def test_recovery_write_root_itself(
    tmp_path,
):
    root = _candidate_tree(tmp_path)

    record = _review(root)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="outside the candidate tree",
    ):
        recovery.write_gaze_in_wild_recovery_candidate_review(
            record,
            root,
            candidate_root=root,
        )


def test_recovery_write_overwrite_true(
    tmp_path,
):
    root = _candidate_tree(tmp_path)

    record = _review(root)

    target = tmp_path / "out" / "review.json"

    recovery.write_gaze_in_wild_recovery_candidate_review(
        record,
        target,
        candidate_root=root,
    )

    target.write_text(
        "{}",
        encoding="utf-8",
    )

    written = recovery.write_gaze_in_wild_recovery_candidate_review(
        record,
        target,
        candidate_root=root,
        overwrite=True,
    )

    assert written == target

    loaded = json.loads(target.read_text(encoding="utf-8"))

    assert loaded == record


# ============================================================
# EVIDENCE STATUS FIXTURES
# ============================================================


def _benchmark_source_payload(
    *,
    name="Fixture",
):
    body = {
        "benchmark": {
            "name": name,
        },
        "model": {
            "name": "fixture-model",
        },
        "protocol": {
            "reviewed": True,
        },
        "metrics": {
            "accuracy": 0.75,
        },
    }

    return {
        **body,
        "report_fingerprint_sha256": (benchmark_fingerprint(body)),
    }


def _status_row(
    *,
    slug="fixture",
    validator="benchmark_report",
    source_path=("validation/evidence/fixture.json"),
    git_blob_sha1=None,
    fingerprint_field=("report_fingerprint_sha256"),
    fingerprint=None,
    required_equals=None,
    blockers=None,
    state_value=("frozen_empirical_evidence"),
):
    return {
        "dataset": "Fixture dataset",
        "slug": slug,
        "state": state_value,
        "summary": ("Fixture reviewed evidence."),
        "scope": "test scope",
        "sampling_origin": "native",
        "reference_strength": ("human-reference"),
        "source_path": source_path,
        "git_blob_sha1": git_blob_sha1,
        "fingerprint_field": (fingerprint_field),
        "fingerprint": fingerprint,
        "validator": validator,
        "required_equals": ({} if required_equals is None else required_equals),
        "blockers": ([] if blockers is None else blockers),
    }


def _write_status_fixture(
    root: Path,
    *,
    rows=None,
    payload=None,
):
    if payload is None:
        payload = _benchmark_source_payload()

    source = root / "validation" / "evidence" / "fixture.json"

    _write_json(
        source,
        payload,
    )

    if rows is None:
        rows = [
            _status_row(
                git_blob_sha1=(_git_blob_sha1(source.read_bytes())),
                fingerprint=payload["report_fingerprint_sha256"],
                required_equals={
                    "benchmark.name": "Fixture",
                },
            )
        ]

    body = {
        "schema_version": 1,
        "records": rows,
    }

    manifest = {
        **body,
        "manifest_fingerprint_sha256": (benchmark_fingerprint(body)),
    }

    manifest_path = root / "validation" / "evidence-status-manifest.json"

    _write_json(
        manifest_path,
        manifest,
    )

    return (
        source,
        manifest_path,
        manifest,
    )


def _refingerprint_manifest(
    manifest,
):
    body = {key: value for key, value in manifest.items() if key != "manifest_fingerprint_sha256"}

    manifest["manifest_fingerprint_sha256"] = benchmark_fingerprint(body)


# ============================================================
# EVIDENCE STATUS DATACLASSES
# ============================================================


def test_status_record_to_dict():
    record = status.EvidenceStatusRecord(
        dataset="D",
        slug="d",
        state=status.EvidenceState.IMPLEMENTED,
        summary="s",
        scope="scope",
        sampling_origin="native",
        reference_strength="none",
        blockers=("a", "b"),
        source_path=None,
        fingerprint=None,
    )

    payload = record.to_dict()

    assert payload["state"] == "implemented"

    assert payload["blockers"] == [
        "a",
        "b",
    ]


def test_status_bundle_to_dict():
    record = status.EvidenceStatusRecord(
        dataset="D",
        slug="d",
        state=status.EvidenceState.IMPLEMENTED,
        summary="s",
        scope="scope",
        sampling_origin="native",
        reference_strength="none",
        blockers=(),
        source_path=None,
        fingerprint=None,
    )

    bundle = status.EvidenceStatusBundle(
        schema_version=1,
        records=(record,),
        manifest_fingerprint_sha256=("a" * 64),
        bundle_fingerprint_sha256=("b" * 64),
    )

    payload = bundle.to_dict()

    assert payload["schema_version"] == 1

    assert payload["records"][0]["slug"] == "d"


def test_status_git_blob_sha():
    raw = b"abc"

    expected = hashlib.sha1(
        ("blob 3\0").encode("ascii") + raw,
        usedforsecurity=False,
    ).hexdigest()

    assert status._git_blob_sha1(raw) == expected


# ============================================================
# STATUS JSON LOADER
# ============================================================


def test_status_load_missing(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        status._load_json_object(
            tmp_path / "missing.json",
            label="fixture",
        )


def test_status_load_bad_json(
    tmp_path,
):
    path = tmp_path / "bad.json"

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not valid UTF-8 JSON",
    ):
        status._load_json_object(
            path,
            label="fixture",
        )


def test_status_load_bad_utf8(
    tmp_path,
):
    path = tmp_path / "bad.json"

    path.write_bytes(b"\xff\xfe")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not valid UTF-8 JSON",
    ):
        status._load_json_object(
            path,
            label="fixture",
        )


def test_status_load_nonobject(
    tmp_path,
):
    path = tmp_path / "bad.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        status._load_json_object(
            path,
            label="fixture",
        )


def test_status_load_valid(
    tmp_path,
):
    path = tmp_path / "ok.json"

    _write_json(
        path,
        {
            "x": 1,
        },
    )

    assert status._load_json_object(
        path,
        label="fixture",
    ) == {
        "x": 1,
    }


# ============================================================
# STATUS LOOKUP + SAFE PATH
# ============================================================


def test_status_lookup_nested():
    payload = {
        "a": {
            "b": {
                "c": 3,
            }
        }
    }

    assert (
        status._lookup(
            payload,
            "a.b.c",
        )
        == 3
    )


@pytest.mark.parametrize(
    "path",
    [
        "a.missing",
        "a.b.c.d",
    ],
)
def test_status_lookup_missing(
    path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing required field",
    ):
        status._lookup(
            {
                "a": {
                    "b": {
                        "c": 1,
                    }
                }
            },
            path,
        )


@pytest.mark.parametrize(
    "relative",
    [
        "",
        "../escape.json",
        "x/../../escape.json",
    ],
)
def test_status_safe_path_rejects(
    tmp_path,
    relative,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="unsafe source path",
    ):
        status._safe_repository_path(
            tmp_path,
            relative,
        )


def test_status_safe_path_absolute(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="unsafe source path",
    ):
        status._safe_repository_path(
            tmp_path,
            str((tmp_path / "absolute.json").resolve()),
        )


def test_status_safe_path_valid(
    tmp_path,
):
    result = status._safe_repository_path(
        tmp_path,
        "validation/evidence/x.json",
    )

    assert result == (tmp_path / "validation" / "evidence" / "x.json").resolve()


# ============================================================
# STATUS MANIFEST VALIDATOR
# ============================================================


@pytest.mark.parametrize(
    "missing",
    [
        "schema_version",
        "records",
        ("manifest_fingerprint_sha256"),
    ],
)
def test_status_manifest_required(
    missing,
):
    manifest = {
        "schema_version": 1,
        "records": [
            {
                "slug": "x",
                "state": "implemented",
            }
        ],
        "manifest_fingerprint_sha256": ("a" * 64),
    }

    manifest.pop(missing)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing required fields",
    ):
        status._validate_manifest(manifest)


def test_status_manifest_schema():
    manifest = {
        "schema_version": 2,
        "records": [
            {
                "slug": "x",
                "state": "implemented",
            }
        ],
        "manifest_fingerprint_sha256": ("a" * 64),
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Unsupported",
    ):
        status._validate_manifest(manifest)


@pytest.mark.parametrize(
    "records",
    [
        None,
        [],
        {},
    ],
)
def test_status_manifest_records(
    records,
):
    manifest = {
        "schema_version": 1,
        "records": records,
        "manifest_fingerprint_sha256": ("a" * 64),
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-empty list",
    ):
        status._validate_manifest(manifest)


@pytest.mark.parametrize(
    "fingerprint",
    [
        None,
        "",
        "a" * 63,
        1,
    ],
)
def test_status_manifest_fp_format(
    fingerprint,
):
    manifest = {
        "schema_version": 1,
        "records": [
            {
                "slug": "x",
                "state": "implemented",
            }
        ],
        "manifest_fingerprint_sha256": (fingerprint),
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint is missing or invalid",
    ):
        status._validate_manifest(manifest)


def test_status_manifest_fp_mismatch():
    manifest = {
        "schema_version": 1,
        "records": [
            {
                "slug": "x",
                "state": "implemented",
            }
        ],
        "manifest_fingerprint_sha256": ("a" * 64),
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint mismatch",
    ):
        status._validate_manifest(manifest)


def _valid_manifest_for_rows(
    rows,
):
    body = {
        "schema_version": 1,
        "records": rows,
    }

    return {
        **body,
        "manifest_fingerprint_sha256": (benchmark_fingerprint(body)),
    }


def test_status_manifest_row_object():
    manifest = _valid_manifest_for_rows(
        [
            "bad",
        ]
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-object row",
    ):
        status._validate_manifest(manifest)


@pytest.mark.parametrize(
    "slug",
    [
        None,
        "",
        1,
    ],
)
def test_status_manifest_slug(
    slug,
):
    manifest = _valid_manifest_for_rows(
        [
            {
                "slug": slug,
                "state": ("implemented"),
            }
        ]
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="unique and non-empty",
    ):
        status._validate_manifest(manifest)


def test_status_manifest_duplicate_slug():
    rows = [
        {
            "slug": "x",
            "state": "implemented",
        },
        {
            "slug": "x",
            "state": "implemented",
        },
    ]

    manifest = _valid_manifest_for_rows(rows)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="unique and non-empty",
    ):
        status._validate_manifest(manifest)


@pytest.mark.parametrize(
    "state_value",
    [
        None,
        "invalid",
    ],
)
def test_status_manifest_state(
    state_value,
):
    manifest = _valid_manifest_for_rows(
        [
            {
                "slug": "x",
                "state": state_value,
            }
        ]
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="invalid state",
    ):
        status._validate_manifest(manifest)


def test_status_manifest_blockers():
    manifest = _valid_manifest_for_rows(
        [
            {
                "slug": "x",
                "state": "implemented",
                "blockers": "bad",
            }
        ]
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="blockers must be a list",
    ):
        status._validate_manifest(manifest)


def test_status_manifest_required_equals():
    manifest = _valid_manifest_for_rows(
        [
            {
                "slug": "x",
                "state": "implemented",
                "required_equals": [],
            }
        ]
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="required_equals must be an object",
    ):
        status._validate_manifest(manifest)


def test_status_manifest_valid():
    rows = [
        {
            "slug": "a",
            "state": "implemented",
            "blockers": [],
            "required_equals": {},
        },
        {
            "slug": "b",
            "state": ("frozen_empirical_evidence"),
            "blockers": ["boundary"],
            "required_equals": {},
        },
    ]

    manifest = _valid_manifest_for_rows(rows)

    assert status._validate_manifest(manifest) == manifest["manifest_fingerprint_sha256"]


# ============================================================
# STATUS SOURCE BINDING — POLICY ONLY
# ============================================================


def test_status_policy_only_clean(
    tmp_path,
):
    row = _status_row(
        validator="policy_only",
        source_path=None,
        git_blob_sha1=None,
        fingerprint_field=None,
        fingerprint=None,
    )

    assert (
        status._validate_bound_source(
            tmp_path,
            row,
        )
        is None
    )


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        (
            "source_path",
            "x.json",
        ),
        (
            "git_blob_sha1",
            "a",
        ),
        (
            "fingerprint_field",
            "x",
        ),
        (
            "fingerprint",
            "a",
        ),
    ],
)
def test_status_policy_only_binding_refused(
    tmp_path,
    field,
    value,
):
    row = _status_row(
        validator="policy_only",
        source_path=None,
        git_blob_sha1=None,
        fingerprint_field=None,
        fingerprint=None,
    )

    row[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not bind",
    ):
        status._validate_bound_source(
            tmp_path,
            row,
        )


# ============================================================
# STATUS SOURCE BINDING — GENERAL
# ============================================================


@pytest.mark.parametrize(
    "field",
    [
        "source_path",
        "git_blob_sha1",
        "fingerprint_field",
        "fingerprint",
    ],
)
def test_status_incomplete_binding(
    tmp_path,
    field,
):
    row = _status_row(
        git_blob_sha1="a",
        fingerprint="b",
    )

    row[field] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="incomplete source binding",
    ):
        status._validate_bound_source(
            tmp_path,
            row,
        )


def test_status_source_missing(
    tmp_path,
):
    row = _status_row(
        git_blob_sha1="a",
        fingerprint="b",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source is missing",
    ):
        status._validate_bound_source(
            tmp_path,
            row,
        )


def test_status_blob_mismatch(
    tmp_path,
):
    source, _, _ = _write_status_fixture(tmp_path)

    payload = json.loads(source.read_text(encoding="utf-8"))

    row = _status_row(
        git_blob_sha1=("0" * 40),
        fingerprint=payload["report_fingerprint_sha256"],
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="byte identity mismatch",
    ):
        status._validate_bound_source(
            tmp_path,
            row,
        )


def test_status_payload_fp_mismatch(
    tmp_path,
):
    source, _, _ = _write_status_fixture(tmp_path)

    row = _status_row(
        git_blob_sha1=(_git_blob_sha1(source.read_bytes())),
        fingerprint=("0" * 64),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Evidence fingerprint mismatch",
    ):
        status._validate_bound_source(
            tmp_path,
            row,
        )


def test_status_required_equals_missing(
    tmp_path,
):
    source, _, _ = _write_status_fixture(tmp_path)

    payload = json.loads(source.read_text(encoding="utf-8"))

    row = _status_row(
        git_blob_sha1=(_git_blob_sha1(source.read_bytes())),
        fingerprint=payload["report_fingerprint_sha256"],
        required_equals={
            "benchmark.missing": 1,
        },
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing required field",
    ):
        status._validate_bound_source(
            tmp_path,
            row,
        )


def test_status_required_equals_mismatch(
    tmp_path,
):
    source, _, _ = _write_status_fixture(tmp_path)

    payload = json.loads(source.read_text(encoding="utf-8"))

    row = _status_row(
        git_blob_sha1=(_git_blob_sha1(source.read_bytes())),
        fingerprint=payload["report_fingerprint_sha256"],
        required_equals={
            "benchmark.name": ("Wrong"),
        },
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="semantic gate failed",
    ):
        status._validate_bound_source(
            tmp_path,
            row,
        )


def test_status_benchmark_report_valid(
    tmp_path,
):
    source, _, _ = _write_status_fixture(tmp_path)

    payload = json.loads(source.read_text(encoding="utf-8"))

    row = _status_row(
        git_blob_sha1=(_git_blob_sha1(source.read_bytes())),
        fingerprint=payload["report_fingerprint_sha256"],
        required_equals={
            "benchmark.name": ("Fixture"),
        },
    )

    validated = status._validate_bound_source(
        tmp_path,
        row,
    )

    assert validated == payload


def test_status_benchmark_report_recompute_failure(
    tmp_path,
):
    payload = _benchmark_source_payload()

    payload["report_fingerprint_sha256"] = "a" * 64

    source = tmp_path / "validation" / "evidence" / "fixture.json"

    _write_json(
        source,
        payload,
    )

    row = _status_row(
        git_blob_sha1=(_git_blob_sha1(source.read_bytes())),
        fingerprint=("a" * 64),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="recomputation failed",
    ):
        status._validate_bound_source(
            tmp_path,
            row,
        )


def test_status_semantic_lock(
    tmp_path,
):
    payload = {
        "fingerprint": ("a" * 64),
        "semantic": {
            "verified": True,
        },
    }

    source = tmp_path / "validation" / "evidence" / "fixture.json"

    _write_json(
        source,
        payload,
    )

    row = _status_row(
        validator="semantic_lock",
        git_blob_sha1=(_git_blob_sha1(source.read_bytes())),
        fingerprint_field=("fingerprint"),
        fingerprint=("a" * 64),
        required_equals={
            "semantic.verified": True,
        },
    )

    assert (
        status._validate_bound_source(
            tmp_path,
            row,
        )
        == payload
    )


def test_status_unknown_validator(
    tmp_path,
):
    payload = {
        "fingerprint": ("a" * 64),
    }

    source = tmp_path / "validation" / "evidence" / "fixture.json"

    _write_json(
        source,
        payload,
    )

    row = _status_row(
        validator="unknown",
        git_blob_sha1=(_git_blob_sha1(source.read_bytes())),
        fingerprint_field=("fingerprint"),
        fingerprint=("a" * 64),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Unknown evidence-status validator",
    ):
        status._validate_bound_source(
            tmp_path,
            row,
        )


def test_status_lund_validator_valid(
    monkeypatch,
    tmp_path,
):
    payload = {
        "suite_fingerprint_sha256": ("a" * 64),
    }

    source = tmp_path / "validation" / "evidence" / "fixture.json"

    _write_json(
        source,
        payload,
    )

    monkeypatch.setattr(
        status,
        "validate_lund2013_suite_manifest",
        lambda path, verify_reports: {"suite_fingerprint_sha256": ("a" * 64)},
    )

    row = _status_row(
        validator="lund2013_suite",
        git_blob_sha1=(_git_blob_sha1(source.read_bytes())),
        fingerprint_field=("suite_fingerprint_sha256"),
        fingerprint=("a" * 64),
    )

    assert (
        status._validate_bound_source(
            tmp_path,
            row,
        )
        == payload
    )


def test_status_lund_validator_mismatch(
    monkeypatch,
    tmp_path,
):
    payload = {
        "suite_fingerprint_sha256": ("a" * 64),
    }

    source = tmp_path / "validation" / "evidence" / "fixture.json"

    _write_json(
        source,
        payload,
    )

    monkeypatch.setattr(
        status,
        "validate_lund2013_suite_manifest",
        lambda path, verify_reports: {"suite_fingerprint_sha256": ("b" * 64)},
    )

    row = _status_row(
        validator="lund2013_suite",
        git_blob_sha1=(_git_blob_sha1(source.read_bytes())),
        fingerprint_field=("suite_fingerprint_sha256"),
        fingerprint=("a" * 64),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not match status policy",
    ):
        status._validate_bound_source(
            tmp_path,
            row,
        )


# ============================================================
# BUILD STATUS BUNDLE
# ============================================================


def test_status_build_policy_only(
    tmp_path,
):
    row_b = _status_row(
        slug="b",
        validator="policy_only",
        source_path=None,
        git_blob_sha1=None,
        fingerprint_field=None,
        fingerprint=None,
        blockers=["open boundary"],
        state_value="implemented",
    )

    row_a = _status_row(
        slug="a",
        validator="policy_only",
        source_path=None,
        git_blob_sha1=None,
        fingerprint_field=None,
        fingerprint=None,
        blockers=[],
        state_value=("infrastructure_validated"),
    )

    body = {
        "schema_version": 1,
        "records": [
            row_b,
            row_a,
        ],
    }

    manifest = {
        **body,
        "manifest_fingerprint_sha256": (benchmark_fingerprint(body)),
    }

    custom = tmp_path / "policy.json"

    _write_json(
        custom,
        manifest,
    )

    bundle = status.build_evidence_status(
        tmp_path,
        manifest_path="policy.json",
    )

    assert [record.slug for record in bundle.records] == [
        "a",
        "b",
    ]

    assert bundle.records[0].source_path is None

    assert bundle.records[0].fingerprint is None

    assert len(bundle.bundle_fingerprint_sha256) == 64


def test_status_build_default_manifest(
    tmp_path,
):
    _write_status_fixture(tmp_path)

    bundle = status.build_evidence_status(tmp_path)

    assert len(bundle.records) == 1

    assert bundle.records[0].slug == "fixture"


def test_status_build_custom_unsafe_manifest(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="unsafe source path",
    ):
        status.build_evidence_status(
            tmp_path,
            manifest_path="../outside.json",
        )


# ============================================================
# STATUS RENDERERS
# ============================================================


def _render_bundle():
    first = status.EvidenceStatusRecord(
        dataset="Dataset A",
        slug="a",
        state=(status.EvidenceState.FROZEN_EMPIRICAL_EVIDENCE),
        summary="Reviewed.",
        scope="scope A",
        sampling_origin="native",
        reference_strength="strong",
        blockers=("Open boundary A",),
        source_path="a.json",
        fingerprint="a" * 64,
    )

    second = status.EvidenceStatusRecord(
        dataset="Dataset B",
        slug="b",
        state=(status.EvidenceState.IMPLEMENTED),
        summary="Implemented.",
        scope="scope B",
        sampling_origin="derived",
        reference_strength="none",
        blockers=(),
        source_path=None,
        fingerprint=None,
    )

    body = {
        "schema_version": 1,
        "manifest_fingerprint_sha256": ("c" * 64),
        "records": [
            first.to_dict(),
            second.to_dict(),
        ],
    }

    return status.EvidenceStatusBundle(
        schema_version=1,
        records=(
            first,
            second,
        ),
        manifest_fingerprint_sha256=("c" * 64),
        bundle_fingerprint_sha256=(benchmark_fingerprint(body)),
    )


def test_status_render_json():
    bundle = _render_bundle()

    rendered = status.render_evidence_status_json(bundle)

    decoded = json.loads(rendered)

    assert decoded["records"][0]["slug"] == "a"

    assert rendered.endswith("\n")


def test_status_render_markdown_all_branches():
    bundle = _render_bundle()

    rendered = status.render_evidence_status_markdown(bundle)

    assert "Frozen empirical evidence" in rendered

    assert "Versioned source: `a.json`" in rendered

    assert "Bound evidence fingerprint" in rendered

    assert "Open boundary A" in rendered

    assert "Open boundaries: none recorded" in rendered

    assert "Status is not inferred" in rendered
