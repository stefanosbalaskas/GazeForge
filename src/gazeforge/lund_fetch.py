"""Explicit pinned fetcher for the external Lund2013 benchmark files."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from .exceptions import BenchmarkIntegrityError

LUND2013_REPOSITORY = "richardandersson/EyeMovementDetectorEvaluation"
LUND2013_COMMIT = "3e12416ab3fd6254c81811cf03f8e5d67c5d7129"
LUND2013_DATA_PATH = "annotated_data/data used in the article"
LUND2013_FAMILIES = ("dots", "img", "video")
LUND2013_ANNOTATORS = ("RA", "MN")
_MANIFEST_NAME = "_gazeforge_source_manifest.json"
_USER_AGENT = "GazeForge-Lund2013-fetcher/0.1"


@dataclass(slots=True)
class Lund2013FetchResult:
    """Local checkout metadata returned by :func:`fetch_lund2013_dataset`."""

    root: Path
    files: tuple[Path, ...]
    manifest_path: Path
    manifest: dict[str, Any]
    manifest_fingerprint_sha256: str


def _request_json(url: str) -> Any:
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=60) as response:  # noqa: S310 - pinned HTTPS GitHub endpoint
        return json.loads(response.read().decode("utf-8"))


def _request_bytes(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "raw.githubusercontent.com":
        raise BenchmarkIntegrityError(
            "Lund2013 download URL is not an expected raw.githubusercontent.com HTTPS URL."
        )
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(request, timeout=120) as response:  # noqa: S310 - validated HTTPS host
        return response.read()


def _git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _manifest_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _validate_selection(
    annotators: tuple[str, ...],
    stimulus_families: tuple[str, ...],
) -> None:
    unknown_annotators = sorted(set(annotators) - set(LUND2013_ANNOTATORS))
    if unknown_annotators:
        raise ValueError(f"Unknown Lund2013 annotators: {unknown_annotators}")
    unknown_families = sorted(set(stimulus_families) - set(LUND2013_FAMILIES))
    if unknown_families:
        raise ValueError(f"Unknown Lund2013 stimulus families: {unknown_families}")
    if not annotators:
        raise ValueError("At least one Lund2013 annotator must be selected.")
    if not stimulus_families:
        raise ValueError("At least one Lund2013 stimulus family must be selected.")


def _family_entries(family: str) -> list[dict[str, Any]]:
    path = quote(f"{LUND2013_DATA_PATH}/{family}", safe="/")
    url = (
        f"https://api.github.com/repos/{LUND2013_REPOSITORY}/contents/{path}"
        f"?ref={LUND2013_COMMIT}"
    )
    payload = _request_json(url)
    if not isinstance(payload, list):
        raise BenchmarkIntegrityError(
            f"Unexpected GitHub response while listing Lund2013 family {family!r}."
        )
    return [entry for entry in payload if isinstance(entry, dict)]


def _selected_entries(
    *,
    annotators: tuple[str, ...],
    stimulus_families: tuple[str, ...],
) -> list[tuple[str, dict[str, Any]]]:
    selected: list[tuple[str, dict[str, Any]]] = []
    for family in stimulus_families:
        for entry in _family_entries(family):
            name = str(entry.get("name", ""))
            if entry.get("type") != "file" or not name.endswith(".mat"):
                continue
            if not any(name.endswith(f"_labelled_{annotator}.mat") for annotator in annotators):
                continue
            selected.append((family, entry))
    if not selected:
        raise BenchmarkIntegrityError("No labelled Lund2013 MATLAB files matched the selection.")
    return sorted(selected, key=lambda value: (value[0], str(value[1].get("name", ""))))


def _verified_payload(entry: dict[str, Any], *, existing: bytes | None = None) -> bytes:
    expected_sha = str(entry.get("sha", ""))
    expected_size = entry.get("size")
    payload = existing
    if payload is None:
        url = entry.get("download_url")
        if not isinstance(url, str) or not url:
            raise BenchmarkIntegrityError("Lund2013 file metadata is missing download_url.")
        payload = _request_bytes(url)
    observed_sha = _git_blob_sha1(payload)
    if not expected_sha or observed_sha != expected_sha:
        raise BenchmarkIntegrityError(
            f"Lund2013 Git blob SHA mismatch for {entry.get('name', '<unknown>')!r}."
        )
    if expected_size is not None and len(payload) != int(expected_size):
        raise BenchmarkIntegrityError(
            f"Lund2013 byte-size mismatch for {entry.get('name', '<unknown>')!r}."
        )
    return payload


def _manifest_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "repository": str(manifest["repository"]),
        "commit": str(manifest["commit"]),
        "data_path": str(manifest["data_path"]),
        "annotators": list(manifest.get("annotators", [])),
        "stimulus_families": list(manifest.get("stimulus_families", [])),
        "file_count": int(manifest["file_count"]),
        "manifest_fingerprint_sha256": str(manifest["manifest_fingerprint_sha256"]),
        "files_verified_at_run": True,
    }


def validate_lund2013_source_manifest(
    root: str | Path,
    *,
    verify_files: bool = True,
) -> dict[str, Any] | None:
    """Validate a GazeForge Lund source manifest and optionally every referenced local file.

    Directories without a GazeForge source manifest remain supported and return ``None``. Once a
    manifest exists, however, it is treated as an integrity claim: its own fingerprint, pinned
    upstream identity, file inventory, and (by default) every referenced MATLAB file must validate
    before the checkout may be recorded as verified benchmark provenance.
    """
    root_path = Path(root)
    manifest_path = root_path / _MANIFEST_NAME
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkIntegrityError("Lund2013 source manifest is not valid JSON.") from exc
    if not isinstance(manifest, dict):
        raise BenchmarkIntegrityError("Lund2013 source manifest must be a JSON object.")

    required = {
        "dataset",
        "repository",
        "commit",
        "data_path",
        "file_count",
        "files",
        "manifest_fingerprint_sha256",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise BenchmarkIntegrityError(f"Lund2013 source manifest is missing fields: {missing}")

    claimed_fingerprint = str(manifest["manifest_fingerprint_sha256"])
    body = {key: value for key, value in manifest.items() if key != "manifest_fingerprint_sha256"}
    observed_fingerprint = _manifest_fingerprint(body)
    if claimed_fingerprint != observed_fingerprint:
        raise BenchmarkIntegrityError("Lund2013 source manifest fingerprint mismatch.")
    if manifest["dataset"] != "Lund2013":
        raise BenchmarkIntegrityError("Source manifest does not identify the Lund2013 dataset.")
    if manifest["repository"] != LUND2013_REPOSITORY:
        raise BenchmarkIntegrityError("Lund2013 source manifest repository does not match the pin.")
    if manifest["commit"] != LUND2013_COMMIT:
        raise BenchmarkIntegrityError("Lund2013 source manifest commit does not match the pin.")
    if manifest["data_path"] != LUND2013_DATA_PATH:
        raise BenchmarkIntegrityError("Lund2013 source manifest data path does not match the pin.")

    records = manifest["files"]
    if not isinstance(records, list):
        raise BenchmarkIntegrityError("Lund2013 source manifest files must be a list.")
    if int(manifest["file_count"]) != len(records):
        raise BenchmarkIntegrityError("Lund2013 source manifest file_count does not match files.")

    if verify_files:
        resolved_root = root_path.resolve()
        for record in records:
            if not isinstance(record, dict):
                raise BenchmarkIntegrityError("Lund2013 source manifest contains an invalid file row.")
            relative = Path(str(record.get("relative_path", "")))
            if not relative.parts or relative.is_absolute() or ".." in relative.parts:
                raise BenchmarkIntegrityError("Lund2013 source manifest contains an unsafe path.")
            local_path = (root_path / relative).resolve()
            if local_path != resolved_root and resolved_root not in local_path.parents:
                raise BenchmarkIntegrityError("Lund2013 source manifest path escapes the checkout.")
            if not local_path.is_file():
                raise BenchmarkIntegrityError(f"Lund2013 source file is missing: {relative.as_posix()}")
            payload = local_path.read_bytes()
            expected_size = int(record.get("size_bytes", -1))
            if len(payload) != expected_size:
                raise BenchmarkIntegrityError(
                    f"Lund2013 source file byte-size mismatch: {relative.as_posix()}"
                )
            expected_sha = str(record.get("git_blob_sha1", ""))
            if _git_blob_sha1(payload) != expected_sha:
                raise BenchmarkIntegrityError(
                    f"Lund2013 source file Git blob SHA mismatch: {relative.as_posix()}"
                )

    return _manifest_summary(manifest)


def fetch_lund2013_dataset(
    destination: str | Path,
    *,
    annotators: tuple[str, ...] = LUND2013_ANNOTATORS,
    stimulus_families: tuple[str, ...] = LUND2013_FAMILIES,
    overwrite: bool = False,
) -> Lund2013FetchResult:
    """Fetch the pinned external Lund2013 labelled files into a local directory.

    This operation is explicit and opt-in. Raw benchmark files remain external to GazeForge and
    retain the upstream repository licence. Existing files are reused only when their Git blob SHA
    matches the immutable upstream metadata; mismatching files are never silently replaced unless
    ``overwrite=True`` is requested.
    """
    annotators = tuple(dict.fromkeys(str(value).upper() for value in annotators))
    stimulus_families = tuple(dict.fromkeys(str(value).lower() for value in stimulus_families))
    _validate_selection(annotators, stimulus_families)

    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    local_files: list[Path] = []

    for family, entry in _selected_entries(
        annotators=annotators,
        stimulus_families=stimulus_families,
    ):
        name = str(entry["name"])
        target = root / family / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not overwrite:
            payload = _verified_payload(entry, existing=target.read_bytes())
        else:
            payload = _verified_payload(entry)
            temporary = target.with_suffix(target.suffix + ".tmp")
            temporary.write_bytes(payload)
            temporary.replace(target)

        annotator = next(
            value for value in annotators if name.endswith(f"_labelled_{value}.mat")
        )
        local_files.append(target)
        records.append(
            {
                "relative_path": target.relative_to(root).as_posix(),
                "stimulus_family": family,
                "annotator": annotator,
                "git_blob_sha1": str(entry["sha"]),
                "size_bytes": len(payload),
            }
        )

    manifest_body: dict[str, Any] = {
        "dataset": "Lund2013",
        "repository": LUND2013_REPOSITORY,
        "commit": LUND2013_COMMIT,
        "data_path": LUND2013_DATA_PATH,
        "repository_license": "GPL-3.0",
        "bundled_by_gazeforge": False,
        "annotators": list(annotators),
        "stimulus_families": list(stimulus_families),
        "file_count": len(records),
        "files": records,
    }
    fingerprint = _manifest_fingerprint(manifest_body)
    manifest = {
        **manifest_body,
        "manifest_fingerprint_sha256": fingerprint,
    }
    manifest_path = root / _MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return Lund2013FetchResult(
        root=root,
        files=tuple(local_files),
        manifest_path=manifest_path,
        manifest=manifest,
        manifest_fingerprint_sha256=fingerprint,
    )
