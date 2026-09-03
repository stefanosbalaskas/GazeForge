"""One-command orchestration for the complete Lund2013 validation tranche."""

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
from .lund_fetch import validate_lund2013_source_manifest
from .lund_sensitivity import run_lund2013_sampling_sensitivity

_SUITE_NAME = "lund2013-event-validation-v1"


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


def _validate_child_report(name: str, report: dict[str, Any]) -> None:
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
    manifest_path = output_path / "lund2013-suite-manifest.json"
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
