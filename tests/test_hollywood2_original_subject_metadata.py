from gazeforge.hollywood2_original_subject_metadata import build_probe_record


def _fetch(body: bytes, *, url: str, status: int = 200, content_type: str = "text/html"):
    return {
        "requested_url": url,
        "final_url": url,
        "http_status": status,
        "content_type": content_type,
        "content_length": str(len(body)),
        "content_disposition": None,
        "body": body,
    }


def test_public_subject_counts_never_become_identity_mapping():
    description = b"""
    <html><body>
    <p>We have collected data from 16 human volunteers.</p>
    <p>We split them into an active group and a free-viewing group.</p>
    <p>There were 12 active subjects and 4 free viewing subjects.</p>
    <p>The active group had to solve an action recognition task.</p>
    <p>The free-viewing group was not required to solve any specific task.</p>
    <p>Sampling frequency 500Hz.</p>
    <a href="data/hollywood2.tar.gz">Hollywood-2 gaze data (1.8Gib)</a>
    </body></html>
    """
    license_page = b"""
    <html><body>
    GRANT OF LICENCE FREE OF CHARGE FOR ACADEMIC USE ONLY.
    Provided you send the request from an academic address, you are granted a limited,
    non-exclusive, non-assignable and non-transferable license. You may not sub-license
    or transfer the dataset. It is your responsibility to seek prior written permission.
    </body></html>
    """
    record = build_probe_record(
        _fetch(description, url="https://example.test/description.php"),
        _fetch(license_page, url="https://example.test/license.php"),
        data_link_head={
            "requested_url": "https://example.test/data/hollywood2.tar.gz",
            "final_url": "https://example.test/data/hollywood2.tar.gz",
            "http_status": 200,
            "content_type": "application/gzip",
            "content_length": "123",
            "content_disposition": None,
        },
    )
    context = record["observed_subject_context"]
    mapping = record["mapping_boundary"]
    rights = record["rights_boundary"]
    assert context["public_page_states_sixteen_volunteers"] is True
    assert context["public_page_states_twelve_active_subjects"] is True
    assert context["public_page_states_four_free_viewing_subjects"] is True
    assert context["advertised_hollywood2_data_link_count"] == 1
    assert mapping["participant_identity_mapping_verified"] is False
    assert mapping["gin_token_to_original_subject_id_verified"] is False
    assert rights["dataset_archive_download_performed"] is False
    assert rights["dataset_use_authorized_by_this_probe"] is False


def test_public_readme_or_extra_links_do_not_promote_mapping():
    description = b"""
    <html><body>
    <a href="README.txt">README</a>
    <a href="data.tar.gz">Hollywood-2 gaze data</a>
    </body></html>
    """
    record = build_probe_record(
        _fetch(description, url="https://example.test/description.php"),
        _fetch(b"academic use only", url="https://example.test/license.php"),
    )
    assert record["description"]["markers"]["public_readme_link_present"] is True
    assert (
        record["mapping_boundary"]["original_subject_ids_recovered_from_public_metadata"]
        is False
    )


def test_failed_public_fetch_stays_fail_closed():
    record = build_probe_record(
        _fetch(b"forbidden", url="https://example.test/description.php", status=403),
        _fetch(b"forbidden", url="https://example.test/license.php", status=403),
    )
    assert record["rights_boundary"]["public_license_page_observed"] is False
    assert record["mapping_boundary"]["participant_identity_mapping_verified"] is False
    assert record["scientific_boundary"]["source_audit_ready"] is False
