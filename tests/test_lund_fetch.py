import json

import pytest

from gazeforge import lund_fetch
from gazeforge.exceptions import BenchmarkIntegrityError


def _entry(name, payload):
    return {
        "name": name,
        "type": "file",
        "sha": lund_fetch._git_blob_sha1(payload),
        "size": len(payload),
        "download_url": "https://raw.githubusercontent.com/example/repo/pinned/" + name,
    }


def _fetched_checkout(monkeypatch, tmp_path, payload=b"verified-matlab"):
    entry = _entry("P01_trial1_labelled_RA.mat", payload)
    monkeypatch.setattr(lund_fetch, "_selected_entries", lambda **kwargs: [("dots", entry)])
    monkeypatch.setattr(lund_fetch, "_request_bytes", lambda url: payload)
    return lund_fetch.fetch_lund2013_dataset(tmp_path, annotators=("RA",))


def _rewrite_manifest(path, manifest):
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_fetch_lund2013_writes_verified_files_and_manifest(monkeypatch, tmp_path):
    ra = b"ra-matlab-bytes"
    mn = b"mn-matlab-bytes"
    entries = [
        ("dots", _entry("P01_trial1_labelled_RA.mat", ra)),
        ("dots", _entry("P01_trial1_labelled_MN.mat", mn)),
    ]
    monkeypatch.setattr(lund_fetch, "_selected_entries", lambda **kwargs: entries)
    payloads = {
        entries[0][1]["download_url"]: ra,
        entries[1][1]["download_url"]: mn,
    }
    monkeypatch.setattr(lund_fetch, "_request_bytes", lambda url: payloads[url])

    result = lund_fetch.fetch_lund2013_dataset(tmp_path)

    assert len(result.files) == 2
    assert (tmp_path / "dots" / "P01_trial1_labelled_RA.mat").read_bytes() == ra
    assert (tmp_path / "dots" / "P01_trial1_labelled_MN.mat").read_bytes() == mn
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["commit"] == lund_fetch.LUND2013_COMMIT
    assert manifest["file_count"] == 2
    assert manifest["bundled_by_gazeforge"] is False
    assert manifest["manifest_fingerprint_sha256"] == result.manifest_fingerprint_sha256


def test_fetch_reuses_existing_file_only_when_blob_identity_matches(monkeypatch, tmp_path):
    payload = b"verified"
    entry = _entry("P01_trial1_labelled_RA.mat", payload)
    monkeypatch.setattr(lund_fetch, "_selected_entries", lambda **kwargs: [("dots", entry)])
    monkeypatch.setattr(
        lund_fetch,
        "_request_bytes",
        lambda url: pytest.fail("verified existing file should not be downloaded"),
    )
    target = tmp_path / "dots" / entry["name"]
    target.parent.mkdir(parents=True)
    target.write_bytes(payload)

    result = lund_fetch.fetch_lund2013_dataset(tmp_path, annotators=("RA",))

    assert result.files == (target,)


def test_fetch_rejects_modified_existing_file_without_overwrite(monkeypatch, tmp_path):
    payload = b"expected"
    entry = _entry("P01_trial1_labelled_RA.mat", payload)
    monkeypatch.setattr(lund_fetch, "_selected_entries", lambda **kwargs: [("dots", entry)])
    target = tmp_path / "dots" / entry["name"]
    target.parent.mkdir(parents=True)
    target.write_bytes(b"modified")

    with pytest.raises(BenchmarkIntegrityError, match="Git blob SHA mismatch"):
        lund_fetch.fetch_lund2013_dataset(tmp_path, annotators=("RA",))


def test_fetch_overwrite_replaces_modified_file_with_verified_upstream(monkeypatch, tmp_path):
    payload = b"expected"
    entry = _entry("P01_trial1_labelled_RA.mat", payload)
    monkeypatch.setattr(lund_fetch, "_selected_entries", lambda **kwargs: [("dots", entry)])
    monkeypatch.setattr(lund_fetch, "_request_bytes", lambda url: payload)
    target = tmp_path / "dots" / entry["name"]
    target.parent.mkdir(parents=True)
    target.write_bytes(b"modified")

    lund_fetch.fetch_lund2013_dataset(tmp_path, annotators=("RA",), overwrite=True)

    assert target.read_bytes() == payload


def test_request_bytes_rejects_unexpected_download_host():
    with pytest.raises(BenchmarkIntegrityError, match="raw.githubusercontent.com"):
        lund_fetch._request_bytes("https://example.com/file.mat")


def test_fetch_rejects_unknown_annotator_before_network_access(tmp_path):
    with pytest.raises(ValueError, match="Unknown Lund2013 annotators"):
        lund_fetch.fetch_lund2013_dataset(tmp_path, annotators=("UNKNOWN",))


def test_manifest_fingerprint_is_deterministic():
    payload = {"b": 2, "a": [1, 3]}
    assert lund_fetch._manifest_fingerprint(payload) == lund_fetch._manifest_fingerprint(
        {"a": [1, 3], "b": 2}
    )


def test_source_manifest_is_optional_for_user_managed_checkout(tmp_path):
    assert lund_fetch.validate_lund2013_source_manifest(tmp_path) is None


def test_source_manifest_validation_returns_verified_provenance(monkeypatch, tmp_path):
    fetched = _fetched_checkout(monkeypatch, tmp_path)

    provenance = lund_fetch.validate_lund2013_source_manifest(tmp_path)

    assert provenance is not None
    assert provenance["commit"] == lund_fetch.LUND2013_COMMIT
    assert provenance["file_count"] == 1
    assert provenance["manifest_fingerprint_sha256"] == fetched.manifest_fingerprint_sha256
    assert provenance["files_verified_at_run"] is True


def test_source_manifest_rejects_tampering_without_recomputed_fingerprint(monkeypatch, tmp_path):
    fetched = _fetched_checkout(monkeypatch, tmp_path)
    manifest = dict(fetched.manifest)
    manifest["commit"] = "0" * 40
    _rewrite_manifest(fetched.manifest_path, manifest)

    with pytest.raises(BenchmarkIntegrityError, match="fingerprint mismatch"):
        lund_fetch.validate_lund2013_source_manifest(tmp_path)


def test_source_manifest_rejects_wrong_commit_even_with_valid_fingerprint(monkeypatch, tmp_path):
    fetched = _fetched_checkout(monkeypatch, tmp_path)
    manifest = dict(fetched.manifest)
    manifest["commit"] = "0" * 40
    body = {key: value for key, value in manifest.items() if key != "manifest_fingerprint_sha256"}
    manifest["manifest_fingerprint_sha256"] = lund_fetch._manifest_fingerprint(body)
    _rewrite_manifest(fetched.manifest_path, manifest)

    with pytest.raises(BenchmarkIntegrityError, match="commit does not match"):
        lund_fetch.validate_lund2013_source_manifest(tmp_path)


def test_source_manifest_rechecks_file_identity_at_benchmark_time(monkeypatch, tmp_path):
    fetched = _fetched_checkout(monkeypatch, tmp_path, payload=b"verified-matlab")
    fetched.files[0].write_bytes(b"modified-matlab")

    with pytest.raises(BenchmarkIntegrityError, match="Git blob SHA mismatch"):
        lund_fetch.validate_lund2013_source_manifest(tmp_path)
