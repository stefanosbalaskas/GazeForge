"""Fail-closed Gaze-in-the-Wild filename/schema convergence evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "gaze-in-wild-layout-convergence-evidence-v1"
PROBE_RECORD_TYPE = "gaze-in-wild-layout-convergence-probe-v1"
STATUS = (
    "first_party_layout_verified_secondary_convergence_verified_"
    "candidate_screening_only"
)
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "b9c006e7bc367d7a66a4e78577d4d267b488eec298619b7e2e6707468172ac12"
)
EXPECTED_PROBE_FINGERPRINT_SHA256 = (
    "98d9f5d81bed214248c08dbb3901b548b1ae6849f1fd85a33bec474c6e202943"
)
HISTORY_EVIDENCE_FINGERPRINT_SHA256 = (
    "800d84d71d1d4b1a07e3b6d07c3bb7093c679284f49db0930a9836d77da30ad3"
)
SECONDARY_LEAD_EVIDENCE_FINGERPRINT_SHA256 = (
    "e312079108f8b50ddedd6f361272218fc8665c880b147797aee5bb434ebc8c29"
)
DISTRIBUTION_EVIDENCE_FINGERPRINT_SHA256 = (
    "2400c81a0897fb414285069c368a8a9d96de1d18eb185b1073cf15bb1c8bd1da"
)
FIRST_PARTY_REPOSITORY = "https://github.com/RSKothari/Gaze-in-Wild"
FIRST_PARTY_COMMIT = "52262d44e366a53369e10ca73c5f41daf0e8f1e5"
FIRST_PARTY_PLOT_LABELS_BLOB = "511581250e04c62037c71d2da16271be4979d434"
FIRST_PARTY_GITIGNORE_BLOB = "85f9e994c92da6cbb5632ab241ae7473a83b35e5"
PROCESS_FILENAME_PATTERN = "PrIdx_%d_TrIdx_%d.mat"
LABEL_FILENAME_PATTERN = "PrIdx_%d_TrIdx_%d_Lbr_%d.mat"
PROCESS_VARIABLE = "ProcessData"
LABEL_VARIABLE = "LabelData"

_SECONDARY_SOURCES = (
    {
        "key": "dfki_open_gaze_lab",
        "repository": (
            "https://github.com/DFKI-Interactive-Machine-Learning/open-gaze-lab"
        ),
        "pinned_commit_sha1": "2c87abb3ed5d3e21ed027252a8fcd4fcfd9bdeee",
        "path": "backend/src/preprocess_headmounted/giw.py",
        "git_blob_sha1": "eebf405662caa0657095012d9451b3a0576bb5dc",
        "classification": "independent_downstream_full_layout_match",
    },
    {
        "key": "ace_dnv",
        "repository": "https://github.com/arnejad/ACE-DNV",
        "pinned_commit_sha1": "3142eb4457087743664d96994e952ed784741d1f",
        "path": "modules/GiW.py",
        "git_blob_sha1": "eb30815510c2e04d4239e06b7b22ffc74c10c595",
        "classification": "independent_downstream_full_layout_match",
    },
    {
        "key": "leo_umcg_unsupervised",
        "repository": (
            "https://github.com/LEO-UMCG/Unsupervised-Gaze-Event-Discrimination"
        ),
        "pinned_commit_sha1": "12ff306d8690e483d5e721e18d447fbd0d887e54",
        "path": "preprocessing.py",
        "git_blob_sha1": "7489c5df1ef5f5d7125f14b6b609ab2e170c0d3e",
        "classification": "independent_downstream_label_schema_corroboration",
    },
)


@dataclass(frozen=True, slots=True)
class GazeInWildLayoutConvergenceEvidence:
    """Reviewed layout evidence that remains non-authoritative for candidate use."""

    path: Path | None
    fingerprint_sha256: str
    probe_fingerprint_sha256: str
    full_layout_match_count: int
    label_schema_corroboration_count: int
    candidate_layout_screening_signal_only: bool
    exact_copy_identity_verified: bool


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return canonical SHA-256 excluding the stored evidence fingerprint."""

    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def probe_fingerprint(record: Mapping[str, Any]) -> str:
    """Return canonical SHA-256 excluding the stored live-probe fingerprint."""

    body = dict(record)
    body.pop("probe_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def git_blob_sha1(content: bytes) -> str:
    """Return the Git object SHA-1 for raw file bytes."""

    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324


def _load(
    record_or_path: Mapping[str, Any] | str | Path,
    *,
    label: str,
) -> tuple[dict[str, Any], Path | None]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path), None
    path = Path(record_or_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"Could not load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return payload, path


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild layout convergence field {key!r} is missing."
        )
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild layout convergence {label} drifted."
        )


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild layout convergence must preserve {label}."
        )


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild layout convergence must not promote {label}."
        )


def _decode(content: bytes, label: str) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BenchmarkIntegrityError(f"{label} must be UTF-8 text.") from exc


def _require(text: str, tokens: tuple[str, ...], label: str) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild {label} no longer contains required schema tokens: "
            + ", ".join(repr(token) for token in missing)
        )


def _verify_blob(content: bytes, expected: str, label: str) -> None:
    actual = git_blob_sha1(content)
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild {label} Git blob drifted: {actual} != {expected}."
        )


def build_gaze_in_wild_layout_convergence_probe(
    *,
    first_party_plot_labels: bytes,
    first_party_gitignore: bytes,
    dfki_giw: bytes,
    ace_giw: bytes,
    leo_preprocessing: bytes,
) -> dict[str, Any]:
    """Build a deterministic exact-file probe for reviewed layout convergence."""

    _verify_blob(
        first_party_plot_labels,
        FIRST_PARTY_PLOT_LABELS_BLOB,
        "first-party PlotLabels.m",
    )
    _verify_blob(
        first_party_gitignore,
        FIRST_PARTY_GITIGNORE_BLOB,
        "first-party .gitignore",
    )
    _verify_blob(dfki_giw, str(_SECONDARY_SOURCES[0]["git_blob_sha1"]), "DFKI giw.py")
    _verify_blob(ace_giw, str(_SECONDARY_SOURCES[1]["git_blob_sha1"]), "ACE-DNV GiW.py")
    _verify_blob(
        leo_preprocessing,
        str(_SECONDARY_SOURCES[2]["git_blob_sha1"]),
        "LEO-UMCG preprocessing.py",
    )

    first_party = _decode(first_party_plot_labels, "first-party PlotLabels.m")
    gitignore = _decode(first_party_gitignore, "first-party .gitignore")
    dfki = _decode(dfki_giw, "DFKI giw.py")
    ace = _decode(ace_giw, "ACE-DNV GiW.py")
    leo = _decode(leo_preprocessing, "LEO-UMCG preprocessing.py")

    _require(
        first_party,
        (
            "PrIdx_%d_TrIdx_%d.mat",
            "PrIdx_%d_TrIdx_%d_Lbr_%d.mat",
            "load(str_pd, 'ProcessData')",
            "'LabelData'",
        ),
        "first-party PlotLabels.m",
    )
    _require(
        gitignore,
        ("*.mat", "*.npy", "*.mp4"),
        "first-party .gitignore",
    )
    _require(
        dfki,
        (
            "PrIdx_<P>_TrIdx_<T>.mat",
            "PrIdx_<P>_TrIdx_<T>_Lbr_<N>.mat",
            'data["ProcessData"]',
            '["LabelData"]["Labels"]',
        ),
        "DFKI downstream implementation",
    )
    _require(
        ace,
        (
            "'PrIdx_'+participantNum+'_TrIdx_'",
            "'_Lbr_'+ str(lblr) +'.mat'",
            "processData['ProcessData']",
            "labels['LabelData']",
        ),
        "ACE-DNV downstream implementation",
    )
    _require(
        leo,
        (
            "raw_file_labeler_opener",
            "./data/Extracted_Data/%s/Labels/",
            "mat['LabelData']['Labels']",
        ),
        "LEO-UMCG downstream implementation",
    )

    secondary_sources = [
        {
            **_SECONDARY_SOURCES[0],
            "process_filename_grammar_matches_first_party": True,
            "label_filename_grammar_matches_first_party": True,
            "process_variable_matches_first_party": True,
            "label_variable_matches_first_party": True,
            "exact_copy_identity_verified": False,
            "dataset_file_rights_resolved": False,
        },
        {
            **_SECONDARY_SOURCES[1],
            "process_filename_grammar_matches_first_party": True,
            "label_filename_grammar_matches_first_party": True,
            "process_variable_matches_first_party": True,
            "label_variable_matches_first_party": True,
            "exact_copy_identity_verified": False,
            "dataset_file_rights_resolved": False,
        },
        {
            **_SECONDARY_SOURCES[2],
            "raw_giw_label_files_read": True,
            "label_variable_matches_first_party": True,
            "full_filename_grammar_independently_verified": False,
            "exact_copy_identity_verified": False,
            "dataset_file_rights_resolved": False,
        },
    ]
    record: dict[str, Any] = {
        "record_type": PROBE_RECORD_TYPE,
        "first_party": {
            "repository": FIRST_PARTY_REPOSITORY,
            "pinned_commit_sha1": FIRST_PARTY_COMMIT,
            "plot_labels_path": "PlotLabels.m",
            "plot_labels_git_blob_sha1": FIRST_PARTY_PLOT_LABELS_BLOB,
            "gitignore_path": ".gitignore",
            "gitignore_git_blob_sha1": FIRST_PARTY_GITIGNORE_BLOB,
            "process_filename_pattern": PROCESS_FILENAME_PATTERN,
            "label_filename_pattern": LABEL_FILENAME_PATTERN,
            "process_variable": PROCESS_VARIABLE,
            "label_variable": LABEL_VARIABLE,
            "mat_files_ignored_by_processing_repository": True,
            "repository_is_exact_dataset_copy": False,
        },
        "secondary_sources": secondary_sources,
        "convergence": {
            "independent_downstream_source_count": 3,
            "full_layout_match_count": 2,
            "label_schema_corroboration_count": 3,
            "candidate_layout_screening_signal_only": True,
            "filename_or_schema_match_proves_exact_copy": False,
            "filename_or_schema_match_proves_source_authority": False,
            "filename_or_schema_match_proves_dataset_file_rights": False,
            "filename_or_schema_match_authorizes_empirical_use": False,
        },
        "scientific_boundary": {
            "authoritative_original_or_canonical_dataset_copy_obtained": False,
            "original_distribution_equivalence_verified": False,
            "dataset_file_rights_resolved": False,
            "analysis_use_permitted": False,
            "redistribution_authorized": False,
            "quarantine_exit_authorized": False,
            "source_audit_ready": False,
            "empirical_evidence_eligible": False,
            "human_human_agreement_created": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "gp3_validity_claim_created": False,
            "frozen_evidence_performance_claim_created": False,
        },
    }
    record["probe_fingerprint_sha256"] = probe_fingerprint(record)
    return record


def validate_gaze_in_wild_layout_convergence_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Strictly validate the frozen layout-convergence evidence record."""

    record, _ = _load(record_or_path, label="GIW layout-convergence evidence")
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("checked_on"), "2026-09-06", "review date")
    _equal(
        record.get("dataset"),
        "Gaze-in-the-Wild naturalistic eye-head event benchmark",
        "dataset identity",
    )

    parents = _mapping(record, "parent_evidence")
    _equal(
        parents.get("repository_history_evidence_fingerprint_sha256"),
        HISTORY_EVIDENCE_FINGERPRINT_SHA256,
        "repository-history parent fingerprint",
    )
    _equal(
        parents.get("secondary_recovery_lead_evidence_fingerprint_sha256"),
        SECONDARY_LEAD_EVIDENCE_FINGERPRINT_SHA256,
        "secondary-lead parent fingerprint",
    )
    _equal(
        parents.get("distribution_availability_evidence_fingerprint_sha256"),
        DISTRIBUTION_EVIDENCE_FINGERPRINT_SHA256,
        "distribution parent fingerprint",
    )

    first = _mapping(record, "first_party_schema")
    expected_first = {
        "repository": FIRST_PARTY_REPOSITORY,
        "pinned_commit_sha1": FIRST_PARTY_COMMIT,
        "plot_labels_path": "PlotLabels.m",
        "plot_labels_git_blob_sha1": FIRST_PARTY_PLOT_LABELS_BLOB,
        "gitignore_path": ".gitignore",
        "gitignore_git_blob_sha1": FIRST_PARTY_GITIGNORE_BLOB,
        "process_filename_pattern": PROCESS_FILENAME_PATTERN,
        "label_filename_pattern": LABEL_FILENAME_PATTERN,
        "process_variable": PROCESS_VARIABLE,
        "label_variable": LABEL_VARIABLE,
        "mat_files_ignored_by_processing_repository": True,
        "repository_is_exact_dataset_copy": False,
    }
    _equal(dict(first), expected_first, "first-party schema identity")

    convergence = _mapping(record, "downstream_convergence")
    _equal(
        convergence.get("reviewed_probe_record_type"),
        PROBE_RECORD_TYPE,
        "reviewed probe record type",
    )
    _equal(
        convergence.get("reviewed_probe_fingerprint_sha256"),
        EXPECTED_PROBE_FINGERPRINT_SHA256,
        "reviewed probe fingerprint",
    )
    _equal(convergence.get("independent_downstream_source_count"), 3, "source count")
    _equal(convergence.get("full_layout_match_count"), 2, "full-layout count")
    _equal(
        convergence.get("label_schema_corroboration_count"),
        3,
        "label-schema corroboration count",
    )
    sources = convergence.get("sources")
    if not isinstance(sources, list):
        raise BenchmarkIntegrityError("GIW convergence sources must be a list.")
    _equal(tuple(sources), _SECONDARY_SOURCES, "pinned secondary source inventory")
    _true(
        convergence.get("candidate_layout_screening_signal_only"),
        "candidate-screening-only interpretation",
    )
    for key, label in (
        ("convergence_is_exact_copy_identity_evidence", "exact-copy identity"),
        ("convergence_is_dataset_file_rights_evidence", "dataset-file rights"),
        ("convergence_is_empirical_authorization", "empirical authorization"),
    ):
        _false(convergence.get(key), label)

    boundary = _mapping(record, "scientific_boundary")
    _true(
        boundary.get("first_party_filename_and_matlab_variable_schema_verified"),
        "first-party filename/MATLAB schema verification",
    )
    _true(
        boundary.get("independent_downstream_layout_convergence_verified"),
        "independent downstream convergence verification",
    )
    for key, label in (
        (
            "authoritative_original_or_canonical_dataset_copy_obtained",
            "authoritative dataset acquisition",
        ),
        ("original_distribution_equivalence_verified", "distribution equivalence"),
        ("dataset_file_rights_resolved", "dataset-file rights"),
        ("analysis_use_permitted", "analysis permission"),
        ("redistribution_authorized", "redistribution authorization"),
        ("quarantine_exit_authorized", "quarantine exit"),
        ("source_audit_ready", "source-audit readiness"),
        ("empirical_evidence_eligible", "empirical eligibility"),
        ("human_human_agreement_created", "human-human agreement"),
        (
            "participant_disjoint_model_validation_created",
            "participant-disjoint validation",
        ),
        ("cross_dataset_validation_created", "cross-dataset validation"),
        ("gp3_validity_claim_created", "GP3 validity"),
        ("frozen_evidence_performance_claim_created", "Frozen Evidence performance"),
    ):
        _false(boundary.get(key), label)

    limits = record.get("claim_limits")
    actions = record.get("next_required_actions")
    if not isinstance(limits, list) or len(limits) < 5:
        raise BenchmarkIntegrityError("GIW convergence must retain claim limits.")
    if not isinstance(actions, list) or len(actions) < 4:
        raise BenchmarkIntegrityError("GIW convergence must retain next actions.")

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    calculated = evidence_fingerprint(record)
    if stored != calculated:
        raise BenchmarkIntegrityError("GIW convergence evidence self-fingerprint is invalid.")
    if stored != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError("GIW convergence immutable fingerprint drifted.")
    return record


def validate_gaze_in_wild_layout_convergence_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildLayoutConvergenceEvidence:
    """Bind a fresh exact-file probe to the reviewed frozen convergence evidence."""

    probe, _ = _load(probe_or_path, label="GIW layout-convergence probe")
    evidence, path = _load(evidence_or_path, label="GIW layout-convergence evidence")
    validated = validate_gaze_in_wild_layout_convergence_evidence(evidence)

    _equal(probe.get("record_type"), PROBE_RECORD_TYPE, "probe record type")
    _equal(
        probe.get("probe_fingerprint_sha256"),
        probe_fingerprint(probe),
        "probe self-fingerprint",
    )
    _equal(
        probe.get("probe_fingerprint_sha256"),
        EXPECTED_PROBE_FINGERPRINT_SHA256,
        "reviewed probe fingerprint",
    )
    _equal(
        probe.get("first_party"),
        validated.get("first_party_schema"),
        "fresh first-party schema",
    )

    probe_sources = probe.get("secondary_sources")
    if not isinstance(probe_sources, list) or len(probe_sources) != 3:
        raise BenchmarkIntegrityError("GIW convergence probe must retain three sources.")
    for index, expected in enumerate(_SECONDARY_SOURCES):
        source = probe_sources[index]
        if not isinstance(source, Mapping):
            raise BenchmarkIntegrityError("GIW convergence probe source must be an object.")
        for key, value in expected.items():
            _equal(source.get(key), value, f"probe source {expected['key']} {key}")
        _false(source.get("exact_copy_identity_verified"), "downstream exact-copy identity")
        _false(source.get("dataset_file_rights_resolved"), "downstream dataset-file rights")

    for index in (0, 1):
        source = probe_sources[index]
        for key in (
            "process_filename_grammar_matches_first_party",
            "label_filename_grammar_matches_first_party",
            "process_variable_matches_first_party",
            "label_variable_matches_first_party",
        ):
            _true(source.get(key), f"{source['key']} {key}")
    _true(probe_sources[2].get("raw_giw_label_files_read"), "LEO raw GIW label reading")
    _true(
        probe_sources[2].get("label_variable_matches_first_party"),
        "LEO LabelData corroboration",
    )
    _false(
        probe_sources[2].get("full_filename_grammar_independently_verified"),
        "LEO full filename-grammar verification",
    )

    convergence = _mapping(probe, "convergence")
    _equal(convergence.get("independent_downstream_source_count"), 3, "probe source count")
    _equal(convergence.get("full_layout_match_count"), 2, "probe full-layout count")
    _equal(
        convergence.get("label_schema_corroboration_count"),
        3,
        "probe label-schema count",
    )
    _true(
        convergence.get("candidate_layout_screening_signal_only"),
        "probe screening-only interpretation",
    )
    for key in (
        "filename_or_schema_match_proves_exact_copy",
        "filename_or_schema_match_proves_source_authority",
        "filename_or_schema_match_proves_dataset_file_rights",
        "filename_or_schema_match_authorizes_empirical_use",
    ):
        _false(convergence.get(key), key)

    boundary = _mapping(probe, "scientific_boundary")
    for key, value in boundary.items():
        _false(value, f"probe scientific boundary {key}")

    return GazeInWildLayoutConvergenceEvidence(
        path=path,
        fingerprint_sha256=EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        probe_fingerprint_sha256=EXPECTED_PROBE_FINGERPRINT_SHA256,
        full_layout_match_count=2,
        label_schema_corroboration_count=3,
        candidate_layout_screening_signal_only=True,
        exact_copy_identity_verified=False,
    )
