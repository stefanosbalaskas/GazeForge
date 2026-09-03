"""Native-rate human event benchmark intake and matched model validation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .benchmarks import BenchmarkDatasetCard, benchmark_fingerprint, build_benchmark_report
from .comparison import EventModelComparison, compare_event_models_grouped
from .exceptions import SchemaError
from .paired import PairedModelDifferences, paired_model_metric_differences
from .provenance import fingerprint_frame
from .schema import canonicalize_gaze, infer_sampling_rate_hz

_REQUIRED_COLUMN_KEYS = (
    "participant_id",
    "trial_id",
    "timestamp_ms",
    "x_px",
    "y_px",
    "event_label",
)
_ANGULAR_GEOMETRY_COLUMNS = (
    "screen_width_px",
    "screen_height_px",
    "screen_width_physical",
    "screen_height_physical",
    "view_distance_physical",
)


@dataclass(slots=True)
class NativeEventBenchmarkSpec:
    """Explicit metadata contract for a native-rate human-labelled event corpus."""

    name: str
    version: str
    source: str
    license: str
    tracker_model: str
    expected_sampling_rate_hz: float
    dataset_status: str = "empirical"
    annotation_origin: str = "expert-manual"
    human_annotator_count: int = 1
    reference_description: str = "Expert manual sample-level eye-movement event labels."
    sampling_rate_tolerance_fraction: float = 0.05
    column_map: dict[str, str] = field(default_factory=dict)
    analysis_excluded_labels: tuple[str, ...] = ("unlabelled", "undefined")
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Reject incomplete or misleading native-evidence metadata."""
        for field_name in ("name", "version", "source", "license", "tracker_model"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must not be empty.")
        if self.dataset_status not in {"empirical", "template"}:
            raise ValueError("dataset_status must be 'empirical' or 'template'.")
        if self.annotation_origin not in {"expert-manual", "human-manual"}:
            raise ValueError(
                "Native event benchmark references must be expert-manual or human-manual."
            )
        if self.human_annotator_count < 1:
            raise ValueError("human_annotator_count must be at least one.")
        if not np.isfinite(self.expected_sampling_rate_hz) or self.expected_sampling_rate_hz <= 0:
            raise ValueError("expected_sampling_rate_hz must be finite and positive.")
        tolerance = float(self.sampling_rate_tolerance_fraction)
        if not np.isfinite(tolerance) or not 0.0 <= tolerance < 1.0:
            raise ValueError("sampling_rate_tolerance_fraction must be in [0, 1).")
        if not self.column_map:
            self.column_map = {key: key for key in _REQUIRED_COLUMN_KEYS}
        missing = [key for key in _REQUIRED_COLUMN_KEYS if key not in self.column_map]
        if missing:
            raise ValueError(f"column_map is missing required canonical keys: {missing}")
        source_columns = list(self.column_map.values())
        if len(source_columns) != len(set(source_columns)):
            raise ValueError("column_map source-column names must be unique.")
        self.analysis_excluded_labels = tuple(
            str(label).strip() for label in self.analysis_excluded_labels
        )
        self.notes = [str(note) for note in self.notes]

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible specification mapping."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> NativeEventBenchmarkSpec:
        """Construct a specification from decoded JSON without silently ignoring keys."""
        values = dict(payload)
        if "analysis_excluded_labels" in values:
            values["analysis_excluded_labels"] = tuple(values["analysis_excluded_labels"])
        if "notes" in values:
            values["notes"] = list(values["notes"])
        if "column_map" in values:
            values["column_map"] = dict(values["column_map"])
        return cls(**values)


@dataclass(slots=True)
class NativeEventPreparedBenchmark:
    """Verified native-rate analysis table plus evidence metadata."""

    data: pd.DataFrame
    dataset_card: BenchmarkDatasetCard
    spec: NativeEventBenchmarkSpec
    preparation_report: dict[str, Any]


@dataclass(slots=True)
class NativeEventBenchmarkRun:
    """Prepared native corpus, matched model comparison, and frozen-report payload."""

    prepared: NativeEventPreparedBenchmark
    comparison: EventModelComparison
    paired_model_differences: PairedModelDifferences
    report: dict[str, Any]


def _json_safe_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def file_sha256(path: str | Path) -> str:
    """Return the SHA-256 digest of an external benchmark source file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_native_event_spec(path: str | Path) -> NativeEventBenchmarkSpec:
    """Load a native event benchmark specification from JSON."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Native event benchmark specification must contain one JSON object.")
    return NativeEventBenchmarkSpec.from_dict(payload)


def load_native_event_table(path: str | Path) -> pd.DataFrame:
    """Load a portable native benchmark table from CSV or TSV without altering rows."""
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(source)
    if suffix in {".tsv", ".tab"}:
        return pd.read_csv(source, sep="\t")
    raise ValueError("Native event benchmark tables must be CSV or TSV files.")


def _standardize_columns(
    data: pd.DataFrame,
    spec: NativeEventBenchmarkSpec,
) -> pd.DataFrame:
    if not isinstance(data, pd.DataFrame):
        raise SchemaError("Native event benchmark data must be a pandas DataFrame.")
    missing_sources = [
        source for source in spec.column_map.values() if source not in data.columns
    ]
    if missing_sources:
        raise SchemaError(f"Native event source columns are missing: {missing_sources}")
    reverse = {source: canonical for canonical, source in spec.column_map.items()}
    frame = data.rename(columns=reverse).copy()
    if frame.columns.duplicated().any():
        duplicates = frame.columns[frame.columns.duplicated()].astype(str).tolist()
        raise SchemaError(f"Column mapping produced duplicate canonical columns: {duplicates}")
    return frame


def _select_annotator(
    data: pd.DataFrame,
    *,
    annotator: str | None,
) -> tuple[pd.DataFrame, str | None]:
    if "annotator_id" not in data.columns:
        if annotator is not None:
            raise SchemaError(
                "An annotator was requested but column_map does not provide annotator_id."
            )
        return data.copy(), None

    if data["annotator_id"].isna().any():
        raise SchemaError("annotator_id contains missing values.")
    values = data["annotator_id"].astype(str).str.strip()
    if values.eq("").any():
        raise SchemaError("annotator_id contains empty values.")
    available = sorted(values.unique().tolist())
    if annotator is None:
        if len(available) != 1:
            raise SchemaError(
                "Multiple annotation streams are present; select one annotator explicitly."
            )
        selected = available[0]
    else:
        selected = str(annotator)
        if selected not in available:
            raise SchemaError(
                f"Unknown annotator {selected!r}; available annotators are {available}."
            )
    frame = data.loc[values == selected].copy()
    frame["annotator_id"] = selected
    return frame, selected


def _group_sampling_rates(data: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (participant, trial), part in data.groupby(
        ["participant_id", "trial_id"], sort=True, dropna=False
    ):
        timestamps = pd.to_numeric(part["timestamp_ms"], errors="coerce").to_numpy(float)
        timestamps = np.sort(timestamps[np.isfinite(timestamps)])
        if len(timestamps) < 2:
            raise SchemaError(
                "Every native benchmark trial needs at least two timestamps for rate verification."
            )
        deltas = np.diff(timestamps)
        deltas = deltas[deltas > 0]
        if len(deltas) == 0:
            raise SchemaError("A native benchmark trial has no positive timestamp intervals.")
        rows.append(
            {
                "participant_id": str(participant),
                "trial_id": str(trial),
                "sampling_rate_hz": float(1000.0 / np.median(deltas)),
            }
        )
    return pd.DataFrame(rows)


def prepare_native_event_benchmark(
    data: pd.DataFrame,
    spec: NativeEventBenchmarkSpec,
    *,
    annotator: str | None = None,
    source_file_name: str | None = None,
    source_file_sha256: str | None = None,
) -> NativeEventPreparedBenchmark:
    """Verify that human-labelled samples are genuinely native-rate benchmark evidence.

    No temporal resampling occurs in this function. The declared native sampling rate is checked
    both globally and within every participant/trial group before the dataset card can claim native
    human-reference evidence.
    """
    if spec.dataset_status != "empirical":
        raise SchemaError(
            "Template benchmark specifications cannot produce empirical reports; set "
            "dataset_status='empirical' only after real data and provenance are available."
        )

    frame = _standardize_columns(data, spec)
    frame, selected_annotator = _select_annotator(frame, annotator=annotator)
    if frame.empty:
        raise SchemaError("Selected native event annotation stream is empty.")
    if frame[["participant_id", "trial_id"]].isna().any().any():
        raise SchemaError("participant_id and trial_id must not contain missing values.")
    if frame["event_label"].isna().any():
        raise SchemaError("event_label contains missing values; encode exclusions explicitly.")
    frame["event_label"] = frame["event_label"].astype(str).str.strip()
    if frame["event_label"].eq("").any():
        raise SchemaError("event_label contains empty values.")

    keys = ["participant_id", "trial_id", "timestamp_ms"]
    if frame.duplicated(keys).any():
        raise SchemaError(
            "Selected native event stream contains duplicate participant/trial/timestamp keys."
        )

    gaze = canonicalize_gaze(frame, sort=True)
    source = gaze.data.copy()
    observed_rate = float(infer_sampling_rate_hz(source))
    group_rates = _group_sampling_rates(source)
    expected = float(spec.expected_sampling_rate_hz)
    tolerance = float(spec.sampling_rate_tolerance_fraction)
    group_rates["relative_error"] = (
        (group_rates["sampling_rate_hz"] - expected).abs() / expected
    )
    outliers = group_rates.loc[group_rates["relative_error"] > tolerance]
    global_relative_error = abs(observed_rate - expected) / expected
    if global_relative_error > tolerance or not outliers.empty:
        raise SchemaError(
            "Native sampling-rate verification failed: "
            f"declared={expected:.6g} Hz, observed={observed_rate:.6g} Hz, "
            f"tolerance={tolerance:.1%}, outlier_groups={len(outliers)}. "
            "Do not label resampled or rate-incompatible data as native evidence."
        )

    labels_before = source["event_label"].astype(str)
    excluded = {label.lower() for label in spec.analysis_excluded_labels if label}
    retained_mask = ~labels_before.str.lower().isin(excluded)
    retained = source.loc[retained_mask].copy().reset_index(drop=True)
    if retained.empty:
        raise SchemaError("Native event exclusions removed every benchmark row.")
    if retained["event_label"].nunique() < 2:
        raise SchemaError("Native event benchmark requires at least two retained event classes.")
    if retained["participant_id"].nunique() < 2:
        raise SchemaError("Native event benchmark requires at least two participants.")

    reference_strength = (
        "expert-human-reference"
        if spec.annotation_origin == "expert-manual"
        else "human-reference"
    )
    dataset_card = BenchmarkDatasetCard(
        name=spec.name,
        version=spec.version,
        source=spec.source,
        license=spec.license,
        task="native-rate sample-level eye-movement event classification",
        sampling_rates_hz=[observed_rate],
        participant_count=int(retained["participant_id"].nunique()),
        stimulus_count=int(retained["trial_id"].nunique()),
        split_unit="participant_id",
        validation_scope="native-device-empirical-benchmark",
        annotation_origin=spec.annotation_origin,
        sampling_origin="native",
        reference_strength=reference_strength,
        human_annotator_count=int(spec.human_annotator_count),
        reference_description=spec.reference_description,
        notes=[
            f"Tracker/device declaration: {spec.tracker_model}.",
            "Observed native sampling rate was verified from timestamps; no resampling was used.",
            *spec.notes,
        ],
    )
    preparation_report: dict[str, Any] = {
        "dataset_status": spec.dataset_status,
        "tracker_model": spec.tracker_model,
        "selected_annotator": selected_annotator,
        "expected_sampling_rate_hz": expected,
        "observed_sampling_rate_hz": observed_rate,
        "sampling_rate_tolerance_fraction": tolerance,
        "native_rate_verified": True,
        "resampling": None,
        "group_sampling_rate_hz": _json_safe_records(group_rates),
        "source_rows": int(len(source)),
        "analysis_rows": int(len(retained)),
        "excluded_rows": int((~retained_mask).sum()),
        "excluded_labels": sorted(excluded),
        "label_counts_before_exclusions": labels_before.value_counts().sort_index().to_dict(),
        "label_counts_analysis": (
            retained["event_label"].value_counts().sort_index().to_dict()
        ),
        "participant_count": int(retained["participant_id"].nunique()),
        "trial_count": int(retained["trial_id"].nunique()),
        "spec_fingerprint_sha256": benchmark_fingerprint(spec.to_dict()),
        "source_frame_fingerprint_sha256": fingerprint_frame(source),
        "analysis_frame_fingerprint_sha256": fingerprint_frame(retained),
        "source_file_name": source_file_name,
        "source_file_sha256": source_file_sha256,
    }
    return NativeEventPreparedBenchmark(
        data=retained,
        dataset_card=dataset_card,
        spec=spec,
        preparation_report=preparation_report,
    )


def run_native_event_benchmark(
    data: pd.DataFrame,
    spec: NativeEventBenchmarkSpec,
    *,
    annotator: str | None = None,
    n_splits: int = 5,
    ivt_velocity_threshold_deg_s: float | None = None,
    ivt_velocity_threshold_px_s: float | None = None,
    random_state: int = 42,
    n_estimators: int = 200,
    context_radius_ms: float = 50.0,
    hidden_layer_sizes: tuple[int, ...] = (64, 32),
    temporal_solver: str = "adam",
    temporal_max_iter: int = 200,
    source_file_name: str | None = None,
    source_file_sha256: str | None = None,
) -> NativeEventBenchmarkRun:
    """Run matched participant-held-out validation on verified native-rate human labels."""
    if (ivt_velocity_threshold_deg_s is None) == (ivt_velocity_threshold_px_s is None):
        raise ValueError("Provide exactly one angular or pixel I-VT velocity threshold.")
    prepared = prepare_native_event_benchmark(
        data,
        spec,
        annotator=annotator,
        source_file_name=source_file_name,
        source_file_sha256=source_file_sha256,
    )
    if ivt_velocity_threshold_deg_s is not None:
        missing_geometry = [
            col for col in _ANGULAR_GEOMETRY_COLUMNS if col not in prepared.data.columns
        ]
        if missing_geometry:
            raise SchemaError(
                "Angular I-VT native validation requires explicit screen/viewing geometry: "
                f"{missing_geometry}"
            )

    groups = int(prepared.data["participant_id"].nunique())
    folds = min(int(n_splits), groups)
    if folds < 2:
        raise SchemaError("At least two participant folds are required for native validation.")
    rate = float(prepared.preparation_report["observed_sampling_rate_hz"])
    comparison = compare_event_models_grouped(
        prepared.data,
        n_splits=folds,
        sampling_rate_hz=rate,
        ivt_velocity_threshold_deg_s=ivt_velocity_threshold_deg_s,
        ivt_velocity_threshold_px_s=ivt_velocity_threshold_px_s,
        random_state=random_state,
        n_estimators=n_estimators,
        context_radius_ms=context_radius_ms,
        hidden_layer_sizes=hidden_layer_sizes,
        temporal_solver=temporal_solver,
        temporal_max_iter=temporal_max_iter,
    )
    paired_differences = paired_model_metric_differences(comparison.fold_metrics)
    metrics = {
        "summary": _json_safe_records(comparison.summary),
        "fold_metrics": _json_safe_records(comparison.fold_metrics),
        "paired_model_difference_summary": _json_safe_records(
            paired_differences.summary
        ),
        "paired_model_fold_deltas": _json_safe_records(paired_differences.deltas),
        "analysis_label_counts": prepared.preparation_report["label_counts_analysis"],
    }
    protocol = {
        "native_intake": prepared.preparation_report,
        "comparison_design": comparison.design,
        "paired_model_difference_design": paired_differences.design,
        "claim_limit": (
            "This report supports only the tracker/task/reference population declared in the "
            "empirical specification; it does not establish cross-device generalizability."
        ),
    }
    report = build_benchmark_report(
        benchmark=prepared.dataset_card,
        metrics=metrics,
        model={"models": comparison.design["models"]},
        protocol=protocol,
    )
    return NativeEventBenchmarkRun(
        prepared=prepared,
        comparison=comparison,
        paired_model_differences=paired_differences,
        report=report,
    )


def run_native_event_file_benchmark(
    data_path: str | Path,
    spec_path: str | Path,
    **kwargs: Any,
) -> NativeEventBenchmarkRun:
    """Load, fingerprint, verify, and benchmark one native human-labelled event table."""
    data_file = Path(data_path)
    spec = load_native_event_spec(spec_path)
    data = load_native_event_table(data_file)
    return run_native_event_benchmark(
        data,
        spec,
        source_file_name=data_file.name,
        source_file_sha256=file_sha256(data_file),
        **kwargs,
    )
