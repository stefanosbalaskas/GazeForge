"""Closed-schema certificate semantics layered onto authority-bound VISUS provenance v2."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .visus_audit import VisusSourceAuditRun
from .visus_authoritative_source_certificate import validate_certificate_record
from .visus_authority_binding import (
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
    source_authority_certificate_record,
)
from .visus_authority_execution import (
    VisusExecutionInputSnapshot,
    VisusExecutionProvenanceRun,
    build_visus_authority_execution_provenance as _build_transport_provenance,
    validate_visus_authority_execution_provenance as _validate_transport_provenance,
    write_visus_authority_execution_provenance as _write_transport_provenance,
)
from .visus_suite import VisusDynamicAOIValidationSuiteRun

AUTHORITY_CERTIFICATE_RECORD_FIELD = "source_authority_certificate"
_AUTHORITY_ROLE = "source_authority_certificate"


def _valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _read_manifest(path: str | Path) -> tuple[Path, dict[str, Any]]:
    source = Path(path)
    manifest_path = source / "visus-execution-provenance.json" if source.is_dir() else source
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance is not valid JSON."
        ) from exc
    if not isinstance(value, dict):
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance must be a JSON object."
        )
    return manifest_path, value


def _embedded_certificate(manifest: Mapping[str, Any]) -> dict[str, Any]:
    raw = manifest.get(AUTHORITY_CERTIFICATE_RECORD_FIELD)
    if not isinstance(raw, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance is missing the reviewed certificate record."
        )
    certificate = validate_certificate_record(raw)

    source = manifest.get("source")
    rows = manifest.get("raw_inputs")
    if not isinstance(source, Mapping) or not isinstance(rows, list):
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance source/input structure is invalid."
        )
    fingerprint = certificate["certificate_fingerprint_sha256"]
    if source.get(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD) != fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS embedded authority certificate does not match the execution source identity."
        )
    authority_rows = [
        row
        for row in rows
        if isinstance(row, Mapping) and row.get("role") == _AUTHORITY_ROLE
    ]
    if len(authority_rows) != 1:
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance requires one authority-certificate raw input."
        )
    if authority_rows[0].get("semantic_fingerprint_sha256") != fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS embedded authority certificate does not match its raw-input semantic identity."
        )
    return certificate


def build_visus_authority_execution_provenance(
    audit: VisusSourceAuditRun,
    suite: VisusDynamicAOIValidationSuiteRun,
    snapshots: tuple[VisusExecutionInputSnapshot, ...],
) -> dict[str, Any]:
    """Build v2 provenance and preserve the validated, non-raw authority certificate semantics."""
    manifest = _build_transport_provenance(audit, suite, snapshots)
    certificate = source_authority_certificate_record(audit, required=True)
    assert certificate is not None

    body = {
        key: copy.deepcopy(value)
        for key, value in manifest.items()
        if key != "execution_fingerprint_sha256"
    }
    if AUTHORITY_CERTIFICATE_RECORD_FIELD in body:
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance already contains a certificate record."
        )
    body[AUTHORITY_CERTIFICATE_RECORD_FIELD] = certificate
    result = {
        **body,
        "execution_fingerprint_sha256": benchmark_fingerprint(body),
    }
    _embedded_certificate(result)
    return result


def validate_visus_authority_execution_provenance(
    path: str | Path,
    *,
    verify_suite: bool = True,
) -> dict[str, Any]:
    """Validate v2 transport, then revalidate the embedded certificate closed schema."""
    manifest_path, manifest = _read_manifest(path)
    claimed = manifest.get("execution_fingerprint_sha256")
    body = {
        key: value
        for key, value in manifest.items()
        if key != "execution_fingerprint_sha256"
    }
    if not _valid_sha256(claimed) or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance fingerprint mismatch."
        )
    certificate = _embedded_certificate(manifest)
    summary = _validate_transport_provenance(
        manifest_path,
        verify_suite=verify_suite,
    )
    fingerprint = certificate["certificate_fingerprint_sha256"]
    if summary.get(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD) != fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS authority execution certificate/transport identity mismatch."
        )
    return {
        **summary,
        "authority_certificate_semantics_verified": True,
        AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: fingerprint,
    }


def write_visus_authority_execution_provenance(
    manifest: dict[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> VisusExecutionProvenanceRun:
    """Write v2 provenance only after the embedded certificate semantics revalidate."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest must be a dictionary.")
    _embedded_certificate(manifest)
    run = _write_transport_provenance(
        manifest,
        output_dir,
        overwrite=overwrite,
    )
    validate_visus_authority_execution_provenance(
        run.manifest_path,
        verify_suite=True,
    )
    return run
