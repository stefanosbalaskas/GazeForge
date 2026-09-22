from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from test_visus_evidence import (
    _execution_summary,
    _resign_transition,
    _signed,
    _synthetic_bundle,
    _write,
)

from gazeforge import visus_evidence as evidence
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_authority_binding import (
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
)


def _transition_payload(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _transition_call(
    root: Path,
    suite: dict,
):
    return evidence._transition_summary(
        root,
        root / evidence._SUITE_MANIFEST_NAME,
        suite,
    )


def _binding_context(tmp_path):
    (
        root,
        suite,
        binding_path,
        transition_path,
    ) = _synthetic_bundle(tmp_path)

    transition = _transition_payload(transition_path)

    return (
        root,
        suite,
        binding_path,
        transition_path,
        transition,
    )


def _rewrite_binding(
    binding_path: Path,
    transition: dict,
    mutate,
):
    binding = json.loads(binding_path.read_text(encoding="utf-8"))

    mutate(binding)

    binding = _signed(
        binding,
        "binding_fingerprint_sha256",
    )

    _write(
        binding_path,
        binding,
    )

    transition = copy.deepcopy(transition)

    transition["protocol_validation_binding_fingerprint_sha256"] = binding[
        "binding_fingerprint_sha256"
    ]

    return binding, transition


# ============================================================
# LOW-LEVEL FILE / FINGERPRINT / PATH CONTRACTS
# ============================================================


def test_read_json_object_missing_file(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-symlink regular file",
    ):
        evidence._read_json_object(
            tmp_path / "missing.json",
            label="fixture",
        )


def test_read_json_object_invalid_json(
    tmp_path,
):
    path = tmp_path / "bad.json"
    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        evidence._read_json_object(
            path,
            label="fixture",
        )


def test_read_json_object_requires_object(
    tmp_path,
):
    path = tmp_path / "array.json"
    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        evidence._read_json_object(
            path,
            label="fixture",
        )


def test_file_sha256_missing_file(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-symlink regular file",
    ):
        evidence._file_sha256(
            tmp_path / "missing.bin",
            label="fixture",
        )


def test_revalidate_fingerprint_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint does not revalidate",
    ):
        evidence._revalidate_fingerprint(
            {
                "value": 1,
                "fingerprint": "bad",
            },
            "fingerprint",
            label="fixture",
        )


@pytest.mark.parametrize(
    "relative",
    [
        "",
        None,
    ],
)
def test_safe_child_rejects_empty_path(
    tmp_path,
    relative,
):
    value = "" if relative is None else relative

    with pytest.raises(
        BenchmarkIntegrityError,
        match="child path is invalid",
    ):
        evidence._safe_child(
            tmp_path,
            value,
        )


def test_safe_child_rejects_absolute_path(
    tmp_path,
):
    absolute = (tmp_path / "absolute.json").resolve()

    with pytest.raises(
        BenchmarkIntegrityError,
        match="child path is invalid",
    ):
        evidence._safe_child(
            tmp_path,
            str(absolute),
        )


def test_safe_child_rejects_escape(
    tmp_path,
):
    root = tmp_path / "root"
    root.mkdir()

    with pytest.raises(
        BenchmarkIntegrityError,
        match="escapes the suite root",
    ):
        evidence._safe_child(
            root,
            "../outside.json",
        )


# ============================================================
# TRANSITION SUMMARY GUARDS
# ============================================================


def test_transition_schema_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    payload = _transition_payload(transition_path)
    payload["schema"] = "wrong"

    _write(
        transition_path,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="transition schema is invalid",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_semantics_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    _resign_transition(
        transition_path,
        lambda payload: payload.__setitem__(
            "transition_semantics",
            None,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="transition semantics are invalid",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_certificate_consumption_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    _resign_transition(
        transition_path,
        lambda payload: payload.__setitem__(
            "source_authority_certificate_consumed",
            False,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="did not consume",
    ):
        _transition_call(
            root,
            suite,
        )


@pytest.mark.parametrize(
    "field",
    [
        "post_authority_suite",
        "pre_authority_suite",
    ],
)
def test_transition_requires_suite_identities(
    tmp_path,
    field,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    _resign_transition(
        transition_path,
        lambda payload: payload.__setitem__(
            field,
            None,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="suite identities are incomplete",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_manifest_filename_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    def mutate(payload):
        payload["post_authority_suite"]["manifest_filename"] = "wrong.json"

    _resign_transition(
        transition_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="different authority suite manifest",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_suite_fingerprint_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    def mutate(payload):
        payload["post_authority_suite"]["suite_fingerprint_sha256"] = "0" * 64

    _resign_transition(
        transition_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="transition/suite fingerprints disagree",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_report_count_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    def mutate(payload):
        payload["post_authority_suite"]["report_count"] = 999

    _resign_transition(
        transition_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report counts disagree",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_suite_manifest_bytes_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    def mutate(payload):
        payload["post_authority_suite"]["manifest_sha256"] = "0" * 64

    _resign_transition(
        transition_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="suite-manifest bytes drifted",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_pre_authority_fingerprint_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    def mutate(payload):
        payload["pre_authority_suite"]["suite_fingerprint_sha256"] = "bad"

    _resign_transition(
        transition_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="pre-authority suite identity is invalid",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_projection_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    _resign_transition(
        transition_path,
        lambda payload: payload.__setitem__(
            "pre_authority_projection_fingerprint_sha256",
            "0" * 64,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="no longer reconstructs",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_requires_distinct_authority_suite(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    def mutate(payload):
        current = suite["suite_fingerprint_sha256"]

        payload["pre_authority_suite"]["suite_fingerprint_sha256"] = current

        payload["pre_authority_projection_fingerprint_sha256"] = current

    _resign_transition(
        transition_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="did not create a distinct authority suite",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_source_structure_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    _resign_transition(
        transition_path,
        lambda payload: payload.__setitem__(
            "source",
            None,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="transition/source identity is invalid",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_source_identity_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    def mutate(payload):
        payload["source"]["source_manifest_fingerprint_sha256"] = "0" * 64

    _resign_transition(
        transition_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identities disagree",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_child_ledger_structure_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    _resign_transition(
        transition_path,
        lambda payload: payload.__setitem__(
            "child_reports",
            None,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="child-report ledger is invalid",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_child_inventory_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    def mutate(payload):
        payload["child_reports"] = payload["child_reports"][:-1]

    _resign_transition(
        transition_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="child-report inventory disagrees",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_child_filename_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    def mutate(payload):
        payload["child_reports"][0]["filename"] = "wrong.json"

    _resign_transition(
        transition_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="changed a child-report filename",
    ):
        _transition_call(
            root,
            suite,
        )


def test_transition_child_report_fingerprint_guard(
    tmp_path,
):
    root, suite, _, transition_path = _synthetic_bundle(tmp_path)

    def mutate(payload):
        payload["child_reports"][0]["report_fingerprint_sha256"] = "0" * 64

    _resign_transition(
        transition_path,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="child-report fingerprint drifted",
    ):
        _transition_call(
            root,
            suite,
        )


# ============================================================
# PROTOCOL BINDING DISCOVERY
# ============================================================


def test_binding_identity_guard(
    tmp_path,
):
    root, _, _, transition_path = _synthetic_bundle(tmp_path)

    payload = _transition_payload(transition_path)

    payload["protocol_validation_binding_filename"] = "wrong.json"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="binding identity is invalid",
    ):
        evidence._find_protocol_binding(
            root,
            payload,
            None,
        )


def test_explicit_binding_filename_guard(
    tmp_path,
):
    root, _, _, transition_path = _synthetic_bundle(tmp_path)

    payload = _transition_payload(transition_path)

    wrong = tmp_path / "wrong.json"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="binding filename is invalid",
    ):
        evidence._find_protocol_binding(
            root,
            payload,
            wrong,
        )


def test_explicit_binding_bytes_guard(
    tmp_path,
):
    root, _, _, transition_path = _synthetic_bundle(tmp_path)

    payload = _transition_payload(transition_path)

    candidate = tmp_path / evidence._PROTOCOL_VALIDATION_BINDING_NAME

    candidate.write_bytes(b"wrong bytes")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="binding bytes disagree",
    ):
        evidence._find_protocol_binding(
            root,
            payload,
            candidate,
        )


def test_binding_lookup_skips_nonfiles(
    tmp_path,
):
    (
        root,
        _,
        binding_path,
        transition_path,
    ) = _synthetic_bundle(tmp_path)

    payload = _transition_payload(transition_path)

    decoy = root.parent / "decoy" / evidence._PROTOCOL_VALIDATION_BINDING_NAME

    decoy.mkdir(
        parents=True,
    )

    found = evidence._find_protocol_binding(
        root,
        payload,
        None,
    )

    assert found == binding_path


# ============================================================
# PROTOCOL BINDING CONTENT
# ============================================================


def test_protocol_binding_schema_guard(
    tmp_path,
):
    (
        _,
        suite,
        binding_path,
        _,
        transition,
    ) = _binding_context(tmp_path)

    binding = json.loads(binding_path.read_text(encoding="utf-8"))

    binding["schema"] = "wrong"

    _write(
        binding_path,
        binding,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="binding schema is invalid",
    ):
        evidence._validate_protocol_binding(
            binding_path,
            transition,
            suite,
        )


def test_protocol_binding_status_guard(
    tmp_path,
):
    (
        _,
        suite,
        binding_path,
        _,
        transition,
    ) = _binding_context(tmp_path)

    binding = json.loads(binding_path.read_text(encoding="utf-8"))

    binding["status"] = "wrong"

    _write(
        binding_path,
        binding,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="binding status is invalid",
    ):
        evidence._validate_protocol_binding(
            binding_path,
            transition,
            suite,
        )


def test_protocol_binding_fingerprint_identity_guard(
    tmp_path,
):
    (
        _,
        suite,
        binding_path,
        _,
        transition,
    ) = _binding_context(tmp_path)

    transition["protocol_validation_binding_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint disagrees",
    ):
        evidence._validate_protocol_binding(
            binding_path,
            transition,
            suite,
        )


def test_protocol_fingerprint_guard(
    tmp_path,
):
    (
        _,
        suite,
        binding_path,
        _,
        transition,
    ) = _binding_context(tmp_path)

    transition["protocol_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="pre-execution protocol fingerprint disagrees",
    ):
        evidence._validate_protocol_binding(
            binding_path,
            transition,
            suite,
        )


def test_protocol_batch_fingerprint_guard(
    tmp_path,
):
    (
        _,
        suite,
        binding_path,
        _,
        transition,
    ) = _binding_context(tmp_path)

    transition["protocol_batch_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="protocol-batch fingerprint disagrees",
    ):
        evidence._validate_protocol_binding(
            binding_path,
            transition,
            suite,
        )


def test_protocol_binding_requires_pre_authority_identity(
    tmp_path,
):
    (
        _,
        suite,
        binding_path,
        _,
        transition,
    ) = _binding_context(tmp_path)

    transition["pre_authority_suite"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="pre-authority suite identity is invalid",
    ):
        evidence._validate_protocol_binding(
            binding_path,
            transition,
            suite,
        )


def test_protocol_binding_pre_authority_suite_guard(
    tmp_path,
):
    (
        _,
        suite,
        binding_path,
        _,
        transition,
    ) = _binding_context(tmp_path)

    transition["pre_authority_suite"]["suite_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not identify",
    ):
        evidence._validate_protocol_binding(
            binding_path,
            transition,
            suite,
        )


def test_protocol_binding_source_structure_guard(
    tmp_path,
):
    (
        _,
        suite,
        binding_path,
        _,
        transition,
    ) = _binding_context(tmp_path)

    _, transition = _rewrite_binding(
        binding_path,
        transition,
        lambda binding: binding.__setitem__(
            "source",
            None,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity is invalid",
    ):
        evidence._validate_protocol_binding(
            binding_path,
            transition,
            suite,
        )


def test_protocol_binding_source_identity_guard(
    tmp_path,
):
    (
        _,
        suite,
        binding_path,
        _,
        transition,
    ) = _binding_context(tmp_path)

    def mutate(binding):
        binding["source"]["source_manifest_fingerprint_sha256"] = "0" * 64

    _, transition = _rewrite_binding(
        binding_path,
        transition,
        mutate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source authority identities disagree",
    ):
        evidence._validate_protocol_binding(
            binding_path,
            transition,
            suite,
        )


def test_protocol_binding_evaluation_grid_guard(
    tmp_path,
):
    (
        _,
        suite,
        binding_path,
        _,
        transition,
    ) = _binding_context(tmp_path)

    _, transition = _rewrite_binding(
        binding_path,
        transition,
        lambda binding: binding.__setitem__(
            "frozen_evaluation",
            None,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="external evaluation-grid boundary",
    ):
        evidence._validate_protocol_binding(
            binding_path,
            transition,
            suite,
        )


def test_protocol_binding_model_human_execution_guard(
    tmp_path,
):
    (
        _,
        suite,
        binding_path,
        _,
        transition,
    ) = _binding_context(tmp_path)

    _, transition = _rewrite_binding(
        binding_path,
        transition,
        lambda binding: binding.__setitem__(
            "model_human_validation_executed",
            False,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not prove model-human execution",
    ):
        evidence._validate_protocol_binding(
            binding_path,
            transition,
            suite,
        )


def test_protocol_binding_separate_authority_gate_guard(
    tmp_path,
):
    (
        _,
        suite,
        binding_path,
        _,
        transition,
    ) = _binding_context(tmp_path)

    _, transition = _rewrite_binding(
        binding_path,
        transition,
        lambda binding: binding.__setitem__(
            "source_authority_certificate_required_separately",
            False,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="bypasses the separate authority gate",
    ):
        evidence._validate_protocol_binding(
            binding_path,
            transition,
            suite,
        )


def test_protocol_binding_self_certification_guard(
    tmp_path,
):
    (
        _,
        suite,
        binding_path,
        _,
        transition,
    ) = _binding_context(tmp_path)

    _, transition = _rewrite_binding(
        binding_path,
        transition,
        lambda binding: binding.__setitem__(
            "source_authority_certificate_bound_by_this_layer",
            True,
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="improperly self-certifies",
    ):
        evidence._validate_protocol_binding(
            binding_path,
            transition,
            suite,
        )


# ============================================================
# HIGH-LEVEL FROZEN-EVIDENCE GATE
# ============================================================


def _patch_high_level_lineage(
    monkeypatch,
    *,
    suite,
    execution,
    binding_path,
):
    monkeypatch.setattr(
        evidence,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda path, verify_reports=True: suite,
    )

    monkeypatch.setattr(
        evidence,
        "validate_visus_authority_execution_provenance",
        lambda path, verify_suite=True: execution,
    )

    monkeypatch.setattr(
        evidence,
        "_transition_summary",
        lambda *args, **kwargs: (
            {"pre_authority_suite": {"suite_fingerprint_sha256": ("9" * 64)}},
            "d" * 64,
        ),
    )

    monkeypatch.setattr(
        evidence,
        "_find_protocol_binding",
        lambda *args, **kwargs: binding_path,
    )

    monkeypatch.setattr(
        evidence,
        "_validate_protocol_binding",
        lambda *args, **kwargs: (
            {
                "protocol_fingerprint_sha256": ("4" * 64),
                "protocol_batch_fingerprint_sha256": ("5" * 64),
            },
            "e" * 64,
        ),
    )


def test_bundle_requires_suite_manifest(
    tmp_path,
):
    root = tmp_path / "bundle"
    root.mkdir()

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing the validation-suite completion manifest",
    ):
        evidence.validate_visus_frozen_evidence_bundle(root)


def test_bundle_requires_execution_manifest(
    tmp_path,
):
    root = tmp_path / "bundle"
    root.mkdir()

    (root / evidence._SUITE_MANIFEST_NAME).write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing raw-execution provenance",
    ):
        evidence.validate_visus_frozen_evidence_bundle(root)


@pytest.mark.parametrize(
    "field",
    [
        "source",
        "protocol",
    ],
)
def test_bundle_requires_source_protocol_objects(
    monkeypatch,
    tmp_path,
    field,
):
    (
        root,
        suite,
        binding_path,
        _,
    ) = _synthetic_bundle(tmp_path)

    execution = _execution_summary()

    suite[field] = None

    _patch_high_level_lineage(
        monkeypatch,
        suite=suite,
        execution=execution,
        binding_path=binding_path,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="suite source/protocol identity is invalid",
    ):
        evidence.validate_visus_frozen_evidence_bundle(root)


def test_bundle_requires_complete_source_fingerprints(
    monkeypatch,
    tmp_path,
):
    (
        root,
        suite,
        binding_path,
        _,
    ) = _synthetic_bundle(tmp_path)

    execution = _execution_summary()

    suite["source"]["source_manifest_fingerprint_sha256"] = "bad"

    _patch_high_level_lineage(
        monkeypatch,
        suite=suite,
        execution=execution,
        binding_path=binding_path,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source fingerprints are incomplete",
    ):
        evidence.validate_visus_frozen_evidence_bundle(root)


def test_bundle_requires_authority_certificate_seal(
    monkeypatch,
    tmp_path,
):
    (
        root,
        suite,
        binding_path,
        _,
    ) = _synthetic_bundle(tmp_path)

    execution = _execution_summary()

    suite["protocol"]["source_authority_certificate_bound"] = False

    _patch_high_level_lineage(
        monkeypatch,
        suite=suite,
        execution=execution,
        binding_path=binding_path,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not sealed to a reviewed authority certificate",
    ):
        evidence.validate_visus_frozen_evidence_bundle(root)


def test_bundle_protocol_authority_identity_guard(
    monkeypatch,
    tmp_path,
):
    (
        root,
        suite,
        binding_path,
        _,
    ) = _synthetic_bundle(tmp_path)

    execution = _execution_summary()

    suite["protocol"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = "0" * 64

    _patch_high_level_lineage(
        monkeypatch,
        suite=suite,
        execution=execution,
        binding_path=binding_path,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="authority fingerprint is inconsistent",
    ):
        evidence.validate_visus_frozen_evidence_bundle(root)


def test_bundle_execution_authority_identity_guard(
    monkeypatch,
    tmp_path,
):
    (
        root,
        suite,
        binding_path,
        _,
    ) = _synthetic_bundle(tmp_path)

    execution = _execution_summary()

    execution[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = "0" * 64

    _patch_high_level_lineage(
        monkeypatch,
        suite=suite,
        execution=execution,
        binding_path=binding_path,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="execution/suite authority fingerprints disagree",
    ):
        evidence.validate_visus_frozen_evidence_bundle(root)
