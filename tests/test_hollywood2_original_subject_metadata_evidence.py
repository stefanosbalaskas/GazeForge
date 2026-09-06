import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_original_subject_metadata import (
    DESCRIPTION_URL,
    LICENSE_URL,
    build_probe_record,
)
from gazeforge.hollywood2_original_subject_metadata_evidence import (
    ADVERTISED_ARCHIVE_URL,
    LOGIN_URL,
    validate_hollywood2_original_subject_evidence,
    validate_hollywood2_original_subject_live_probe,
)

EVIDENCE = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-original-subject-metadata-evidence-v1.json"
)


def _fetch(body: bytes, *, url: str) -> dict:
    return {
        "requested_url": url,
        "final_url": url,
        "http_status": 200,
        "content_type": "text/html; charset=utf-8",
        "content_length": str(len(body)),
        "content_disposition": None,
        "body": body,
    }


DESCRIPTION = b"""
<html><body>
<p>We have collected data from 16 human volunteers.</p>
<p>We split them into an active group and a free-viewing group.</p>
<p>There were 12 active subjects and 4 free viewing subjects.</p>
<p>The active group had to solve an action recognition task.</p>
<p>The free-viewing group was not required to solve any specific task.</p>
<p>Sampling frequency 500Hz.</p>
<a href="http://vision.imar.ro/eyetracking/getdata.php?\
filepath=data&amp;filename=gaze_hollywood2.zip">
Hollywood-2 gaze data (1.8Gib)</a>
</body></html>
"""

LICENSE = b"""
<html><body>
GRANT OF LICENCE FREE OF CHARGE FOR ACADEMIC USE ONLY.
Provided you send the request from an academic address, you are granted a limited,
non-exclusive, non-assignable and non-transferable license. You may not sub-license
or transfer the dataset. It is your responsibility to seek prior written permission.
</body></html>
"""


def _current_probe() -> dict:
    return build_probe_record(
        _fetch(DESCRIPTION, url=DESCRIPTION_URL),
        _fetch(LICENSE, url=LICENSE_URL),
        data_link_head={
            "requested_url": ADVERTISED_ARCHIVE_URL,
            "final_url": LOGIN_URL,
            "http_status": 200,
            "content_type": "text/html; charset=utf-8",
            "content_length": "2889",
            "content_disposition": None,
        },
    )


def _refingerprint(probe: dict) -> dict:
    from gazeforge.hollywood2_original_subject_metadata import probe_fingerprint

    probe["probe_fingerprint_sha256"] = probe_fingerprint(probe)
    return probe


def test_frozen_original_subject_metadata_evidence_validates():
    record = validate_hollywood2_original_subject_evidence(EVIDENCE)
    assert record["rights_boundary"]["public_license_page_observed"] is True
    assert record["mapping_boundary"]["participant_identity_mapping_verified"] is False
    assert record["scientific_boundary"]["source_audit_ready"] is False


def test_frozen_original_subject_metadata_rejects_mapping_promotion():
    record = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    record["mapping_boundary"]["gin_token_to_task_group_verified"] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_original_subject_evidence(record)


def test_current_login_gated_public_semantics_pass():
    validate_hollywood2_original_subject_live_probe(_current_probe(), EVIDENCE)


def test_direct_archive_route_triggers_manual_review():
    probe = _current_probe()
    probe["advertised_data_link_head"]["final_url"] = ADVERTISED_ARCHIVE_URL
    probe["advertised_data_link_head"]["content_type"] = "application/zip"
    probe["advertised_data_link_head"]["content_disposition"] = (
        'attachment; filename="gaze_hollywood2.zip"'
    )
    _refingerprint(probe)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_original_subject_live_probe(probe, EVIDENCE)


def test_public_readme_surface_triggers_manual_review():
    description = DESCRIPTION.replace(
        b"</body>",
        b'<a href="README.txt">README subject IDs</a></body>',
    )
    probe = build_probe_record(
        _fetch(description, url=DESCRIPTION_URL),
        _fetch(LICENSE, url=LICENSE_URL),
        data_link_head={
            "requested_url": ADVERTISED_ARCHIVE_URL,
            "final_url": LOGIN_URL,
            "http_status": 200,
            "content_type": "text/html; charset=utf-8",
            "content_length": "2889",
            "content_disposition": None,
        },
    )
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_original_subject_live_probe(probe, EVIDENCE)


def test_revised_license_terms_fail_closed():
    probe = build_probe_record(
        _fetch(DESCRIPTION, url=DESCRIPTION_URL),
        _fetch(
            LICENSE.replace(b"ACADEMIC USE ONLY", b"general public use"),
            url=LICENSE_URL,
        ),
        data_link_head={
            "requested_url": ADVERTISED_ARCHIVE_URL,
            "final_url": LOGIN_URL,
            "http_status": 200,
            "content_type": "text/html; charset=utf-8",
            "content_length": "2889",
            "content_disposition": None,
        },
    )
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_original_subject_live_probe(probe, EVIDENCE)


def test_fresh_probe_rejects_participant_mapping_promotion():
    probe = copy.deepcopy(_current_probe())
    probe["mapping_boundary"]["participant_identity_mapping_verified"] = True
    _refingerprint(probe)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_original_subject_live_probe(probe, EVIDENCE)
