"""Hollywood2EM validation across stable canonical filename tokens.

This module deliberately separates a leakage-resistant *source-token* split from
participant-held-out validation. The canonical GIN filenames expose stable three-digit prefixes,
but the repository history does not prove that those prefixes are original participant identifiers.
The workflow therefore treats them only as opaque source tokens and preserves the unresolved
participant identity boundary throughout preparation, modelling, and report validation.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import pandas as pd

from .benchmarks import BenchmarkDatasetCard, benchmark_fingerprint, build_benchmark_report
from .comparison import EventModelComparison, compare_event_models_grouped
from .exceptions import BenchmarkIntegrityError, SchemaError
from .hollywood2 import load_hollywood2_arff
from .paired import PairedModelDifferences, paired_model_metric_differences
from .resampling import resample_labeled_gaze
from .stratified import StratifiedEventPerformance, summarize_event_predictions_by_stratum

HOLLYWOOD2_GIN_REPOSITORY = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
HOLLYWOOD2_GIN_COMMIT = "870fa6d6209c9085260918d61433a0a2c70fd497"
HOLLYWOOD2_AUTHORITATIVE_EVIDENCE_FINGERPRINT = (
    "d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea"
)
HOLLYWOOD2_ANNOTATION_PROVENANCE_FINGERPRINT = (
    "a08510e43caca2a8e6d5c85e7b1ad41c9f312247cd9bd8367372f8ecad8aacab"
)
HOLLYWOOD2_GIN_HISTORY_EVIDENCE_FINGERPRINT = (
    "c7d2f477a66feca3676482ffdabff2b0778196db99e48b86104fe86d0f5bfae1"
)
HOLLYWOOD2_CANONICAL_SOURCE_TOKENS = (
    "001",
    "002",
    "003",
    "004",
    "005",
    "006",
    "008",
    "010",
    "011",
    "012",
    "013",
    "014",
    "015",
    "017",
    "018",
    "019",
)
HOLLYWOOD2_GROUND_TRUTH_FILE_COUNT = 697
HOLLYWOOD2_GROUND_TRUTH_SAMPLE_COUNT = 3_871_580
HOLLYWOOD2_CLIP_COUNT = 56

_AUTH_RECORD_TYPE = "hollywood2-source-token-analysis-authorization-v1"
_REPORT_SCOPE = "hollywood2-source-token-disjoint-validation-v1"
_TOKEN_RE = re.compile(r"^(?P<token>\d{3})_")
_DEFAULT_EXCLUDED_LABELS = ("ambiguous", "unlabelled", "undefined")

_AUTH_SCIENTIFIC_BOUNDARY = {
    "aggregate_nonredistributive_analysis_authorized": True,
    "operator_authorization_is_license_determination": False,
    "exact_license_identifier_verified": False,
    "exact_license_text_verified": False,
    "dataset_specific_analysis_terms_verified": False,
    "raw_source_redistribution_authorized": False,
    "participant_identity_mapping_verified": False,
    "participant_generalization_claim_authorized": False,
    "source_token_semantics_verified": True,
}


@dataclass(frozen=True, slots=True)
class Hollywood2SourceTokenAnalysisAuthorization:
    """Authorize aggregate analysis without resolving licence or identity semantics."""

    decision: str
    reviewer: str
    reviewed_on: str
    authorization_basis: str
    authoritative_evidence_fingerprint_sha256: str
    annotation_provenance_evidence_fingerprint_sha256: str
    gin_history_evidence_fingerprint_sha256: str
    repository: str = HOLLYWOOD2_GIN_REPOSITORY
    pinned_commit_sha1: str = HOLLYWOOD2_GIN_COMMIT
    raw_source_redistribution_authorized: bool = False
    exact_license_identifier_verified: bool = False
    exact_license_text_verified: bool = False
    dataset_specific_analysis_terms_verified: bool = False
    participant_identity_mapping_verified: bool = False
    participant_generalization_claim_authorized: bool = False
    aggregate_nonredistributive_analysis_authorized: bool = True
    source_token_semantics_verified: bool = True
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if str(self.decision).strip().lower() != "authorized":
            raise BenchmarkIntegrityError(
                "Hollywood2 source-token analysis requires an explicit decision='authorized'."
            )
        for field_name in ("reviewer", "reviewed_on", "authorization_basis"):
            if not str(getattr(self, field_name)).strip():
                raise BenchmarkIntegrityError(f"Authorization field {field_name!r} is unresolved.")
        expected = {
            "authoritative_evidence_fingerprint_sha256": (
                HOLLYWOOD2_AUTHORITATIVE_EVIDENCE_FINGERPRINT
            ),
            "annotation_provenance_evidence_fingerprint_sha256": (
                HOLLYWOOD2_ANNOTATION_PROVENANCE_FINGERPRINT
            ),
            "gin_history_evidence_fingerprint_sha256": (
                HOLLYWOOD2_GIN_HISTORY_EVIDENCE_FINGERPRINT
            ),
            "repository": HOLLYWOOD2_GIN_REPOSITORY,
            "pinned_commit_sha1": HOLLYWOOD2_GIN_COMMIT,
        }
        for field_name, required in expected.items():
            if str(getattr(self, field_name)).strip() != required:
                raise BenchmarkIntegrityError(
                    f"Hollywood2 authorization {field_name} is not bound to the frozen source."
                )
        required_false = (
            "raw_source_redistribution_authorized",
            "exact_license_identifier_verified",
            "exact_license_text_verified",
            "dataset_specific_analysis_terms_verified",
            "participant_identity_mapping_verified",
            "participant_generalization_claim_authorized",
        )
        if any(bool(getattr(self, field_name)) for field_name in required_false):
            raise BenchmarkIntegrityError(
                "Hollywood2 source-token authorization must preserve unresolved rights and "
                "participant-identity boundaries."
            )
        if not self.aggregate_nonredistributive_analysis_authorized:
            raise BenchmarkIntegrityError(
                "Hollywood2 aggregate non-redistributive analysis was not authorized."
            )
        if not self.source_token_semantics_verified:
            raise BenchmarkIntegrityError(
                "Hollywood2 canonical source-token semantics must be verified before this analysis."
            )
        object.__setattr__(self, "decision", "authorized")
        object.__setattr__(self, "notes", tuple(str(note) for note in self.notes))

    def to_dict(self) -> dict[str, Any]:
        """Return the deterministic authorization payload, excluding a self-fingerprint."""
        return {
            "record_type": _AUTH_RECORD_TYPE,
            "decision": self.decision,
            "reviewer": self.reviewer,
            "reviewed_on": self.reviewed_on,
            "authorization_basis": self.authorization_basis,
            "repository": self.repository,
            "pinned_commit_sha1": self.pinned_commit_sha1,
            "authoritative_evidence_fingerprint_sha256": (
                self.authoritative_evidence_fingerprint_sha256
            ),
            "annotation_provenance_evidence_fingerprint_sha256": (
                self.annotation_provenance_evidence_fingerprint_sha256
            ),
            "gin_history_evidence_fingerprint_sha256": (
                self.gin_history_evidence_fingerprint_sha256
            ),
            "raw_source_redistribution_authorized": self.raw_source_redistribution_authorized,
            "exact_license_identifier_verified": self.exact_license_identifier_verified,
            "exact_license_text_verified": self.exact_license_text_verified,
            "dataset_specific_analysis_terms_verified": (
                self.dataset_specific_analysis_terms_verified
            ),
            "participant_identity_mapping_verified": self.participant_identity_mapping_verified,
            "participant_generalization_claim_authorized": (
                self.participant_generalization_claim_authorized
            ),
            "aggregate_nonredistributive_analysis_authorized": (
                self.aggregate_nonredistributive_analysis_authorized
            ),
            "source_token_semantics_verified": self.source_token_semantics_verified,
            "scientific_boundary": dict(_AUTH_SCIENTIFIC_BOUNDARY),
            "notes": list(self.notes),
        }


@dataclass(slots=True)
class Hollywood2SourceTokenPreparedBenchmark:
    """Prepared Hollywood2 rows and provenance for an opaque source-token split."""

    data: pd.DataFrame
    dataset_card: BenchmarkDatasetCard
    preparation_report: dict[str, Any]
    authorization_fingerprint_sha256: str


@dataclass(slots=True)
class Hollywood2SourceTokenValidationRun:
    """Aggregate source-token-held-out model comparison and its audit-ready report."""

    prepared: Hollywood2SourceTokenPreparedBenchmark
    comparison: EventModelComparison
    paired_model_differences: PairedModelDifferences
    source_token_performance: StratifiedEventPerformance
    report: dict[str, Any]


def authorization_fingerprint(
    authorization: Hollywood2SourceTokenAnalysisAuthorization | dict[str, Any],
) -> str:
    """Return the SHA-256 binding for one authorization payload."""
    payload = (
        authorization.to_dict()
        if isinstance(authorization, Hollywood2SourceTokenAnalysisAuthorization)
        else dict(authorization)
    )
    payload.pop("authorization_fingerprint_sha256", None)
    return benchmark_fingerprint(payload)


def load_hollywood2_source_token_analysis_authorization(
    path: str | Path,
) -> Hollywood2SourceTokenAnalysisAuthorization:
    """Load and strictly validate one source-token analysis authorization record."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            "Hollywood2 source-token authorization must be valid UTF-8 JSON."
        ) from exc
    if not isinstance(payload, dict) or payload.get("record_type") != _AUTH_RECORD_TYPE:
        raise BenchmarkIntegrityError(
            f"Hollywood2 authorization record_type must be {_AUTH_RECORD_TYPE!r}."
        )
    if payload.get("scientific_boundary") != _AUTH_SCIENTIFIC_BOUNDARY:
        raise BenchmarkIntegrityError(
            "Hollywood2 authorization scientific boundary has drifted."
        )
    recorded_fingerprint = str(payload.get("authorization_fingerprint_sha256", "")).strip()
    if not recorded_fingerprint:
        raise BenchmarkIntegrityError("Hollywood2 authorization fingerprint is missing.")
    observed = authorization_fingerprint(payload)
    if recorded_fingerprint != observed:
        raise BenchmarkIntegrityError(
            "Hollywood2 authorization fingerprint does not match content."
        )

    values = dict(payload)
    for key in ("record_type", "scientific_boundary", "authorization_fingerprint_sha256"):
        values.pop(key, None)
    if "notes" in values:
        if not isinstance(values["notes"], list):
            raise BenchmarkIntegrityError("Hollywood2 authorization notes must be a JSON list.")
        values["notes"] = tuple(values["notes"])
    try:
        return Hollywood2SourceTokenAnalysisAuthorization(**values)
    except (TypeError, ValueError) as exc:
        raise BenchmarkIntegrityError("Hollywood2 source-token authorization is invalid.") from exc


def hollywood2_source_token_from_filename(filename: str | Path) -> str:
    """Extract the stable three-digit canonical filename prefix as an opaque source token."""
    name = Path(filename).name
    match = _TOKEN_RE.match(name)
    if match is None:
        raise SchemaError(
            "Hollywood2 canonical source-token validation requires filenames beginning "
            "with a three-digit token followed by '_'."
        )
    return match.group("token")


def attach_hollywood2_source_tokens(
    data: pd.DataFrame,
    *,
    source_file_col: str = "source_file",
    output_col: str = "source_token",
) -> pd.DataFrame:
    """Attach filename tokens without promoting them to participant identities."""
    if source_file_col not in data.columns:
        raise SchemaError(f"Missing Hollywood2 source-file column: {source_file_col!r}.")
    out = data.copy()
    out[output_col] = [
        hollywood2_source_token_from_filename(value)
        for value in out[source_file_col].astype(str)
    ]
    return out


def _normalise_repository_url(value: str) -> str:
    text = str(value).strip().rstrip("/")
    return text[:-4] if text.endswith(".git") else text


def _verify_pinned_checkout(root: Path) -> dict[str, Any]:
    """Require an exact, clean Git checkout of the frozen canonical GIN revision."""
    if not (root / ".git").exists():
        raise BenchmarkIntegrityError(
            "Hollywood2 empirical source-token validation requires the canonical Git checkout."
        )

    def run(*args: str) -> str:
        result = subprocess.run(
            args,
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise BenchmarkIntegrityError(
                f"Could not verify Hollywood2 Git checkout with {' '.join(args)}: "
                f"{result.stderr.strip()}"
            )
        return result.stdout.strip()

    head = run("git", "rev-parse", "HEAD")
    if head != HOLLYWOOD2_GIN_COMMIT:
        raise BenchmarkIntegrityError(
            "Hollywood2 checkout is not at the frozen authoritative commit."
        )
    origin = run("git", "remote", "get-url", "origin")
    if _normalise_repository_url(origin) != _normalise_repository_url(
        HOLLYWOOD2_GIN_REPOSITORY
    ):
        raise BenchmarkIntegrityError("Hollywood2 checkout origin is not the canonical GIN source.")
    dirty = run("git", "status", "--porcelain", "--untracked-files=no")
    if dirty:
        raise BenchmarkIntegrityError(
            "Hollywood2 checkout contains tracked modifications; refusing mixed source identity."
        )
    return {
        "repository": HOLLYWOOD2_GIN_REPOSITORY,
        "commit_sha1": head,
        "tracked_tree_clean": True,
    }


def _relative_clip_id(relative: Path) -> str:
    parts = relative.parts
    if len(parts) >= 3 and parts[0] in {"train", "test"}:
        return str(parts[1])
    if len(parts) >= 2:
        return str(parts[-2])
    return relative.stem


def _load_and_prepare_files(
    data_root: Path,
    *,
    target_sampling_rate_hz: float | None,
    min_label_purity: float,
    max_interpolation_gap_ms: float | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    paths = sorted(data_root.rglob("*.arff"))
    if len(paths) != HOLLYWOOD2_GROUND_TRUTH_FILE_COUNT:
        raise BenchmarkIntegrityError(
            "Hollywood2 source-token validation requires the complete 697-file ground-truth tree."
        )

    output_parts: list[pd.DataFrame] = []
    source_rates: list[float] = []
    source_rows = 0
    source_tokens: set[str] = set()
    clip_ids: set[str] = set()
    resampling_totals = {
        "source_rows": 0,
        "target_rows": 0,
        "ambiguous_rows": 0,
        "label_purity_weighted_sum": 0.0,
        "label_purity_weight": 0,
    }

    for path in paths:
        relative = path.relative_to(data_root)
        split = (
            relative.parts[0]
            if relative.parts and relative.parts[0] in {"train", "test"}
            else None
        )
        token = hollywood2_source_token_from_filename(path.name)
        clip_id = _relative_clip_id(relative)
        source_tokens.add(token)
        clip_ids.add(clip_id)
        trial_id = PurePosixPath(*relative.with_suffix("").parts).as_posix()
        gaze = load_hollywood2_arff(
            path,
            annotator="final",
            participant_id=None,
            trial_id=trial_id,
            split=split,
            expected_sampling_rate_hz=500.0,
            sampling_rate_tolerance=0.05,
            coordinate_unit="pixels",
        )
        source_rates.append(float(gaze.sampling_rate_hz))
        part = gaze.data.copy()
        source_rows += len(part)
        part["source_token"] = token
        part["clip_id"] = clip_id

        if target_sampling_rate_hz is not None and not np.isclose(
            float(target_sampling_rate_hz), gaze.sampling_rate_hz
        ):
            carry_cols = (
                "annotator",
                "dataset_id",
                "source_file",
                "split",
                "coordinate_unit",
                "coordinate_unit_verified",
                "source_token",
                "clip_id",
            )
            sampled = resample_labeled_gaze(
                part,
                target_sampling_rate_hz=float(target_sampling_rate_hz),
                min_label_purity=float(min_label_purity),
                max_interpolation_gap_ms=max_interpolation_gap_ms,
                source_sampling_rate_hz=float(gaze.sampling_rate_hz),
                continuous_cols=("x_px", "y_px"),
                carry_cols=carry_cols,
            )
            part = sampled.data
            report = sampled.report
            resampling_totals["source_rows"] += int(report["source_rows"])
            resampling_totals["target_rows"] += int(report["target_rows"])
            resampling_totals["ambiguous_rows"] += int(report["ambiguous_rows"])
            valid_purity = part["benchmark_label_purity"].dropna()
            resampling_totals["label_purity_weighted_sum"] += float(valid_purity.sum())
            resampling_totals["label_purity_weight"] += int(valid_purity.count())
        output_parts.append(part)

    if source_rows != HOLLYWOOD2_GROUND_TRUTH_SAMPLE_COUNT:
        raise BenchmarkIntegrityError(
            "Hollywood2 sample count does not match the frozen authoritative evidence."
        )
    if tuple(sorted(source_tokens)) != HOLLYWOOD2_CANONICAL_SOURCE_TOKENS:
        raise BenchmarkIntegrityError(
            "Hollywood2 canonical source-token set does not match frozen evidence."
        )
    if len(clip_ids) != HOLLYWOOD2_CLIP_COUNT:
        raise BenchmarkIntegrityError(
            "Hollywood2 clip inventory does not match frozen authoritative evidence."
        )

    prepared = pd.concat(output_parts, ignore_index=True)
    resampling_report: dict[str, Any] | None = None
    if target_sampling_rate_hz is not None and output_parts and (
        resampling_totals["target_rows"] > 0
    ):
        target_rows = int(resampling_totals["target_rows"])
        ambiguous_rows = int(resampling_totals["ambiguous_rows"])
        purity_weight = int(resampling_totals["label_purity_weight"])
        resampling_report = {
            "method": "linear_coordinates_majority_window_labels",
            "target_sampling_rate_hz": float(target_sampling_rate_hz),
            "min_label_purity": float(min_label_purity),
            "max_interpolation_gap_ms": (
                float(max_interpolation_gap_ms)
                if max_interpolation_gap_ms is not None
                else 2.0 * (1000.0 / float(target_sampling_rate_hz))
            ),
            "source_rows": int(resampling_totals["source_rows"]),
            "target_rows": target_rows,
            "ambiguous_rows": ambiguous_rows,
            "ambiguous_fraction": ambiguous_rows / target_rows if target_rows else None,
            "mean_label_purity": (
                float(resampling_totals["label_purity_weighted_sum"]) / purity_weight
                if purity_weight
                else None
            ),
            "per_file_group_reports_embedded": False,
        }

    inventory = {
        "ground_truth_file_count": len(paths),
        "ground_truth_sample_count": source_rows,
        "clip_count": len(clip_ids),
        "source_token_count": len(source_tokens),
        "source_tokens": sorted(source_tokens),
        "source_rate_min_hz": float(min(source_rates)),
        "source_rate_median_hz": float(np.median(source_rates)),
        "source_rate_max_hz": float(max(source_rates)),
        "resampling": resampling_report,
    }
    return prepared, inventory


def prepare_hollywood2_source_token_benchmark(
    root: str | Path,
    authorization: Hollywood2SourceTokenAnalysisAuthorization,
    *,
    target_sampling_rate_hz: float | None = 60.0,
    min_label_purity: float = 0.75,
    max_interpolation_gap_ms: float | None = None,
    excluded_labels: tuple[str, ...] = _DEFAULT_EXCLUDED_LABELS,
) -> Hollywood2SourceTokenPreparedBenchmark:
    """Prepare the complete canonical source for an opaque-token-held-out comparison.

    The canonical Git revision, complete ground-truth inventory, token set, clip count, sample
    count, pixel coordinate semantics, and unresolved participant identity are all checked before
    analysis. Raw source rows and filenames are intentionally omitted from the returned report.
    """
    if not isinstance(authorization, Hollywood2SourceTokenAnalysisAuthorization):
        raise TypeError(
            "authorization must be a Hollywood2SourceTokenAnalysisAuthorization instance."
        )
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(root_path)
    checkout = _verify_pinned_checkout(root_path)
    data_root = root_path / "ground_truth"
    if not data_root.is_dir():
        raise BenchmarkIntegrityError(
            "Hollywood2 canonical checkout is missing the ground_truth directory."
        )
    if target_sampling_rate_hz is not None and float(target_sampling_rate_hz) <= 0:
        raise ValueError("target_sampling_rate_hz must be positive when supplied.")

    prepared, inventory = _load_and_prepare_files(
        data_root,
        target_sampling_rate_hz=target_sampling_rate_hz,
        min_label_purity=min_label_purity,
        max_interpolation_gap_ms=max_interpolation_gap_ms,
    )
    if set(prepared["participant_id"].astype(str)) != {"__unresolved__"}:
        raise BenchmarkIntegrityError(
            "Hollywood2 source-token analysis must not materialize participant identities."
        )
    labels_before = prepared["event_label"].fillna("MISSING").astype(str)
    excluded = {str(value) for value in excluded_labels}
    retained_mask = ~labels_before.isin(excluded)
    retained = prepared.loc[retained_mask].copy().reset_index(drop=True)
    if retained.empty or retained["event_label"].nunique() < 2:
        raise SchemaError(
            "Hollywood2 source-token preparation retained insufficient labelled benchmark rows."
        )
    retained_tokens = tuple(sorted(retained["source_token"].astype(str).unique()))
    if retained_tokens != HOLLYWOOD2_CANONICAL_SOURCE_TOKENS:
        raise BenchmarkIntegrityError(
            "Hollywood2 exclusions removed an entire canonical source token."
        )
    analysis_rate = (
        float(target_sampling_rate_hz)
        if target_sampling_rate_hz is not None
        else float(inventory["source_rate_median_hz"])
    )
    sampling_origin = (
        "native"
        if target_sampling_rate_hz is None
        or np.isclose(float(target_sampling_rate_hz), 500.0)
        else "resampled"
    )
    token_counts = (
        retained.groupby("source_token", sort=True)
        .agg(rows=("event_label", "size"), files=("trial_id", "nunique"))
        .reset_index()
    )
    token_count_records = token_counts.to_dict(orient="records")
    auth_fingerprint = authorization_fingerprint(authorization)

    preparation_report = {
        "scope": _REPORT_SCOPE,
        "source_identity": checkout,
        "authoritative_evidence_fingerprint_sha256": (
            HOLLYWOOD2_AUTHORITATIVE_EVIDENCE_FINGERPRINT
        ),
        "annotation_provenance_evidence_fingerprint_sha256": (
            HOLLYWOOD2_ANNOTATION_PROVENANCE_FINGERPRINT
        ),
        "gin_history_evidence_fingerprint_sha256": (
            HOLLYWOOD2_GIN_HISTORY_EVIDENCE_FINGERPRINT
        ),
        "authorization_fingerprint_sha256": auth_fingerprint,
        "source_sampling_rate_hz_nominal": 500.0,
        "analysis_sampling_rate_hz": analysis_rate,
        "sampling_origin": sampling_origin,
        "inventory": inventory,
        "prepared_rows_before_exclusions": int(len(prepared)),
        "analysis_rows": int(len(retained)),
        "excluded_rows": int((~retained_mask).sum()),
        "excluded_labels": sorted(excluded),
        "label_counts_before_exclusions": labels_before.value_counts().sort_index().to_dict(),
        "label_counts_analysis": (
            retained["event_label"].astype(str).value_counts().sort_index().to_dict()
        ),
        "source_token_analysis_counts": token_count_records,
        "participant_identity_resolved": False,
        "participant_id_value": "__unresolved__",
        "split_unit": "canonical_file_subject_token",
        "split_unit_interpretation": (
            "Stable three-digit canonical filename prefix; opaque source token only, not a "
            "verified participant identifier."
        ),
        "raw_source_rows_embedded": False,
        "source_filenames_embedded": False,
    }
    card = BenchmarkDatasetCard(
        name="Hollywood2EM",
        version=HOLLYWOOD2_GIN_COMMIT,
        source=HOLLYWOOD2_GIN_REPOSITORY,
        license=(
            "Author-level open-source declaration verified; exact annotation-repository licence "
            "identifier/text and dataset-specific analysis terms remain unresolved. GazeForge "
            "does not redistribute source bytes."
        ),
        task="sample-level eye-movement event classification",
        sampling_rates_hz=[500.0, analysis_rate]
        if not np.isclose(analysis_rate, 500.0)
        else [500.0],
        participant_count=None,
        stimulus_count=HOLLYWOOD2_CLIP_COUNT,
        split_unit="canonical_file_subject_token",
        validation_scope="external-empirical-source-token-held-out",
        annotation_origin="human-assisted",
        sampling_origin=preparation_report["sampling_origin"],
        reference_strength=(
            "derived-human-reference"
            if preparation_report["sampling_origin"] == "resampled"
            else "expert-human-reference"
        ),
        human_annotator_count=None,
        reference_description=(
            "Expert-corrected final Hollywood2EM sample labels. The student-to-expert correction "
            "stream is sequential and is not independent human-human agreement."
        ),
        notes=[
            "Validation groups are stable canonical filename tokens, not verified participants.",
            "Participant-held-out and participant-generalization claims are prohibited.",
            "Exact annotation-repository licence terms remain unresolved.",
            "Only aggregate model outputs are eligible for the validation report; raw source rows "
            "are never embedded or redistributed.",
        ],
    )
    return Hollywood2SourceTokenPreparedBenchmark(
        data=retained,
        dataset_card=card,
        preparation_report=preparation_report,
        authorization_fingerprint_sha256=auth_fingerprint,
    )


def _json_safe_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def run_hollywood2_source_token_validation(
    root: str | Path,
    authorization: Hollywood2SourceTokenAnalysisAuthorization,
    *,
    target_sampling_rate_hz: float | None = 60.0,
    min_label_purity: float = 0.75,
    n_splits: int = 4,
    ivt_velocity_threshold_px_s: float = 1000.0,
    random_state: int = 42,
    n_estimators: int = 100,
    context_radius_ms: float = 50.0,
    rolling_window_ms: float = 80.0,
    hidden_layer_sizes: tuple[int, ...] = (32, 16),
    temporal_solver: str = "adam",
    temporal_max_iter: int = 50,
) -> Hollywood2SourceTokenValidationRun:
    """Run matched I-VT/RF/ContextMLP folds held out by canonical source token only."""
    prepared = prepare_hollywood2_source_token_benchmark(
        root,
        authorization,
        target_sampling_rate_hz=target_sampling_rate_hz,
        min_label_purity=min_label_purity,
    )
    n_tokens = int(prepared.data["source_token"].nunique())
    folds = min(int(n_splits), n_tokens)
    if folds < 2:
        raise SchemaError("At least two source-token folds are required.")
    analysis_rate = float(prepared.preparation_report["analysis_sampling_rate_hz"])
    comparison = compare_event_models_grouped(
        prepared.data,
        group_col="source_token",
        n_splits=folds,
        sampling_rate_hz=analysis_rate,
        ivt_velocity_threshold_px_s=float(ivt_velocity_threshold_px_s),
        ivt_velocity_threshold_deg_s=None,
        random_state=int(random_state),
        n_estimators=int(n_estimators),
        context_radius_ms=float(context_radius_ms),
        rolling_window_ms=float(rolling_window_ms),
        hidden_layer_sizes=hidden_layer_sizes,
        temporal_solver=temporal_solver,
        temporal_max_iter=int(temporal_max_iter),
        include_event_level_metrics=True,
        event_group_cols=("participant_id", "trial_id"),
    )
    paired = paired_model_metric_differences(comparison.fold_metrics)
    token_performance = summarize_event_predictions_by_stratum(
        comparison.predictions,
        stratify_col="source_token",
        group_col="source_token",
        sampling_rate_hz=analysis_rate,
        calibration_bins=int(comparison.design["calibration_bins"]),
        include_event_level_metrics=bool(
            comparison.design["include_event_level_metrics"]
        ),
        event_group_cols=tuple(comparison.design["event_group_cols"]),
        event_min_iou=float(comparison.design["event_min_iou"]),
        event_excluded_labels=tuple(comparison.design["event_excluded_labels"]),
    )
    token_fold_assignment = (
        comparison.predictions[["source_token", "validation_fold"]]
        .drop_duplicates()
        .sort_values(["validation_fold", "source_token"], kind="stable")
        .reset_index(drop=True)
    )
    if token_fold_assignment["source_token"].nunique() != n_tokens:
        raise BenchmarkIntegrityError(
            "Hollywood2 source-token fold assignment does not cover every canonical token."
        )
    if token_fold_assignment["source_token"].duplicated().any():
        raise BenchmarkIntegrityError(
            "A Hollywood2 source token appeared in more than one held-out fold."
        )
    protocol = {
        "scope": _REPORT_SCOPE,
        "preparation": prepared.preparation_report,
        "comparison_design": comparison.design,
        "paired_model_difference_design": paired.design,
        "source_token_stratification_design": token_performance.design,
        "scientific_boundary": {
            "validation_split_unit": "canonical_file_subject_token",
            "source_token_to_participant_mapping_verified": False,
            "participant_identity_mapping_verified": False,
            "participant_disjoint_validation_created": False,
            "participant_generalization_claim": False,
            "cross_dataset_validation_created": False,
            "exact_license_identifier_verified": False,
            "exact_license_text_verified": False,
            "dataset_specific_analysis_terms_verified": False,
            "operator_authorized_nonredistributive_analysis": True,
            "raw_source_redistributed_by_gazeforge": False,
            "raw_predictions_embedded": False,
            "aggregate_metrics_only": True,
        },
        "claim_limit": (
            "Performance estimates generalize across held-out canonical filename tokens under this "
            "design. They are not participant-held-out estimates because token-to-participant "
            "identity and task-group mapping remain unresolved."
        ),
    }
    metrics = {
        "summary": _json_safe_records(comparison.summary),
        "fold_metrics": _json_safe_records(comparison.fold_metrics),
        "paired_model_difference_summary": _json_safe_records(paired.summary),
        "paired_model_fold_deltas": _json_safe_records(paired.deltas),
        "source_token_summary": _json_safe_records(token_performance.summary),
        "source_token_fold_metrics": _json_safe_records(token_performance.fold_metrics),
        "source_token_fold_assignment": _json_safe_records(token_fold_assignment),
        "analysis_label_counts": prepared.preparation_report["label_counts_analysis"],
    }
    report = build_benchmark_report(
        benchmark=prepared.dataset_card,
        metrics=metrics,
        model={
            "models": comparison.design["models"],
            "random_state": int(random_state),
            "random_forest_n_estimators": int(n_estimators),
            "context_hidden_layer_sizes": list(hidden_layer_sizes),
            "context_solver": temporal_solver,
            "context_max_iter": int(temporal_max_iter),
            "ivt_velocity_threshold_px_s": float(ivt_velocity_threshold_px_s),
        },
        protocol=protocol,
    )
    validate_hollywood2_source_token_validation_report(report)
    return Hollywood2SourceTokenValidationRun(
        prepared=prepared,
        comparison=comparison,
        paired_model_differences=paired,
        source_token_performance=token_performance,
        report=report,
    )


def validate_hollywood2_source_token_validation_report(
    report_or_path: dict[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate aggregate report integrity and every scientific claim boundary."""
    if isinstance(report_or_path, dict):
        report = dict(report_or_path)
    else:
        path = Path(report_or_path)
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BenchmarkIntegrityError(
                "Could not load Hollywood2 source-token validation report."
            ) from exc
        if not isinstance(report, dict):
            raise BenchmarkIntegrityError("Hollywood2 validation report must be one JSON object.")

    fingerprint = str(report.get("report_fingerprint_sha256", ""))
    body = dict(report)
    body.pop("report_fingerprint_sha256", None)
    if not fingerprint or benchmark_fingerprint(body) != fingerprint:
        raise BenchmarkIntegrityError(
            "Hollywood2 source-token report fingerprint does not match content."
        )
    benchmark = report.get("benchmark")
    protocol = report.get("protocol")
    metrics = report.get("metrics")
    if (
        not isinstance(benchmark, dict)
        or not isinstance(protocol, dict)
        or not isinstance(metrics, dict)
    ):
        raise BenchmarkIntegrityError("Hollywood2 source-token report structure is incomplete.")
    if benchmark.get("name") != "Hollywood2EM":
        raise BenchmarkIntegrityError("Hollywood2 source-token report dataset identity drifted.")
    if benchmark.get("version") != HOLLYWOOD2_GIN_COMMIT:
        raise BenchmarkIntegrityError("Hollywood2 source-token report revision drifted.")
    if benchmark.get("split_unit") != "canonical_file_subject_token":
        raise BenchmarkIntegrityError("Hollywood2 report must retain the source-token split unit.")
    if protocol.get("scope") != _REPORT_SCOPE:
        raise BenchmarkIntegrityError("Hollywood2 source-token report scope drifted.")
    boundary = protocol.get("scientific_boundary")
    expected_false = (
        "source_token_to_participant_mapping_verified",
        "participant_identity_mapping_verified",
        "participant_disjoint_validation_created",
        "participant_generalization_claim",
        "cross_dataset_validation_created",
        "exact_license_identifier_verified",
        "exact_license_text_verified",
        "dataset_specific_analysis_terms_verified",
        "raw_source_redistributed_by_gazeforge",
        "raw_predictions_embedded",
    )
    if not isinstance(boundary, dict):
        raise BenchmarkIntegrityError("Hollywood2 report scientific boundary is missing.")
    if boundary.get("validation_split_unit") != "canonical_file_subject_token":
        raise BenchmarkIntegrityError("Hollywood2 validation split semantics drifted.")
    if any(boundary.get(key) is not False for key in expected_false):
        raise BenchmarkIntegrityError(
            "Hollywood2 report attempted to promote an unresolved scientific or rights claim."
        )
    if boundary.get("operator_authorized_nonredistributive_analysis") is not True:
        raise BenchmarkIntegrityError("Hollywood2 report is missing operator authorization.")
    if boundary.get("aggregate_metrics_only") is not True:
        raise BenchmarkIntegrityError("Hollywood2 report must remain aggregate-only.")
    preparation = protocol.get("preparation")
    if not isinstance(preparation, dict):
        raise BenchmarkIntegrityError("Hollywood2 preparation provenance is missing.")
    expected_fingerprints = {
        "authoritative_evidence_fingerprint_sha256": (
            HOLLYWOOD2_AUTHORITATIVE_EVIDENCE_FINGERPRINT
        ),
        "annotation_provenance_evidence_fingerprint_sha256": (
            HOLLYWOOD2_ANNOTATION_PROVENANCE_FINGERPRINT
        ),
        "gin_history_evidence_fingerprint_sha256": (
            HOLLYWOOD2_GIN_HISTORY_EVIDENCE_FINGERPRINT
        ),
    }
    for key, value in expected_fingerprints.items():
        if preparation.get(key) != value:
            raise BenchmarkIntegrityError(
                f"Hollywood2 report is not bound to expected {key}."
            )
    inventory = preparation.get("inventory")
    if not isinstance(inventory, dict):
        raise BenchmarkIntegrityError("Hollywood2 report source inventory is missing.")
    if int(inventory.get("ground_truth_file_count", -1)) != HOLLYWOOD2_GROUND_TRUTH_FILE_COUNT:
        raise BenchmarkIntegrityError("Hollywood2 report file count drifted.")
    if int(inventory.get("ground_truth_sample_count", -1)) != HOLLYWOOD2_GROUND_TRUTH_SAMPLE_COUNT:
        raise BenchmarkIntegrityError("Hollywood2 report sample count drifted.")
    if tuple(inventory.get("source_tokens", [])) != HOLLYWOOD2_CANONICAL_SOURCE_TOKENS:
        raise BenchmarkIntegrityError("Hollywood2 report source-token inventory drifted.")
    if preparation.get("participant_identity_resolved") is not False:
        raise BenchmarkIntegrityError(
            "Hollywood2 source-token report must preserve unresolved participant identity."
        )
    forbidden_metric_keys = {"predictions", "raw_rows", "source_rows", "samples"}
    if forbidden_metric_keys & set(metrics):
        raise BenchmarkIntegrityError(
            "Hollywood2 aggregate report must not embed raw samples or predictions."
        )
    return report
