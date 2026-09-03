"""Audited model-prediction intake for VISUS dynamic AOI validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from .benchmarks import benchmark_fingerprint
from .dynamic_aoi import DynamicAOIKeyframe
from .exceptions import BenchmarkIntegrityError, SchemaError
from .provenance import fingerprint_frame
from .visus_audit import VisusSourceAuditRun

_REQUIRED_COLUMNS = (
    "stimulus_id",
    "frame_index",
    "aoi_id",
    "label",
    "xmin",
    "ymin",
    "xmax",
    "ymax",
)

_PIXEL_UNITS = {"pixel", "pixels", "px"}


@dataclass(slots=True)
class VisusDynamicAOIPredictionIntakeRun:
    """Canonical model AOI predictions linked to an audited VISUS video snapshot."""

    canonical: pd.DataFrame
    by_stimulus: dict[str, list[DynamicAOIKeyframe]]
    report: dict[str, Any]


def _resolved(value: str) -> bool:
    text = str(value).strip()
    upper = text.upper()
    return bool(text) and "REPLACE" not in upper and "VERIFY" not in upper


def _verify_audit_integrity(audit: VisusSourceAuditRun) -> None:
    if not isinstance(audit, VisusSourceAuditRun):
        raise TypeError("audit must be a VisusSourceAuditRun instance.")
    if audit.report.get("status") != "verified":
        raise BenchmarkIntegrityError("VISUS source audit is not verified.")

    report_fingerprint = str(audit.report.get("report_fingerprint_sha256", ""))
    report_body = {
        key: value
        for key, value in audit.report.items()
        if key != "report_fingerprint_sha256"
    }
    if len(report_fingerprint) != 64 or benchmark_fingerprint(report_body) != report_fingerprint:
        raise BenchmarkIntegrityError("VISUS source-audit report fingerprint does not revalidate.")

    spec_fingerprint = str(audit.report.get("spec_fingerprint_sha256", ""))
    if benchmark_fingerprint(audit.spec.to_dict()) != spec_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS source-audit specification fingerprint does not revalidate."
        )

    manifest_rows = [asdict(item.record) for item in audit.files]
    expected_manifest = str(
        audit.report.get("inventory", {}).get("manifest_fingerprint_sha256", "")
    )
    if benchmark_fingerprint(manifest_rows) != expected_manifest:
        raise BenchmarkIntegrityError("VISUS source manifest fingerprint does not revalidate.")


def _audited_stimuli(audit: VisusSourceAuditRun) -> list[str]:
    values = audit.report.get("identity", {}).get("stimulus_ids", [])
    stimuli = sorted(str(value) for value in values)
    if not stimuli:
        raise BenchmarkIntegrityError(
            "VISUS source audit contains no verified stimulus identities."
        )
    return stimuli


def _video_ledger(audit: VisusSourceAuditRun, stimuli: list[str]) -> list[dict[str, Any]]:
    by_stimulus: dict[str, list[Any]] = {stimulus: [] for stimulus in stimuli}
    for item in audit.files:
        record = item.record
        if record.role != "video":
            continue
        stimulus_id = str(record.stimulus_id)
        if stimulus_id in by_stimulus:
            by_stimulus[stimulus_id].append(record)

    ledger: list[dict[str, Any]] = []
    for stimulus_id in stimuli:
        records = by_stimulus[stimulus_id]
        if len(records) != 1:
            raise BenchmarkIntegrityError(
                "VISUS prediction intake requires exactly one audited video per stimulus: "
                f"stimulus={stimulus_id!r}, count={len(records)}."
            )
        record = records[0]
        ledger.append(
            {
                "stimulus_id": stimulus_id,
                "path": record.path,
                "sha256": record.sha256,
                "bytes": int(record.bytes),
            }
        )
    return ledger


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise SchemaError(
            f"VISUS prediction column {column!r} must contain finite numeric data."
        )
    return values.astype(float)


def _normalize_coordinate_unit(value: str) -> str:
    unit = str(value).strip().lower()
    if unit in _PIXEL_UNITS:
        return "pixels"
    return unit


def _validate_model_artifact_sha256(value: str | None) -> str | None:
    if value is None:
        return None
    digest = str(value).strip().lower()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("model_artifact_sha256 must be a 64-character hexadecimal SHA-256.")
    return digest


def _validate_prediction_rows(
    table: pd.DataFrame,
    *,
    stimuli: list[str],
    frame_index_base: int,
    video_rate_hz: float,
    coordinate_unit: str,
    video_resolution_px: tuple[int, int],
    require_complete_stimulus_coverage: bool,
) -> pd.DataFrame:
    missing = [column for column in _REQUIRED_COLUMNS if column not in table.columns]
    if missing:
        raise SchemaError(f"VISUS prediction table is missing columns: {missing}")
    if table.empty:
        raise SchemaError("VISUS prediction table cannot be empty.")

    selected_columns = list(_REQUIRED_COLUMNS)
    if "confidence" in table:
        selected_columns.append("confidence")
    canonical = table.loc[:, selected_columns].copy()

    for column in ("stimulus_id", "aoi_id", "label"):
        canonical[column] = canonical[column].astype(str).str.strip()
        if (canonical[column] == "").any():
            raise SchemaError(f"VISUS prediction column {column!r} cannot contain empty values.")

    observed_stimuli = set(canonical["stimulus_id"].tolist())
    expected_stimuli = set(stimuli)
    extra = sorted(observed_stimuli - expected_stimuli)
    missing_stimuli = sorted(expected_stimuli - observed_stimuli)
    if extra or (require_complete_stimulus_coverage and missing_stimuli):
        raise SchemaError(
            "VISUS predictions must use only audited stimuli and satisfy the requested coverage: "
            f"missing={missing_stimuli}, extra={extra}."
        )

    frame_values = _numeric(canonical, "frame_index")
    rounded = np.rint(frame_values.to_numpy(dtype=float))
    if not np.allclose(frame_values.to_numpy(dtype=float), rounded, rtol=0.0, atol=1e-9):
        raise SchemaError("VISUS prediction frame_index values must be integers.")
    canonical["frame_index"] = rounded.astype(int)
    if (canonical["frame_index"] < frame_index_base).any():
        raise SchemaError(
            f"VISUS prediction frame_index values must be >= explicit base {frame_index_base}."
        )

    for column in ("xmin", "ymin", "xmax", "ymax"):
        canonical[column] = _numeric(canonical, column)
    if (canonical["xmax"] <= canonical["xmin"]).any() or (
        canonical["ymax"] <= canonical["ymin"]
    ).any():
        raise SchemaError("VISUS predicted AOI boxes must satisfy xmax > xmin and ymax > ymin.")

    confidence_defaulted = "confidence" not in canonical
    if confidence_defaulted:
        canonical["confidence"] = 1.0
    else:
        canonical["confidence"] = _numeric(canonical, "confidence")
    if ((canonical["confidence"] < 0.0) | (canonical["confidence"] > 1.0)).any():
        raise SchemaError("VISUS prediction confidence must lie in [0, 1].")

    if coordinate_unit == "pixels":
        width, height = video_resolution_px
        outside = (
            (canonical["xmin"] < 0.0)
            | (canonical["ymin"] < 0.0)
            | (canonical["xmax"] > float(width))
            | (canonical["ymax"] > float(height))
        )
        if outside.any():
            raise SchemaError(
                "VISUS predicted pixel AOI bounds must remain inside the audited video resolution."
            )

    duplicate_key = ["stimulus_id", "aoi_id", "frame_index"]
    if canonical.duplicated(duplicate_key).any():
        raise SchemaError(
            "VISUS prediction table contains duplicate stimulus/AOI/frame identities."
        )

    label_counts = canonical.groupby(["stimulus_id", "aoi_id"], dropna=False)[
        "label"
    ].nunique()
    if (label_counts > 1).any():
        raise SchemaError("Each VISUS predicted AOI track must keep one label across keyframes.")

    canonical["timestamp_ms"] = (
        canonical["frame_index"].astype(float) - float(frame_index_base)
    ) * (1000.0 / float(video_rate_hz))
    canonical["confidence_defaulted"] = bool(confidence_defaulted)
    canonical = canonical.sort_values(
        ["stimulus_id", "aoi_id", "frame_index"],
        kind="stable",
    ).reset_index(drop=True)
    return canonical


def _to_keyframes(
    canonical: pd.DataFrame,
    *,
    model_name: str,
    model_version: str,
) -> dict[str, list[DynamicAOIKeyframe]]:
    result: dict[str, list[DynamicAOIKeyframe]] = {}
    for stimulus_id, subset in canonical.groupby("stimulus_id", sort=True):
        result[str(stimulus_id)] = [
            DynamicAOIKeyframe(
                aoi_id=str(row.aoi_id),
                label=str(row.label),
                timestamp_ms=float(row.timestamp_ms),
                xmin=float(row.xmin),
                ymin=float(row.ymin),
                xmax=float(row.xmax),
                ymax=float(row.ymax),
                confidence=float(row.confidence),
                source="model",
                model_name=model_name,
                model_version=model_version,
            )
            for row in subset.itertuples(index=False)
        ]
    return result


def prepare_visus_dynamic_aoi_predictions(
    audit: VisusSourceAuditRun,
    table: pd.DataFrame,
    *,
    model_name: str,
    model_version: str,
    prediction_basis: str,
    prediction_coordinate_unit: str,
    frame_index_base: int,
    model_artifact_sha256: str | None = None,
    require_complete_stimulus_coverage: bool = True,
) -> VisusDynamicAOIPredictionIntakeRun:
    """Canonicalize externally generated VISUS model AOI tracks with audited provenance.

    The function expects frame-indexed model detections/tracks. It links every stimulus to the exact
    audited VISUS video file, converts frame indices with the audited video rate, and returns
    `DynamicAOIKeyframe` mappings suitable for model-human validation. It deliberately does not
    create an evaluation timestamp grid; prediction emission frames must never define that grid.
    """
    _verify_audit_integrity(audit)
    if not isinstance(table, pd.DataFrame):
        raise TypeError("table must be a pandas DataFrame.")
    if not _resolved(model_name) or not _resolved(model_version):
        raise ValueError("model_name and model_version must be explicit resolved values.")
    if not _resolved(prediction_basis):
        raise ValueError("prediction_basis must describe how the model output was generated.")
    if int(frame_index_base) not in {0, 1}:
        raise ValueError("frame_index_base must be explicitly 0 or 1.")
    if not audit.spec.timestamp_basis_verified:
        raise BenchmarkIntegrityError(
            "VISUS prediction intake requires an audited timestamp/frame-time basis."
        )
    if not audit.spec.coordinate_unit_verified:
        raise BenchmarkIntegrityError(
            "VISUS prediction intake requires an audited coordinate-unit basis."
        )

    audited_unit = _normalize_coordinate_unit(audit.spec.coordinate_unit)
    prediction_unit = _normalize_coordinate_unit(prediction_coordinate_unit)
    if not prediction_unit:
        raise ValueError("prediction_coordinate_unit cannot be empty.")
    if prediction_unit != audited_unit:
        raise SchemaError(
            "VISUS prediction coordinate unit must match the audited reference coordinate unit: "
            f"prediction={prediction_unit!r}, audited={audited_unit!r}."
        )

    video_rate_hz = float(audit.spec.published_video_frame_rate_hz)
    if not np.isfinite(video_rate_hz) or video_rate_hz <= 0:
        raise BenchmarkIntegrityError("VISUS audited video frame rate must be finite and positive.")

    stimuli = _audited_stimuli(audit)
    video_ledger = _video_ledger(audit, stimuli)
    input_fingerprint = fingerprint_frame(table)
    artifact_digest = _validate_model_artifact_sha256(model_artifact_sha256)
    canonical = _validate_prediction_rows(
        table,
        stimuli=stimuli,
        frame_index_base=int(frame_index_base),
        video_rate_hz=video_rate_hz,
        coordinate_unit=prediction_unit,
        video_resolution_px=audit.spec.published_video_resolution_px,
        require_complete_stimulus_coverage=bool(require_complete_stimulus_coverage),
    )
    by_stimulus = _to_keyframes(
        canonical,
        model_name=str(model_name).strip(),
        model_version=str(model_version).strip(),
    )

    body = {
        "status": "verified-prediction-intake",
        "dataset": "VISUS",
        "source_audit_report_fingerprint_sha256": audit.report["report_fingerprint_sha256"],
        "source_audit_spec_fingerprint_sha256": audit.report["spec_fingerprint_sha256"],
        "source_manifest_fingerprint_sha256": audit.report["inventory"][
            "manifest_fingerprint_sha256"
        ],
        "input_table_fingerprint_sha256": input_fingerprint,
        "canonical_table_fingerprint_sha256": fingerprint_frame(canonical),
        "model": {
            "name": str(model_name).strip(),
            "version": str(model_version).strip(),
            "artifact_sha256": artifact_digest,
            "prediction_basis": str(prediction_basis).strip(),
        },
        "frame_index_base": int(frame_index_base),
        "video_frame_rate_hz": video_rate_hz,
        "frame_to_timestamp_formula": (
            "(frame_index - frame_index_base) * 1000 / video_frame_rate_hz"
        ),
        "prediction_coordinate_unit": prediction_unit,
        "audited_coordinate_unit": audited_unit,
        "video_resolution_px": list(audit.spec.published_video_resolution_px),
        "complete_audited_stimulus_coverage_required": bool(
            require_complete_stimulus_coverage
        ),
        "stimulus_ids": sorted(canonical["stimulus_id"].unique().tolist()),
        "row_count": int(len(canonical)),
        "audited_video_files": video_ledger,
        "evaluation_timestamp_grid_generated": False,
        "claim_limits": [
            "Prediction intake validates model-output provenance and geometry, not performance.",
            (
                "Model emission frames are not an evaluation grid; validation requires an "
                "external timestamp grid."
            ),
            "No VISUS empirical performance claim exists until reviewed real data are evaluated.",
        ],
    }
    report = {**body, "report_fingerprint_sha256": benchmark_fingerprint(body)}
    return VisusDynamicAOIPredictionIntakeRun(
        canonical=canonical,
        by_stimulus=by_stimulus,
        report=report,
    )
