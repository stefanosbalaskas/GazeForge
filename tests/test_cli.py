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
