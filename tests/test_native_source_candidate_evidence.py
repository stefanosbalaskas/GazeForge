from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "validation"
    / "evidence"
    / "native-source-recheck"
    / "notaro-gp3-source-candidate-evidence-v1.json"
)


def test_notaro_gp3_candidate_evidence_is_integrity_checked_and_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    observed = payload.pop("evidence_fingerprint_sha256")
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest() == observed

    assert payload["review_status"] == "candidate_source_only_not_native_validation_evidence"
    boundary = payload["scientific_boundary"]
    assert boundary["real_gp3_source_candidate_recovered"] is True
    assert boundary["native_60hz_rate_verified"] is False
    assert boundary["expert_labelled_native_corpus_verified"] is False
    assert boundary["empirical_native_benchmark_eligible"] is False
    assert boundary["approved_for_public_frozen_evidence"] is False
    assert boundary["gp3_validity_created"] is False
    assert boundary["performance_claim_created"] is False

    assert "report_fingerprint_sha256" not in payload
    assert not all(key in payload for key in ("benchmark", "model", "protocol", "metrics"))
