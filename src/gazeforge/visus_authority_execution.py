"""Authority-bound execution provenance for publishable VISUS validation."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .visus_audit import VisusSourceAuditRun
from .visus_authority_binding import (
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
    load_visus_source_authority_certificate,
    source_authority_certificate_fingerprint,
)
from .visus_execution import (
    VisusExecutionInputSnapshot,
    VisusExecutionProvenanceRun,
    _load_suite_children,
    _parsed_input_binding,
    _validate_internal_manifest as _validate_v1_internal_manifest,
    build_visus_execution_provenance as _build_v1_execution_provenance,
    snapshot_visus_execution_inputs as _snapshot_v1_execution_inputs,
    visus_execution_provenance_path,
)
from .visus_suite import (
    VisusDynamicAOIValidationSuiteRun,
    validate_visus_dynamic_aoi_suite_manifest,
)

_EXECUTION_SCHEMA = "gazeforge-visus-execution-provenance-v2"
_EXECUTION_SCOPE = "exact-authority-and-raw-input-files-to-frozen-visus-suite"
_V1_EXECUTION_SCHEMA = "gazeforge-visus-execution-provenance-v1"
_V1_EXECUTION_SCOPE = "exact-raw-input-files-to-frozen-visus-suite"
_AUTHORITY_ROLE = "source_authority_certificate"
_INPUT_ROLES = (
    "source_audit_spec",
    _AUTHORITY_ROLE,
    "human_aoi_table",
    "model_prediction_table",
    "timestamp_grid_json",
)
_BASE_INPUT_ROLES = (
    "source_audit_spec",
    "human_aoi_table",
    "model_prediction_table",
    "timestamp_grid_json",
)
_BASE_SOURCE_KEYS = (
    "source_audit_report_fingerprint_sha256",
    "source_audit_spec_fingerprint_sha256",
    "source_manifest_fingerprint_sha256",
)
_MAX_AUTHORITY_CERTIFICATE_BYTES = 2 * 1024**2


def _valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _hash_regular_file(
    role: str,
    path: str | Path,
    *,
    semantic_fingerprint_sha256: str | None = None,
) -> VisusExecutionInputSnapshot:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise BenchmarkIntegrityError(
            f"VISUS execution input {role!r} must be a non-symlink regular file."
        )
    size = int(source.stat().st_size)
    if size <= 0:
        raise BenchmarkIntegrityError(
            f"VISUS execution input {role!r} must be a non-empty regular file."
        )
    if role == _AUTHORITY_ROLE and size > _MAX_AUTHORITY_CERTIFICATE_BYTES:
        raise BenchmarkIntegrityError(
            "VISUS authority-certificate execution input exceeds the allowed size bound."
        )
    if semantic_fingerprint_sha256 is not None and not _valid_sha256(
        semantic_fingerprint_sha256
    ):
        raise BenchmarkIntegrityError(
            f"VISUS execution input {role!r} has an invalid semantic fingerprint."
        )
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return VisusExecutionInputSnapshot(
        role=role,
        filename=source.name,
        sha256=digest.hexdigest(),
        bytes=size,
        semantic_fingerprint_sha256=semantic_fingerprint_sha256,
    )


def _snapshot_authority_certificate(path: str | Path) -> VisusExecutionInputSnapshot:
    before = _hash_regular_file(_AUTHORITY_ROLE, path)
    certificate = load_visus_source_authority_certificate(path)
    fingerprint = str(certificate["certificate_fingerprint_sha256"])
    after = _hash_regular_file(_AUTHORITY_ROLE, path)
    if before != after:
        raise BenchmarkIntegrityError(
            "VISUS authority certificate changed while its semantic fingerprint was computed."
        )
    return VisusExecutionInputSnapshot(
        role=_AUTHORITY_ROLE,
        filename=before.filename,
        sha256=before.sha256,
        bytes=before.bytes,
        semantic_fingerprint_sha256=fingerprint,
    )


def snapshot_visus_authority_execution_inputs(
    *,
    source_audit_spec: str | Path,
    source_authority_certificate: str | Path,
    human_aoi_table: str | Path,
    model_prediction_table: str | Path,
    timestamp_grid_json: str | Path,
) -> tuple[VisusExecutionInputSnapshot, ...]:
    """Fingerprint the five governed inputs required for publishable VISUS execution."""
    base = _snapshot_v1_execution_inputs(
        source_audit_spec=source_audit_spec,
        human_aoi_table=human_aoi_table,
        model_prediction_table=model_prediction_table,
        timestamp_grid_json=timestamp_grid_json,
    )
    by_role = {item.role: item for item in base}
    authority = _snapshot_authority_certificate(source_authority_certificate)
    return (
        by_role["source_audit_spec"],
        authority,
        by_role["human_aoi_table"],
        by_role["model_prediction_table"],
        by_role["timestamp_grid_json"],
    )


def verify_visus_authority_execution_inputs_unchanged(
    snapshots: tuple[VisusExecutionInputSnapshot, ...],
    *,
    source_audit_spec: str | Path,
    source_authority_certificate: str | Path,
    human_aoi_table: str | Path,
    model_prediction_table: str | Path,
    timestamp_grid_json: str | Path,
) -> None:
    """Refuse provenance freezing when any of the five governed inputs changed."""
    observed = snapshot_visus_authority_execution_inputs(
        source_audit_spec=source_audit_spec,
        source_authority_certificate=source_authority_certificate,
        human_aoi_table=human_aoi_table,
        model_prediction_table=model_prediction_table,
        timestamp_grid_json=timestamp_grid_json,
    )
    if tuple(snapshots) != observed:
        raise BenchmarkIntegrityError(
            "One or more authority-bound VISUS execution inputs changed after the "
            "pre-execution snapshot."
        )


def _suite_authority_fingerprint(
    suite: VisusDynamicAOIValidationSuiteRun | dict[str, Any],
) -> str:
    manifest = suite.manifest if isinstance(suite, VisusDynamicAOIValidationSuiteRun) else suite
    source = manifest.get("source")
    protocol = manifest.get("protocol")
    if not isinstance(source, dict) or not isinstance(protocol, dict):
        raise BenchmarkIntegrityError(
            "VISUS suite authority binding requires source and protocol objects."
        )
    fingerprint = source.get(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD)
    if not _valid_sha256(fingerprint):
        raise BenchmarkIntegrityError(
            "VISUS suite is missing a valid source-authority certificate fingerprint."
        )
    if protocol.get("source_authority_certificate_bound") is not True:
        raise BenchmarkIntegrityError(
            "VISUS suite does not declare an authority-bound source audit."
        )
    if protocol.get(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD) != fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS suite authority fingerprint is inconsistent across source and protocol."
        )
    return str(fingerprint)


def bind_visus_suite_to_source_authority(
    audit: VisusSourceAuditRun,
    suite: VisusDynamicAOIValidationSuiteRun,
) -> VisusDynamicAOIValidationSuiteRun:
    """Add the reviewed authority-certificate identity to one already verified suite."""
    if not isinstance(suite, VisusDynamicAOIValidationSuiteRun):
        raise TypeError("suite must be a VisusDynamicAOIValidationSuiteRun instance.")
    certificate_fingerprint = source_authority_certificate_fingerprint(
        audit,
        required=True,
    )
    assert certificate_fingerprint is not None

    verified = validate_visus_dynamic_aoi_suite_manifest(
        suite.manifest_path,
        verify_reports=True,
    )
    if verified["suite_fingerprint_sha256"] != suite.suite_fingerprint_sha256:
        raise BenchmarkIntegrityError(
            "VISUS suite object does not match its verified completion manifest."
        )
    if verified["source"].get("source_audit_report_fingerprint_sha256") != audit.report.get(
        "report_fingerprint_sha256"
    ):
        raise BenchmarkIntegrityError(
            "VISUS suite cannot be authority-bound to a different source audit."
        )

    body = {
        key: copy.deepcopy(value)
        for key, value in suite.manifest.items()
        if key != "suite_fingerprint_sha256"
    }
    source = body.get("source")
    protocol = body.get("protocol")
    if not isinstance(source, dict) or not isinstance(protocol, dict):
        raise BenchmarkIntegrityError("VISUS suite source/protocol structure is invalid.")

    existing = source.get(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD)
    if existing is not None and existing != certificate_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS suite already carries a different authority-certificate fingerprint."
        )
    source[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = certificate_fingerprint
    protocol["source_authority_certificate_bound"] = True
    protocol[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = certificate_fingerprint

    manifest = {
        **body,
        "suite_fingerprint_sha256": benchmark_fingerprint(body),
    }
    suite.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    suite.manifest = manifest
    suite.suite_fingerprint_sha256 = str(manifest["suite_fingerprint_sha256"])

    revalidated = validate_visus_dynamic_aoi_suite_manifest(
        suite.manifest_path,
        verify_reports=True,
    )
    if revalidated["suite_fingerprint_sha256"] != suite.suite_fingerprint_sha256:
        raise BenchmarkIntegrityError(
            "VISUS authority-bound suite did not revalidate after sealing."
        )
    _suite_authority_fingerprint(suite)
    return suite


def _authority_snapshot(
    snapshots: tuple[VisusExecutionInputSnapshot, ...],
) -> VisusExecutionInputSnapshot:
    if not isinstance(snapshots, tuple) or any(
        not isinstance(item, VisusExecutionInputSnapshot) for item in snapshots
    ):
        raise TypeError(
            "snapshots must be a tuple of VisusExecutionInputSnapshot values."
        )
    roles = tuple(item.role for item in snapshots)
    if roles != _INPUT_ROLES:
        raise BenchmarkIntegrityError(
            "Authority-bound VISUS execution requires exactly five governed input roles."
        )
    return snapshots[1]


def _base_snapshots(
    snapshots: tuple[VisusExecutionInputSnapshot, ...],
) -> tuple[VisusExecutionInputSnapshot, ...]:
    _authority_snapshot(snapshots)
    by_role = {item.role: item for item in snapshots}
    return tuple(by_role[role] for role in _BASE_INPUT_ROLES)


def build_visus_authority_execution_provenance(
    audit: VisusSourceAuditRun,
    suite: VisusDynamicAOIValidationSuiteRun,
    snapshots: tuple[VisusExecutionInputSnapshot, ...],
) -> dict[str, Any]:
    """Build v2 provenance binding the authority certificate plus the four analysis inputs."""
    certificate_fingerprint = source_authority_certificate_fingerprint(
        audit,
        required=True,
    )
    assert certificate_fingerprint is not None
    suite_fingerprint = _suite_authority_fingerprint(suite)
    if suite_fingerprint != certificate_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS suite authority fingerprint does not match the bound source audit."
        )

    authority = _authority_snapshot(snapshots)
    if authority.semantic_fingerprint_sha256 != certificate_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS authority-certificate file does not semantically match the bound audit."
        )

    base_manifest = _build_v1_execution_provenance(
        audit,
        suite,
        _base_snapshots(snapshots),
    )
    body = {
        key: copy.deepcopy(value)
        for key, value in base_manifest.items()
        if key != "execution_fingerprint_sha256"
    }
    body["schema"] = _EXECUTION_SCHEMA
    body["provenance_scope"] = _EXECUTION_SCOPE
    source = body.get("source")
    if not isinstance(source, dict):
        raise BenchmarkIntegrityError("VISUS execution source identity is invalid.")
    source[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = certificate_fingerprint
    body["raw_inputs"] = [asdict(item) for item in snapshots]
    return {
        **body,
        "execution_fingerprint_sha256": benchmark_fingerprint(body),
    }


def _base_projection(manifest: dict[str, Any]) -> dict[str, Any]:
    body = {
        key: copy.deepcopy(value)
        for key, value in manifest.items()
        if key != "execution_fingerprint_sha256"
    }
    body["schema"] = _V1_EXECUTION_SCHEMA
    body["provenance_scope"] = _V1_EXECUTION_SCOPE
    source = body.get("source")
    if not isinstance(source, dict):
        raise BenchmarkIntegrityError("VISUS execution source identity is invalid.")
    source.pop(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD, None)
    rows = body.get("raw_inputs")
    if not isinstance(rows, list):
        raise BenchmarkIntegrityError("VISUS execution raw-input inventory is invalid.")
    body["raw_inputs"] = [
        copy.deepcopy(row)
        for row in rows
        if isinstance(row, dict) and row.get("role") != _AUTHORITY_ROLE
    ]
    return {
        **body,
        "execution_fingerprint_sha256": benchmark_fingerprint(body),
    }


def _validate_authority_row(
    rows: Any,
    *,
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or len(rows) != len(_INPUT_ROLES):
        raise BenchmarkIntegrityError(
            "Authority-bound VISUS execution provenance must bind exactly five raw inputs."
        )
    roles = [str(row.get("role", "")) for row in rows if isinstance(row, dict)]
    if roles != list(_INPUT_ROLES):
        raise BenchmarkIntegrityError(
            "Authority-bound VISUS execution raw-input roles are invalid."
        )
    authority = rows[1]
    if not isinstance(authority, dict):
        raise BenchmarkIntegrityError(
            "VISUS authority-certificate raw-input record is invalid."
        )
    filename = authority.get("filename")
    if (
        not isinstance(filename, str)
        or not filename
        or Path(filename).name != filename
        or not _valid_sha256(authority.get("sha256"))
        or not isinstance(authority.get("bytes"), int)
        or isinstance(authority.get("bytes"), bool)
        or authority["bytes"] <= 0
        or authority["bytes"] > _MAX_AUTHORITY_CERTIFICATE_BYTES
        or not _valid_sha256(authority.get("semantic_fingerprint_sha256"))
    ):
        raise BenchmarkIntegrityError(
            "VISUS authority-certificate raw-input record is incomplete."
        )
    certificate_fingerprint = source.get(
        AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD
    )
    if authority["semantic_fingerprint_sha256"] != certificate_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS authority-certificate semantic fingerprint does not match source identity."
        )
    for row in rows[2:]:
        if not isinstance(row, dict):
            raise BenchmarkIntegrityError(
                "VISUS execution provenance contains a non-object raw-input record."
            )
        if row.get("semantic_fingerprint_sha256") is not None:
            raise BenchmarkIntegrityError(
                "Only the source-audit JSON and authority certificate may carry semantic "
                "raw-input fingerprints."
            )
    return rows


def _validate_suite_binding(
    manifest_path: Path,
    manifest: dict[str, Any],
    *,
    verify_suite: bool,
) -> None:
    if not verify_suite:
        return
    suite = manifest.get("suite")
    if not isinstance(suite, dict):
        raise BenchmarkIntegrityError("VISUS execution suite binding is invalid.")
    summary = validate_visus_dynamic_aoi_suite_manifest(
        manifest_path.parent / str(suite.get("manifest_filename", "")),
        verify_reports=True,
    )
    if summary["suite_fingerprint_sha256"] != suite.get("suite_fingerprint_sha256"):
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance/suite fingerprint mismatch."
        )
    if int(summary["report_count"]) != int(suite.get("report_count", -1)):
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance/suite report-count mismatch."
        )

    source = manifest["source"]
    observed_base = {
        key: str(summary["source"].get(key, ""))
        for key in _BASE_SOURCE_KEYS
    }
    expected_base = {key: str(source.get(key, "")) for key in _BASE_SOURCE_KEYS}
    if observed_base != expected_base:
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance/suite source identity mismatch."
        )
    observed_authority = summary["source"].get(
        AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD
    )
    if observed_authority != source.get(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD):
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance/suite certificate identity mismatch."
        )
    protocol = summary.get("protocol")
    if not isinstance(protocol, dict):
        raise BenchmarkIntegrityError("VISUS suite protocol must be a dictionary.")
    if protocol.get("source_authority_certificate_bound") is not True:
        raise BenchmarkIntegrityError(
            "VISUS suite lacks the required authority-bound protocol declaration."
        )
    if protocol.get(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD) != observed_authority:
        raise BenchmarkIntegrityError(
            "VISUS suite authority protocol/source fingerprint mismatch."
        )

    children = _load_suite_children(manifest_path.parent, summary)
    reference = children.get("human_reference_intake")
    prediction = children.get("model_prediction_intake")
    if not isinstance(reference, dict) or not isinstance(prediction, dict):
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance cannot recover verified intake children."
        )
    observed_parsed = _parsed_input_binding(
        reference,
        prediction,
        protocol,
    )
    if observed_parsed != manifest.get("parsed_inputs"):
        raise BenchmarkIntegrityError(
            "VISUS authority execution parsed-input binding does not match suite children."
        )


def validate_visus_authority_execution_provenance(
    path: str | Path,
    *,
    verify_suite: bool = True,
) -> dict[str, Any]:
    """Validate the v2 five-input authority-bound VISUS execution manifest."""
    source_path = Path(path)
    manifest_path = (
        visus_execution_provenance_path(source_path)
        if source_path.is_dir()
        else source_path
    )
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance is not valid JSON."
        ) from exc
    if not isinstance(manifest, dict):
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance must be a JSON object."
        )
    claimed = str(manifest.get("execution_fingerprint_sha256", ""))
    body = {
        key: value
        for key, value in manifest.items()
        if key != "execution_fingerprint_sha256"
    }
    if not _valid_sha256(claimed) or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance fingerprint mismatch."
        )
    if manifest.get("schema") != _EXECUTION_SCHEMA:
        raise BenchmarkIntegrityError(
            "VISUS Frozen Evidence requires authority-bound execution provenance v2."
        )
    if manifest.get("status") != "complete":
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance status is invalid."
        )
    if manifest.get("provenance_scope") != _EXECUTION_SCOPE:
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance scope is invalid."
        )
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise BenchmarkIntegrityError(
            "VISUS authority execution provenance source identity is invalid."
        )
    for key in (*_BASE_SOURCE_KEYS, AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD):
        if not _valid_sha256(source.get(key)):
            raise BenchmarkIntegrityError(
                "VISUS authority execution provenance source fingerprints are incomplete."
            )

    rows = _validate_authority_row(manifest.get("raw_inputs"), source=source)
    base_projection = _base_projection(manifest)
    _validate_v1_internal_manifest(base_projection)
    _validate_suite_binding(
        manifest_path,
        manifest,
        verify_suite=verify_suite,
    )
    return {
        "schema": _EXECUTION_SCHEMA,
        "status": "complete",
        "input_count": len(rows),
        "suite_fingerprint_sha256": str(
            manifest.get("suite", {}).get("suite_fingerprint_sha256", "")
        ),
        "execution_fingerprint_sha256": claimed,
        AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: str(
            source[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD]
        ),
        "suite_verified": bool(verify_suite),
        "manifest_path": str(manifest_path),
    }


def write_visus_authority_execution_provenance(
    manifest: dict[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> VisusExecutionProvenanceRun:
    """Write and immediately revalidate one authority-bound execution manifest."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest must be a dictionary.")
    claimed = str(manifest.get("execution_fingerprint_sha256", ""))
    body = {
        key: value
        for key, value in manifest.items()
        if key != "execution_fingerprint_sha256"
    }
    if (
        manifest.get("schema") != _EXECUTION_SCHEMA
        or not _valid_sha256(claimed)
        or benchmark_fingerprint(body) != claimed
    ):
        raise BenchmarkIntegrityError(
            "VISUS authority execution manifest does not revalidate before writing."
        )
    target = visus_execution_provenance_path(output_dir)
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    validate_visus_authority_execution_provenance(target, verify_suite=True)
    return VisusExecutionProvenanceRun(
        manifest_path=target,
        manifest=manifest,
        execution_fingerprint_sha256=claimed,
    )
