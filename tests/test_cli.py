from types import SimpleNamespace

from gazeforge import cli


def test_cli_parses_hidden_layers():
    args = cli.build_parser().parse_args(
        ["lund2013-benchmark", "/tmp/lund", "--hidden-layers", "16,8"]
    )
    assert args.hidden_layers == (16, 8)


def test_cli_parses_sensitivity_grid():
    args = cli.build_parser().parse_args(
        [
            "lund2013-sensitivity",
            "/tmp/lund",
            "--target-rates",
            "120,60,30",
            "--purities",
            "0.6,0.75,0.9",
        ]
    )
    assert args.target_rates == (120.0, 60.0, 30.0)
    assert args.purities == (0.6, 0.75, 0.9)


def test_cli_parses_fetch_selection():
    args = cli.build_parser().parse_args(
        [
            "lund2013-fetch",
            "/tmp/lund",
            "--annotators",
            "RA,MN",
            "--families",
            "dots,video",
        ]
    )
    assert args.annotators == ("RA", "MN")
    assert args.families == ("dots", "video")


def test_cli_fetches_pinned_lund_dataset(monkeypatch, tmp_path, capsys):
    manifest_path = tmp_path / "_gazeforge_source_manifest.json"
    result = SimpleNamespace(
        root=tmp_path,
        files=(tmp_path / "a.mat", tmp_path / "b.mat"),
        manifest_path=manifest_path,
        manifest={"commit": "pinned-commit"},
        manifest_fingerprint_sha256="f" * 64,
    )
    monkeypatch.setattr(cli, "fetch_lund2013_dataset", lambda *args, **kwargs: result)

    code = cli.main(["lund2013-fetch", str(tmp_path), "--families", "dots,img"])

    assert code == 0
    captured = capsys.readouterr().out
    assert '"file_count": 2' in captured
    assert '"source_commit": "pinned-commit"' in captured
    assert '"manifest_fingerprint_sha256": "' in captured


def test_cli_freezes_benchmark_report(monkeypatch, tmp_path, capsys):
    report = {
        "benchmark": {"name": "Lund2013"},
        "model": {},
        "protocol": {},
        "metrics": {},
        "report_fingerprint_sha256": "a" * 64,
    }
    monkeypatch.setattr(
        cli,
        "run_lund2013_event_benchmark",
        lambda *args, **kwargs: SimpleNamespace(report=report),
    )
    output = tmp_path / "report.json"
    code = cli.main(
        [
            "lund2013-benchmark",
            str(tmp_path),
            "--output",
            str(output),
            "--n-estimators",
            "10",
        ]
    )
    assert code == 0
    assert output.exists()
    assert '"report_fingerprint_sha256": "' in capsys.readouterr().out


def test_cli_freezes_sensitivity_report(monkeypatch, tmp_path, capsys):
    report = {
        "benchmark": {"name": "Lund2013-sampling-sensitivity"},
        "model": {},
        "protocol": {},
        "metrics": {},
        "report_fingerprint_sha256": "c" * 64,
    }
    monkeypatch.setattr(
        cli,
        "run_lund2013_sampling_sensitivity",
        lambda *args, **kwargs: SimpleNamespace(report=report),
    )
    output = tmp_path / "sensitivity.json"
    code = cli.main(
        [
            "lund2013-sensitivity",
            str(tmp_path),
            "--target-rates",
            "120,60",
            "--purities",
            "0.6,0.9",
            "--output",
            str(output),
            "--n-estimators",
            "10",
        ]
    )
    assert code == 0
    assert output.exists()
    captured = capsys.readouterr().out
    assert "Lund2013-sampling-sensitivity" in captured
    assert '"report_fingerprint_sha256": "' in captured
