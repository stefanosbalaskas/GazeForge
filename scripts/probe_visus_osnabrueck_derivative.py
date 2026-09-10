#!/usr/bin/env python3
"""Temporary reconnaissance for the Osnabrueck-converted Kurzhals/VISUS MKV.

The script downloads one institutional USF container into the ephemeral Actions
workspace, fingerprints and inspects it, and emits only structural metadata and
hashes. Source bytes and extracted subtitle payloads are never uploaded.
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
K1_USF_URL = (
    "https://www.ikw.uni-osnabrueck.de/fileadmin/user_upload/computer_vision/"
    "downloads/mm_mkv/Kurzhals/01-car_pursuit_usf.mkv"
)
BUNDLE_URL = "https://w3o.ikw.uni-osnabrueck.de/media/cv/mm_mkv/Kurzhals.zip"
OUT = Path("visus_osnabrueck_derivative_probe.json")
DOWNLOAD = Path("01-car_pursuit_usf.mkv")


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def head_probe(url: str) -> dict[str, object]:
    proc = run(
        "curl",
        "-L",
        "-I",
        "--connect-timeout",
        "20",
        "--max-time",
        "90",
        "--silent",
        "--show-error",
        url,
        check=False,
    )
    blocks = [b.strip() for b in re.split(r"\r?\n\r?\n", proc.stdout) if b.strip()]
    return {
        "url": url,
        "curl_exit": proc.returncode,
        "header_blocks": blocks[-4:],
        "stderr": proc.stderr.strip()[:2000],
    }


def download_k1() -> dict[str, object]:
    proc = run(
        "curl",
        "-L",
        "--fail",
        "--retry",
        "2",
        "--retry-all-errors",
        "--connect-timeout",
        "30",
        "--max-time",
        "900",
        "--silent",
        "--show-error",
        "-o",
        str(DOWNLOAD),
        K1_USF_URL,
        check=False,
    )
    ok = proc.returncode == 0 and DOWNLOAD.exists() and DOWNLOAD.stat().st_size > 0
    return {
        "url": K1_USF_URL,
        "curl_exit": proc.returncode,
        "stderr": proc.stderr.strip()[:4000],
        "downloaded": ok,
        "bytes": DOWNLOAD.stat().st_size if ok else 0,
        "sha256": sha256(DOWNLOAD) if ok else None,
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
    coordinate_terms = sorted(
        term
        for term in {
            "x",
            "y",
            "gaze",
            "fixation",
            "timestamp",
            "duration",
            "point",
            "polygon",
            "rectangle",
            "comment",
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
        "structural_terms_present": coordinate_terms,
    }


def inspect_mkv() -> dict[str, object]:
    if not DOWNLOAD.exists():
        return {"available": False}

    ffprobe = run(
        "ffprobe",
        "-v",
        "error",
        "-count_packets",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(DOWNLOAD),
        check=False,
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
            streams.append(
                {
                    key: stream.get(key)
                    for key in (
                        "index",
                        "codec_name",
                        "codec_long_name",
                        "codec_type",
                        "codec_tag_string",
                        "duration",
                        "nb_read_packets",
                        "width",
                        "height",
                        "r_frame_rate",
                        "avg_frame_rate",
                    )
                    if key in stream
                }
                | {"tags": stream.get("tags", {})}
            )
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
    track_summary = []
    extracted_summary = []
    for track in identified.get("tracks", []):
        props = track.get("properties", {})
        track_summary.append(
            {
                "id": track.get("id"),
                "type": track.get("type"),
                "codec": track.get("codec"),
                "codec_id": props.get("codec_id"),
                "track_name": props.get("track_name"),
                "language": props.get("language"),
                "default_track": props.get("default_track"),
                "forced_track": props.get("forced_track"),
            }
        )
        if track.get("type") != "subtitles":
            continue
        track_id = int(track["id"])
        out = Path(f"track_{track_id}.subtitle")
        extracted = run(
            mkvextract_path,
            "tracks",
            str(DOWNLOAD),
            f"{track_id}:{out}",
            check=False,
        )
        entry: dict[str, object] = {
            "track_id": track_id,
            "extract_exit": extracted.returncode,
            "stderr": extracted.stderr.strip()[:2000],
        }
        if extracted.returncode == 0 and out.exists():
            entry.update(summarize_extracted_track(out))
            out.unlink()
        extracted_summary.append(entry)

    result["mkvmerge"] = {
        "container": identified.get("container", {}),
        "track_count": len(track_summary),
        "track_type_counts": dict(collections.Counter(t["type"] for t in track_summary)),
        "tracks": track_summary,
    }
    result["subtitle_payload_summaries"] = extracted_summary
    return result


def main() -> None:
    report: dict[str, object] = {
        "schema": "gazeforge.visus_osnabrueck_derivative_probe.v1",
        "scope": {
            "dataset": "Kurzhals et al. 2014 VISUS benchmark",
            "scenario": "K1 / 01-car pursuit",
            "variant": "USF lossless multimedia-container derivative",
            "source_page": SOURCE_PAGE,
            "rights_promotion_authorized": False,
            "empirical_promotion_authorized": False,
            "redistribution_authorized": False,
        },
        "head_probes": {
            "k1_usf": head_probe(K1_USF_URL),
            "bundle": head_probe(BUNDLE_URL),
        },
    }
    report["download"] = download_k1()
    report["inspection"] = inspect_mkv()
    report["claim_boundary"] = {
        "institutional_derivative_candidate_only": True,
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
