"""Fail-closed validation for reviewed Gaze-in-the-Wild overlap human agreement."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "gaze-in-wild-distributed-overlap-human-human-agreement-evidence-v1"
STATUS = "verified-distributed-overlap-subset-human-human-agreement"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "7e6d6180b01417d7be2e07483cc0c7e0feb86a1d08be6b8aeba03f48fdb27f02"
)
EXPECTED_DISCOVERY_FINGERPRINT_SHA256 = (
    "ed0af8abff6d235c71810f3964dc0c9a3dafd33d8260415e333d199da5713569"
)
EXPECTED_VERIFICATION_MANIFEST_SHA256 = (
    "b93b8a89b5cc72c057973bddeccb17f15114afa7865d44ddf460b9762dd85c0a"
)
EXPECTED_FEASIBILITY_FINGERPRINT_SHA256 = (
    "90249ed3daf543910ab1c269520246cf6dd12fb94d136f875729fb444407590c"
)
EXPECTED_CANDIDATE_FINGERPRINT_SHA256 = (
    "46967ca0d96e0dd1c87d6f781234b1f4e3c3d8bf2318e697524c8b8b33f32a87"
)
EXPECTED_EXACT_BYTE_EVIDENCE_FINGERPRINT_SHA256 = (
    "dbf277d698266fe53e337a15fc342e9af1835460d2bcc69c3992635de8fa0a00"
)
EXPECTED_ARTIFACT_ZIP_SHA256 = (
    "67bebc822a3633b03e81914c542abb78c64c1e75d42c13a95be60dfd3ad4f87c"
)
EXPECTED_RECORDINGS = (
    "PrIdx_1_TrIdx_1",
    "PrIdx_1_TrIdx_2",
    "PrIdx_2_TrIdx_1",
    "PrIdx_2_TrIdx_2",
    "PrIdx_6_TrIdx_2",
)
EXPECTED_PAIR_COUNTS = {"1-2": 4, "1-5": 4, "1-6": 4, "2-5": 4, "2-6": 4, "5-6": 5}
EXPECTED_RATES = (
    299.990148050583,
    299.993916027871,
    299.99537216017,
    299.995594281077,
    299.996710812083,
)
TOKEN_RE = re.compile(r"^PrIdx_\d+_TrIdx_\d+$")


@dataclass(frozen=True, slots=True)
class GazeInWildOverlapHHAEvidence:
    path: Path | None
    fingerprint_sha256: str
    pair_count: int
    recording_count: int
    selected_label_file_count: int
    overlap_hha_verified: bool
    quarantine_exit_authorized: bool


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(value: Mapping[str, Any] | str | Path) -> tuple[dict[str, Any], Path | None]:
    if isinstance(value, Mapping):
        return dict(value), None
    path = Path(value)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"Could not load GIW overlap-HHA evidence: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError("GIW overlap-HHA evidence must contain one JSON object.")
    return payload, path


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"GIW overlap-HHA field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"GIW overlap-HHA {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"GIW overlap-HHA must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"GIW overlap-HHA must not promote {label}.")


def _finite_probability(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise BenchmarkIntegrityError(f"GIW overlap-HHA {label} must be numeric.") from exc
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise BenchmarkIntegrityError(f"GIW overlap-HHA {label} must be in [0, 1].")
    return result


def _finite_kappa(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise BenchmarkIntegrityError(f"GIW overlap-HHA {label} must be numeric.") from exc
    if not math.isfinite(result) or not -1.0 <= result <= 1.0:
        raise BenchmarkIntegrityError(f"GIW overlap-HHA {label} must be in [-1, 1].")
    return result


def _validate_binding(record: Mapping[str, Any]) -> None:
    binding = _mapping(record, "source_binding")
    _equal(binding.get("workflow_run_id"), 34170510919, "workflow run id")
    _equal(binding.get("workflow_job_id"), 101889768746, "workflow job id")
    _equal(
        binding.get("workflow_head_sha"),
        "94996d99010ca5ed5f988bcb60cebb053923ffc2",
        "workflow head sha",
    )
    _equal(binding.get("artifact_id"), 10035567001, "artifact id")
    _equal(
        binding.get("artifact_name"),
        "gaze-in-wild-labeldata-hha-discovery",
        "artifact name",
    )
    _equal(
        binding.get("artifact_zip_sha256"),
        EXPECTED_ARTIFACT_ZIP_SHA256,
        "artifact ZIP digest",
    )
    _equal(
        binding.get("discovery_fingerprint_sha256"),
        EXPECTED_DISCOVERY_FINGERPRINT_SHA256,
        "discovery fingerprint",
    )
    _equal(
        binding.get("verification_manifest_sha256"),
        EXPECTED_VERIFICATION_MANIFEST_SHA256,
        "verification manifest",
    )
    _equal(
        binding.get("feasibility_probe_fingerprint_sha256"),
        EXPECTED_FEASIBILITY_FINGERPRINT_SHA256,
        "feasibility fingerprint",
    )
    _equal(
        binding.get("candidate_selection_evidence_fingerprint_sha256"),
        EXPECTED_CANDIDATE_FINGERPRINT_SHA256,
        "candidate-selection fingerprint",
    )
    _equal(
        binding.get("exact_byte_reviewed_evidence_fingerprint_sha256"),
        EXPECTED_EXACT_BYTE_EVIDENCE_FINGERPRINT_SHA256,
        "exact-byte evidence fingerprint",
    )


def _validate_inputs(record: Mapping[str, Any]) -> None:
    inputs = _mapping(record, "verified_inputs")
    _equal(inputs.get("selected_label_file_count"), 18, "selected LabelData file count")
    _equal(inputs.get("selected_recording_count"), 5, "selected recording count")
    _equal(inputs.get("selected_total_size_bytes"), 10_274_311, "selected total bytes")
    _equal(inputs.get("download_attempt_distribution"), {"1": 18}, "download attempts")
    _true(inputs.get("all_files_matched_prior_size_md5_sha256"), "prior byte identity")
    _true(
        inputs.get("all_filename_internal_pridx_tridx_lbridx_agree"),
        "filename/internal identity agreement",
    )
    _true(inputs.get("all_raw_mat_bytes_deleted_after_inspection"), "raw-byte deletion")
    rates = inputs.get("distinct_inferred_sampling_rates_hz")
    _equal(rates, list(EXPECTED_RATES), "inferred sampling rates")
    recordings = inputs.get("recording_tokens")
    _equal(recordings, list(EXPECTED_RECORDINGS), "recording tokens")
    for token in recordings:
        if not isinstance(token, str) or TOKEN_RE.fullmatch(token) is None:
            raise BenchmarkIntegrityError("GIW overlap-HHA recording token grammar drifted.")


def _validate_protocol(record: Mapping[str, Any]) -> None:
    protocol = _mapping(record, "analysis_protocol")
    _equal(
        protocol.get("scope"),
        "distributed_multi_labeller_overlap_subset_only",
        "analysis scope",
    )
    _true(protocol.get("sample_all_labels_includes_unlabelled_code_0"), "all-label code 0")
    _equal(
        protocol.get("pairwise_clearly_labelled_definition"),
        "retain a sample only when both selected labellers have nonzero label codes",
        "clear-label definition",
    )
    _equal(
        protocol.get("event_unlabelled_code_0_policy"),
        "hard_separator_and_excluded_event_class",
        "event code-0 policy",
    )
    _equal(protocol.get("event_min_iou"), 0.5, "event minimum IoU")
    _true(protocol.get("event_label_match_required"), "event label matching")
    _true(protocol.get("event_metrics_bidirectional"), "bidirectional event metrics")
    _true(protocol.get("neither_labeller_treated_as_truth"), "symmetric human references")
    _equal(
        protocol.get("sampling_rate_policy"),
        "timestamp_inferred_per_recording",
        "sampling-rate policy",
    )
    _equal(protocol.get("resampling"), None, "resampling policy")
    _false(protocol.get("coordinate_data_used"), "coordinate use")
    _false(protocol.get("processdata_loaded"), "ProcessData use")
    _false(protocol.get("tridx_to_publication_task_mapping_used"), "task-name mapping")
    _equal(
        protocol.get("event_matching"),
        "one_to_one_hungarian_temporal_iou_equivalent_sparse_components",
        "event matching semantics",
    )


def _validate_pairs(record: Mapping[str, Any]) -> None:
    _equal(record.get("pair_shared_recording_counts"), EXPECTED_PAIR_COUNTS, "pair coverage")
    pairs = record.get("pair_results")
    if not isinstance(pairs, list) or len(pairs) != 6:
        raise BenchmarkIntegrityError("GIW overlap-HHA must contain exactly six labeller pairs.")
    observed: set[str] = set()
    for pair in pairs:
        if not isinstance(pair, Mapping):
            raise BenchmarkIntegrityError("GIW overlap-HHA pair result is malformed.")
        left = pair.get("left_labeller_id")
        right = pair.get("right_labeller_id")
        if not isinstance(left, int) or not isinstance(right, int) or left <= 0 or right <= left:
            raise BenchmarkIntegrityError("GIW overlap-HHA labeller-pair identity is invalid.")
        key = f"{left}-{right}"
        if key in observed or key not in EXPECTED_PAIR_COUNTS:
            raise BenchmarkIntegrityError("GIW overlap-HHA pair set drifted.")
        observed.add(key)
        _equal(pair.get("shared_recording_count"), EXPECTED_PAIR_COUNTS[key], f"{key} coverage")
        shared = pair.get("shared_recordings")
        if not isinstance(shared, list) or len(shared) != EXPECTED_PAIR_COUNTS[key]:
            raise BenchmarkIntegrityError(f"GIW overlap-HHA {key} shared recordings drifted.")
        if any(token not in EXPECTED_RECORDINGS for token in shared):
            raise BenchmarkIntegrityError(f"GIW overlap-HHA {key} widened beyond reviewed recordings.")
        n_all = pair.get("n_aligned_samples")
        n_clear = pair.get("n_pairwise_clearly_labelled_samples")
        if not isinstance(n_all, int) or not isinstance(n_clear, int) or not 0 < n_clear <= n_all:
            raise BenchmarkIntegrityError(f"GIW overlap-HHA {key} sample counts are invalid.")
        clear_fraction = _finite_probability(
            pair.get("pairwise_clearly_labelled_fraction"), f"{key} clear fraction"
        )
        if not math.isclose(clear_fraction, n_clear / n_all, rel_tol=0.0, abs_tol=1e-15):
            raise BenchmarkIntegrityError(f"GIW overlap-HHA {key} clear fraction is inconsistent.")
        sample_all = _mapping(pair, "sample_all_labels")
        sample_clear = _mapping(pair, "sample_pairwise_clearly_labelled")
        _finite_probability(sample_all.get("exact_agreement"), f"{key} all-label agreement")
        _finite_kappa(sample_all.get("cohen_kappa"), f"{key} all-label kappa")
        _finite_probability(sample_clear.get("exact_agreement"), f"{key} clear agreement")
        _finite_kappa(sample_clear.get("cohen_kappa"), f"{key} clear kappa")
        event = _mapping(pair, "event_agreement")
        _finite_probability(event.get("f1"), f"{key} event F1")
        _finite_probability(event.get("mean_matched_iou"), f"{key} mean matched IoU")
        left_event = _mapping(event, "left_as_reference")
        right_event = _mapping(event, "right_as_reference")
        _equal(left_event.get("precision"), right_event.get("recall"), f"{key} P/R symmetry")
        _equal(left_event.get("recall"), right_event.get("precision"), f"{key} R/P symmetry")
        _equal(left_event.get("false_positive"), right_event.get("false_negative"), f"{key} FP/FN symmetry")
        _equal(left_event.get("false_negative"), right_event.get("false_positive"), f"{key} FN/FP symmetry")
    _equal(observed, set(EXPECTED_PAIR_COUNTS), "labeller pair identities")


def _validate_boundaries(record: Mapping[str, Any]) -> None:
    boundary = _mapping(record, "scientific_boundary")
    _true(
        boundary.get("human_human_agreement_created_for_distributed_overlap_subset"),
        "reviewed overlap-subset HHA",
    )
    for key in (
        "full_distributed_labeldata_hha_created",
        "task_stratified_hha_created",
        "gaze_coordinate_validation_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "complete_file_to_publication_task_mapping_verified",
        "quarantine_exit_authorized",
        "new_model_performance_claim_created",
    ):
        _false(boundary.get(key), key)
    _false(record.get("raw_dataset_bytes_retained"), "raw dataset retention")


def validate_gaze_in_wild_overlap_hha_evidence(
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildOverlapHHAEvidence:
    """Validate the immutable reviewed overlap-subset human-human agreement baseline."""

    record, path = _load(evidence_or_path)
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("reviewed_on"), "2026-09-08", "review date")
    _equal(
        record.get("evidence_fingerprint_sha256"),
        EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        "stored evidence fingerprint",
    )
    _equal(
        evidence_fingerprint(record),
        EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        "recomputed evidence fingerprint",
    )
    _validate_binding(record)
    _validate_inputs(record)
    _validate_protocol(record)
    _validate_pairs(record)
    _validate_boundaries(record)

    limitations = record.get("limitations")
    if not isinstance(limitations, list) or len(limitations) != 5:
        raise BenchmarkIntegrityError("GIW overlap-HHA limitations must remain explicit.")
    joined = " ".join(str(value).lower() for value in limitations)
    for phrase in ("no publication task-name mapping", "not gazeforge model validation", "no gaze coordinates", "gp3"):
        if phrase not in joined:
            raise BenchmarkIntegrityError(f"GIW overlap-HHA limitation {phrase!r} was lost.")

    inputs = _mapping(record, "verified_inputs")
    boundary = _mapping(record, "scientific_boundary")
    return GazeInWildOverlapHHAEvidence(
        path=path,
        fingerprint_sha256=EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        pair_count=6,
        recording_count=int(inputs["selected_recording_count"]),
        selected_label_file_count=int(inputs["selected_label_file_count"]),
        overlap_hha_verified=True,
        quarantine_exit_authorized=bool(boundary["quarantine_exit_authorized"]),
    )
