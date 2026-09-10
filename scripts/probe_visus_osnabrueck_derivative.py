#!/usr/bin/env python3
"""Temporary reconnaissance for the Osnabrueck-converted Kurzhals/VISUS data.

Only structural metadata and cryptographic hashes are emitted. Recovered source
bytes and extracted subtitle payloads remain inside the ephemeral Actions runner.
"""

from __future__ import annotations

import collections
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

SOURCE_PAGE = (
    "https://www.ikw.uni-osnabrueck.de/en/research_groups/computer_vision/"
    "research/interactive_3d_modelling/multimedia_container/wacv17.html"
)
CURRENT_K1_URL = (
    "https://www.ikw.uni-osnabrueck.de/fileadmin/user_upload/computer_vision/"
    "downloads/mm_mkv/Kurzhals/01-car_pursuit_usf.mkv"
)
BUNDLE_URL = "https://w3o.ikw.uni-osnabrueck.de/media/cv/mm_mkv/Kurzhals.zip"
LEGACY_K1_URL = (
    "https://w3o.ikw.uni-osnabrueck.de/media/cv/mm_mkv/Kurzhals/"
    "01-car_pursuit_usf.mkv"
)
OUT = Path("visus_osnabrueck_derivative_probe.json")
DOWNLOAD = Path("01-car_pursuit_usf.mkv")
EBML_MAGIC = bytes.fromhex("1a45dfa3")
ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args), check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def header_blocks(text: str) -> list[str]:
    return [b.strip() for b in re.split(r"\r?\n\r?\n", text) if b.strip()][-6:]


def prefix_probe(url: str, *, insecure: bool) -> dict[str, object]:
    prefix = Path("prefix.bin")
    headers = Path("headers.txt")
    prefix.unlink(missing_ok=True)
    headers.unlink(missing_ok=True)
    args = [
        "curl", "-L", "--fail", "--connect-timeout", "20", "--max-time", "120",
        "--silent", "--show-error", "--range", "0-31", "-D", str(headers),
        "-o", str(prefix),
    ]
    if insecure:
        args.insert(1, "--insecure")
    args.append(url)
    proc = run(*args, check=False)
    raw = prefix.read_bytes() if prefix.exists() else b""
    htext = headers.read_text(encoding="utf-8", errors="replace") if headers.exists() else ""
    result = {
        "url": url,
        "insecure_tls": insecure,
        "curl_exit": proc.returncode,
        "stderr": proc.stderr.strip()[:3000],
        "header_blocks": header_blocks(htext),
        "prefix_bytes_received": len(raw),
        "prefix_hex_32": raw[:32].hex(),
        "ebml_magic": raw.startswith(EBML_MAGIC),
        "zip_magic": raw.startswith(ZIP_MAGICS),
        "html_like": raw.lstrip().lower().startswith((b"<!doctype html", b"<html")),
    }
    prefix.unlink(missing_ok=True)
    headers.unlink(missing_ok=True)
    return result


def download(url: str, *, insecure: bool) -> dict[str, object]:
    DOWNLOAD.unlink(missing_ok=True)
    args = [
        "curl", "-L", "--fail", "--retry", "2", "--retry-all-errors",
        "--connect-timeout", "30", "--max-time", "900", "--silent", "--show-error",
        "-o", str(DOWNLOAD),
    ]
    if insecure:
        args.insert(1, "--insecure")
    args.append(url)
    proc = run(*args, check=False)
    raw4 = DOWNLOAD.read_bytes()[:4] if DOWNLOAD.exists() else b""
    valid_mkv = proc.returncode == 0 and raw4 == EBML_MAGIC
    return {
        "url": url,
        "insecure_tls": insecure,
        "curl_exit": proc.returncode,
        "stderr": proc.stderr.strip()[:4000],
        "bytes": DOWNLOAD.stat().st_size if DOWNLOAD.exists() else 0,
        "sha256": sha256(DOWNLOAD) if DOWNLOAD.exists() else None,
        "ebml_magic": raw4 == EBML_MAGIC,
        "valid_mkv_candidate": valid_mkv,
    }


def summarize_extracted_track(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    tags = collections.Counter(
        m.group(1).lower() for m in re.finditer(r"<\s*/?\s*([A-Za-z_][\w:.-]*)", text)
    )
    attrs = collections.Counter(
        m.group(1).lower() for m in re.finditer(r"\s([A-Za-z_][\w:.-]*)\s*=\s*[\"']", text)
    )
    participant_tokens = sorted(set(re.findall(r"\bP\d{1,3}[A-Z]?\b", text)))
    structural_terms = sorted(
        term
        for term in {
            "x", "y", "gaze", "fixation", "timestamp", "duration", "point",
            "polygon", "rectangle", "comment",
        }
        if term in text.lower()
    )
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "line_count": text.count("\n") + 1,
        "top_tag_names": tags.most_common(30),
        "top_attribute_names": attrs.most_common(40),
        "participant_like_tokens": participant_tokens[:100],
        "participant_like_token_count": len(participant_tokens),
        "structural_terms_present": structural_terms,
    }


def inspect_mkv() -> dict[str, object]:
    if not DOWNLOAD.exists() or DOWNLOAD.read_bytes()[:4] != EBML_MAGIC:
        return {"available": False, "reason": "no EBML-valid MKV recovered"}

    ffprobe = run(
        "ffprobe", "-v", "error", "-count_packets", "-show_format", "-show_streams",
        "-of", "json", str(DOWNLOAD), check=False,
    )
    result: dict[str, object] = {
        "available": True,
        "ffprobe_exit": ffprobe.returncode,
        "ffprobe_stderr": ffprobe.stderr.strip()[:4000],
    }
    if ffprobe.returncode == 0:
        data = json.loads(ffprobe.stdout)
        streams = []
        for stream in data.get("streams", []):
            item = {
                key: stream.get(key)
                for key in (
                    "index", "codec_name", "codec_long_name", "codec_type", "duration",
                    "nb_read_packets", "width", "height", "r_frame_rate", "avg_frame_rate",
                )
                if key in stream
            }
            item["tags"] = stream.get("tags", {})
            streams.append(item)
        result["ffprobe"] = {
            "format": {
                key: data.get("format", {}).get(key)
                for key in ("format_name", "format_long_name", "duration", "size", "bit_rate")
            },
            "streams": streams,
            "stream_type_counts": dict(collections.Counter(s.get("codec_type") for s in streams)),
        }

    mkvmerge_path = shutil.which("mkvmerge")
    mkvextract_path = shutil.which("mkvextract")
    result["mkvtoolnix_available"] = bool(mkvmerge_path and mkvextract_path)
    if not (mkvmerge_path and mkvextract_path):
        return result

    identify = run(mkvmerge_path, "-J", str(DOWNLOAD), check=False)
    result["mkvmerge_exit"] = identify.returncode
    result["mkvmerge_stderr"] = identify.stderr.strip()[:4000]
    if identify.returncode != 0:
        return result

    identified = json.loads(identify.stdout)
    tracks = []
    payloads = []
    for track in identified.get("tracks", []):
        props = track.get("properties", {})
        tracks.append({
            "id": track.get("id"), "type": track.get("type"), "codec": track.get("codec"),
            "codec_id": props.get("codec_id"), "track_name": props.get("track_name"),
            "language": props.get("language"), "default_track": props.get("default_track"),
            "forced_track": props.get("forced_track"),
        })
        if track.get("type") != "subtitles":
            continue
        tid = int(track["id"])
        out = Path(f"track_{tid}.subtitle")
        extracted = run(mkvextract_path, "tracks", str(DOWNLOAD), f"{tid}:{out}", check=False)
        entry: dict[str, object] = {
            "track_id": tid, "extract_exit": extracted.returncode,
            "stderr": extracted.stderr.strip()[:2000],
        }
        if extracted.returncode == 0 and out.exists():
            entry.update(summarize_extracted_track(out))
            out.unlink()
        payloads.append(entry)

    result["mkvmerge"] = {
        "container": identified.get("container", {}),
        "track_count": len(tracks),
        "track_type_counts": dict(collections.Counter(t["type"] for t in tracks)),
        "tracks": tracks,
    }
    result["subtitle_payload_summaries"] = payloads
    return result


def main() -> None:
    current = prefix_probe(CURRENT_K1_URL, insecure=False)
    legacy_k1 = prefix_probe(LEGACY_K1_URL, insecure=True)
    bundle = prefix_probe(BUNDLE_URL, insecure=True)

    chosen_url = None
    chosen_insecure = False
    if legacy_k1["ebml_magic"]:
        chosen_url = LEGACY_K1_URL
        chosen_insecure = True
    elif current["ebml_magic"]:
        chosen_url = CURRENT_K1_URL

    report: dict[str, object] = {
        "schema": "gazeforge.visus_osnabrueck_derivative_probe.v2",
        "scope": {
            "dataset": "Kurzhals et al. 2014 VISUS benchmark",
            "scenario": "K1 / 01-car pursuit",
            "variant": "USF lossless multimedia-container derivative",
            "source_page": SOURCE_PAGE,
            "legacy_k1_url_derivation": (
                "published Kurzhals.zip namespace plus the exact individual filename linked on source page"
            ),
            "rights_promotion_authorized": False,
            "empirical_promotion_authorized": False,
            "redistribution_authorized": False,
        },
        "prefix_probes": {"current_k1": current, "legacy_k1": legacy_k1, "legacy_bundle": bundle},
        "selected_binary_url": chosen_url,
    }
    if chosen_url:
        report["download"] = download(chosen_url, insecure=chosen_insecure)
        report["inspection"] = inspect_mkv()
    else:
        report["download"] = None
        report["inspection"] = {"available": False, "reason": "no MKV magic at reviewed candidates"}
    report["claim_boundary"] = {
        "institutional_derivative_candidate_only": True,
        "insecure_tls_retrieval_is_authority_evidence": False,
        "original_visus_copy_proven": False,
        "complete_25_participant_corpus_proven": False,
        "annotation_identity_proven": False,
        "analysis_rights_proven": False,
        "redistribution_rights_proven": False,
        "frozen_evidence_promoted": False,
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
