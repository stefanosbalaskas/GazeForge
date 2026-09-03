from __future__ import annotations

from gazeforge.cli import build_parser


def test_native_event_agreement_cli_requires_named_annotators() -> None:
    args = build_parser().parse_args(
        [
            "native-event-agreement",
            "expert-events.csv",
            "native-spec.json",
            "--left-annotator",
            "expert-a",
            "--right-annotator",
            "expert-b",
            "--event-min-iou",
            "0.6",
        ]
    )

    assert args.command == "native-event-agreement"
    assert args.left_annotator == "expert-a"
    assert args.right_annotator == "expert-b"
    assert args.event_min_iou == 0.6
