from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

import gazeforge.visus_authoritative_source_common as common
from gazeforge.exceptions import BenchmarkIntegrityError

A = "a" * 64
B = "b" * 64
C = "c" * 64


def _manifest(
    *,
    file_count: Any = 2,
) -> dict[str, Any]:
    return {
        "record_type": common.SOURCE_RECORD_TYPE,
        "source_reference": "synthetic://visus-source",
        "source_revision": "fixture-revision-1",
        "source_authority_claim": "institutional_repository",
        "source_artifact_sha256": A,
        "rights_evidence_reference": "synthetic://rights",
        "rights_evidence_sha256": B,
        "inventory_fingerprint_sha256": C,
        "file_count": file_count,
        "obtained_via_authorized_channel_affirmed": True,
    }


def test_canonical_bytes_are_deterministic() -> None:
    left = {
        "b": 2,
        "a": 1,
    }

    right = {
        "a": 1,
        "b": 2,
    }

    assert common._canonical_bytes(left) == common._canonical_bytes(right)


def test_canonical_bytes_reject_nan() -> None:
    with pytest.raises(ValueError):
        common._canonical_bytes(
            {
                "x": float("nan"),
            }
        )


@pytest.mark.parametrize(
    ("function", "field"),
    [
        (
            common.candidate_fingerprint,
            "candidate_fingerprint_sha256",
        ),
        (
            common.review_fingerprint,
            "review_fingerprint_sha256",
        ),
        (
            common.certificate_fingerprint,
            "certificate_fingerprint_sha256",
        ),
    ],
)
def test_public_fingerprint_helpers_ignore_self_field(
    function,
    field: str,
) -> None:
    record = {
        "a": 1,
    }

    before = function(record)

    record[field] = "0" * 64

    after = function(record)

    assert before == after
    assert len(before) == 64


def test_generic_fingerprint_success() -> None:
    value = {
        "x": 1,
        "fingerprint": "ignored",
    }

    observed = common._fingerprint(
        value,
        field="fingerprint",
    )

    expected = hashlib.sha256(
        common._canonical_bytes(
            {
                "x": 1,
            }
        )
    ).hexdigest()

    assert observed == expected


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        " ",
        "review_required",
        "REVIEW_REQUIRED",
        "__unresolved__",
        "unknown",
        "none",
        "nan",
        "todo",
        "tbd",
    ],
)
def test_resolved_text_rejects_unresolved_values(
    value: Any,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires resolved",
    ):
        common._resolved_text(
            value,
            label="fixture",
        )


def test_resolved_text_length_guard() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="exceeds text guardrail",
    ):
        common._resolved_text(
            "x" * (common.MAX_TEXT_FIELD_LENGTH + 1),
            label="fixture",
        )


def test_resolved_text_success_and_strip() -> None:
    assert (
        common._resolved_text(
            "  resolved value  ",
            label="fixture",
        )
        == "resolved value"
    )


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "a" * 63,
        "A" * 64,
        "g" * 64,
        "not-a-hash",
    ],
)
def test_sha256_value_rejects_invalid_digest(
    value: Any,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="lowercase SHA-256 digest",
    ):
        common._sha256_value(
            value,
            label="fixture",
        )


def test_sha256_value_success() -> None:
    assert (
        common._sha256_value(
            A,
            label="fixture",
        )
        == A
    )


def test_hash_file_missing_guard(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-symlink regular file",
    ):
        common._hash_file(
            tmp_path / "missing.bin",
            label="fixture",
        )


def test_hash_file_symlink_guard_portable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"abc")

    original = Path.is_symlink

    def fake_is_symlink(
        self: Path,
    ) -> bool:
        if self == path:
            return True
        return original(self)

    monkeypatch.setattr(
        Path,
        "is_symlink",
        fake_is_symlink,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-symlink regular file",
    ):
        common._hash_file(
            path,
            label="fixture",
        )


def test_hash_file_empty_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="size is outside",
    ):
        common._hash_file(
            path,
            label="fixture",
        )


def test_hash_file_max_size_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"abc")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="size is outside",
    ):
        common._hash_file(
            path,
            label="fixture",
            max_bytes=2,
        )


def test_hash_file_success_without_max(
    tmp_path: Path,
) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"abc")

    size, digest = common._hash_file(
        path,
        label="fixture",
    )

    assert size == 3

    assert digest == hashlib.sha256(b"abc").hexdigest()


def test_hash_file_success_with_max(
    tmp_path: Path,
) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"abc")

    size, digest = common._hash_file(
        path,
        label="fixture",
        max_bytes=3,
    )

    assert size == 3
    assert len(digest) == 64


def test_read_json_invalid_json_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad.json"

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        common._read_json(
            path,
            label="fixture",
            max_bytes=100,
        )


def test_read_json_invalid_utf8_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad.json"
    path.write_bytes(b"\xff\xfe")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        common._read_json(
            path,
            label="fixture",
            max_bytes=100,
        )


def test_read_json_oserror_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "payload.json"

    path.write_text(
        "{}",
        encoding="utf-8",
    )

    original = Path.read_text

    def fake_read_text(
        self: Path,
        *args,
        **kwargs,
    ):
        if self == path:
            raise OSError("synthetic read failure")

        return original(
            self,
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        Path,
        "read_text",
        fake_read_text,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        common._read_json(
            path,
            label="fixture",
            max_bytes=100,
        )


def test_read_json_requires_object(
    tmp_path: Path,
) -> None:
    path = tmp_path / "array.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        common._read_json(
            path,
            label="fixture",
            max_bytes=100,
        )


def test_read_json_success(
    tmp_path: Path,
) -> None:
    path = tmp_path / "payload.json"

    path.write_text(
        '{"x": 1}',
        encoding="utf-8",
    )

    assert common._read_json(
        path,
        label="fixture",
        max_bytes=100,
    ) == {
        "x": 1,
    }


def test_require_exact_keys_success() -> None:
    common._require_exact_keys(
        {
            "a": 1,
            "b": 2,
        },
        {
            "a",
            "b",
        },
        label="fixture",
    )


def test_require_exact_keys_missing_guard() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match=r"missing=\['b'\]",
    ):
        common._require_exact_keys(
            {
                "a": 1,
            },
            {
                "a",
                "b",
            },
            label="fixture",
        )


def test_require_exact_keys_extra_guard() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match=r"extra=\['c'\]",
    ):
        common._require_exact_keys(
            {
                "a": 1,
                "b": 2,
                "c": 3,
            },
            {
                "a",
                "b",
            },
            label="fixture",
        )


def test_outside_root_rejects_root_itself(
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve()

    with pytest.raises(
        BenchmarkIntegrityError,
        match="outside the inventoried source tree",
    ):
        common._outside_root(
            root,
            root,
            label="fixture",
        )


def test_outside_root_rejects_descendant(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    root.mkdir()

    child = root / "inside.txt"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="outside the inventoried source tree",
    ):
        common._outside_root(
            root.resolve(),
            child,
            label="fixture",
        )


def test_outside_root_success(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    root.mkdir()

    external = tmp_path / "external.txt"

    common._outside_root(
        root.resolve(),
        external,
        label="fixture",
    )


def test_validate_source_manifest_success() -> None:
    common._validate_source_manifest(
        _manifest(),
        source_sha256=A,
        rights_sha256=B,
        inventory_fingerprint_sha256=C,
        file_count=2,
    )


def test_validate_source_manifest_schema_guard() -> None:
    manifest = _manifest()
    manifest["extra"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source manifest schema drifted",
    ):
        common._validate_source_manifest(
            manifest,
            source_sha256=A,
            rights_sha256=B,
            inventory_fingerprint_sha256=C,
            file_count=2,
        )


def test_validate_source_manifest_record_type_guard() -> None:
    manifest = _manifest()
    manifest["record_type"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record type drifted",
    ):
        common._validate_source_manifest(
            manifest,
            source_sha256=A,
            rights_sha256=B,
            inventory_fingerprint_sha256=C,
            file_count=2,
        )


@pytest.mark.parametrize(
    "field",
    [
        "source_reference",
        "source_revision",
        "rights_evidence_reference",
    ],
)
def test_validate_source_manifest_resolved_text_guards(
    field: str,
) -> None:
    manifest = _manifest()
    manifest[field] = "TODO"

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        common._validate_source_manifest(
            manifest,
            source_sha256=A,
            rights_sha256=B,
            inventory_fingerprint_sha256=C,
            file_count=2,
        )


def test_validate_source_manifest_authority_guard() -> None:
    manifest = _manifest()

    manifest["source_authority_claim"] = "third_party_repack"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source_authority_claim is unsupported",
    ):
        common._validate_source_manifest(
            manifest,
            source_sha256=A,
            rights_sha256=B,
            inventory_fingerprint_sha256=C,
            file_count=2,
        )


def test_validate_source_manifest_authorized_channel_guard() -> None:
    manifest = _manifest()

    manifest["obtained_via_authorized_channel_affirmed"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="authorized-channel affirmation",
    ):
        common._validate_source_manifest(
            manifest,
            source_sha256=A,
            rights_sha256=B,
            inventory_fingerprint_sha256=C,
            file_count=2,
        )


@pytest.mark.parametrize(
    ("field", "expected", "match"),
    [
        (
            "source_artifact_sha256",
            A,
            "source artifact bytes",
        ),
        (
            "rights_evidence_sha256",
            B,
            "rights evidence bytes",
        ),
        (
            "inventory_fingerprint_sha256",
            C,
            "source-tree inventory",
        ),
    ],
)
def test_validate_source_manifest_hash_identity_guards(
    field: str,
    expected: str,
    match: str,
) -> None:
    manifest = _manifest()

    manifest[field] = "f" * 64

    assert manifest[field] != expected

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        common._validate_source_manifest(
            manifest,
            source_sha256=A,
            rights_sha256=B,
            inventory_fingerprint_sha256=C,
            file_count=2,
        )


@pytest.mark.parametrize(
    "declared",
    [
        0,
        1,
        3,
        "2",
        None,
        False,
        True,
    ],
)
def test_validate_source_manifest_file_count_guard(
    declared: Any,
) -> None:
    manifest = _manifest(file_count=declared)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file count drifted",
    ):
        common._validate_source_manifest(
            manifest,
            source_sha256=A,
            rights_sha256=B,
            inventory_fingerprint_sha256=C,
            file_count=2,
        )


def test_validate_source_manifest_bool_one_edge_guard() -> None:
    manifest = _manifest(file_count=True)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file count drifted",
    ):
        common._validate_source_manifest(
            manifest,
            source_sha256=A,
            rights_sha256=B,
            inventory_fingerprint_sha256=C,
            file_count=1,
        )
