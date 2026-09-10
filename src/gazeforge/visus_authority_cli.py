"""Strict authority-aware console wrapper for empirical VISUS workflows."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

from . import visus_cli as _legacy
from .exceptions import BenchmarkIntegrityError
from .visus_audit import load_visus_source_audit_spec
from .visus_authority_binding import (
    audit_visus_source_with_authority,
    load_visus_source_authority_certificate,
)
from .visus_authority_execution import (
    bind_visus_suite_to_source_authority,
    build_visus_authority_execution_provenance,
    snapshot_visus_authority_execution_inputs,
    validate_visus_authority_execution_provenance,
    verify_visus_authority_execution_inputs_unchanged,
    write_visus_authority_execution_provenance,
)

_EMPIRICAL_COMMANDS = frozenset(
    {
        "audit",
        "human-intake",
        "prediction-intake",
        "suite",
    }
)
_AUTHORITY_OPTION = "--authority-certificate"


def _extract_authority_option(
    argv: Sequence[str],
) -> tuple[Path | None, list[str]]:
    values = list(argv)
    if not values:
        return None, values
    command = values[0]
    if command not in _EMPIRICAL_COMMANDS:
        return None, values

    positions: list[tuple[int, str]] = []
    for index, value in enumerate(values[1:], start=1):
        if value == _AUTHORITY_OPTION:
            if index + 1 >= len(values):
                raise SystemExit(
                    "gazeforge-visus: error: --authority-certificate requires a path"
                )
            positions.append((index, values[index + 1]))
        elif value.startswith(f"{_AUTHORITY_OPTION}="):
            positions.append((index, value.split("=", 1)[1]))

    if not positions:
        raise SystemExit(
            "gazeforge-visus: error: empirical VISUS commands require "
            "--authority-certificate PATH"
        )
    if len(positions) != 1:
        raise SystemExit(
            "gazeforge-visus: error: --authority-certificate must be supplied exactly once"
        )
    index, raw_path = positions[0]
    if not str(raw_path).strip():
        raise SystemExit(
            "gazeforge-visus: error: --authority-certificate requires a non-empty path"
        )

    forwarded = list(values)
    if forwarded[index] == _AUTHORITY_OPTION:
        del forwarded[index : index + 2]
    else:
        del forwarded[index]
    return Path(raw_path), forwarded


@contextmanager
def _authority_runtime(
    certificate_path: Path | None,
) -> Iterator[None]:
    saved = {
        "_load_audit": _legacy._load_audit,
        "snapshot_visus_execution_inputs": _legacy.snapshot_visus_execution_inputs,
        "verify_visus_execution_inputs_unchanged": (
            _legacy.verify_visus_execution_inputs_unchanged
        ),
        "run_visus_dynamic_aoi_validation_suite": (
            _legacy.run_visus_dynamic_aoi_validation_suite
        ),
        "build_visus_execution_provenance": _legacy.build_visus_execution_provenance,
        "write_visus_execution_provenance": _legacy.write_visus_execution_provenance,
        "validate_visus_execution_provenance": (
            _legacy.validate_visus_execution_provenance
        ),
    }
    base_suite_runner = _legacy.run_visus_dynamic_aoi_validation_suite

    def load_bound_audit(source_root: Path, spec_path: Path):
        if certificate_path is None:
            raise BenchmarkIntegrityError(
                "Empirical VISUS execution requires a reviewed authority certificate."
            )
        spec = load_visus_source_audit_spec(spec_path)
        certificate = load_visus_source_authority_certificate(certificate_path)
        return audit_visus_source_with_authority(
            source_root,
            spec,
            certificate,
        )

    def snapshot_inputs(**kwargs):
        if certificate_path is None:
            raise BenchmarkIntegrityError(
                "VISUS suite execution requires an authority certificate."
            )
        return snapshot_visus_authority_execution_inputs(
            source_authority_certificate=certificate_path,
            **kwargs,
        )

    def verify_inputs(snapshots, **kwargs):
        if certificate_path is None:
            raise BenchmarkIntegrityError(
                "VISUS suite execution requires an authority certificate."
            )
        return verify_visus_authority_execution_inputs_unchanged(
            snapshots,
            source_authority_certificate=certificate_path,
            **kwargs,
        )

    def run_bound_suite(audit, *args, **kwargs):
        suite = base_suite_runner(audit, *args, **kwargs)
        return bind_visus_suite_to_source_authority(audit, suite)

    _legacy._load_audit = load_bound_audit
    _legacy.snapshot_visus_execution_inputs = snapshot_inputs
    _legacy.verify_visus_execution_inputs_unchanged = verify_inputs
    _legacy.run_visus_dynamic_aoi_validation_suite = run_bound_suite
    _legacy.build_visus_execution_provenance = build_visus_authority_execution_provenance
    _legacy.write_visus_execution_provenance = write_visus_authority_execution_provenance
    _legacy.validate_visus_execution_provenance = validate_visus_authority_execution_provenance
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(_legacy, name, value)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the VISUS CLI with fail-closed authority binding for empirical creation."""
    values = list(sys.argv[1:] if argv is None else argv)
    certificate_path, forwarded = _extract_authority_option(values)
    if (
        forwarded
        and forwarded[0] in _EMPIRICAL_COMMANDS
        and any(value in {"-h", "--help"} for value in forwarded[1:])
    ):
        print(
            "Authority requirement: empirical VISUS commands also require "
            "--authority-certificate PATH."
        )
    with _authority_runtime(certificate_path):
        return _legacy.main(forwarded)


if __name__ == "__main__":
    raise SystemExit(main())
