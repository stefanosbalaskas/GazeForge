"""Command-line execution for audited VISUS dynamic-AOI validation workflows."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from .exceptions import BenchmarkIntegrityError
from .visus_audit import audit_visus_source, load_visus_source_audit_spec
from .visus_execution import (
    build_visus_execution_provenance,
    snapshot_visus_execution_inputs,
    validate_visus_execution_provenance,
    verify_visus_execution_inputs_unchanged,
    visus_execution_provenance_path,
    write_visus_execution_provenance,
)
from .visus_intake import prepare_visus_canonical_aoi_intake
from .visus_prediction import prepare_visus_dynamic_aoi_predictions
from .visus_scaffold import (
    build_visus_source_audit_scaffold,
    write_visus_source_audit_scaffold,
)
from .visus_suite import (
    run_visus_dynamic_aoi_validation_suite,
    validate_visus_dynamic_aoi_suite_manifest,
)


def _annotation_pair(value: str) -> tuple[str, str]:
    values = tuple(part.strip() for part in value.split(",") if part.strip())
    if len(values) != 2 or values[0] == values[1]:
        raise argparse.ArgumentTypeError(
            "human agreement streams must contain two distinct comma-separated IDs"
        )
    return values[0], values[1]


def _read_table(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(source)
    if suffix in {".tsv", ".txt"}:
        return pd.read_csv(source, sep="\t")
    raise ValueError("VISUS tabular inputs must be CSV or TSV files.")


def load_visus_timestamp_grids(path: str | Path) -> dict[str, list[float]]:
    """Load explicit per-stimulus evaluation timestamp grids from JSON.

    The JSON must contain one object mapping stimulus IDs to non-empty, strictly increasing
    timestamp arrays in milliseconds. The loader never derives timestamps from model emissions;
    callers must supply a separately reviewed grid file.
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or not payload:
        raise ValueError("VISUS timestamp-grid JSON must be a non-empty object.")

    grids: dict[str, list[float]] = {}
    for raw_stimulus, raw_values in payload.items():
        stimulus = str(raw_stimulus).strip()
        if not stimulus:
            raise ValueError("VISUS timestamp-grid stimulus IDs cannot be empty.")
        if not isinstance(raw_values, list) or not raw_values:
            raise ValueError(
                f"VISUS timestamp grid for {stimulus!r} must be a non-empty JSON array."
            )
        values: list[float] = []
        for raw_value in raw_values:
            if isinstance(raw_value, bool):
                raise ValueError(
                    f"VISUS timestamp grid for {stimulus!r} contains a boolean value."
                )
            try:
                value = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"VISUS timestamp grid for {stimulus!r} contains a non-numeric value."
                ) from exc
            if not math.isfinite(value):
                raise ValueError(
                    f"VISUS timestamp grid for {stimulus!r} must contain finite values."
                )
            values.append(value)
        if any(right <= left for left, right in zip(values, values[1:], strict=False)):
            raise ValueError(
                f"VISUS timestamp grid for {stimulus!r} must be strictly increasing."
            )
        grids[stimulus] = values
    return grids


def _emit_report(
    report: Mapping[str, Any],
    *,
    output: Path | None,
    overwrite: bool,
) -> None:
    if output is None:
        print(json.dumps(dict(report), indent=2, sort_keys=True, allow_nan=False))
        return

    target = Path(output)
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dict(report), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(target),
                "report_fingerprint_sha256": report["report_fingerprint_sha256"],
            },
            sort_keys=True,
        )
    )


def _load_audit(source_root: Path, spec_path: Path):
    spec = load_visus_source_audit_spec(spec_path)
    return audit_visus_source(source_root, spec)


def build_parser() -> argparse.ArgumentParser:
    """Build the dedicated VISUS execution parser."""
    parser = argparse.ArgumentParser(
        prog="gazeforge-visus",
        description=(
            "Audited VISUS dynamic-AOI execution. This interface never promotes templates or "
            "model-emission frames into empirical evidence."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    scaffold = subparsers.add_parser(
        "scaffold",
        help=(
            "Inventory a candidate VISUS tree into a deliberately non-empirical review template "
            "without inferring scientific file roles or identities."
        ),
    )
    scaffold.add_argument("source_root", type=Path)
    scaffold.add_argument("output", type=Path)
    scaffold.add_argument("--overwrite", action="store_true")

    audit = subparsers.add_parser(
        "audit",
        help="Verify one exact empirical VISUS snapshot against a reviewed JSON source spec.",
    )
    audit.add_argument("source_root", type=Path)
    audit.add_argument("spec", type=Path)
    audit.add_argument("--output", type=Path)
    audit.add_argument("--overwrite", action="store_true")

    human = subparsers.add_parser(
        "human-intake",
        help="Validate a reviewed frame-indexed human AOI table against the audited source.",
    )
    human.add_argument("source_root", type=Path)
    human.add_argument("spec", type=Path)
    human.add_argument("table", type=Path)
    human.add_argument("--extraction-basis", required=True)
    human.add_argument("--frame-index-base", type=int, choices=(0, 1), required=True)
    human.add_argument("--output", type=Path)
    human.add_argument("--overwrite", action="store_true")

    prediction = subparsers.add_parser(
        "prediction-intake",
        help="Validate frame-indexed detector/tracker output against exact audited videos.",
    )
    prediction.add_argument("source_root", type=Path)
    prediction.add_argument("spec", type=Path)
    prediction.add_argument("table", type=Path)
    prediction.add_argument("--model-name", required=True)
    prediction.add_argument("--model-version", required=True)
    prediction.add_argument("--prediction-basis", required=True)
    prediction.add_argument("--prediction-coordinate-unit", required=True)
    prediction.add_argument("--frame-index-base", type=int, choices=(0, 1), required=True)
    prediction.add_argument("--model-artifact-sha256")
    prediction.add_argument("--output", type=Path)
    prediction.add_argument("--overwrite", action="store_true")

    suite = subparsers.add_parser(
        "suite",
        help=(
            "Audit source, canonicalize human/model AOIs, consume a separately supplied timestamp "
            "grid, freeze the suite, and bind exact raw execution inputs to it."
        ),
    )
    suite.add_argument("source_root", type=Path)
    suite.add_argument("spec", type=Path)
    suite.add_argument("human_table", type=Path)
    suite.add_argument("prediction_table", type=Path)
    suite.add_argument("timestamp_grids", type=Path)
    suite.add_argument("output_dir", type=Path)
    suite.add_argument("--extraction-basis", required=True)
    suite.add_argument("--human-frame-index-base", type=int, choices=(0, 1), required=True)
    suite.add_argument("--model-name", required=True)
    suite.add_argument("--model-version", required=True)
    suite.add_argument("--prediction-basis", required=True)
    suite.add_argument("--prediction-coordinate-unit", required=True)
    suite.add_argument("--prediction-frame-index-base", type=int, choices=(0, 1), required=True)
    suite.add_argument("--model-artifact-sha256")
    suite.add_argument("--reference-stream-id", required=True)
    suite.add_argument("--timestamp-grid-basis", required=True)
    suite.add_argument("--max-interpolation-gap-ms", type=float, required=True)
    suite.add_argument("--min-iou", type=float, default=0.50)
    suite.add_argument(
        "--overlap-rule",
        choices=("highest_confidence", "smallest_area", "first"),
        default="highest_confidence",
    )
    suite.add_argument(
        "--human-agreement-streams",
        type=_annotation_pair,
        help=(
            "Two distinct comma-separated stream IDs. Supplying this remains blocked unless the "
            "source audit independently verifies separately recoverable annotation streams."
        ),
    )
    suite.add_argument(
        "--allow-label-mismatch",
        action="store_true",
        help="Permit geometric matching between AOIs whose semantic labels differ.",
    )
    suite.add_argument("--include-matches", action="store_true")
    suite.add_argument("--overwrite", action="store_true")

    validate = subparsers.add_parser(
        "suite-validate",
        help="Verify a frozen VISUS suite completion manifest and its child reports.",
    )
    validate.add_argument("path", type=Path)
    validate.add_argument("--manifest-only", action="store_true")

    execution_validate = subparsers.add_parser(
        "execution-validate",
        help="Verify frozen raw-input execution provenance and, by default, its sibling suite.",
    )
    execution_validate.add_argument("path", type=Path)
    execution_validate.add_argument(
        "--provenance-only",
        action="store_true",
        help="Validate only the provenance manifest without reopening the sibling suite reports.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one guarded VISUS command."""
    args = build_parser().parse_args(argv)

    if args.command == "scaffold":
        run = build_visus_source_audit_scaffold(args.source_root)
        target = write_visus_source_audit_scaffold(
            run,
            args.output,
            overwrite=args.overwrite,
        )
        print(
            json.dumps(
                {
                    "dataset": "VISUS",
                    "status": "template",
                    "output": str(target),
                    "file_count": run.file_count,
                    "inventory_fingerprint_sha256": run.inventory_fingerprint_sha256,
                    "roles_inferred": False,
                    "scientific_identities_inferred": False,
                    "empirical_evidence_created": False,
                },
                sort_keys=True,
            )
        )
        return 0

    if args.command == "audit":
        run = _load_audit(args.source_root, args.spec)
        _emit_report(run.report, output=args.output, overwrite=args.overwrite)
        return 0

    if args.command == "human-intake":
        audit = _load_audit(args.source_root, args.spec)
        run = prepare_visus_canonical_aoi_intake(
            audit,
            _read_table(args.table),
            extraction_basis=args.extraction_basis,
            frame_index_base=args.frame_index_base,
        )
        _emit_report(run.report, output=args.output, overwrite=args.overwrite)
        return 0

    if args.command == "prediction-intake":
        audit = _load_audit(args.source_root, args.spec)
        run = prepare_visus_dynamic_aoi_predictions(
            audit,
            _read_table(args.table),
            model_name=args.model_name,
            model_version=args.model_version,
            prediction_basis=args.prediction_basis,
            prediction_coordinate_unit=args.prediction_coordinate_unit,
            frame_index_base=args.frame_index_base,
            model_artifact_sha256=args.model_artifact_sha256,
        )
        _emit_report(run.report, output=args.output, overwrite=args.overwrite)
        return 0

    if args.command == "suite":
        provenance_target = visus_execution_provenance_path(args.output_dir)
        if provenance_target.exists() and not args.overwrite:
            raise FileExistsError(provenance_target)
        snapshots = snapshot_visus_execution_inputs(
            source_audit_spec=args.spec,
            human_aoi_table=args.human_table,
            model_prediction_table=args.prediction_table,
            timestamp_grid_json=args.timestamp_grids,
        )
        audit = _load_audit(args.source_root, args.spec)
        reference = prepare_visus_canonical_aoi_intake(
            audit,
            _read_table(args.human_table),
            extraction_basis=args.extraction_basis,
            frame_index_base=args.human_frame_index_base,
        )
        prediction = prepare_visus_dynamic_aoi_predictions(
            audit,
            _read_table(args.prediction_table),
            model_name=args.model_name,
            model_version=args.model_version,
            prediction_basis=args.prediction_basis,
            prediction_coordinate_unit=args.prediction_coordinate_unit,
            frame_index_base=args.prediction_frame_index_base,
            model_artifact_sha256=args.model_artifact_sha256,
        )
        timestamp_grids = load_visus_timestamp_grids(args.timestamp_grids)
        run = run_visus_dynamic_aoi_validation_suite(
            audit,
            reference,
            prediction,
            timestamp_grids,
            args.output_dir,
            reference_stream_id=args.reference_stream_id,
            timestamp_grid_basis=args.timestamp_grid_basis,
            max_interpolation_gap_ms=args.max_interpolation_gap_ms,
            min_iou=args.min_iou,
            require_label_match=not args.allow_label_mismatch,
            overlap_rule=args.overlap_rule,
            human_agreement_streams=args.human_agreement_streams,
            include_matches=args.include_matches,
            overwrite=args.overwrite,
        )
        verify_visus_execution_inputs_unchanged(
            snapshots,
            source_audit_spec=args.spec,
            human_aoi_table=args.human_table,
            model_prediction_table=args.prediction_table,
            timestamp_grid_json=args.timestamp_grids,
        )
        post_audit = _load_audit(args.source_root, args.spec)
        if post_audit.report["report_fingerprint_sha256"] != audit.report[
            "report_fingerprint_sha256"
        ]:
            raise BenchmarkIntegrityError(
                "The audited VISUS source tree changed during suite execution."
            )
        provenance_manifest = build_visus_execution_provenance(audit, run, snapshots)
        provenance = write_visus_execution_provenance(
            provenance_manifest,
            args.output_dir,
            overwrite=args.overwrite,
        )
        validate_visus_execution_provenance(provenance.manifest_path, verify_suite=True)
        print(
            json.dumps(
                {
                    "suite": run.manifest["suite"],
                    "status": run.manifest["status"],
                    "output_dir": str(run.output_dir),
                    "report_count": len(run.reports),
                    "manifest": str(run.manifest_path),
                    "source_audit_report_fingerprint_sha256": audit.report[
                        "report_fingerprint_sha256"
                    ],
                    "suite_fingerprint_sha256": run.suite_fingerprint_sha256,
                    "execution_provenance": str(provenance.manifest_path),
                    "execution_fingerprint_sha256": (
                        provenance.execution_fingerprint_sha256
                    ),
                    "external_timestamp_grid_required": True,
                    "prediction_emission_grid_used": False,
                },
                sort_keys=True,
            )
        )
        return 0

    if args.command == "suite-validate":
        summary = validate_visus_dynamic_aoi_suite_manifest(
            args.path,
            verify_reports=not args.manifest_only,
        )
        print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
        return 0

    if args.command == "execution-validate":
        summary = validate_visus_execution_provenance(
            args.path,
            verify_suite=not args.provenance_only,
        )
        print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
        return 0

    build_parser().print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
