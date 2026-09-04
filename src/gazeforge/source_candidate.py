"""Exact non-empirical inventories for candidate external benchmark copies."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .exceptions import BenchmarkIntegrityError

_RECORD_TYPE = "candidate-source-inventory-v1"
_ALLOWED_DATASET_KEYS = {"hollywood2em", "gaze-in-the-wild"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SCIENTIFIC_BOUNDARY = {
    "candidate_copy_only": True,
    "source_authority_verified": False,
    "reuse_terms_verified": False,
    "analysis_use_permitted": False,
    "source_audit_ready": False,
    "empirical_evidence_created": False,
}


def _canonical_fingerprint(dataset_key: str, files: Sequence[CandidateSourceFile]) -> str:
    payload = {
        "dataset_key": dataset_key,
        "files": [record.to_dict() for record in files],
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _dataset_key(value: Any) -> str:
    key = str(value).strip().lower()
    if key not in _ALLOWED_DATASET_KEYS:
        allowed = ", ".join(sorted(_ALLOWED_DATASET_KEYS))
        raise ValueError(f"dataset_key must be one of: {allowed}.")
    return key


@dataclass(frozen=True, slots=True)
class CandidateSourceFile:
    """One exact regular file in a candidate external benchmark snapshot."""

    path: str
    sha256: str
    bytes: int

    def __post_init__(self) -> None:
        relative = PurePosixPath(str(self.path))
        unsafe = relative.is_absolute() or not relative.parts or any(
            part in {"", ".", ".."} for part in relative.parts
        )
        if unsafe:
            raise ValueError("Candidate source paths must be safe relative POSIX paths.")
        digest = str(self.sha256).strip().lower()
        if _SHA256_RE.fullmatch(digest) is None:
            raise ValueError("Candidate source sha256 must contain 64 hexadecimal characters.")
        size = int(self.bytes)
        if size <= 0:
            raise ValueError("Candidate source byte size must be positive.")
        object.__setattr__(self, "path", relative.as_posix())
        object.__setattr__(self, "sha256", digest)
        object.__setattr__(self, "bytes", size)

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible file record."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CandidateSourceInventory:
    """Exact local snapshot that deliberately carries no scientific identity inference."""

    root: Path
    dataset_key: str
    files: tuple[CandidateSourceFile, ...]
    inventory_fingerprint_sha256: str

    @property
    def file_count(self) -> int:
        """Number of regular files captured by the snapshot."""
        return len(self.files)

    def to_dict(self) -> dict[str, Any]:
        """Return the portable non-empirical inventory payload."""
        return {
            "record_type": _RECORD_TYPE,
            "dataset_key": self.dataset_key,
            "file_count": self.file_count,
            "files": [record.to_dict() for record in self.files],
            "inventory_fingerprint_sha256": self.inventory_fingerprint_sha256,
            "scientific_boundary": dict(_SCIENTIFIC_BOUNDARY),
        }


def _inventory_root(root: Path) -> tuple[CandidateSourceFile, ...]:
    if root.is_symlink():
        raise BenchmarkIntegrityError(
            "Candidate source inventory refuses a symbolic-link root because snapshot identity "
            "must refer to the reviewed directory itself."
        )
    if not root.is_dir():
        raise FileNotFoundError(f"Candidate source directory does not exist: {root}")

    resolved = root.resolve()
    entries = sorted(resolved.rglob("*"), key=lambda path: path.relative_to(resolved).as_posix())
    symlinks = [path.relative_to(resolved).as_posix() for path in entries if path.is_symlink()]
    if symlinks:
        raise BenchmarkIntegrityError(
            "Candidate source inventory refuses symbolic links because snapshot identity must not "
            f"depend on external targets: {symlinks}"
        )

    regular_files = [path for path in entries if path.is_file()]
    if not regular_files:
        raise ValueError("Candidate source inventory requires at least one regular file.")

    records: list[CandidateSourceFile] = []
    for path in regular_files:
        relative = path.relative_to(resolved).as_posix()
        size = int(path.stat().st_size)
        if size <= 0:
            raise BenchmarkIntegrityError(
                "Candidate source inventory refuses zero-byte files in an exact snapshot: "
                f"{relative!r}."
            )
        records.append(
            CandidateSourceFile(
                path=relative,
                sha256=_file_sha256(path),
                bytes=size,
            )
        )
    return tuple(records)


def build_candidate_source_inventory(
    root: str | Path,
    *,
    dataset_key: str,
) -> CandidateSourceInventory:
    """Fingerprint a candidate Hollywood2EM or Gaze-in-the-Wild copy without inferring semantics.

    The inventory deliberately records only safe relative paths, byte sizes, and SHA-256 digests.
    File names, directory names, extensions, and apparent structure are not converted into
    participant, trial, annotator, coordinate, licensing, source-authority, or empirical-evidence
    claims.
    """
    key = _dataset_key(dataset_key)
    source = Path(root)
    files = _inventory_root(source)
    resolved = source.resolve()
    fingerprint = _canonical_fingerprint(key, files)
    return CandidateSourceInventory(
        root=resolved,
        dataset_key=key,
        files=files,
        inventory_fingerprint_sha256=fingerprint,
    )


def write_candidate_source_inventory(
    inventory: CandidateSourceInventory,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a portable inventory outside the candidate source tree."""
    if not isinstance(inventory, CandidateSourceInventory):
        raise TypeError("inventory must be a CandidateSourceInventory instance.")
    target = Path(path)
    resolved_target = target.resolve(strict=False)
    if resolved_target == inventory.root or inventory.root in resolved_target.parents:
        raise BenchmarkIntegrityError(
            "Candidate source inventory output must be outside the inventoried tree so writing the "
            "manifest cannot mutate the snapshot it describes."
        )
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(inventory.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return target


def _load_inventory_payload(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            "Candidate source inventory must be valid UTF-8 JSON."
        ) from exc
    if not isinstance(payload, Mapping):
        raise BenchmarkIntegrityError("Candidate source inventory must contain one JSON object.")
    return payload


def validate_candidate_source_inventory(
    inventory_path: str | Path,
    root: str | Path,
) -> CandidateSourceInventory:
    """Revalidate a saved candidate inventory against the complete current local tree."""
    payload = _load_inventory_payload(Path(inventory_path))
    if payload.get("record_type") != _RECORD_TYPE:
        raise BenchmarkIntegrityError(
            f"Candidate source record_type must be {_RECORD_TYPE!r}."
        )
    key = _dataset_key(payload.get("dataset_key"))
    if payload.get("scientific_boundary") != _SCIENTIFIC_BOUNDARY:
        raise BenchmarkIntegrityError(
            "Candidate source scientific_boundary must preserve the non-empirical limits exactly."
        )

    raw_files = payload.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise BenchmarkIntegrityError("Candidate source inventory requires a non-empty files list.")
    try:
        files = tuple(
            CandidateSourceFile(
                path=item["path"],
                sha256=item["sha256"],
                bytes=item["bytes"],
            )
            for item in raw_files
            if isinstance(item, Mapping)
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise BenchmarkIntegrityError("Candidate source file records are invalid.") from exc
    if len(files) != len(raw_files):
        raise BenchmarkIntegrityError("Candidate source files must all be JSON objects.")
    paths = [record.path for record in files]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise BenchmarkIntegrityError(
            "Candidate source file records must be uniquely sorted by relative path."
        )

    file_count = payload.get("file_count")
    if not isinstance(file_count, int) or isinstance(file_count, bool) or file_count != len(files):
        raise BenchmarkIntegrityError(
            "Candidate source file_count must exactly match the inventoried file list."
        )

    expected_fingerprint = _canonical_fingerprint(key, files)
    stored_fingerprint = str(payload.get("inventory_fingerprint_sha256", "")).strip().lower()
    if stored_fingerprint != expected_fingerprint:
        raise BenchmarkIntegrityError(
            "Candidate source inventory fingerprint does not match its serialized content."
        )

    current = build_candidate_source_inventory(root, dataset_key=key)
    if current.files != files:
        raise BenchmarkIntegrityError(
            "Candidate source tree no longer matches the saved exact file inventory."
        )
    if current.inventory_fingerprint_sha256 != expected_fingerprint:
        raise BenchmarkIntegrityError(
            "Candidate source tree fingerprint no longer matches the saved inventory."
        )
    return current
