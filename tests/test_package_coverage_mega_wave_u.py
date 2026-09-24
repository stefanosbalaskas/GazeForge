from __future__ import annotations

import copy
import hashlib
import json

import pytest

import gazeforge.source_candidate as candidate
import gazeforge.source_candidate_review as review
from gazeforge.exceptions import BenchmarkIntegrityError

# ============================================================
# FIXTURES
# ============================================================


def _candidate_tree(
    tmp_path,
    *,
    dataset_key="gaze-in-the-wild",
):
    root = tmp_path / "candidate"
    root.mkdir()

    if dataset_key == "hollywood2em":
        (root / "a.arff").write_text(
            "@relation fixture\n@data\n1\n",
            encoding="utf-8",
        )

        (root / "notes.txt").write_text(
            "review notes\n",
            encoding="utf-8",
        )
    else:
        (root / "label.mat").write_bytes(b"label-data")

        (root / "process.mat").write_bytes(b"process-data")

    return root


def _inventory_bundle(
    tmp_path,
    *,
    dataset_key="gaze-in-the-wild",
):
    root = _candidate_tree(
        tmp_path,
        dataset_key=dataset_key,
    )

    inventory = candidate.build_candidate_source_inventory(
        root,
        dataset_key=dataset_key,
    )

    inventory_path = tmp_path / "inventory.json"

    candidate.write_candidate_source_inventory(
        inventory,
        inventory_path,
    )

    return (
        root,
        inventory,
        inventory_path,
    )


def _review_bundle(
    tmp_path,
    *,
    dataset_key="gaze-in-the-wild",
):
    (
        root,
        inventory,
        inventory_path,
    ) = _inventory_bundle(
        tmp_path,
        dataset_key=dataset_key,
    )

    scaffold = review.build_candidate_source_review_scaffold(inventory)

    review_path = tmp_path / "review.json"

    review.write_candidate_source_review_scaffold(
        scaffold,
        review_path,
    )

    return (
        root,
        inventory,
        inventory_path,
        scaffold,
        review_path,
    )


def _write_json(
    path,
    payload,
):
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


# ============================================================
# CANDIDATE SOURCE BASIC HELPERS
# ============================================================


@pytest.mark.parametrize(
    (
        "raw",
        "expected",
    ),
    [
        (
            " HOLLYWOOD2EM ",
            "hollywood2em",
        ),
        (
            " GAZE-IN-THE-WILD ",
            "gaze-in-the-wild",
        ),
    ],
)
def test_candidate_dataset_key_normalizes(
    raw,
    expected,
):
    assert candidate._dataset_key(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "other",
        None,
    ],
)
def test_candidate_dataset_key_rejects(
    raw,
):
    with pytest.raises(
        ValueError,
        match="dataset_key must be one of",
    ):
        candidate._dataset_key(raw)


def test_candidate_file_sha(
    tmp_path,
):
    path = tmp_path / "x.bin"

    path.write_bytes(b"abc")

    assert candidate._file_sha256(path) == hashlib.sha256(b"abc").hexdigest()


def test_candidate_canonical_fingerprint():
    file = candidate.CandidateSourceFile(
        path="x.dat",
        sha256="a" * 64,
        bytes=1,
    )

    first = candidate._canonical_fingerprint(
        "hollywood2em",
        (file,),
    )

    second = candidate._canonical_fingerprint(
        "hollywood2em",
        (file,),
    )

    assert first == second

    assert len(first) == 64


# ============================================================
# CANDIDATE SOURCE FILE CONTRACT
# ============================================================


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/absolute.dat",
        "../escape.dat",
        "a/../escape.dat",
    ],
)
def test_candidate_file_path_rejected(
    path,
):
    with pytest.raises(
        ValueError,
        match="safe relative POSIX paths",
    ):
        candidate.CandidateSourceFile(
            path=path,
            sha256="a" * 64,
            bytes=1,
        )


@pytest.mark.parametrize(
    "digest",
    [
        "",
        "a" * 63,
        "g" * 64,
    ],
)
def test_candidate_file_sha_rejected(
    digest,
):
    with pytest.raises(
        ValueError,
        match="64 hexadecimal",
    ):
        candidate.CandidateSourceFile(
            path="x.dat",
            sha256=digest,
            bytes=1,
        )


def test_candidate_file_sha_normalized():
    record = candidate.CandidateSourceFile(
        path="x.dat",
        sha256="A" * 64,
        bytes=1,
    )

    assert record.sha256 == "a" * 64


@pytest.mark.parametrize(
    "size",
    [
        0,
        -1,
    ],
)
def test_candidate_file_size_rejected(
    size,
):
    with pytest.raises(
        ValueError,
        match="byte size must be positive",
    ):
        candidate.CandidateSourceFile(
            path="x.dat",
            sha256="a" * 64,
            bytes=size,
        )


def test_candidate_file_to_dict():
    record = candidate.CandidateSourceFile(
        path="x.dat",
        sha256="a" * 64,
        bytes=5,
    )

    assert record.to_dict() == {
        "path": "x.dat",
        "sha256": "a" * 64,
        "bytes": 5,
    }


# ============================================================
# INVENTORY ROOT
# ============================================================


def test_candidate_inventory_root_missing(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError,
    ):
        candidate._inventory_root(tmp_path / "missing")


def test_candidate_inventory_root_empty(
    tmp_path,
):
    root = tmp_path / "empty"
    root.mkdir()

    with pytest.raises(
        ValueError,
        match="at least one regular file",
    ):
        candidate._inventory_root(root)


def test_candidate_inventory_root_zero_byte(
    tmp_path,
):
    root = tmp_path / "candidate"
    root.mkdir()

    (root / "empty.dat").write_bytes(b"")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="zero-byte",
    ):
        candidate._inventory_root(root)


def test_candidate_inventory_root_sorted(
    tmp_path,
):
    root = tmp_path / "candidate"
    root.mkdir()

    nested = root / "z"
    nested.mkdir()

    (nested / "b.dat").write_bytes(b"b")

    (root / "a.dat").write_bytes(b"a")

    records = candidate._inventory_root(root)

    assert [item.path for item in records] == [
        "a.dat",
        "z/b.dat",
    ]


# ============================================================
# INVENTORY OBJECT + BUILD
# ============================================================


def test_candidate_inventory_properties(
    tmp_path,
):
    root = _candidate_tree(tmp_path)

    inventory = candidate.build_candidate_source_inventory(
        root,
        dataset_key="gaze-in-the-wild",
    )

    assert inventory.root == root.resolve()

    assert inventory.file_count == 2

    payload = inventory.to_dict()

    assert payload["file_count"] == 2

    assert payload["scientific_boundary"] == candidate._SCIENTIFIC_BOUNDARY


def test_candidate_build_normalizes_dataset(
    tmp_path,
):
    root = _candidate_tree(
        tmp_path,
        dataset_key="hollywood2em",
    )

    result = candidate.build_candidate_source_inventory(
        root,
        dataset_key=" HOLLYWOOD2EM ",
    )

    assert result.dataset_key == "hollywood2em"


# ============================================================
# INVENTORY WRITER
# ============================================================


def test_candidate_writer_type(
    tmp_path,
):
    with pytest.raises(
        TypeError,
        match="CandidateSourceInventory",
    ):
        candidate.write_candidate_source_inventory(
            {},
            tmp_path / "x.json",
        )


def test_candidate_writer_root_itself(
    tmp_path,
):
    root = _candidate_tree(tmp_path)

    inventory = candidate.build_candidate_source_inventory(
        root,
        dataset_key="gaze-in-the-wild",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="outside the inventoried tree",
    ):
        candidate.write_candidate_source_inventory(
            inventory,
            root,
        )


def test_candidate_writer_existing(
    tmp_path,
):
    (
        root,
        inventory,
        _,
    ) = _inventory_bundle(tmp_path)

    assert root.is_dir()

    target = tmp_path / "existing.json"

    target.write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
    ):
        candidate.write_candidate_source_inventory(
            inventory,
            target,
        )


def test_candidate_writer_overwrite(
    tmp_path,
):
    root = _candidate_tree(tmp_path)

    inventory = candidate.build_candidate_source_inventory(
        root,
        dataset_key="gaze-in-the-wild",
    )

    target = tmp_path / "out" / "inventory.json"

    target.parent.mkdir()

    target.write_text(
        "{}",
        encoding="utf-8",
    )

    written = candidate.write_candidate_source_inventory(
        inventory,
        target,
        overwrite=True,
    )

    assert written == target

    payload = json.loads(target.read_text(encoding="utf-8"))

    assert payload["record_type"] == candidate._RECORD_TYPE


# ============================================================
# INVENTORY LOADER
# ============================================================


def test_candidate_loader_missing(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError,
    ):
        candidate._load_inventory_payload(tmp_path / "missing.json")


def test_candidate_loader_bad_json(
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
        candidate._load_inventory_payload(path)


def test_candidate_loader_bad_utf8(
    tmp_path,
):
    path = tmp_path / "bad.json"

    path.write_bytes(b"\xff\xfe")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        candidate._load_inventory_payload(path)


def test_candidate_loader_nonobject(
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
        candidate._load_inventory_payload(path)


# ============================================================
# INVENTORY VALIDATION — SERIALIZED CONTRACT
# ============================================================


def test_candidate_validate_record_type(
    tmp_path,
):
    (
        root,
        _,
        path,
    ) = _inventory_bundle(tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))

    payload["record_type"] = "wrong"

    _write_json(
        path,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record_type",
    ):
        candidate.validate_candidate_source_inventory(
            path,
            root,
        )


def test_candidate_validate_dataset_key(
    tmp_path,
):
    (
        root,
        _,
        path,
    ) = _inventory_bundle(tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))

    payload["dataset_key"] = "other"

    _write_json(
        path,
        payload,
    )

    with pytest.raises(
        ValueError,
        match="dataset_key must be one of",
    ):
        candidate.validate_candidate_source_inventory(
            path,
            root,
        )


def test_candidate_validate_boundary(
    tmp_path,
):
    (
        root,
        _,
        path,
    ) = _inventory_bundle(tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))

    payload["scientific_boundary"]["analysis_use_permitted"] = True

    _write_json(
        path,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-empirical limits",
    ):
        candidate.validate_candidate_source_inventory(
            path,
            root,
        )


@pytest.mark.parametrize(
    "files",
    [
        None,
        [],
        {},
    ],
)
def test_candidate_validate_files_required(
    tmp_path,
    files,
):
    (
        root,
        _,
        path,
    ) = _inventory_bundle(tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))

    payload["files"] = files

    _write_json(
        path,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-empty files list",
    ):
        candidate.validate_candidate_source_inventory(
            path,
            root,
        )


def test_candidate_validate_bad_file_mapping(
    tmp_path,
):
    (
        root,
        _,
        path,
    ) = _inventory_bundle(tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))

    payload["files"][0].pop("sha256")

    _write_json(
        path,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file records are invalid",
    ):
        candidate.validate_candidate_source_inventory(
            path,
            root,
        )


def test_candidate_validate_nonobject_file(
    tmp_path,
):
    (
        root,
        _,
        path,
    ) = _inventory_bundle(tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))

    payload["files"][0] = "bad"

    _write_json(
        path,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="all be JSON objects",
    ):
        candidate.validate_candidate_source_inventory(
            path,
            root,
        )


def test_candidate_validate_unsorted(
    tmp_path,
):
    (
        root,
        _,
        path,
    ) = _inventory_bundle(tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))

    payload["files"] = list(reversed(payload["files"]))

    _write_json(
        path,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="uniquely sorted",
    ):
        candidate.validate_candidate_source_inventory(
            path,
            root,
        )


def test_candidate_validate_duplicate_paths(
    tmp_path,
):
    (
        root,
        _,
        path,
    ) = _inventory_bundle(tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))

    duplicate = copy.deepcopy(payload["files"][0])

    payload["files"] = [
        duplicate,
        copy.deepcopy(duplicate),
    ]

    payload["file_count"] = 2

    _write_json(
        path,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="uniquely sorted",
    ):
        candidate.validate_candidate_source_inventory(
            path,
            root,
        )


@pytest.mark.parametrize(
    "count",
    [
        True,
        1,
        "2",
    ],
)
def test_candidate_validate_file_count(
    tmp_path,
    count,
):
    (
        root,
        inventory,
        path,
    ) = _inventory_bundle(tmp_path)

    assert inventory.file_count == 2

    payload = json.loads(path.read_text(encoding="utf-8"))

    payload["file_count"] = count

    _write_json(
        path,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file_count",
    ):
        candidate.validate_candidate_source_inventory(
            path,
            root,
        )


def test_candidate_validate_fingerprint(
    tmp_path,
):
    (
        root,
        _,
        path,
    ) = _inventory_bundle(tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))

    payload["inventory_fingerprint_sha256"] = "0" * 64

    _write_json(
        path,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="serialized content",
    ):
        candidate.validate_candidate_source_inventory(
            path,
            root,
        )


def test_candidate_validate_current_files_drift(
    tmp_path,
):
    (
        root,
        _,
        path,
    ) = _inventory_bundle(tmp_path)

    (root / "label.mat").write_bytes(b"changed")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="tree no longer matches",
    ):
        candidate.validate_candidate_source_inventory(
            path,
            root,
        )


def test_candidate_validate_current_fp_drift(
    monkeypatch,
    tmp_path,
):
    (
        root,
        inventory,
        path,
    ) = _inventory_bundle(tmp_path)

    current = candidate.CandidateSourceInventory(
        root=root.resolve(),
        dataset_key=inventory.dataset_key,
        files=inventory.files,
        inventory_fingerprint_sha256=("0" * 64),
    )

    monkeypatch.setattr(
        candidate,
        "build_candidate_source_inventory",
        lambda *args, **kwargs: current,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="tree fingerprint",
    ):
        candidate.validate_candidate_source_inventory(
            path,
            root,
        )


def test_candidate_validate_success(
    tmp_path,
):
    (
        root,
        inventory,
        path,
    ) = _inventory_bundle(tmp_path)

    observed = candidate.validate_candidate_source_inventory(
        path,
        root,
    )

    assert observed.files == inventory.files


# ============================================================
# REVIEW DATACLASSES + BLANK SCHEMAS
# ============================================================


def test_review_file_to_dict():
    row = review.CandidateSourceReviewFile(
        path="x.dat",
        sha256="a" * 64,
        bytes=1,
        role="exclude",
    )

    assert row.to_dict()["role"] == "exclude"


@pytest.mark.parametrize(
    (
        "dataset_key",
        "specific",
    ),
    [
        (
            "hollywood2em",
            "annotation_columns_review",
        ),
        (
            "gaze-in-the-wild",
            "label_process_mapping_basis",
        ),
    ],
)
def test_review_blank_source_review(
    dataset_key,
    specific,
):
    value = review._blank_source_review(dataset_key)

    assert value["dataset_status"] == "template"

    assert specific in value


def test_review_scaffold_to_dict(
    tmp_path,
):
    (
        _,
        inventory,
        _,
    ) = _inventory_bundle(tmp_path)

    scaffold = review.build_candidate_source_review_scaffold(inventory)

    payload = scaffold.to_dict()

    assert payload["record_type"] == review._RECORD_TYPE

    assert payload["scientific_boundary"] == review._SCIENTIFIC_BOUNDARY


# ============================================================
# REVIEW BUILD + WRITER
# ============================================================


def test_review_build_type():
    with pytest.raises(
        TypeError,
        match="CandidateSourceInventory",
    ):
        review.build_candidate_source_review_scaffold({})


def test_review_build_unsupported_dataset(
    tmp_path,
):
    inventory = candidate.CandidateSourceInventory(
        root=tmp_path.resolve(),
        dataset_key="other",
        files=(),
        inventory_fingerprint_sha256=("a" * 64),
    )

    with pytest.raises(
        ValueError,
        match="Unsupported candidate dataset key",
    ):
        review.build_candidate_source_review_scaffold(inventory)


def test_review_writer_type(
    tmp_path,
):
    with pytest.raises(
        TypeError,
        match="CandidateSourceReviewScaffold",
    ):
        review.write_candidate_source_review_scaffold(
            {},
            tmp_path / "review.json",
        )


def test_review_writer_root_itself(
    tmp_path,
):
    (
        root,
        inventory,
        _,
    ) = _inventory_bundle(tmp_path)

    scaffold = review.build_candidate_source_review_scaffold(inventory)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="outside the candidate source tree",
    ):
        review.write_candidate_source_review_scaffold(
            scaffold,
            root,
        )


def test_review_writer_existing(
    tmp_path,
):
    (
        _,
        _,
        _,
        scaffold,
        review_path,
    ) = _review_bundle(tmp_path)

    with pytest.raises(
        FileExistsError,
    ):
        review.write_candidate_source_review_scaffold(
            scaffold,
            review_path,
        )


def test_review_writer_overwrite(
    tmp_path,
):
    (
        _,
        _,
        _,
        scaffold,
        review_path,
    ) = _review_bundle(tmp_path)

    review_path.write_text(
        "{}",
        encoding="utf-8",
    )

    written = review.write_candidate_source_review_scaffold(
        scaffold,
        review_path,
        overwrite=True,
    )

    assert written == review_path


# ============================================================
# REVIEW PAYLOAD LOADER
# ============================================================


def test_review_loader_missing(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError,
    ):
        review._load_payload(tmp_path / "missing.json")


def test_review_loader_bad_json(
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
        review._load_payload(path)


def test_review_loader_bad_utf8(
    tmp_path,
):
    path = tmp_path / "bad.json"

    path.write_bytes(b"\xff\xfe")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        review._load_payload(path)


def test_review_loader_nonobject(
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
        review._load_payload(path)


# ============================================================
# REVIEW ROW PARSING
# ============================================================


def _review_row(
    **changes,
):
    value = {
        "path": "x.dat",
        "sha256": "a" * 64,
        "bytes": 1,
        "role": "unresolved",
        "include_in_audit": False,
        "participant_id": None,
        "trial_id": None,
        "labeller_id": None,
        "process_path": None,
    }

    value.update(changes)

    return value


def test_review_row_role_normalized():
    row = review._review_file_from_payload(
        _review_row(role=" EXCLUDE "),
        dataset_key="hollywood2em",
    )

    assert row.role == "exclude"


def test_review_row_role_invalid():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Unsupported review role",
    ):
        review._review_file_from_payload(
            _review_row(role="other"),
            dataset_key="hollywood2em",
        )


def test_review_row_include_bool():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="include_in_audit must be boolean",
    ):
        review._review_file_from_payload(
            _review_row(include_in_audit=1),
            dataset_key="hollywood2em",
        )


@pytest.mark.parametrize(
    "value",
    [
        True,
        0,
        -1,
    ],
)
def test_review_row_labeller_invalid(
    value,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="labeller_id must be a positive integer",
    ):
        review._review_file_from_payload(
            _review_row(
                role="label",
                labeller_id=value,
            ),
            dataset_key="gaze-in-the-wild",
        )


def test_review_row_labeller_coercion():
    row = review._review_file_from_payload(
        _review_row(
            role="label",
            labeller_id="2",
        ),
        dataset_key="gaze-in-the-wild",
    )

    assert row.labeller_id == 2


def test_review_row_invalid_payload():
    value = _review_row()

    value.pop("bytes")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file row is invalid",
    ):
        review._review_file_from_payload(
            value,
            dataset_key="hollywood2em",
        )


@pytest.mark.parametrize(
    (
        "value",
        "expected",
    ),
    [
        (
            None,
            False,
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
            "P01",
            True,
        ),
    ],
)
def test_review_resolved_text(
    value,
    expected,
):
    assert review._resolved_text(value) is expected


# ============================================================
# DIRECT REVIEW SEMANTICS — HOLLYWOOD
# ============================================================


def _row(
    *,
    path="x.dat",
    role="unresolved",
    include=False,
    participant=None,
    trial=None,
    labeller=None,
    process_path=None,
):
    return review.CandidateSourceReviewFile(
        path=path,
        sha256="a" * 64,
        bytes=1,
        role=role,
        include_in_audit=include,
        participant_id=participant,
        trial_id=trial,
        labeller_id=labeller,
        process_path=process_path,
    )


@pytest.mark.parametrize(
    "role",
    [
        "unresolved",
        "exclude",
    ],
)
def test_review_semantics_included_unresolved(
    role,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="dataset-specific file role",
    ):
        review._validate_review_semantics(
            (
                _row(
                    role=role,
                    include=True,
                ),
            ),
            dataset_key="hollywood2em",
        )


@pytest.mark.parametrize(
    (
        "participant",
        "trial",
    ),
    [
        (
            None,
            "T01",
        ),
        (
            "P01",
            None,
        ),
        (
            "",
            "T01",
        ),
    ],
)
def test_review_hollywood_requires_identity(
    participant,
    trial,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="require participant_id and trial_id",
    ):
        review._validate_review_semantics(
            (
                _row(
                    role="arff",
                    include=True,
                    participant=participant,
                    trial=trial,
                ),
            ),
            dataset_key="hollywood2em",
        )


@pytest.mark.parametrize(
    (
        "labeller",
        "process_path",
    ),
    [
        (
            1,
            None,
        ),
        (
            None,
            "process.mat",
        ),
    ],
)
def test_review_hollywood_forbidden_fields(
    labeller,
    process_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot define labeller_id or process_path",
    ):
        review._validate_review_semantics(
            (
                _row(
                    role="arff",
                    include=True,
                    participant="P01",
                    trial="T01",
                    labeller=labeller,
                    process_path=process_path,
                ),
            ),
            dataset_key="hollywood2em",
        )


def test_review_hollywood_duplicate_identity():
    rows = (
        _row(
            path="a.arff",
            role="arff",
            include=True,
            participant="P01",
            trial="T01",
        ),
        _row(
            path="b.arff",
            role="arff",
            include=True,
            participant=" P01 ",
            trial=" T01 ",
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="identities must be unique",
    ):
        review._validate_review_semantics(
            rows,
            dataset_key="hollywood2em",
        )


def test_review_hollywood_valid():
    review._validate_review_semantics(
        (
            _row(
                role="arff",
                include=True,
                participant="P01",
                trial="T01",
            ),
        ),
        dataset_key="hollywood2em",
    )


# ============================================================
# DIRECT REVIEW SEMANTICS — GIW
# ============================================================


def test_review_giw_process_identity_forbidden():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="process rows carry file identity only",
    ):
        review._validate_review_semantics(
            (
                _row(
                    path="process.mat",
                    role="process",
                    include=True,
                    participant="P01",
                ),
            ),
            dataset_key="gaze-in-the-wild",
        )


@pytest.mark.parametrize(
    (
        "participant",
        "trial",
    ),
    [
        (
            None,
            "T01",
        ),
        (
            "P01",
            None,
        ),
    ],
)
def test_review_giw_label_requires_identity(
    participant,
    trial,
):
    rows = (
        _row(
            path="process.mat",
            role="process",
            include=True,
        ),
        _row(
            path="label.mat",
            role="label",
            include=True,
            participant=participant,
            trial=trial,
            labeller=1,
            process_path="process.mat",
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="require participant_id and trial_id",
    ):
        review._validate_review_semantics(
            rows,
            dataset_key="gaze-in-the-wild",
        )


@pytest.mark.parametrize(
    (
        "labeller",
        "process_path",
    ),
    [
        (
            None,
            "process.mat",
        ),
        (
            1,
            None,
        ),
        (
            1,
            "",
        ),
    ],
)
def test_review_giw_label_requires_link(
    labeller,
    process_path,
):
    rows = (
        _row(
            path="process.mat",
            role="process",
            include=True,
        ),
        _row(
            path="label.mat",
            role="label",
            include=True,
            participant="P01",
            trial="T01",
            labeller=labeller,
            process_path=process_path,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="require labeller_id and process_path",
    ):
        review._validate_review_semantics(
            rows,
            dataset_key="gaze-in-the-wild",
        )


def test_review_giw_process_not_included():
    rows = (
        _row(
            path="process.mat",
            role="process",
            include=False,
        ),
        _row(
            path="label.mat",
            role="label",
            include=True,
            participant="P01",
            trial="T01",
            labeller=1,
            process_path="process.mat",
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="reference an included process row",
    ):
        review._validate_review_semantics(
            rows,
            dataset_key="gaze-in-the-wild",
        )


def test_review_giw_trial_process_mismatch():
    rows = (
        _row(
            path="process-a.mat",
            role="process",
            include=True,
        ),
        _row(
            path="process-b.mat",
            role="process",
            include=True,
        ),
        _row(
            path="label-a.mat",
            role="label",
            include=True,
            participant="P01",
            trial="T01",
            labeller=1,
            process_path="process-a.mat",
        ),
        _row(
            path="label-b.mat",
            role="label",
            include=True,
            participant="P01",
            trial="T01",
            labeller=2,
            process_path="process-b.mat",
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="same reviewed process file",
    ):
        review._validate_review_semantics(
            rows,
            dataset_key="gaze-in-the-wild",
        )


def test_review_giw_duplicate_label_identity():
    rows = (
        _row(
            path="process.mat",
            role="process",
            include=True,
        ),
        _row(
            path="label-a.mat",
            role="label",
            include=True,
            participant="P01",
            trial="T01",
            labeller=1,
            process_path="process.mat",
        ),
        _row(
            path="label-b.mat",
            role="label",
            include=True,
            participant=" P01 ",
            trial=" T01 ",
            labeller=1,
            process_path="process.mat",
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="identities must be unique",
    ):
        review._validate_review_semantics(
            rows,
            dataset_key="gaze-in-the-wild",
        )


def test_review_giw_valid():
    review._validate_review_semantics(
        (
            _row(
                path="process.mat",
                role="process",
                include=True,
            ),
            _row(
                path="label.mat",
                role="label",
                include=True,
                participant="P01",
                trial="T01",
                labeller=1,
                process_path="process.mat",
            ),
        ),
        dataset_key="gaze-in-the-wild",
    )


# ============================================================
# REVIEW VALIDATOR TOP-LEVEL CONTRACT
# ============================================================


def _mutate_review(
    tmp_path,
    mutator,
    *,
    dataset_key="gaze-in-the-wild",
):
    (
        root,
        _,
        inventory_path,
        _,
        review_path,
    ) = _review_bundle(
        tmp_path,
        dataset_key=dataset_key,
    )

    payload = json.loads(review_path.read_text(encoding="utf-8"))

    mutator(payload)

    _write_json(
        review_path,
        payload,
    )

    return (
        root,
        inventory_path,
        review_path,
    )


def test_review_validate_record_type(
    tmp_path,
):
    (
        root,
        inventory_path,
        review_path,
    ) = _mutate_review(
        tmp_path,
        lambda payload: payload.update({"record_type": "wrong"}),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record_type",
    ):
        review.validate_candidate_source_review_scaffold(
            review_path,
            inventory_path,
            root,
        )


def test_review_validate_dataset(
    tmp_path,
):
    (
        root,
        inventory_path,
        review_path,
    ) = _mutate_review(
        tmp_path,
        lambda payload: payload.update({"dataset_key": "other"}),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="dataset identity",
    ):
        review.validate_candidate_source_review_scaffold(
            review_path,
            inventory_path,
            root,
        )


def test_review_validate_boundary(
    tmp_path,
):
    def mutate(payload):
        payload["scientific_boundary"]["authorizes_empirical_evidence"] = True

    (
        root,
        inventory_path,
        review_path,
    ) = _mutate_review(
        tmp_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-empirical limits",
    ):
        review.validate_candidate_source_review_scaffold(
            review_path,
            inventory_path,
            root,
        )


def test_review_validate_inventory_fp(
    tmp_path,
):
    (
        root,
        inventory_path,
        review_path,
    ) = _mutate_review(
        tmp_path,
        lambda payload: payload.update({("candidate_inventory_fingerprint_sha256"): ("0" * 64)}),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="current candidate inventory fingerprint",
    ):
        review.validate_candidate_source_review_scaffold(
            review_path,
            inventory_path,
            root,
        )


def test_review_validate_file_count(
    tmp_path,
):
    (
        root,
        inventory_path,
        review_path,
    ) = _mutate_review(
        tmp_path,
        lambda payload: payload.update({"candidate_file_count": 99}),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file count",
    ):
        review.validate_candidate_source_review_scaffold(
            review_path,
            inventory_path,
            root,
        )


def test_review_validate_source_review_object(
    tmp_path,
):
    (
        root,
        inventory_path,
        review_path,
    ) = _mutate_review(
        tmp_path,
        lambda payload: payload.update({"source_review": []}),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source_review object",
    ):
        review.validate_candidate_source_review_scaffold(
            review_path,
            inventory_path,
            root,
        )


def test_review_validate_schema_extra(
    tmp_path,
):
    def mutate(payload):
        payload["source_review"]["extra"] = True

    (
        root,
        inventory_path,
        review_path,
    ) = _mutate_review(
        tmp_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="complete dataset-specific review schema",
    ):
        review.validate_candidate_source_review_scaffold(
            review_path,
            inventory_path,
            root,
        )


def test_review_validate_dataset_status(
    tmp_path,
):
    def mutate(payload):
        payload["source_review"]["dataset_status"] = "empirical"

    (
        root,
        inventory_path,
        review_path,
    ) = _mutate_review(
        tmp_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must remain 'template'",
    ):
        review.validate_candidate_source_review_scaffold(
            review_path,
            inventory_path,
            root,
        )


def test_review_validate_notes(
    tmp_path,
):
    def mutate(payload):
        payload["source_review"]["notes"] = "bad"

    (
        root,
        inventory_path,
        review_path,
    ) = _mutate_review(
        tmp_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="notes must remain a JSON list",
    ):
        review.validate_candidate_source_review_scaffold(
            review_path,
            inventory_path,
            root,
        )


def test_review_validate_files_count(
    tmp_path,
):
    def mutate(payload):
        payload["files"] = []

    (
        root,
        inventory_path,
        review_path,
    ) = _mutate_review(
        tmp_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly one row",
    ):
        review.validate_candidate_source_review_scaffold(
            review_path,
            inventory_path,
            root,
        )


def test_review_validate_file_rows_objects(
    tmp_path,
):
    def mutate(payload):
        payload["files"][0] = "bad"

    (
        root,
        inventory_path,
        review_path,
    ) = _mutate_review(
        tmp_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file rows must be JSON objects",
    ):
        review.validate_candidate_source_review_scaffold(
            review_path,
            inventory_path,
            root,
        )


def test_review_validate_identity(
    tmp_path,
):
    def mutate(payload):
        payload["files"][0]["bytes"] += 1

    (
        root,
        inventory_path,
        review_path,
    ) = _mutate_review(
        tmp_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="path/hash/size identity",
    ):
        review.validate_candidate_source_review_scaffold(
            review_path,
            inventory_path,
            root,
        )


@pytest.mark.parametrize(
    "dataset_key",
    [
        "hollywood2em",
        "gaze-in-the-wild",
    ],
)
def test_review_validate_unedited_success(
    tmp_path,
    dataset_key,
):
    (
        root,
        inventory,
        inventory_path,
        _,
        review_path,
    ) = _review_bundle(
        tmp_path,
        dataset_key=dataset_key,
    )

    observed = review.validate_candidate_source_review_scaffold(
        review_path,
        inventory_path,
        root,
    )

    assert observed.candidate_file_count == inventory.file_count
