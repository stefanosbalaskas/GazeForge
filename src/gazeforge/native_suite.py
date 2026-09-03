"""Atomic orchestration and verification for native human event validation suites."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint, freeze_benchmark_report
from .exceptions import BenchmarkIntegrityError
from .native_agreement import run_native_event_annotator_agreement
from .native_event import (
    file_sha256,
    load_native_event_spec,
    load_native_event_table,
    run_native_event_benchmark,
)

_SUITE_NAME = "native-event-validation-v1"
_SUITE_MANIFEST_NAME = "native-event-suite-manifest.json"
_SUITE_REPORT_NAMES = frozenset(
    {
        "human_agreement",
        "primary_annotator_model",
        "annotator_sensitivity_model",
    }
)


@dataclass(slots=True)
class NativeEventValidationSuiteRun:
    """Frozen native-event child reports plus the deterministic completion manifest."""

    output_dir: Path
    report_paths: dict[str, Path]
    reports: dict[str, dict[str, Any]]
    manifest_path: Path
    manifest: dict[str, Any]
    suite_fingerprint_sha256: str


def _target_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "human_agreement": output_dir / "native-human-agreement.json",
        "primary_annotator_model": output_dir / "native-primary-model.json",
        "annotator_sensitivity_model": output_dir / "native-annotator-sensitivity-model.json",
    }


def _preflight_targets(
    paths: dict[str, Path],
    manifest_path: Path,
    *,
    overwrite: bool,
) -> None:
    if overwrite:
        return
    existing = [path for path in [*paths.values(), manifest_path] if path.exists()]
    if existing:
        joined = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"Native event suite output already exists: {joined}")


def _validate_child_report(name: str, report: dict[str, Any]) -> str:
    claimed = report.get("report_fingerprint_sha256")
    if not isinstance(claimed, str) or not claimed:
        raise BenchmarkIntegrityError(
            f"Native event suite child {name!r} is missing a report fingerprint."
        )
    body = {
        key: value
        for key, value in report.items()
        if key != "report_fingerprint_sha256"
    }
    observed = benchmark_fingerprint(body)
    if observed != claimed:
        raise BenchmarkIntegrityError(
            f"Native event suite child {name!r} has a report fingerprint mismatch."
        )
    return observed


def _child_identity(report: dict[str, Any], *, kind: str) -> dict[str, Any]:
    protocol = report.get("protocol")
    if not isinstance(protocol, dict):
        raise BenchmarkIntegrityError("Native suite child protocol must be an object.")
    if kind == "agreement":
        return {
            "source_file_name": protocol.get("source_file_name"),
            "source_file_sha256": protocol.get("source_file_sha256"),
            "spec_fingerprint_sha256": protocol.get("spec_fingerprint_sha256"),
        }
    intake = protocol.get("native_intake")
    if not isinstance(intake, dict):
        raise BenchmarkIntegrityError(
            "Native model child is missing its native_intake provenance."
        )
    return {
        "source_file_name": intake.get("source_file_name"),
        "source_file_sha256": intake.get("source_file_sha256"),
        "spec_fingerprint_sha256": intake.get("spec_fingerprint_sha256"),
    }


def _assert_shared_identity(
    reports: dict[str, dict[str, Any]],
    *,
    expected_source_file_name: str,
    expected_source_file_sha256: str,
    expected_spec_fingerprint_sha256: str,
) -> None:
    expected = {
        "source_file_name": expected_source_file_name,
        "source_file_sha256": expected_source_file_sha256,
        "spec_fingerprint_sha256": expected_spec_fingerprint_sha256,
    }
    kinds = {
        "human_agreement": "agreement",
        "primary_annotator_model": "model",
        "annotator_sensitivity_model": "model",
    }
    for name, report in reports.items():
        _validate_child_report(name, report)
        observed = _child_identity(report, kind=kinds[name])
        if observed != expected:
            raise BenchmarkIntegrityError(
                f"Native event suite child {name!r} does not share the suite source/spec identity."
            )


def _manifest_path(path: str | Path) -> Path:
    source = Path(path)
    return source / _SUITE_MANIFEST_NAME if source.is_dir() else source


def _safe_child_path(root: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise BenchmarkIntegrityError("Native event suite manifest contains an unsafe report path.")
    resolved_root = root.resolve()
    resolved = (root / relative).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise BenchmarkIntegrityError("Native event suite report path escapes the suite directory.")
    return resolved


def _validate_manifest_source(source: Any) -> dict[str, str]:
    if not isinstance(source, dict):
        raise BenchmarkIntegrityError("Native event suite source must be an object.")
    required = (
        "data_file_name",
        "data_file_sha256",
        "spec_file_name",
        "spec_fingerprint_sha256",
    )
    values: dict[str, str] = {}
    for field in required:
        value = source.get(field)
        if not isinstance(value, str) or not value:
            raise BenchmarkIntegrityError(
                f"Native event suite source is missing non-empty {field!r}."
            )
        values[field] = value
    return values


def validate_native_event_suite_manifest(
    path: str | Path,
    *,
    verify_reports: bool = True,
) -> dict[str, Any]:
    """Validate a native-event suite manifest and, by default, all child reports."""
    manifest_path = _manifest_path(path)
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkIntegrityError("Native event suite manifest is not valid JSON.") from exc
    if not isinstance(manifest, dict):
        raise BenchmarkIntegrityError("Native event suite manifest must be a JSON object.")

    required = {
        "suite",
        "status",
        "source",
        "protocol",
        "reports",
        "suite_fingerprint_sha256",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise BenchmarkIntegrityError(
            f"Native event suite manifest is missing required fields: {missing}"
        )
    if manifest["suite"] != _SUITE_NAME:
        raise BenchmarkIntegrityError("Native event suite manifest has an unknown suite identity.")
    if manifest["status"] != "complete":
        raise BenchmarkIntegrityError("Native event suite manifest is not marked complete.")

    claimed_suite_fingerprint = manifest["suite_fingerprint_sha256"]
    if not isinstance(claimed_suite_fingerprint, str) or not claimed_suite_fingerprint:
        raise BenchmarkIntegrityError("Native event suite manifest fingerprint is missing.")
    body = {
        key: value
        for key, value in manifest.items()
        if key != "suite_fingerprint_sha256"
    }
    observed_suite_fingerprint = benchmark_fingerprint(body)
    if claimed_suite_fingerprint != observed_suite_fingerprint:
        raise BenchmarkIntegrityError("Native event suite manifest fingerprint mismatch.")

    source = _validate_manifest_source(manifest["source"])
    if not isinstance(manifest["protocol"], dict):
        raise BenchmarkIntegrityError("Native event suite protocol must be an object.")
    records = manifest["reports"]
    if not isinstance(records, list):
        raise BenchmarkIntegrityError("Native event suite reports must be a list.")

    names: set[str] = set()
    paths: set[str] = set()
    verified_reports: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            raise BenchmarkIntegrityError("Native event suite contains an invalid report row.")
        name = str(record.get("name", ""))
        relative_text = str(record.get("path", ""))
        claimed_child = str(record.get("report_fingerprint_sha256", ""))
        if not name or name in names:
            raise BenchmarkIntegrityError("Suite report names must be unique and non-empty.")
        if not relative_text or relative_text in paths:
            raise BenchmarkIntegrityError("Suite report paths must be unique and non-empty.")
        if not claimed_child:
            raise BenchmarkIntegrityError(
                "Native event suite report row is missing its fingerprint."
            )
        names.add(name)
        paths.add(relative_text)
        child_path = _safe_child_path(manifest_path.parent, relative_text)
        if verify_reports:
            if not child_path.is_file():
                raise BenchmarkIntegrityError(
                    f"Native event suite child report is missing: {relative_text}"
                )
            try:
                child = json.loads(child_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise BenchmarkIntegrityError(
                    f"Native event suite child report is invalid JSON: {relative_text}"
                ) from exc
            if not isinstance(child, dict):
                raise BenchmarkIntegrityError(
                    f"Native event suite child report must be an object: {relative_text}"
                )
            observed_child = _validate_child_report(name, child)
            if observed_child != claimed_child:
                raise BenchmarkIntegrityError(
                    f"Native event suite manifest fingerprint does not match child {name!r}."
                )
            kind = "agreement" if name == "human_agreement" else "model"
            identity = _child_identity(child, kind=kind)
            expected_identity = {
                "source_file_name": source["data_file_name"],
                "source_file_sha256": source["data_file_sha256"],
                "spec_fingerprint_sha256": source["spec_fingerprint_sha256"],
            }
            if identity != expected_identity:
                raise BenchmarkIntegrityError(
                    f"Native event suite child {name!r} source/spec identity mismatch."
                )
        verified_reports.append(
            {
                "name": name,
                "path": relative_text,
                "report_fingerprint_sha256": claimed_child,
            }
        )

    if names != _SUITE_REPORT_NAMES:
        missing_names = sorted(_SUITE_REPORT_NAMES - names)
        unexpected_names = sorted(names - _SUITE_REPORT_NAMES)
        raise BenchmarkIntegrityError(
            "Native event suite report inventory does not match the required tranche: "
            f"missing={missing_names}, unexpected={unexpected_names}"
        )

    return {
        "suite": _SUITE_NAME,
        "status": "complete",
        "report_count": len(verified_reports),
        "reports": verified_reports,
        "source": source,
        "protocol": manifest["protocol"],
        "suite_fingerprint_sha256": claimed_suite_fingerprint,
        "reports_verified": bool(verify_reports),
        "manifest_path": str(manifest_path),
    }


def run_native_event_validation_suite(
    data_path: str | Path,
    spec_path: str | Path,
    output_dir: str | Path,
    *,
    primary_annotator: str,
    sensitivity_annotator: str,
    event_min_iou: float = 0.50,
    n_splits: int = 5,
    ivt_velocity_threshold_deg_s: float | None = None,
    ivt_velocity_threshold_px_s: float | None = None,
    random_state: int = 42,
    n_estimators: int = 200,
    context_radius_ms: float = 50.0,
    hidden_layer_sizes: tuple[int, ...] = (64, 32),
    temporal_solver: str = "adam",
    temporal_max_iter: int = 200,
    overwrite: bool = False,
) -> NativeEventValidationSuiteRun:
    """Compute, freeze, and bind the three-report native event validation tranche.

    All analyses are computed and cross-checked before any report is written. The completion
    manifest is written last. Therefore orphan child reports can never, by themselves, represent a
    complete validation suite.
    """
    primary = str(primary_annotator).strip()
    sensitivity = str(sensitivity_annotator).strip()
    if not primary or not sensitivity:
        raise ValueError("primary_annotator and sensitivity_annotator must be non-empty.")
    if primary == sensitivity:
        raise ValueError("Native event suite requires two distinct annotators.")
    if (ivt_velocity_threshold_deg_s is None) == (ivt_velocity_threshold_px_s is None):
        raise ValueError("Provide exactly one angular or pixel I-VT velocity threshold.")

    data_file = Path(data_path)
    spec_file = Path(spec_path)
    output_path = Path(output_dir)
    report_paths = _target_paths(output_path)
    manifest_path = output_path / _SUITE_MANIFEST_NAME
    _preflight_targets(report_paths, manifest_path, overwrite=overwrite)

    spec = load_native_event_spec(spec_file)
    data = load_native_event_table(data_file)
    source_sha256 = file_sha256(data_file)
    spec_fingerprint = benchmark_fingerprint(spec.to_dict())

    agreement = run_native_event_annotator_agreement(
        data,
        spec,
        left_annotator=primary,
        right_annotator=sensitivity,
        event_min_iou=event_min_iou,
        source_file_name=data_file.name,
        source_file_sha256=source_sha256,
    )
    model_kwargs = {
        "n_splits": n_splits,
        "ivt_velocity_threshold_deg_s": ivt_velocity_threshold_deg_s,
        "ivt_velocity_threshold_px_s": ivt_velocity_threshold_px_s,
        "random_state": random_state,
        "n_estimators": n_estimators,
        "context_radius_ms": context_radius_ms,
        "hidden_layer_sizes": hidden_layer_sizes,
        "temporal_solver": temporal_solver,
        "temporal_max_iter": temporal_max_iter,
        "source_file_name": data_file.name,
        "source_file_sha256": source_sha256,
    }
    primary_model = run_native_event_benchmark(
        data,
        spec,
        annotator=primary,
        **model_kwargs,
    )
    sensitivity_model = run_native_event_benchmark(
        data,
        spec,
        annotator=sensitivity,
        **model_kwargs,
    )
    reports = {
        "human_agreement": agreement.report,
        "primary_annotator_model": primary_model.report,
        "annotator_sensitivity_model": sensitivity_model.report,
    }
    _assert_shared_identity(
        reports,
        expected_source_file_name=data_file.name,
        expected_source_file_sha256=source_sha256,
        expected_spec_fingerprint_sha256=spec_fingerprint,
    )

    for name, report in reports.items():
        freeze_benchmark_report(report, report_paths[name], overwrite=overwrite)

    protocol = {
        "primary_annotator": primary,
        "sensitivity_annotator": sensitivity,
        "event_min_iou": float(event_min_iou),
        "n_splits": int(n_splits),
        "ivt_velocity_threshold_deg_s": (
            None
            if ivt_velocity_threshold_deg_s is None
            else float(ivt_velocity_threshold_deg_s)
        ),
        "ivt_velocity_threshold_px_s": (
            None
            if ivt_velocity_threshold_px_s is None
            else float(ivt_velocity_threshold_px_s)
        ),
        "random_state": int(random_state),
        "n_estimators": int(n_estimators),
        "context_radius_ms": float(context_radius_ms),
        "hidden_layer_sizes": [int(value) for value in hidden_layer_sizes],
        "temporal_solver": str(temporal_solver),
        "temporal_max_iter": int(temporal_max_iter),
        "split_unit": "participant_id",
        "resampling": None,
        "completion_rule": "manifest_written_only_after_all_child_reports_freeze",
    }
    source = {
        "data_file_name": data_file.name,
        "data_file_sha256": source_sha256,
        "spec_file_name": spec_file.name,
        "spec_fingerprint_sha256": spec_fingerprint,
    }
    records = [
        {
            "name": name,
            "path": report_paths[name].name,
            "report_fingerprint_sha256": reports[name]["report_fingerprint_sha256"],
        }
        for name in sorted(reports)
    ]
    body = {
        "suite": _SUITE_NAME,
        "status": "complete",
        "source": source,
        "protocol": protocol,
        "reports": records,
    }
    suite_fingerprint = benchmark_fingerprint(body)
    manifest = {**body, "suite_fingerprint_sha256": suite_fingerprint}
    output_path.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    validate_native_event_suite_manifest(manifest_path, verify_reports=True)
    return NativeEventValidationSuiteRun(
        output_dir=output_path,
        report_paths=report_paths,
        reports=reports,
        manifest_path=manifest_path,
        manifest=manifest,
        suite_fingerprint_sha256=suite_fingerprint,
    )
