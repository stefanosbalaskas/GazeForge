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
    / "brand-gp3-device-validation-evidence-v1.json"
)


def test_brand_gp3_device_validation_evidence_is_integrity_checked_and_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    observed = payload.pop("evidence_fingerprint_sha256")
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest() == observed

    assert payload["review_status"] == "published_device_validation_not_event_ground_truth"
    boundary = payload["scientific_boundary"]
    assert boundary["published_gp3_device_validation_recovered"] is True
    assert boundary["collection_specific_sampling_characterized_in_publication"] is True
    assert boundary["independent_manual_event_labels_verified"] is False
    assert boundary["samplewise_fixation_saccade_ground_truth_verified"] is False
    assert boundary["mouse_click_behavioral_reference_is_event_ground_truth"] is False
    assert boundary["empirical_native_event_benchmark_eligible"] is False
    assert boundary["approved_for_public_frozen_evidence"] is False
    assert boundary["gp3_event_classifier_validity_created"] is False
    assert boundary["performance_claim_for_gazeforge_created"] is False

    source = payload["source"]
    assert source["doi"] == "10.3758/s13428-020-01504-2"
    observations = source["study_observations"]
    assert observations["published_visual_search_reference"] == (
        "mouse click indicating target observation"
    )
    assert observations["fixation_detection"].startswith("R saccades package")

    assert "report_fingerprint_sha256" not in payload
    assert not all(key in payload for key in ("benchmark", "model", "protocol", "metrics"))
