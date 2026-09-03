"""One-command orchestration and verification for the Lund2013 validation tranche."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .benchmarks import (
    BenchmarkDatasetCard,
    benchmark_fingerprint,
    build_benchmark_report,
    freeze_benchmark_report,
)
from .exceptions import BenchmarkIntegrityError
from .lund_benchmark import compare_lund2013_annotators, run_lund2013_event_benchmark
from .lund_fetch import (
    LUND2013_COMMIT,
    LUND2013_DATA_PATH,
    LUND2013_REPOSITORY,
    validate_lund2013_source_manifest,
)
from .lund_sensitivity import run_lund2013_sampling_sensitivity

_SUITE_NAME = "lund2013-event-validation-v1"
_SUITE_MANIFEST_NAME = "lund2013-suite-manifest.json"
_SUITE_REPORT_NAMES = frozenset(
    {
        "human_agreement_native",
        "human_agreement_60hz",
        "primary_ra_60hz",
        "annotator_sensitivity_mn_60hz",
        "sampling_purity_sensitivity_ra",
    }
)


@dataclass(slots=True)
class Lund2013BenchmarkSuiteRun:
    """Frozen child reports plus the deterministic suite-level manifest."""

    output_dir: Path
    report_paths: dict[str, Path]
    reports: dict[str, dict[str, Any]]
    manifest_path: Path
    manifest: dict[str, Any]
    suite_fingerprint_sha256: str


def _agreement_report(
    agreement: dict[str, Any],
    *,
    sampling_origin: str,
    reference_strength: str,
) -> dict[str, Any]:
    sampling_rate_hz = float(agreement["sampling_rate_hz"])
    card = BenchmarkDatasetCard(
        name="Lund2013-human-agreement",
        version="Andersson-et-al-2017-public-repository",
        source="richardandersson/EyeMovementDetectorEvaluation",
        license="GPL-3.0 repository license; raw benchmark is not bundled by GazeForge",
        task="human-human sample-label agreement",
        sampling_rates_hz=[sampling_rate_hz],
        split_unit="participant_id",
        validation_scope="external-empirical-human-agreement",
        annotation_origin="expert-manual",
        sampling_origin=sampling_origin,
        reference_strength=reference_strength,
        human_annotator_count=2,
        reference_description=(
            "Paired MN and RA expert annotations from the public Lund2013 benchmark."
        ),
        notes=[
            (
                "Human-human agreement is a reference for annotation variability, "
                "not an error-free ceiling."
            ),
            (
                "Lower-rate agreement is derived independently from each human "
                "annotation stream."
                if sampling_origin == "resampled"
                else "Agreement is evaluated at the native recording cadence."
            ),
        ],
    )
    protocol = {
        "left_annotator": agreement["left_annotator"],
        "right_annotator": agreement["right_annotator"],
        "sampling_rate_hz": sampling_rate_hz,
        "source_manifest": agreement.get("source_manifest"),
    }
    metrics = {
        "overall": agreement["overall"],
        "by_stimulus_type": agreement["by_stimulus_type"],
    }
    return build_benchmark_report(
        benchmark=card,
        metrics=metrics,
        model={"models": []},
        protocol=protocol,
    )


def _target_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "human_agreement_native": output_dir / "lund2013-mn-vs-ra-native.json",
        "human_agreement_60hz": output_dir / "lund2013-mn-vs-ra-60hz.json",
        "primary_ra_60hz": output_dir / "lund2013-ra-60hz-primary.json",
        "annotator_sensitivity_mn_60hz": (
            output_dir / "lund2013-mn-60hz-annotator-sensitivity.json"
        ),
        "sampling_purity_sensitivity_ra": (
            output_dir / "lund2013-ra-sampling-purity-sensitivity.json"
        ),
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
        raise FileExistsError(f"Lund2013 suite output already exists: {joined}")


def _validate_child_report(name: str, report: dict[str, Any]) -> str:
    claimed = report.get("report_fingerprint_sha256")
    if not isinstance(claimed, str) or not claimed:
        raise BenchmarkIntegrityError(
            f"Lund2013 suite child {name!r} is missing a report fingerprint."
        )
    body = {
        key: value
        for key, value in report.items()
        if key != "report_fingerprint_sha256"
    }
    observed = benchmark_fingerprint(body)
    if observed != claimed:
        raise BenchmarkIntegrityError(
            f"Lund2013 suite child {name!r} has a report fingerprint mismatch."
        )
    return observed


def _manifest_path(path: str | Path) -> Path:
    source = Path(path)
    return source / _SUITE_MANIFEST_NAME if source.is_dir() else source


def _safe_child_path(root: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise BenchmarkIntegrityError("Lund2013 suite manifest contains an unsafe report path.")
    resolved_root = root.resolve()
    resolved = (root / relative).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise BenchmarkIntegrityError("Lund2013 suite report path escapes the suite directory.")
    return resolved


def _validate_suite_source_summary(source: Any) -> None:
    if source is None:
        return
    if not isinstance(source, dict):
        raise BenchmarkIntegrityError("Lund2013 suite source_manifest must be an object or null.")
    expected = {
        "repository": LUND2013_REPOSITORY,
        "commit": LUND2013_COMMIT,
        "data_path": LUND2013_DATA_PATH,
    }
    for field, value in expected.items():
        if source.get(field) != value:
            raise BenchmarkIntegrityError(
                f"Lund2013 suite source_manifest {field} does not match the pinned source."
            )
    fingerprint = source.get("manifest_fingerprint_sha256")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise BenchmarkIntegrityError(
            "Lund2013 suite source_manifest is missing its manifest fingerprint."
        )


def validate_lund2013_suite_manifest(
    path: str | Path,
    *,
    verify_reports: bool = True,
) -> dict[str, Any]:
    """Validate a frozen Lund suite manifest and, by default, every referenced child report."""
    manifest_path = _manifest_path(path)
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkIntegrityError("Lund2013 suite manifest is not valid JSON.") from exc
    if not isinstance(manifest, dict):
        raise BenchmarkIntegrityError("Lund2013 suite manifest must be a JSON object.")

    required = {
        "suite",
        "status",
        "source_manifest",
        "protocol",
        "reports",
        "suite_fingerprint_sha256",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise BenchmarkIntegrityError(
            f"Lund2013 suite manifest is missing required fields: {missing}"
        )
    if manifest["suite"] != _SUITE_NAME:
        raise BenchmarkIntegrityError("Lund2013 suite manifest has an unknown suite identity.")
    if manifest["status"] != "complete":
        raise BenchmarkIntegrityError("Lund2013 suite manifest is not marked complete.")

    claimed_suite_fingerprint = str(manifest["suite_fingerprint_sha256"])
    body = {
        key: value
        for key, value in manifest.items()
        if key != "suite_fingerprint_sha256"
    }
    observed_suite_fingerprint = benchmark_fingerprint(body)
    if claimed_suite_fingerprint != observed_suite_fingerprint:
        raise BenchmarkIntegrityError("Lund2013 suite manifest fingerprint mismatch.")

    _validate_suite_source_summary(manifest["source_manifest"])
    records = manifest["reports"]
    if not isinstance(records, list):
        raise BenchmarkIntegrityError("Lund2013 suite reports must be a list.")

    names: set[str] = set()
    paths: set[str] = set()
    verified_reports: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            raise BenchmarkIntegrityError("Lund2013 suite contains an invalid report row.")
        name = str(record.get("name", ""))
        relative_text = str(record.get("path", ""))
        claimed_child = str(record.get("report_fingerprint_sha256", ""))
        if not name or name in names:
            raise BenchmarkIntegrityError("Suite report names must be unique and non-empty.")
        if not relative_text or relative_text in paths:
            raise BenchmarkIntegrityError("Suite report paths must be unique and non-empty.")
        if not claimed_child:
            raise BenchmarkIntegrityError("Lund2013 suite report row is missing its fingerprint.")
        names.add(name)
        paths.add(relative_text)
        child_path = _safe_child_path(manifest_path.parent, relative_text)
        if verify_reports:
            if not child_path.is_file():
                raise BenchmarkIntegrityError(
                    f"Lund2013 suite child report is missing: {relative_text}"
                )
            try:
                child = json.loads(child_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise BenchmarkIntegrityError(
                    f"Lund2013 suite child report is invalid JSON: {relative_text}"
                ) from exc
            if not isinstance(child, dict):
                raise BenchmarkIntegrityError(
                    f"Lund2013 suite child report must be an object: {relative_text}"
                )
            observed_child = _validate_child_report(name, child)
            if observed_child != claimed_child:
                raise BenchmarkIntegrityError(
                    f"Lund2013 suite manifest fingerprint does not match child {name!r}."
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
            "Lund2013 suite report inventory does not match the required tranche: "
            f"missing={missing_names}, unexpected={unexpected_names}"
        )

    return {
        "suite": _SUITE_NAME,
        "status": "complete",
        "report_count": len(verified_reports),
        "reports": verified_reports,
        "source_manifest": manifest["source_manifest"],
        "protocol": manifest["protocol"],
        "suite_fingerprint_sha256": claimed_suite_fingerprint,
        "reports_verified": bool(verify_reports),
        "manifest_path": str(manifest_path),
    }


def run_lund2013_benchmark_suite(
    root: str | Path,
    output_dir: str | Path,
    *,
    target_sampling_rate_hz: float = 60.0,
    min_label_purity: float = 0.75,
    n_splits: int = 5,
    ivt_velocity_threshold_deg_s: float = 45.0,
    random_state: int = 42,
    n_estimators: int = 200,
    context_radius_ms: float = 50.0,
    hidden_layer_sizes: tuple[int, ...] = (64, 32),
    temporal_solver: str = "adam",
    temporal_max_iter: int = 200,
    sensitivity_target_rates_hz: tuple[float, ...] = (120.0, 90.0, 60.0, 30.0),
    sensitivity_min_label_purities: tuple[float, ...] = (0.60, 0.75, 0.90),
    overwrite: bool = False,
) -> Lund2013BenchmarkSuiteRun:
    """Run and freeze the complete first-pass Lund2013 empirical validation suite.

    All analyses are computed before any suite-completion manifest is written. Child reports retain
    independent fingerprints. The suite manifest is written last, so an interrupted or failed run
    cannot masquerade as a complete validation tranche merely because one child report exists.
    """
    root_path = Path(root)
    output_path = Path(output_dir)
    report_paths = _target_paths(output_path)
    manifest_path = output_path / _SUITE_MANIFEST_NAME
    _preflight_targets(report_paths, manifest_path, overwrite=overwrite)

    source_manifest = validate_lund2013_source_manifest(root_path)
    native_agreement = compare_lund2013_annotators(
        root_path,
        left_annotator="MN",
        right_annotator="RA",
        target_sampling_rate_hz=None,
        min_label_purity=min_label_purity,
    )
    derived_agreement = compare_lund2013_annotators(
        root_path,
        left_annotator="MN",
        right_annotator="RA",
        target_sampling_rate_hz=target_sampling_rate_hz,
        min_label_purity=min_label_purity,
    )
    primary_ra = run_lund2013_event_benchmark(
        root_path,
        annotator="RA",
        target_sampling_rate_hz=target_sampling_rate_hz,
        min_label_purity=min_label_purity,
        n_splits=n_splits,
        ivt_velocity_threshold_deg_s=ivt_velocity_threshold_deg_s,
        random_state=random_state,
        n_estimators=n_estimators,
        context_radius_ms=context_radius_ms,
        hidden_layer_sizes=hidden_layer_sizes,
        temporal_solver=temporal_solver,
        temporal_max_iter=temporal_max_iter,
    )
    annotator_sensitivity_mn = run_lund2013_event_benchmark(
        root_path,
        annotator="MN",
        target_sampling_rate_hz=target_sampling_rate_hz,
        min_label_purity=min_label_purity,
        n_splits=n_splits,
        ivt_velocity_threshold_deg_s=ivt_velocity_threshold_deg_s,
        random_state=random_state,
        n_estimators=n_estimators,
        context_radius_ms=context_radius_ms,
        hidden_layer_sizes=hidden_layer_sizes,
        temporal_solver=temporal_solver,
        temporal_max_iter=temporal_max_iter,
    )
    sampling_sensitivity = run_lund2013_sampling_sensitivity(
        root_path,
        annotator="RA",
        target_sampling_rates_hz=sensitivity_target_rates_hz,
        min_label_purities=sensitivity_min_label_purities,
        n_splits=n_splits,
        ivt_velocity_threshold_deg_s=ivt_velocity_threshold_deg_s,
        random_state=random_state,
        n_estimators=n_estimators,
        context_radius_ms=context_radius_ms,
        hidden_layer_sizes=hidden_layer_sizes,
        temporal_solver=temporal_solver,
        temporal_max_iter=temporal_max_iter,
    )

    reports = {
        "human_agreement_native": _agreement_report(
            native_agreement,
            sampling_origin="native",
            reference_strength="expert-human-reference",
        ),
        "human_agreement_60hz": _agreement_report(
            derived_agreement,
            sampling_origin="resampled",
            reference_strength="derived-human-reference",
        ),
        "primary_ra_60hz": primary_ra.report,
        "annotator_sensitivity_mn_60hz": annotator_sensitivity_mn.report,
        "sampling_purity_sensitivity_ra": sampling_sensitivity.report,
    }
    for name, report in reports.items():
        _validate_child_report(name, report)

    output_path.mkdir(parents=True, exist_ok=True)
    for name, report in reports.items():
        freeze_benchmark_report(report, report_paths[name], overwrite=overwrite)

    manifest_body: dict[str, Any] = {
        "suite": _SUITE_NAME,
        "status": "complete",
        "source_manifest": source_manifest,
        "protocol": {
            "target_sampling_rate_hz": float(target_sampling_rate_hz),
            "min_label_purity": float(min_label_purity),
            "n_splits_requested": int(n_splits),
            "ivt_velocity_threshold_deg_s": float(ivt_velocity_threshold_deg_s),
            "random_state": int(random_state),
            "n_estimators": int(n_estimators),
            "context_radius_ms": float(context_radius_ms),
            "hidden_layer_sizes": list(hidden_layer_sizes),
            "temporal_solver": temporal_solver,
            "temporal_max_iter": int(temporal_max_iter),
            "sensitivity_target_rates_hz": [
                float(value) for value in sensitivity_target_rates_hz
            ],
            "sensitivity_min_label_purities": [
                float(value) for value in sensitivity_min_label_purities
            ],
        },
        "reports": [
            {
                "name": name,
                "path": report_paths[name].name,
                "report_fingerprint_sha256": reports[name][
                    "report_fingerprint_sha256"
                ],
            }
            for name in sorted(reports)
        ],
    }
    suite_fingerprint = benchmark_fingerprint(manifest_body)
    manifest = {
        **manifest_body,
        "suite_fingerprint_sha256": suite_fingerprint,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return Lund2013BenchmarkSuiteRun(
        output_dir=output_path,
        report_paths=report_paths,
        reports=reports,
        manifest_path=manifest_path,
        manifest=manifest,
        suite_fingerprint_sha256=suite_fingerprint,
    )
