"""Structural validation-scope inference and replayable split certificates."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .benchmarks import benchmark_fingerprint
from .exceptions import SchemaError
from .provenance import fingerprint_frame

_CERTIFICATE_SCHEMA = "gazeforge.validation-scope-certificate.v1"
_SCOPE_ORDER = {
    "sample_level": 0,
    "trial_level": 1,
    "participant_within": 2,
    "participant_disjoint": 3,
    "dataset_external": 4,
}
_VALID_SCOPES = frozenset(_SCOPE_ORDER)


@dataclass(frozen=True, slots=True)
class ValidationScopeAssessment:
    """Structurally derived train/test separation and overlap evidence."""

    scope: str
    scope_rank: int
    participant_col: str
    trial_col: str
    sample_col: str
    dataset_col: str | None
    dataset_metadata_available: bool
    counts: dict[str, int | None]
    overlap_fingerprints_sha256: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the assessment."""
        return asdict(self)


def _contains_blank(values: pd.Series) -> bool:
    text = values.astype("string").str.strip()
    return bool(text.eq("").fillna(False).any())


def _require_nonempty_identity_table(
    data: pd.DataFrame,
    *,
    label: str,
    required_columns: tuple[str, ...],
) -> None:
    if data.empty:
        raise SchemaError(f"{label} partition must contain at least one row.")
    missing = [column for column in required_columns if column not in data.columns]
    if missing:
        raise SchemaError(f"{label} partition is missing identity columns: {missing}")
    invalid = [
        column
        for column in required_columns
        if bool(data[column].isna().any()) or _contains_blank(data[column])
    ]
    if invalid:
        raise SchemaError(
            f"{label} partition contains missing or blank identity values in: {invalid}"
        )


def _identity_set(data: pd.DataFrame, columns: tuple[str, ...]) -> set[tuple[Any, ...]]:
    try:
        return set(data.loc[:, list(columns)].itertuples(index=False, name=None))
    except TypeError as exc:
        raise SchemaError(
            f"Identity columns must contain hashable scalar values: {list(columns)}"
        ) from exc


def _identity_fingerprint(values: set[tuple[Any, ...]]) -> str:
    canonical = sorted(
        (list(value) for value in values),
        key=lambda item: json.dumps(item, sort_keys=True, default=str),
    )
    return benchmark_fingerprint(canonical)


def _claims_for_scope(scope: str) -> dict[str, bool]:
    rank = _SCOPE_ORDER[scope]
    return {
        "structural_scope_only": True,
        "identity_semantics_verified": False,
        "establishes_model_performance": False,
        "sample_disjoint_evaluation": rank >= _SCOPE_ORDER["trial_level"],
        "trial_disjoint_evaluation": rank >= _SCOPE_ORDER["participant_within"],
        "participant_disjoint_evaluation": rank >= _SCOPE_ORDER["participant_disjoint"],
        "dataset_external_evaluation": rank >= _SCOPE_ORDER["dataset_external"],
        "subject_generalization_eligible": rank >= _SCOPE_ORDER["participant_disjoint"],
        "cross_dataset_generalization_eligible": rank >= _SCOPE_ORDER["dataset_external"],
    }


def derive_validation_scope(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    participant_col: str = "participant_id",
    trial_col: str = "trial_id",
    sample_col: str = "sample_index",
    dataset_col: str | None = "dataset_id",
) -> ValidationScopeAssessment:
    """Derive the strongest defensible validation scope from exact split identities.

    The hierarchy is ``sample_level < trial_level < participant_within <
    participant_disjoint < dataset_external``. The function never trusts a
    caller-supplied scope label. Participant, trial, and sample identities must be
    complete, and sample keys must be unique within each partition. Dataset metadata
    is optional; without complete dataset identities the strongest possible scope is
    ``participant_disjoint``.
    """
    required = (participant_col, trial_col, sample_col)
    _require_nonempty_identity_table(train, label="train", required_columns=required)
    _require_nonempty_identity_table(test, label="test", required_columns=required)

    sample_key_cols = (participant_col, trial_col, sample_col)
    if train.duplicated(list(sample_key_cols)).any():
        raise SchemaError("train partition contains duplicate sample identity keys.")
    if test.duplicated(list(sample_key_cols)).any():
        raise SchemaError("test partition contains duplicate sample identity keys.")

    train_samples = _identity_set(train, sample_key_cols)
    test_samples = _identity_set(test, sample_key_cols)
    train_trials = _identity_set(train, (participant_col, trial_col))
    test_trials = _identity_set(test, (participant_col, trial_col))
    train_participants = _identity_set(train, (participant_col,))
    test_participants = _identity_set(test, (participant_col,))

    sample_overlap = train_samples & test_samples
    trial_overlap = train_trials & test_trials
    participant_overlap = train_participants & test_participants

    dataset_metadata_available = False
    train_datasets: set[tuple[Any, ...]] = set()
    test_datasets: set[tuple[Any, ...]] = set()
    dataset_overlap: set[tuple[Any, ...]] = set()
    dataset_columns_present = (
        dataset_col is not None
        and dataset_col in train.columns
        and dataset_col in test.columns
    )
    if dataset_columns_present:
        train_dataset_valid = not train[dataset_col].isna().any() and not _contains_blank(
            train[dataset_col]
        )
        test_dataset_valid = not test[dataset_col].isna().any() and not _contains_blank(
            test[dataset_col]
        )
        if train_dataset_valid and test_dataset_valid:
            dataset_metadata_available = True
            train_datasets = _identity_set(train, (dataset_col,))
            test_datasets = _identity_set(test, (dataset_col,))
            dataset_overlap = train_datasets & test_datasets

    if sample_overlap:
        scope = "sample_level"
    elif trial_overlap:
        scope = "trial_level"
    elif participant_overlap:
        scope = "participant_within"
    elif dataset_metadata_available and not dataset_overlap:
        scope = "dataset_external"
    else:
        scope = "participant_disjoint"

    counts: dict[str, int | None] = {
        "n_train_rows": int(len(train)),
        "n_test_rows": int(len(test)),
        "n_train_samples": len(train_samples),
        "n_test_samples": len(test_samples),
        "n_overlapping_samples": len(sample_overlap),
        "n_train_trials": len(train_trials),
        "n_test_trials": len(test_trials),
        "n_overlapping_trials": len(trial_overlap),
        "n_train_participants": len(train_participants),
        "n_test_participants": len(test_participants),
        "n_overlapping_participants": len(participant_overlap),
        "n_train_datasets": len(train_datasets) if dataset_metadata_available else None,
        "n_test_datasets": len(test_datasets) if dataset_metadata_available else None,
        "n_overlapping_datasets": len(dataset_overlap) if dataset_metadata_available else None,
    }
    fingerprints = {
        "sample_overlap": _identity_fingerprint(sample_overlap),
        "trial_overlap": _identity_fingerprint(trial_overlap),
        "participant_overlap": _identity_fingerprint(participant_overlap),
        "dataset_overlap": _identity_fingerprint(dataset_overlap),
    }
    return ValidationScopeAssessment(
        scope=scope,
        scope_rank=_SCOPE_ORDER[scope],
        participant_col=participant_col,
        trial_col=trial_col,
        sample_col=sample_col,
        dataset_col=dataset_col,
        dataset_metadata_available=dataset_metadata_available,
        counts=counts,
        overlap_fingerprints_sha256=fingerprints,
    )


def assert_validation_scope(
    assessment: ValidationScopeAssessment,
    minimum_scope: str,
) -> None:
    """Require a minimum structurally derived validation scope."""
    if minimum_scope not in _VALID_SCOPES:
        raise ValueError(f"Unknown validation scope: {minimum_scope!r}")
    if assessment.scope_rank < _SCOPE_ORDER[minimum_scope]:
        raise SchemaError(
            "Validation scope requirement not met: "
            f"actual={assessment.scope}, required={minimum_scope}."
        )


def build_validation_scope_certificate(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    participant_col: str = "participant_id",
    trial_col: str = "trial_id",
    sample_col: str = "sample_index",
    dataset_col: str | None = "dataset_id",
    minimum_scope: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic certificate from the exact train/test split."""
    if minimum_scope is not None and minimum_scope not in _VALID_SCOPES:
        raise ValueError(f"Unknown validation scope: {minimum_scope!r}")

    assessment = derive_validation_scope(
        train,
        test,
        participant_col=participant_col,
        trial_col=trial_col,
        sample_col=sample_col,
        dataset_col=dataset_col,
    )
    if minimum_scope is not None:
        assert_validation_scope(assessment, minimum_scope)

    body = {
        "schema": _CERTIFICATE_SCHEMA,
        "train_fingerprint_sha256": fingerprint_frame(train),
        "test_fingerprint_sha256": fingerprint_frame(test),
        "identity_columns": {
            "participant_col": participant_col,
            "trial_col": trial_col,
            "sample_col": sample_col,
            "dataset_col": dataset_col,
        },
        "assessment": assessment.to_dict(),
        "minimum_scope": minimum_scope,
        "claim_boundary": _claims_for_scope(assessment.scope),
    }
    return {**body, "certificate_fingerprint_sha256": benchmark_fingerprint(body)}


def validate_validation_scope_certificate(
    certificate: dict[str, Any],
    train: pd.DataFrame,
    test: pd.DataFrame,
) -> bool:
    """Replay a scope certificate against the exact train/test inputs."""
    if certificate.get("schema") != _CERTIFICATE_SCHEMA:
        raise ValueError("Unsupported validation-scope certificate schema.")
    fingerprint = certificate.get("certificate_fingerprint_sha256")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise ValueError("Validation-scope certificate fingerprint is missing or malformed.")
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    if benchmark_fingerprint(body) != fingerprint:
        raise ValueError("Validation-scope certificate fingerprint mismatch.")

    identity_columns = certificate.get("identity_columns")
    if not isinstance(identity_columns, dict):
        raise ValueError("Validation-scope certificate is missing identity-column metadata.")

    rebuilt = build_validation_scope_certificate(
        train,
        test,
        participant_col=str(identity_columns.get("participant_col", "")),
        trial_col=str(identity_columns.get("trial_col", "")),
        sample_col=str(identity_columns.get("sample_col", "")),
        dataset_col=identity_columns.get("dataset_col"),
        minimum_scope=certificate.get("minimum_scope"),
    )
    if rebuilt != certificate:
        raise ValueError(
            "Validation-scope certificate does not replay from the exact split inputs."
        )
    return True


def freeze_validation_scope_certificate(
    certificate: dict[str, Any],
    path: str | Path,
    *,
    train: pd.DataFrame,
    test: pd.DataFrame,
    overwrite: bool = False,
) -> Path:
    """Replay-validate and freeze a structural validation-scope certificate."""
    validate_validation_scope_certificate(certificate, train, test)
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Validation-scope certificate already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(certificate, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target
