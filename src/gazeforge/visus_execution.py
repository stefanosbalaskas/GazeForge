"""Raw-input provenance binding for guarded VISUS suite execution."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .visus_audit import VisusSourceAuditRun, load_visus_source_audit_spec
from .visus_suite import (
    VisusDynamicAOIValidationSuiteRun,
    validate_visus_dynamic_aoi_suite_manifest,
)

_EXECUTION_SCHEMA = "gazeforge-visus-execution-provenance-v1"
_EXECUTION_MANIFEST_NAME = "visus-execution-provenance.json"
_INPUT_ROLES = (
    "source_audit_spec",
    "human_aoi_table",
    "model_prediction_table",
    "timestamp_grid_json",
)
_SOURCE_KEYS = (
    "source_audit_report_fingerprint_sha256",
    "source_audit_spec_fingerprint_sha256",
    "source_manifest_fingerprint_sha256",
)
_PARSED_FINGERPRINT_KEYS = (
    "human_input_table_fingerprint_sha256",
    "human_canonical_table_fingerprint_sha256",
    "model_input_table_fingerprint_sha256",
    "model_canonical_table_fingerprint_sha256",
)


@dataclass(frozen=True, slots=True)
class VisusExecutionInputSnapshot:
    """Exact raw-file identity captured before VISUS execution."""

    role: str
    filename: str
    sha256: str
    bytes: int
    semantic_fingerprint_sha256: str | None = None


@dataclass(slots=True)
class VisusExecutionProvenanceRun:
    """Frozen raw-input-to-suite provenance manifest."""

    manifest_path: Path
    manifest: dict[str, Any]
    execution_fingerprint_sha256: str


def _valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _snapshot_file(
    role: str,
    path: str | Path,
    *,
    semantic_fingerprint_sha256: str | None = None,
) -> VisusExecutionInputSnapshot:
    source = Path(path)
    if source.is_symlink():
        raise BenchmarkIntegrityError(
            f"VISUS execution input {role!r} must not be a symbolic link."
        )
    if not source.is_file():
        raise FileNotFoundError(source)
    size = int(source.stat().st_size)
    if size <= 0:
        raise BenchmarkIntegrityError(
            f"VISUS execution input {role!r} must be a non-empty regular file."
        )
    if semantic_fingerprint_sha256 is not None and not _valid_sha256(
        semantic_fingerprint_sha256
    ):
        raise BenchmarkIntegrityError(
            f"VISUS execution input {role!r} has an invalid semantic fingerprint."
        )
    return VisusExecutionInputSnapshot(
        role=role,
        filename=source.name,
        sha256=_sha256(source),
        bytes=size,
        semantic_fingerprint_sha256=semantic_fingerprint_sha256,
    )


def snapshot_visus_execution_inputs(
    *,
    source_audit_spec: str | Path,
    human_aoi_table: str | Path,
    model_prediction_table: str | Path,
    timestamp_grid_json: str | Path,
) -> tuple[VisusExecutionInputSnapshot, ...]:
    """Fingerprint the four raw files consumed by the guarded VISUS CLI.

    The source-audit JSON additionally receives a semantic fingerprint of the parsed
    :class:`~gazeforge.visus_audit.VisusSourceAuditSpec`, allowing the execution manifest to prove
    that the exact raw JSON corresponds to the specification used by the source audit.
    """
    source_spec_snapshot = _snapshot_file("source_audit_spec", source_audit_spec)
    parsed_spec = load_visus_source_audit_spec(source_audit_spec)
    spec_semantic = benchmark_fingerprint(parsed_spec.to_dict())
    source_spec_snapshot = VisusExecutionInputSnapshot(
        role=source_spec_snapshot.role,
        filename=source_spec_snapshot.filename,
        sha256=source_spec_snapshot.sha256,
        bytes=source_spec_snapshot.bytes,
        semantic_fingerprint_sha256=spec_semantic,
    )
    return (
        source_spec_snapshot,
        _snapshot_file("human_aoi_table", human_aoi_table),
        _snapshot_file("model_prediction_table", model_prediction_table),
        _snapshot_file("timestamp_grid_json", timestamp_grid_json),
    )


def verify_visus_execution_inputs_unchanged(
    snapshots: tuple[VisusExecutionInputSnapshot, ...],
    *,
    source_audit_spec: str | Path,
    human_aoi_table: str | Path,
    model_prediction_table: str | Path,
    timestamp_grid_json: str | Path,
) -> None:
    """Refuse provenance freezing if any raw input changed during suite execution."""
    observed = snapshot_visus_execution_inputs(
        source_audit_spec=source_audit_spec,
        human_aoi_table=human_aoi_table,
        model_prediction_table=model_prediction_table,
        timestamp_grid_json=timestamp_grid_json,
    )
    if tuple(snapshots) != observed:
        raise BenchmarkIntegrityError(
            "One or more VISUS raw execution inputs changed after the pre-execution snapshot; "
            "raw-input provenance cannot be frozen for this run."
        )


def _audit_source_identity(audit: VisusSourceAuditRun) -> dict[str, str]:
    if not isinstance(audit, VisusSourceAuditRun):
        raise TypeError("audit must be a VisusSourceAuditRun instance.")
    if audit.report.get("status") != "verified":
        raise BenchmarkIntegrityError("VISUS execution provenance requires a verified source audit.")
    claimed = str(audit.report.get("report_fingerprint_sha256", ""))
    body = {
        key: value
        for key, value in audit.report.items()
        if key != "report_fingerprint_sha256"
    }
    if not _valid_sha256(claimed) or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError(
            "VISUS execution provenance received a source audit with an invalid fingerprint."
        )
    spec_fingerprint = str(audit.report.get("spec_fingerprint_sha256", ""))
    if (
        not _valid_sha256(spec_fingerprint)
        or benchmark_fingerprint(audit.spec.to_dict()) != spec_fingerprint
    ):
        raise BenchmarkIntegrityError(
            "VISUS execution provenance received a source audit with an invalid spec fingerprint."
        )
    manifest_fingerprint = str(
        audit.report.get("inventory", {}).get("manifest_fingerprint_sha256", "")
    )
    if not _valid_sha256(manifest_fingerprint):
        raise BenchmarkIntegrityError(
            "VISUS execution provenance received incomplete source-manifest identity."
        )
    return {
        "source_audit_report_fingerprint_sha256": claimed,
        "source_audit_spec_fingerprint_sha256": spec_fingerprint,
        "source_manifest_fingerprint_sha256": manifest_fingerprint,
    }


def _input_rows(
    snapshots: tuple[VisusExecutionInputSnapshot, ...],
) -> list[dict[str, Any]]:
    if not isinstance(snapshots, tuple):
        raise TypeError("snapshots must be a tuple of VisusExecutionInputSnapshot values.")
    if any(not isinstance(item, VisusExecutionInputSnapshot) for item in snapshots):
        raise TypeError("snapshots contain a non-VisusExecutionInputSnapshot value.")
    by_role = {item.role: item for item in snapshots}
    if len(by_role) != len(snapshots) or set(by_role) != set(_INPUT_ROLES):
        raise BenchmarkIntegrityError(
            "VISUS execution provenance requires exactly one snapshot for each raw input role."
        )
    return [asdict(by_role[role]) for role in _INPUT_ROLES]


def _load_suite_children(
    suite_root: Path,
    verified_suite: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    children: dict[str, dict[str, Any]] = {}
    for record in verified_suite["reports"]:
        name = str(record["name"])
        relative = Path(str(record["path"]))
        child_path = suite_root / relative
        child = json.loads(child_path.read_text(encoding="utf-8"))
        if not isinstance(child, dict):
            raise BenchmarkIntegrityError(
                f"VISUS execution provenance child {name!r} must be a JSON object."
            )
        children[name] = child
    return children


def _parsed_input_binding(
    reference: dict[str, Any],
    prediction: dict[str, Any],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    binding = {
        "human_input_table_fingerprint_sha256": reference.get(
            "input_table_fingerprint_sha256"
        ),
        "human_canonical_table_fingerprint_sha256": reference.get(
            "canonical_table_fingerprint_sha256"
        ),
        "model_input_table_fingerprint_sha256": prediction.get(
            "input_table_fingerprint_sha256"
        ),
        "model_canonical_table_fingerprint_sha256": prediction.get(
            "canonical_table_fingerprint_sha256"
        ),
        "timestamp_grids": protocol.get("timestamp_grids"),
        "timestamp_grid_basis": protocol.get("timestamp_grid_basis"),
        "prediction_emission_grid_used": protocol.get("prediction_emission_grid_used"),
    }
    if any(not _valid_sha256(binding.get(key)) for key in _PARSED_FINGERPRINT_KEYS):
        raise BenchmarkIntegrityError(
            "VISUS execution provenance is missing canonical intake fingerprints."
        )
    if not isinstance(binding.get("timestamp_grids"), dict) or not binding[
        "timestamp_grids"
    ]:
        raise BenchmarkIntegrityError(
            "VISUS execution provenance requires frozen external timestamp-grid fingerprints."
        )
    basis = binding.get("timestamp_grid_basis")
    if not isinstance(basis, str) or not basis.strip():
        raise BenchmarkIntegrityError(
            "VISUS execution provenance requires an explicit timestamp-grid basis."
        )
    if binding.get("prediction_emission_grid_used") is not False:
        raise BenchmarkIntegrityError(
            "VISUS execution provenance refuses a suite that uses prediction emissions as the grid."
        )
    return binding


def build_visus_execution_provenance(
    audit: VisusSourceAuditRun,
    suite: VisusDynamicAOIValidationSuiteRun,
    snapshots: tuple[VisusExecutionInputSnapshot, ...],
) -> dict[str, Any]:
    """Bind exact raw input files to one fully verified frozen VISUS suite."""
    if not isinstance(suite, VisusDynamicAOIValidationSuiteRun):
        raise TypeError("suite must be a VisusDynamicAOIValidationSuiteRun instance.")
    verified_suite = validate_visus_dynamic_aoi_suite_manifest(
        suite.manifest_path,
        verify_reports=True,
    )
    if verified_suite["suite_fingerprint_sha256"] != suite.suite_fingerprint_sha256:
        raise BenchmarkIntegrityError(
            "VISUS execution provenance suite fingerprint does not match the verified manifest."
        )

    source_identity = _audit_source_identity(audit)
    observed_source = {
        key: str(verified_suite["source"].get(key, "")) for key in source_identity
    }
    if observed_source != source_identity:
        raise BenchmarkIntegrityError(
            "VISUS execution provenance source identity does not match the frozen suite."
        )

    rows = _input_rows(snapshots)
    spec_row = next(row for row in rows if row["role"] == "source_audit_spec")
    if spec_row["semantic_fingerprint_sha256"] != source_identity[
        "source_audit_spec_fingerprint_sha256"
    ]:
        raise BenchmarkIntegrityError(
            "Raw VISUS source-audit JSON does not semantically match the audited specification."
        )

    children = _load_suite_children(suite.manifest_path.parent, verified_suite)
    reference = children.get("human_reference_intake")
    prediction = children.get("model_prediction_intake")
    if not isinstance(reference, dict) or not isinstance(prediction, dict):
        raise BenchmarkIntegrityError(
            "VISUS execution provenance requires both verified intake reports."
        )
    protocol = verified_suite["protocol"]
    if not isinstance(protocol, dict):
        raise BenchmarkIntegrityError("VISUS suite protocol must be a dictionary.")
    parsed_inputs = _parsed_input_binding(reference, prediction, protocol)

    body = {
        "schema": _EXECUTION_SCHEMA,
        "status": "complete",
        "provenance_scope": "exact-raw-input-files-to-frozen-visus-suite",
        "source": source_identity,
        "raw_inputs": rows,
        "parsed_inputs": parsed_inputs,
        "suite": {
            "manifest_filename": suite.manifest_path.name,
            "suite_fingerprint_sha256": suite.suite_fingerprint_sha256,
            "report_count": int(verified_suite["report_count"]),
            "reports_verified": True,
        },
        "claim_limits": [
            (
                "This manifest binds raw execution files to a verified suite; it does not "
                "validate the dataset independently."
            ),
            (
                "Analysis-use permission and raw-data redistribution rights remain separate "
                "source-audit evidence fields."
            ),
            "Model-emission frames are not an evaluation timestamp grid.",
            (
                "Human-human agreement remains conditional on independently verified "
                "annotation streams."
            ),
        ],
    }
    return {
        **body,
        "execution_fingerprint_sha256": benchmark_fingerprint(body),
    }


def visus_execution_provenance_path(output_dir: str | Path) -> Path:
    """Return the fixed provenance-manifest path for one VISUS suite directory."""
    return Path(output_dir) / _EXECUTION_MANIFEST_NAME


def write_visus_execution_provenance(
    manifest: dict[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> VisusExecutionProvenanceRun:
    """Freeze an execution provenance manifest after its fingerprint revalidates."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest must be a dictionary.")
    claimed = str(manifest.get("execution_fingerprint_sha256", ""))
    body = {
        key: value
        for key, value in manifest.items()
        if key != "execution_fingerprint_sha256"
    }
    if not _valid_sha256(claimed) or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError(
            "VISUS execution provenance fingerprint does not revalidate before writing."
        )
    target = visus_execution_provenance_path(output_dir)
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return VisusExecutionProvenanceRun(
        manifest_path=target,
        manifest=manifest,
        execution_fingerprint_sha256=claimed,
    )


def _validate_internal_manifest(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if manifest.get("schema") != _EXECUTION_SCHEMA or manifest.get("status") != "complete":
        raise BenchmarkIntegrityError("VISUS execution provenance identity/status is invalid.")
    if manifest.get("provenance_scope") != "exact-raw-input-files-to-frozen-visus-suite":
        raise BenchmarkIntegrityError("VISUS execution provenance scope is invalid.")

    source = manifest.get("source")
    if not isinstance(source, dict) or any(not _valid_sha256(source.get(key)) for key in _SOURCE_KEYS):
        raise BenchmarkIntegrityError("VISUS execution provenance source identity is invalid.")

    rows = manifest.get("raw_inputs")
    if not isinstance(rows, list) or len(rows) != len(_INPUT_ROLES):
        raise BenchmarkIntegrityError("VISUS execution provenance raw-input inventory is invalid.")
    roles = [str(row.get("role", "")) for row in rows if isinstance(row, dict)]
    if roles != list(_INPUT_ROLES):
        raise BenchmarkIntegrityError("VISUS execution provenance raw-input roles are invalid.")
    for row in rows:
        if not isinstance(row, dict):
            raise BenchmarkIntegrityError(
                "VISUS execution provenance contains a non-object raw-input record."
            )
        filename = row.get("filename")
        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).name != filename
            or not _valid_sha256(row.get("sha256"))
            or not isinstance(row.get("bytes"), int)
            or row["bytes"] <= 0
        ):
            raise BenchmarkIntegrityError(
                "VISUS execution provenance contains an invalid raw-input record."
            )
    spec_row = rows[0]
    if not _valid_sha256(spec_row.get("semantic_fingerprint_sha256")):
        raise BenchmarkIntegrityError(
            "VISUS execution provenance source-spec semantic fingerprint is invalid."
        )
    if spec_row["semantic_fingerprint_sha256"] != source[
        "source_audit_spec_fingerprint_sha256"
    ]:
        raise BenchmarkIntegrityError(
            "VISUS execution provenance source-spec semantic binding is inconsistent."
        )
    if any(row.get("semantic_fingerprint_sha256") is not None for row in rows[1:]):
        raise BenchmarkIntegrityError(
            "Only the source-audit JSON may carry a semantic raw-input fingerprint."
        )

    parsed = manifest.get("parsed_inputs")
    if not isinstance(parsed, dict):
        raise BenchmarkIntegrityError("VISUS execution provenance parsed-input binding is invalid.")
    _parsed_input_binding(
        {
            "input_table_fingerprint_sha256": parsed.get(
                "human_input_table_fingerprint_sha256"
            ),
            "canonical_table_fingerprint_sha256": parsed.get(
                "human_canonical_table_fingerprint_sha256"
            ),
        },
        {
            "input_table_fingerprint_sha256": parsed.get(
                "model_input_table_fingerprint_sha256"
            ),
            "canonical_table_fingerprint_sha256": parsed.get(
                "model_canonical_table_fingerprint_sha256"
            ),
        },
        {
            "timestamp_grids": parsed.get("timestamp_grids"),
            "timestamp_grid_basis": parsed.get("timestamp_grid_basis"),
            "prediction_emission_grid_used": parsed.get("prediction_emission_grid_used"),
        },
    )

    suite = manifest.get("suite")
    if not isinstance(suite, dict):
        raise BenchmarkIntegrityError("VISUS execution provenance suite binding is invalid.")
    filename = suite.get("manifest_filename")
    if (
        not isinstance(filename, str)
        or not filename
        or Path(filename).name != filename
        or not _valid_sha256(suite.get("suite_fingerprint_sha256"))
        or not isinstance(suite.get("report_count"), int)
        or suite["report_count"] <= 0
        or suite.get("reports_verified") is not True
    ):
        raise BenchmarkIntegrityError("VISUS execution provenance suite binding is incomplete.")
    return rows, suite


def validate_visus_execution_provenance(
    path: str | Path,
    *,
    verify_suite: bool = True,
) -> dict[str, Any]:
    """Validate a frozen raw-input provenance manifest and optionally its sibling suite."""
    source = Path(path)
    manifest_path = source / _EXECUTION_MANIFEST_NAME if source.is_dir() else source
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkIntegrityError(
            "VISUS execution provenance is not valid JSON."
        ) from exc
    if not isinstance(manifest, dict):
        raise BenchmarkIntegrityError("VISUS execution provenance must be a JSON object.")
    claimed = str(manifest.get("execution_fingerprint_sha256", ""))
    body = {
        key: value
        for key, value in manifest.items()
        if key != "execution_fingerprint_sha256"
    }
    if not _valid_sha256(claimed) or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError("VISUS execution provenance fingerprint mismatch.")

    rows, suite = _validate_internal_manifest(manifest)
    if verify_suite:
        summary = validate_visus_dynamic_aoi_suite_manifest(
            manifest_path.parent / str(suite["manifest_filename"]),
            verify_reports=True,
        )
        if summary["suite_fingerprint_sha256"] != suite["suite_fingerprint_sha256"]:
            raise BenchmarkIntegrityError(
                "VISUS execution provenance/suite fingerprint mismatch."
            )
        if int(summary["report_count"]) != int(suite["report_count"]):
            raise BenchmarkIntegrityError(
                "VISUS execution provenance/suite report-count mismatch."
            )
        observed_source = {
            key: str(summary["source"].get(key, "")) for key in _SOURCE_KEYS
        }
        if observed_source != manifest["source"]:
            raise BenchmarkIntegrityError(
                "VISUS execution provenance/suite source identity mismatch."
            )
        protocol = summary["protocol"]
        parsed = manifest["parsed_inputs"]
        if parsed["timestamp_grids"] != protocol.get("timestamp_grids"):
            raise BenchmarkIntegrityError(
                "VISUS execution provenance/suite timestamp-grid fingerprints mismatch."
            )
        if parsed["timestamp_grid_basis"] != protocol.get("timestamp_grid_basis"):
            raise BenchmarkIntegrityError(
                "VISUS execution provenance/suite timestamp-grid basis mismatch."
            )
        if protocol.get("prediction_emission_grid_used") is not False:
            raise BenchmarkIntegrityError(
                "VISUS execution provenance refuses a suite using prediction emissions as grid."
            )

        children = _load_suite_children(manifest_path.parent, summary)
        reference = children.get("human_reference_intake")
        prediction = children.get("model_prediction_intake")
        if not isinstance(reference, dict) or not isinstance(prediction, dict):
            raise BenchmarkIntegrityError(
                "VISUS execution provenance cannot recover verified intake children."
            )
        observed_parsed = _parsed_input_binding(reference, prediction, protocol)
        if observed_parsed != parsed:
            raise BenchmarkIntegrityError(
                "VISUS execution provenance parsed-input binding does not match suite children."
            )

    return {
        "schema": _EXECUTION_SCHEMA,
        "status": "complete",
        "input_count": len(rows),
        "suite_fingerprint_sha256": suite["suite_fingerprint_sha256"],
        "execution_fingerprint_sha256": claimed,
        "suite_verified": bool(verify_suite),
        "manifest_path": str(manifest_path),
    }
