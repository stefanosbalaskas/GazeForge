from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path("scripts/hollywood2_gin_resilient_probe.py")
EVIDENCE = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-gin-host-availability-change-evidence-v1.json"
)
EXPECTED_EVIDENCE_FINGERPRINT = (
    "bea40ad7dd6b8b7fb056fc1fd4a221c00654c2405edae92c33a4059d6c1e1e8f"
)


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("hollywood2_gin_resilient_probe", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _evidence_fingerprint(record: dict) -> str:
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def test_resilient_probe_builds_fingerprinted_403_record() -> None:
    module = _load_script()
    diagnostic = (
        "fatal: unable to access "
        "'https://gin.g-node.org/ioannis.agtzidis/hollywood2_em/': "
        "The requested URL returned error: 403"
    )
    result = subprocess.CompletedProcess(
        args=["python", "scripts/hollywood2_gin_live_probe.py"],
        returncode=128,
        stdout="",
        stderr=f"Traceback text that must not be embedded\n{diagnostic}\n",
    )
    record = module.build_failure_record(
        repository=module.REPOSITORY,
        attempt=5,
        result=result,
    )
    assert record["record_type"] == "hollywood2-gin-live-probe-unavailable-v1"
    assert record["status"] == "canonical_repository_route_unavailable"
    assert record["attempt"] == 5
    assert record["child_probe"]["failure_class"] == "http_forbidden"
    assert record["child_probe"]["http_status"] == 403
    assert record["child_probe"]["returncode"] == 128
    assert record["child_probe"]["diagnostic_sha256"] == hashlib.sha256(
        diagnostic.encode()
    ).hexdigest()
    assert record["probe_fingerprint_sha256"] == module.probe_fingerprint(record)
    serialized = json.dumps(record)
    assert "Traceback text that must not be embedded" not in serialized


@pytest.mark.parametrize(
    ("diagnostic", "expected_class", "expected_status"),
    [
        ("fatal: unable to access url: The requested URL returned error: 404", "http_not_found", 404),
        ("fatal: unable to access url: Could not resolve host: gin.g-node.org", "dns_resolution_failure", None),
        ("fatal: unable to access url: Connection refused", "connection_failure", None),
        ("fatal: remote operation timed out", "network_timeout", None),
        ("fatal: unexpected transport error", "git_remote_failure", None),
    ],
)
def test_resilient_probe_failure_classification(
    diagnostic: str,
    expected_class: str,
    expected_status: int | None,
) -> None:
    module = _load_script()
    assert module._failure_class(diagnostic) == (expected_class, expected_status)


def test_resilient_probe_failure_record_cannot_promote_scientific_claims() -> None:
    module = _load_script()
    result = subprocess.CompletedProcess(
        args=["python"],
        returncode=128,
        stdout="",
        stderr="fatal: unable to access url: The requested URL returned error: 403\n",
    )
    record = module.build_failure_record(
        repository=module.REPOSITORY,
        attempt=1,
        result=result,
    )
    boundary = record["scientific_boundary"]
    assert boundary["authoritative_repository_revision_resolved_in_this_attempt"] is False
    assert boundary["source_identity_invalidated"] is False
    assert boundary["dataset_license_verified"] is False
    assert boundary["analysis_use_authorized"] is False
    assert boundary["raw_data_redistribution_authorized"] is False
    assert boundary["participant_identity_mapping_verified"] is False
    assert boundary["participant_disjoint_model_validation_created"] is False
    assert boundary["cross_dataset_validation_created"] is False
    assert boundary["new_frozen_evidence_performance_claim_created"] is False
    assert boundary["native_60hz_or_gp3_validity_created"] is False
    assert boundary["scientific_reproduction_failure_inferred"] is False


def test_committed_host_availability_change_evidence_is_frozen() -> None:
    record = _evidence()
    assert record["record_type"] == "hollywood2-gin-host-availability-change-evidence-v1"
    assert record["checked_on"] == "2026-09-09"
    assert record["canonical_repository"]["exact_main_sha"] == (
        "54c190af288a7062db6c294a037dc1f4d4924abc"
    )
    assert record["live_probe_observations"]["workflow_run_id"] == 34401272377
    attempts = record["live_probe_observations"]["workflow_attempts"]
    assert [(item["run_attempt"], item["terminal_http_status"]) for item in attempts] == [
        (1, 403),
        (2, 403),
    ]
    assert all(item["all_bounded_git_attempts_returned_same_http_status"] for item in attempts)
    assert all(item["structured_probe_artifact_uploaded"] is False for item in attempts)
    context = record["same_sha_reproduction_context"]
    assert context["source_token_validation_run_id"] == 34401272530
    assert context["empirical_pinned_source_acquisition_succeeded"] is True
    assert context["empirical_derived_60hz_comparison_succeeded"] is True
    interpretation = record["availability_interpretation"]
    assert interpretation["global_gin_outage_inferred"] is False
    assert interpretation["scientific_reproduction_failure_inferred"] is False
    assert interpretation["dedicated_live_probe_certified_green"] is False
    assert _evidence_fingerprint(record) == EXPECTED_EVIDENCE_FINGERPRINT
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT
