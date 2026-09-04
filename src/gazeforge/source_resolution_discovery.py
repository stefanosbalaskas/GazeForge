"""Discovery of committed source-resolution checkpoints for governance validation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .source_resolution import validate_source_resolution_records

_RECORD_TYPE = "source-resolution-status-v1"
_PATTERN = "*-source-resolution-*.json"


def discover_source_resolution_paths(root: str | Path) -> tuple[Path, ...]:
    """Discover the complete flat set of source-resolution checkpoints under ``root``.

    Discovery is intentionally filename-constrained and strict. Every matching file must be a JSON
    object with the reviewed v1 record type; malformed or mislabeled candidates fail rather than
    disappearing from the governance gate.
    """
    directory = Path(root)
    if directory.is_symlink():
        raise BenchmarkIntegrityError(
            f"Source-resolution checkpoint discovery refuses symbolic-link directories: {directory}."
        )
    if not directory.is_dir():
        raise NotADirectoryError(directory)

    candidates = tuple(sorted(directory.glob(_PATTERN)))
    if not candidates:
        raise BenchmarkIntegrityError(
            f"No source-resolution checkpoints matching {_PATTERN!r} were found in {directory}."
        )

    for path in candidates:
        if path.is_symlink():
            raise BenchmarkIntegrityError(
                f"Source-resolution checkpoint discovery refuses symbolic links: {path}."
            )
        if not path.is_file():
            raise BenchmarkIntegrityError(
                f"Source-resolution checkpoint candidate is not a regular file: {path}."
            )
        try:
            payload: Any = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise BenchmarkIntegrityError(
                f"Source-resolution checkpoint candidate is not valid UTF-8 JSON: {path}."
            ) from exc
        if not isinstance(payload, Mapping):
            raise BenchmarkIntegrityError(
                f"Source-resolution checkpoint candidate must be a JSON object: {path}."
            )
        if payload.get("record_type") != _RECORD_TYPE:
            raise BenchmarkIntegrityError(
                f"Source-resolution checkpoint candidate {path} must use "
                f"record_type {_RECORD_TYPE!r}."
            )

    return candidates


def validate_source_resolution_directory(root: str | Path) -> dict[str, Any]:
    """Discover and validate every committed source-resolution checkpoint in a directory."""
    return validate_source_resolution_records(discover_source_resolution_paths(root))
