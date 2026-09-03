from __future__ import annotations

from gazeforge.cli import build_parser


def test_native_event_suite_cli_requires_annotator_roles_and_explicit_ivt() -> None:
    args = build_parser().parse_args(
        [
            "native-event-suite",
            "expert-events.csv",
            "native-spec.json",
            "validation/native-suite",
            "--primary-annotator",
            "expert-a",
            "--sensitivity-annotator",
            "expert-b",
            "--ivt-threshold-px-s",
            "700",
        ]
    )

    assert args.command == "native-event-suite"
    assert args.primary_annotator == "expert-a"
    assert args.sensitivity_annotator == "expert-b"
    assert args.ivt_threshold_deg_s is None
    assert args.ivt_threshold_px_s == 700.0


def test_native_event_suite_validator_cli_supports_manifest_only() -> None:
    args = build_parser().parse_args(
        [
            "native-event-suite-validate",
            "validation/native-suite",
            "--manifest-only",
        ]
    )

    assert args.command == "native-event-suite-validate"
    assert args.manifest_only is True
