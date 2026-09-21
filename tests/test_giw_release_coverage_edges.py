from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any

import pytest

import gazeforge.gaze_in_wild_exact_processdata_structure_evidence as structure
import gazeforge.gaze_in_wild_exact_validation as exact
import gazeforge.gaze_in_wild_exact_validation_evidence as reviewed
import gazeforge.gaze_in_wild_figshare_exact_bytes_evidence as exact_bytes
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError

ROOT = Path(__file__).parents[1]
BASE = ROOT / "validation" / "evidence" / "gaze-in-wild"

REFERENCE = BASE / "gaze-in-wild-exact-model-reference-manifest-v1.json"
PROTOCOL = BASE / "gaze-in-wild-exact-model-execution-protocol-evidence-v1.json"
REVIEWED = BASE / "gaze-in-wild-exact-participant-disjoint-model-validation-evidence-v1.json"
IDENTITIES = BASE / "gaze-in-wild-processdata-exact-file-identities-v1.json"
RATES = BASE / "gaze-in-wild-processdata-processed-rate-ledger-v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _set_path(
    record: Any,
    path: tuple[Any, ...],
    value: Any,
) -> None:
    target = record

    for key in path[:-1]:
        target = target[key]

    target[path[-1]] = value


def _resign_exact(
    record: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    constant: str,
) -> None:
    body = copy.deepcopy(record)
    body.pop("evidence_fingerprint_sha256", None)

    fingerprint = benchmark_fingerprint(body)

    record["evidence_fingerprint_sha256"] = fingerprint

    monkeypatch.setattr(
        exact,
        constant,
        fingerprint,
    )


def _retag_structure(
    record: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    constant: str,
) -> None:
    fingerprint = structure.evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = fingerprint

    monkeypatch.setattr(
        structure,
        constant,
        fingerprint,
    )


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (
            ("selected_reference",),
            None,
            "lacks selected_reference",
        ),
        (
            ("selected_reference", "observed_label_codes"),
            [0],
            "label-code support",
        ),
        (
            ("selected_reference", "files"),
            [],
            "exactly 18 file rows",
        ),
        (
            (
                "selected_reference",
                "files",
                0,
                "labeller_id",
            ),
            6,
            "file-row boundary",
        ),
        (
            ("scientific_boundary",),
            None,
            "not frozen",
        ),
        (
            (
                "scientific_boundary",
                "reference_manifest_frozen",
            ),
            False,
            "not frozen",
        ),
        (
            (
                "scientific_boundary",
                "gp3_validity_claim_created",
            ),
            True,
            "must keep",
        ),
    ],
)
def test_reference_manifest_deep_fail_closed_edges(
    monkeypatch: pytest.MonkeyPatch,
    path: tuple[Any, ...],
    value: Any,
    match: str,
) -> None:
    record = copy.deepcopy(_load(REFERENCE))

    _set_path(record, path, value)

    _resign_exact(
        record,
        monkeypatch,
        "REFERENCE_MANIFEST_FINGERPRINT",
    )

    with pytest.raises(BenchmarkIntegrityError, match=match):
        exact.validate_exact_reference_manifest(record)


def test_reference_manifest_participant_coverage_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = copy.deepcopy(_load(REFERENCE))

    record["selected_reference"]["files"][0]["participant_token"] = "PrIdx_999"

    _resign_exact(
        record,
        monkeypatch,
        "REFERENCE_MANIFEST_FINGERPRINT",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="participant/recording coverage",
    ):
        exact.validate_exact_reference_manifest(record)


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (
            ("parent_evidence",),
            None,
            "lacks parent evidence",
        ),
        (
            (
                "parent_evidence",
                "model_reference_preflight_evidence_fingerprint_sha256",
            ),
            "0" * 64,
            "parent",
        ),
        (
            ("execution_protocol",),
            None,
            "execution protocol is missing",
        ),
        (
            ("execution_protocol", "models"),
            ["I-VT"],
            "model family",
        ),
        (
            (
                "execution_protocol",
                "hidden_layer_sizes",
            ),
            [64],
            "topology",
        ),
        (
            (
                "execution_protocol",
                "scene_resolution_px",
            ),
            [1, 1],
            "scene resolution",
        ),
        (
            (
                "execution_protocol",
                "label_process_timestamp_vector_alignment_required",
            ),
            "approximately_equal",
            "timestamp-alignment",
        ),
        (
            ("scientific_boundary",),
            None,
            "scientific boundary is missing",
        ),
        (
            (
                "scientific_boundary",
                "exact_distribution_model_execution_authorized",
            ),
            False,
            "not authorized",
        ),
    ],
)
def test_execution_protocol_deep_fail_closed_edges(
    monkeypatch: pytest.MonkeyPatch,
    path: tuple[Any, ...],
    value: Any,
    match: str,
) -> None:
    record = copy.deepcopy(_load(PROTOCOL))

    _set_path(record, path, value)

    _resign_exact(
        record,
        monkeypatch,
        "EXECUTION_PROTOCOL_FINGERPRINT",
    )

    with pytest.raises(BenchmarkIntegrityError, match=match):
        exact.validate_exact_execution_protocol(record)


def test_exact_evidence_record_type_gate() -> None:
    record = copy.deepcopy(_load(REFERENCE))
    record["record_type"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Unexpected GIW exact evidence type",
    ):
        exact.validate_exact_reference_manifest(record)


def test_reviewed_canonicalization_edge_contracts() -> None:
    assert reviewed._canonicalize(float("nan")) is None
    assert reviewed._canonicalize(float("inf")) == "Infinity"
    assert reviewed._canonicalize(float("-inf")) == "-Infinity"

    assert reviewed._canonicalize(
        (0.1234567891,),
    ) == [0.12345679]

    assert reviewed._canonicalize(
        {"x": (0.1234567891,)},
    ) == {"x": [0.12345679]}


def test_reviewed_mapping_rejects_non_mapping() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        reviewed._mapping(None, "test")


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        [{}, {}],
    ],
)
def test_reviewed_summary_core_requires_three_rows(
    value: Any,
) -> None:
    with pytest.raises(BenchmarkIntegrityError):
        reviewed._summary_core(value)


def test_reviewed_summary_core_rejects_non_mapping_row() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="model summary row",
    ):
        reviewed._summary_core(
            [{}, {}, 3],
        )


def test_reviewed_load_rejects_json_array(
    tmp_path: Path,
) -> None:
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        reviewed.load_reviewed_gaze_in_wild_validation_evidence(
            path,
        )


def test_reviewed_split_assignment_count_gate() -> None:
    record = _load(REVIEWED)
    split = copy.deepcopy(record["split_integrity"])

    split["fold_participant_assignments"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="12 fold assignments",
    ):
        reviewed._validate_split(split)


def test_reviewed_split_fold_coverage_gate() -> None:
    record = _load(REVIEWED)
    split = copy.deepcopy(record["split_integrity"])

    for row in split["fold_participant_assignments"]:
        row["validation_fold"] = 1

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fold coverage",
    ):
        reviewed._validate_split(split)


def test_reviewed_pursuit_requires_sections() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="sections are missing",
    ):
        reviewed._extract_pursuit({})


def test_reviewed_pursuit_requires_model_coverage() -> None:
    record = _load(REVIEWED)
    metrics = copy.deepcopy(record["metrics"])

    metrics["sample_event_class_performance"] = [
        row
        for row in metrics["sample_event_class_performance"]
        if not (row.get("event_label") == "pursuit" and row.get("model") == "I-VT")
    ]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="model coverage",
    ):
        reviewed._extract_pursuit(metrics)


def test_reviewed_pursuit_reference_counts_must_agree() -> None:
    record = _load(REVIEWED)
    metrics = copy.deepcopy(record["metrics"])

    for row in metrics["event_class_performance"]:
        if row.get("event_label") == "pursuit" and row.get("model") == "I-VT":
            row["n_reference_events"] += 1
            break

    with pytest.raises(
        BenchmarkIntegrityError,
        match="reference-event counts disagree",
    ):
        reviewed._extract_pursuit(metrics)


def test_structure_load_mapping_round_trip() -> None:
    payload, path = structure._load(
        {"x": 1},
        "test",
    )

    assert payload == {"x": 1}
    assert path is None


def test_structure_load_rejects_bad_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        structure._load(path, "test")


def test_structure_load_rejects_non_object(
    tmp_path: Path,
) -> None:
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must contain one JSON object",
    ):
        structure._load(path, "test")


def test_structure_small_fail_closed_helpers() -> None:
    with pytest.raises(BenchmarkIntegrityError):
        structure._mapping({}, "missing", "test")

    with pytest.raises(BenchmarkIntegrityError):
        structure._equal(1, 2, "test")

    with pytest.raises(BenchmarkIntegrityError):
        structure._true(False, "test")

    with pytest.raises(BenchmarkIntegrityError):
        structure._false(True, "test")


@pytest.mark.parametrize(
    ("case", "match"),
    [
        ("count", "68 rows"),
        ("malformed", "row is malformed"),
        ("duplicate", "invalid/duplicate"),
        ("sha", "SHA-256 is invalid"),
    ],
)
def test_identity_ledger_deep_validation_edges(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    match: str,
) -> None:
    record = copy.deepcopy(_load(IDENTITIES))

    if case == "count":
        record["files"] = []

    elif case == "malformed":
        record["files"][0] = "not-a-row"

    elif case == "duplicate":
        record["files"][1]["name"] = record["files"][0]["name"]

    elif case == "sha":
        record["files"][0]["sha256"] = "bad"

    _retag_structure(
        record,
        monkeypatch,
        "IDENTITY_EVIDENCE_FINGERPRINT_SHA256",
    )

    with pytest.raises(BenchmarkIntegrityError, match=match):
        structure._validate_identity_ledger(record)


@pytest.mark.parametrize(
    ("case", "match"),
    [
        ("count", "68 rows"),
        ("shape", "row shape"),
        ("duplicate", "duplicated a file identity"),
        ("participant", "participant token"),
        ("trial", "trial token"),
        ("stored", "stored processed rate"),
        ("inferred", "inferred processed rate"),
        ("timestamp_count", "timestamp count"),
    ],
)
def test_rate_ledger_deep_validation_edges(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    match: str,
) -> None:
    identities = structure._validate_identity_ledger(
        IDENTITIES,
    )

    record = copy.deepcopy(_load(RATES))

    if case == "count":
        record["rows"] = []

    elif case == "shape":
        record["rows"][0] = ["short"]

    elif case == "duplicate":
        record["rows"][1][0] = record["rows"][0][0]
        record["rows"][1][1] = record["rows"][0][1]

    elif case == "participant":
        record["rows"][0][2] = 0

    elif case == "trial":
        record["rows"][0][3] = 0

    elif case == "stored":
        record["rows"][0][4] = 299.0

    elif case == "inferred":
        record["rows"][0][5] = math.inf

    elif case == "timestamp_count":
        record["rows"][0][6] = 1

    _retag_structure(
        record,
        monkeypatch,
        "RATE_EVIDENCE_FINGERPRINT_SHA256",
    )

    with pytest.raises(BenchmarkIntegrityError, match=match):
        structure._validate_rate_ledger(
            record,
            identities,
        )


def test_exact_bytes_load_mapping_round_trip() -> None:
    payload, path = exact_bytes._load(
        {"x": 1},
        "test",
    )

    assert payload == {"x": 1}
    assert path is None


def test_exact_bytes_load_failures(
    tmp_path: Path,
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        exact_bytes._load(bad, "test")

    array = tmp_path / "array.json"
    array.write_text("[]", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        exact_bytes._load(array, "test")


def test_exact_bytes_small_helpers_fail_closed() -> None:
    with pytest.raises(BenchmarkIntegrityError):
        exact_bytes._mapping({}, "missing")

    with pytest.raises(BenchmarkIntegrityError):
        exact_bytes._equal(1, 2, "test")

    with pytest.raises(BenchmarkIntegrityError):
        exact_bytes._true(False, "test")

    with pytest.raises(BenchmarkIntegrityError):
        exact_bytes._false(True, "test")


def test_exact_bytes_raw_items_contract() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="items are missing",
    ):
        exact_bytes._raw_items(
            {"items": "bad"},
        )

    result = exact_bytes._raw_items(
        {
            "items": [
                {"label": "ProcessData"},
                "ignored",
            ]
        }
    )

    assert result == {
        "ProcessData": {
            "label": "ProcessData",
        }
    }
