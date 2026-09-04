from __future__ import annotations

import csv
import hashlib
import json
import statistics
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

UPSTREAM_REPO = "Maurice189/eye-slitscan"
UPSTREAM_COMMIT = "a8ea2402936122f9e5c98152460bd16a4ba97740"
FPS = 25.0
FPMS = FPS / 1000.0

FILES = {
    "aoi": {
        "path": "core/similarity-measures/util/test/res/01-car pursuit.xml",
        "git_blob_sha1": "10ccee08b5462892eab1506e0fbb455f253e75e9",
    },
    "P1A": {
        "path": "core/similarity-measures/util/test/res/P1A-01-car pursuit.tsv",
        "git_blob_sha1": "52a613c44c9b68ee42c9ae1810cf0f375f60f649",
    },
    "P2B": {
        "path": "core/similarity-measures/util/test/res/P2B-01-car pursuit.tsv",
        "git_blob_sha1": "81463dcfd65e99218eae08436db02b80bb65be71",
    },
    "P9B": {
        "path": "core/similarity-measures/util/test/res/P9B-01-car pursuit.tsv",
        "git_blob_sha1": "54ed468b90bb99e74c29150563cb2750a59be7f6",
    },
}


@dataclass(frozen=True)
class Box:
    frame_start: int
    frame_end: int
    x: int
    y: int
    width: int
    height: int

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height


def _raw_url(path: str) -> str:
    quoted = urllib.parse.quote(path, safe="/")
    return f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/{quoted}"


def _git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def _fetch_exact(key: str, root: Path) -> tuple[Path, dict[str, Any]]:
    spec = FILES[key]
    url = _raw_url(spec["path"])
    request = urllib.request.Request(url, headers={"User-Agent": "GazeForge-VISUS-probe/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    observed_git = _git_blob_sha1(data)
    if observed_git != spec["git_blob_sha1"]:
        raise RuntimeError(
            f"Git blob mismatch for {key}: expected {spec['git_blob_sha1']}, got {observed_git}"
        )
    target = root / Path(spec["path"]).name
    target.write_bytes(data)
    return target, {
        "path": spec["path"],
        "url": url,
        "bytes": len(data),
        "git_blob_sha1": observed_git,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _framespan(value: str) -> tuple[int, int]:
    start, end = value.split(":", 1)
    return int(start), int(end)


def _parse_aoi(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    source = next(node for node in root.iter() if _local(node.tag) == "sourcefile")
    info: dict[str, int] = {}
    objects: dict[str, list[Box]] = {}
    object_spans: dict[str, tuple[int, int]] = {}

    for file_node in source:
        if _local(file_node.tag) != "file":
            continue
        for attr in file_node:
            if _local(attr.tag) != "attribute":
                continue
            name = attr.attrib.get("name")
            dvalue = next((x for x in attr if _local(x.tag) == "dvalue"), None)
            if name and dvalue is not None:
                info[name] = int(dvalue.attrib["value"])

    for obj in source:
        if _local(obj.tag) != "object":
            continue
        name = obj.attrib["name"]
        object_spans[name] = _framespan(obj.attrib["framespan"])
        boxes: list[Box] = []
        for node in obj.iter():
            if _local(node.tag) != "bbox":
                continue
            start, end = _framespan(node.attrib["framespan"])
            boxes.append(
                Box(
                    frame_start=start,
                    frame_end=end,
                    x=int(node.attrib["x"]),
                    y=int(node.attrib["y"]),
                    width=int(node.attrib["width"]),
                    height=int(node.attrib["height"]),
                )
            )
        boxes.sort(key=lambda box: (box.frame_start, box.frame_end))
        objects[name] = boxes

    expected = {"NUMFRAMES": 625, "H-FRAME-SIZE": 1920, "V-FRAME-SIZE": 1080}
    if {key: info.get(key) for key in expected} != expected:
        raise RuntimeError(f"Unexpected AOI source geometry: {info}")
    if source.attrib.get("filename") != "01-car pursuit.avi":
        raise RuntimeError(f"Unexpected source file: {source.attrib.get('filename')}")

    return {
        "source_filename": source.attrib["filename"],
        "number_of_frames": info["NUMFRAMES"],
        "width": info["H-FRAME-SIZE"],
        "height": info["V-FRAME-SIZE"],
        "fps": FPS,
        "duration_seconds": info["NUMFRAMES"] / FPS,
        "objects": objects,
        "object_spans": object_spans,
        "box_counts": {name: len(boxes) for name, boxes in objects.items()},
    }


def _active_box(boxes: list[Box], frame: int) -> Box | None:
    for box in boxes:
        if box.frame_start <= frame <= box.frame_end:
            return box
    return None


def _to_int(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return int(float(value.replace(",", ".")))
        except ValueError:
            return None


def _parse_tsv(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith("Timestamp\t"))
    header = lines[header_index].split("\t")
    index = {name: pos for pos, name in enumerate(header)}
    required = [
        "Timestamp",
        "ValidityLeft",
        "ValidityRight",
        "FixationIndex",
        "MediaWidth",
        "MediaHeight",
        "MappedFixationPointX",
        "MappedFixationPointY",
        "FixationDuration",
        "MappedGazeDataPointX",
        "MappedGazeDataPointY",
        "MicroSecondTimestamp",
    ]
    missing = [name for name in required if name not in index]
    if missing:
        raise RuntimeError(f"Missing TSV fields: {missing}")
    max_index = max(index[name] for name in required)

    rows: list[dict[str, Any]] = []
    skipped_short = 0
    for line in lines[header_index + 1 :]:
        tokens = line.split("\t")
        if len(tokens) <= max_index:
            skipped_short += 1
            continue
        row = {name: _to_int(tokens[index[name]]) for name in required}
        if row["Timestamp"] is None:
            continue
        rows.append(row)

    if not rows:
        raise RuntimeError(f"No parseable data rows in {path}")
    return rows, {
        "line_count": len(lines),
        "data_row_count": len(rows),
        "skipped_short_rows": skipped_short,
        "header_index_zero_based": header_index,
    }


def _frame_for_timestamp(timestamp_ms: int, first_timestamp_ms: int) -> int:
    return 1 + int((timestamp_ms - first_timestamp_ms) * FPMS)


def _row_hits(row: dict[str, Any], frame: int, aoi: dict[str, Any]) -> set[str]:
    x = row["MappedFixationPointX"]
    y = row["MappedFixationPointY"]
    if x is None or y is None:
        return set()
    hits: set[str] = set()
    for name, boxes in aoi["objects"].items():
        span_start, span_end = aoi["object_spans"][name]
        if not span_start <= frame <= span_end:
            continue
        box = _active_box(boxes, frame)
        if box is None:
            raise RuntimeError(f"No active bbox for {name} at frame {frame}")
        if box.contains(x, y):
            hits.add(name)
    return hits


def _participant_metrics(participant: str, path: Path, aoi: dict[str, Any]) -> dict[str, Any]:
    rows, parser = _parse_tsv(path)
    first_timestamp = rows[0]["Timestamp"]
    assert first_timestamp is not None

    media_geometry = sorted(
        {
            (row["MediaWidth"], row["MediaHeight"])
            for row in rows
            if row["MediaWidth"] is not None and row["MediaHeight"] is not None
        }
    )
    if media_geometry != [(1920, 1080)]:
        raise RuntimeError(f"Unexpected media geometry for {participant}: {media_geometry}")

    microseconds = [
        row["MicroSecondTimestamp"] for row in rows if row["MicroSecondTimestamp"] is not None
    ]
    positive_deltas = [b - a for a, b in zip(microseconds, microseconds[1:]) if b > a]
    median_delta_us = statistics.median(positive_deltas)
    inferred_hz = 1_000_000.0 / median_delta_us

    valid_both = sum(
        1 for row in rows if row["ValidityLeft"] == 0 and row["ValidityRight"] == 0
    )

    within_stimulus: list[tuple[dict[str, Any], int, set[str]]] = []
    sample_aoi_counts: dict[str, int] = defaultdict(int)
    multiple_hit_samples = 0
    for row in rows:
        timestamp = row["Timestamp"]
        assert timestamp is not None
        frame = _frame_for_timestamp(timestamp, first_timestamp)
        if not 1 <= frame <= aoi["number_of_frames"]:
            continue
        hits = _row_hits(row, frame, aoi)
        within_stimulus.append((row, frame, hits))
        for hit in hits:
            sample_aoi_counts[hit] += 1
        if len(hits) > 1:
            multiple_hit_samples += 1

    events: list[dict[str, Any]] = []
    current_index: int | None = None
    current: dict[str, Any] | None = None
    for row, frame, hits in within_stimulus:
        fixation_index = row["FixationIndex"]
        if fixation_index is None or fixation_index <= 0:
            current_index = None
            current = None
            continue
        if fixation_index != current_index:
            current = {
                "fixation_index": fixation_index,
                "onset_timestamp_ms": row["Timestamp"],
                "onset_frame": frame,
                "x": row["MappedFixationPointX"],
                "y": row["MappedFixationPointY"],
                "duration_ms": row["FixationDuration"] or 0,
                "hit_aois": set(hits),
                "sample_count": 1,
            }
            events.append(current)
            current_index = fixation_index
        else:
            assert current is not None
            current["hit_aois"].update(hits)
            current["sample_count"] += 1

    event_aoi_counts: dict[str, int] = defaultdict(int)
    event_aoi_duration_ms: dict[str, int] = defaultdict(int)
    hit_any_events = 0
    hit_any_duration_ms = 0
    for event in events:
        if event["hit_aois"]:
            hit_any_events += 1
            hit_any_duration_ms += event["duration_ms"]
        for name in event["hit_aois"]:
            event_aoi_counts[name] += 1
            event_aoi_duration_ms[name] += event["duration_ms"]

    first_stim_ts = within_stimulus[0][0]["Timestamp"] if within_stimulus else None
    last_stim_ts = within_stimulus[-1][0]["Timestamp"] if within_stimulus else None
    total_event_duration = sum(event["duration_ms"] for event in events)

    return {
        "participant": participant,
        "parser": parser,
        "media_geometry": [list(x) for x in media_geometry],
        "first_data_timestamp_ms": first_timestamp,
        "last_data_timestamp_ms": rows[-1]["Timestamp"],
        "first_stimulus_timestamp_ms": first_stim_ts,
        "last_stimulus_timestamp_ms": last_stim_ts,
        "stimulus_span_ms": (last_stim_ts - first_stim_ts) if first_stim_ts is not None else None,
        "valid_both_eye_samples": valid_both,
        "valid_both_eye_fraction": valid_both / len(rows),
        "median_positive_sample_delta_us": median_delta_us,
        "inferred_sampling_rate_hz": inferred_hz,
        "samples_within_625_frames": len(within_stimulus),
        "samples_hitting_any_dynamic_aoi": sum(1 for _, _, hits in within_stimulus if hits),
        "sample_dynamic_aoi_hit_fraction": (
            sum(1 for _, _, hits in within_stimulus if hits) / len(within_stimulus)
        ),
        "sample_hits_by_aoi": dict(sorted(sample_aoi_counts.items())),
        "multiple_aoi_hit_samples": multiple_hit_samples,
        "fixation_event_count": len(events),
        "fixation_events_hitting_any_dynamic_aoi": hit_any_events,
        "fixation_event_dynamic_aoi_hit_fraction": hit_any_events / len(events) if events else 0.0,
        "fixation_events_by_aoi": dict(sorted(event_aoi_counts.items())),
        "total_fixation_duration_ms": total_event_duration,
        "fixation_duration_hitting_any_dynamic_aoi_ms": hit_any_duration_ms,
        "fixation_duration_dynamic_aoi_fraction": (
            hit_any_duration_ms / total_event_duration if total_event_duration else 0.0
        ),
        "fixation_duration_by_aoi_ms": dict(sorted(event_aoi_duration_ms.items())),
    }


def main() -> None:
    root = Path(".visus-public-partial-probe")
    root.mkdir(exist_ok=True)
    source_files: dict[str, Any] = {}
    local_paths: dict[str, Path] = {}
    for key in FILES:
        local_paths[key], source_files[key] = _fetch_exact(key, root)

    aoi = _parse_aoi(local_paths["aoi"])
    participants = [
        _participant_metrics(participant, local_paths[participant], aoi)
        for participant in ("P1A", "P2B", "P9B")
    ]

    result = {
        "record_type": "visus-public-partial-probe-v1",
        "status": "probe_only",
        "upstream": {
            "repository": UPSTREAM_REPO,
            "commit": UPSTREAM_COMMIT,
            "files": source_files,
        },
        "coverage": {
            "participants": ["P1A", "P2B", "P9B"],
            "participant_count": 3,
            "stimuli": ["01-car pursuit"],
            "stimulus_count": 1,
            "full_visus_participant_count": 25,
            "full_visus_stimulus_count": 11,
            "full_visus_recovered": False,
        },
        "aoi": {
            key: value
            for key, value in aoi.items()
            if key not in {"objects", "object_spans"}
        }
        | {
            "object_names": sorted(aoi["objects"]),
            "object_spans": {
                key: list(value) for key, value in sorted(aoi["object_spans"].items())
            },
        },
        "participants": participants,
        "scientific_boundary": {
            "public_derivative_partial_corpus_only": True,
            "original_full_visus_source_resolved": False,
            "human_human_agreement_created": False,
            "native_gp3_evidence": False,
            "unrestricted_redistribution_asserted": False,
            "frozen_evidence_created": False,
        },
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    result["probe_fingerprint_sha256"] = hashlib.sha256(canonical).hexdigest()
    output = Path("visus_public_partial_probe.json")
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    # urllib.parse is deliberately imported here so source fetching has no optional dependencies.
    import urllib.parse

    main()
