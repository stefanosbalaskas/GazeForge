from __future__ import annotations

import json
import stat
import warnings
import zipfile
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_participant_ledger_intake import (
    EXPECTED_ARCHIVE_BASENAME,
    _safe_member_name,
    inspect_original_archive,
    record_fingerprint,
    validate_intake_record,
)


def _archive_path(tmp_path: Path) -> Path:
    return tmp_path / EXPECTED_ARCHIVE_BASENAME


def _write_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in members.items():
            archive.writestr(name, body)


def _valid_archive(tmp_path: Path) -> Path:
    path = _archive_path(tmp_path)
    _write_zip(
        path,
        {
            "README.txt": (
                b"The dataset lists unique subject IDs within each task group.\n"
                b"Active and free-viewing groups are distinct.\n"
                b"Subject ID 001\nSubject ID 002\n"
            ),
            "data/raw_gaze_001.txt.gz": b"raw-gaze-placeholder-that-must-never-be-opened",
            "notes/metadata.json": b'{"description":"participant metadata"}',
        },
    )
    return path


def _refingerprint(record: dict) -> dict:
    record["record_fingerprint_sha256"] = record_fingerprint(record)
    return record


def test_valid_intake_reads_only_bounded_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _valid_archive(tmp_path)
    opened: list[str] = []
    original_read = zipfile.ZipFile.read

    def tracked_read(self, name, pwd=None):  # noqa: ANN001, ANN202
        member = name.filename if isinstance(name, zipfile.ZipInfo) else str(name)
        opened.append(member)
        return original_read(self, name, pwd=pwd)

    monkeypatch.setattr(zipfile.ZipFile, "read", tracked_read)
    record = inspect_original_archive(path, authorized_local_copy=True)
    validated = validate_intake_record(record)

    assert validated["archive"]["basename"] == EXPECTED_ARCHIVE_BASENAME
    assert validated["metadata_inspection"]["candidate_count"] == 2
    assert validated["metadata_inspection"]["inspected_count"] == 2
    assert validated["metadata_inspection"]["raw_gaze_members_opened"] == 0
    assert validated["metadata_inspection"]["archive_members_extracted_to_disk"] == 0
    assert "data/raw_gaze_001.txt.gz" not in opened
    assert set(opened) == {"README.txt", "notes/metadata.json"}
    assert validated["mapping_boundary"]["participant_identity_mapping_verified"] is False
    assert validated["mapping_boundary"]["gin_token_to_task_group_verified"] is False

    readme = next(
        item
        for item in validated["metadata_inspection"]["inspected"]
        if item["member"] == "README.txt"
    )
    summary = readme["text_summary"]
    assert summary["states_unique_subject_ids"] is True
    assert summary["mentions_active_and_free_viewing_groups"] is True
    assert summary["subject_id_like_line_count"] == 2
    serialized = json.dumps(validated)
    assert "Subject ID 001" not in serialized
    assert "Subject ID 002" not in serialized


def test_authorization_affirmation_is_required(tmp_path: Path) -> None:
    path = _valid_archive(tmp_path)
    with pytest.raises(BenchmarkIntegrityError, match="authorized local copy"):
        inspect_original_archive(path, authorized_local_copy=False)


def test_expected_archive_basename_is_required(tmp_path: Path) -> None:
    path = tmp_path / "renamed.zip"
    _write_zip(path, {"README.txt": b"metadata"})
    with pytest.raises(BenchmarkIntegrityError, match="Expected archive basename"):
        inspect_original_archive(path, authorized_local_copy=True)


def test_invalid_zip_is_rejected(tmp_path: Path) -> None:
    path = _archive_path(tmp_path)
    path.write_bytes(b"not a zip")
    with pytest.raises(BenchmarkIntegrityError, match="not a valid ZIP"):
        inspect_original_archive(path, authorized_local_copy=True)


@pytest.mark.parametrize(
    "unsafe_name",
    ["../README.txt", "/README.txt", "C:/README.txt"],
)
def test_unsafe_member_paths_are_rejected(tmp_path: Path, unsafe_name: str) -> None:
    path = _archive_path(tmp_path)
    _write_zip(path, {unsafe_name: b"metadata"})
    with pytest.raises(BenchmarkIntegrityError, match="unsafe member path"):
        inspect_original_archive(path, authorized_local_copy=True)


def test_raw_backslash_member_name_is_rejected_before_zip_normalization() -> None:
    assert _safe_member_name("dir\\README.txt") is False


def test_symbolic_link_member_is_rejected(tmp_path: Path) -> None:
    path = _archive_path(tmp_path)
    info = zipfile.ZipInfo("README.txt")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(info, b"target")
    with pytest.raises(BenchmarkIntegrityError, match="symbolic-link"):
        inspect_original_archive(path, authorized_local_copy=True)


def test_duplicate_member_names_are_rejected(tmp_path: Path) -> None:
    path = _archive_path(tmp_path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("README.txt", b"first")
            archive.writestr("README.txt", b"second")
    with pytest.raises(BenchmarkIntegrityError, match="duplicate member names"):
        inspect_original_archive(path, authorized_local_copy=True)


def test_large_metadata_candidate_is_skipped_without_opening(tmp_path: Path) -> None:
    path = _archive_path(tmp_path)
    _write_zip(path, {"README.txt": b"x" * (512 * 1024 + 1)})
    record = inspect_original_archive(path, authorized_local_copy=True)
    assert record["metadata_inspection"]["candidate_count"] == 1
    assert record["metadata_inspection"]["inspected_count"] == 0
    assert record["metadata_inspection"]["skipped_count"] == 1
    assert record["metadata_inspection"]["skipped"][0]["reason"] == (
        "member_size_guardrail"
    )


def test_intake_fingerprint_is_self_validating(tmp_path: Path) -> None:
    record = inspect_original_archive(_valid_archive(tmp_path), authorized_local_copy=True)
    assert record["record_fingerprint_sha256"] == record_fingerprint(record)
    record["archive"]["member_count"] += 1
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint drifted"):
        validate_intake_record(record)


def test_refingerprinted_mapping_promotion_is_rejected(tmp_path: Path) -> None:
    record = inspect_original_archive(_valid_archive(tmp_path), authorized_local_copy=True)
    record["mapping_boundary"]["participant_identity_mapping_verified"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_intake_record(record)


def test_refingerprinted_raw_gaze_opening_is_rejected(tmp_path: Path) -> None:
    record = inspect_original_archive(_valid_archive(tmp_path), authorized_local_copy=True)
    record["metadata_inspection"]["raw_gaze_members_opened"] = 1
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="opened raw gaze"):
        validate_intake_record(record)


def test_refingerprinted_redistribution_promotion_is_rejected(tmp_path: Path) -> None:
    record = inspect_original_archive(_valid_archive(tmp_path), authorized_local_copy=True)
    record["rights_boundary"]["redistribution_authorized_by_this_intake"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_intake_record(record)
