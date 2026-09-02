"""Command-line entry point for auditable GazeForge workflows."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .benchmarks import freeze_benchmark_report
from .lund_benchmark import compare_lund2013_annotators, run_lund2013_event_benchmark


def _hidden_layers(value: str) -> tuple[int, ...]:
    try:
        layers = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("hidden layers must be comma-separated integers") from exc
    if not layers or any(layer <= 0 for layer in layers):
        raise argparse.ArgumentTypeError("hidden layers must contain positive integers")
    return layers


def build_parser() -> argparse.ArgumentParser:
    """Build the GazeForge command-line parser."""
    parser = argparse.ArgumentParser(prog="gazeforge", description="Auditable AI for eye tracking.")
    parser.add_argument("--version", action="store_true", help="Print installed GazeForge version.")
    subparsers = parser.add_subparsers(dest="command")

    benchmark = subparsers.add_parser(
        "lund2013-benchmark",
        help="Run the participant-held-out Lund2013 event benchmark from a local dataset checkout.",
    )
    benchmark.add_argument("root", type=Path, help="Root containing Lund2013 annotated .mat files.")
    benchmark.add_argument("--annotator", default="RA")
    benchmark.add_argument("--target-rate", type=float, default=60.0)
    benchmark.add_argument("--min-label-purity", type=float, default=0.75)
    benchmark.add_argument("--n-splits", type=int, default=5)
    benchmark.add_argument("--n-estimators", type=int, default=200)
    benchmark.add_argument("--ivt-threshold-deg-s", type=float, default=45.0)
    benchmark.add_argument("--context-radius-ms", type=float, default=50.0)
    benchmark.add_argument("--hidden-layers", type=_hidden_layers, default=(64, 32))
    benchmark.add_argument("--temporal-solver", default="adam")
    benchmark.add_argument("--temporal-max-iter", type=int, default=200)
    benchmark.add_argument("--output", type=Path)
    benchmark.add_argument("--overwrite", action="store_true")

    agreement = subparsers.add_parser(
        "lund2013-agreement",
        help="Measure MN-vs-RA Lund2013 sample-label agreement.",
    )
    agreement.add_argument("root", type=Path)
    agreement.add_argument("--left-annotator", default="MN")
    agreement.add_argument("--right-annotator", default="RA")
    agreement.add_argument("--target-rate", type=float)
    agreement.add_argument("--min-label-purity", type=float, default=0.75)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one GazeForge CLI command."""
    args = build_parser().parse_args(argv)
    if args.version:
        print(__version__)
        return 0

    if args.command == "lund2013-benchmark":
        run = run_lund2013_event_benchmark(
            args.root,
            annotator=args.annotator,
            target_sampling_rate_hz=args.target_rate,
            min_label_purity=args.min_label_purity,
            n_splits=args.n_splits,
            n_estimators=args.n_estimators,
            ivt_velocity_threshold_deg_s=args.ivt_threshold_deg_s,
            context_radius_ms=args.context_radius_ms,
            hidden_layer_sizes=args.hidden_layers,
            temporal_solver=args.temporal_solver,
            temporal_max_iter=args.temporal_max_iter,
        )
        if args.output is not None:
            target = freeze_benchmark_report(run.report, args.output, overwrite=args.overwrite)
            print(
                json.dumps(
                    {
                        "benchmark": "Lund2013",
                        "output": str(target),
                        "report_fingerprint_sha256": run.report["report_fingerprint_sha256"],
                    },
                    sort_keys=True,
                )
            )
        else:
            print(json.dumps(run.report, indent=2, sort_keys=True, allow_nan=False))
        return 0

    if args.command == "lund2013-agreement":
        report = compare_lund2013_annotators(
            args.root,
            left_annotator=args.left_annotator,
            right_annotator=args.right_annotator,
            target_sampling_rate_hz=args.target_rate,
            min_label_purity=args.min_label_purity,
        )
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 0

    print(json.dumps({"package": "gazeforge", "status": "ready"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
