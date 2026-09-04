import json

from gazeforge.source_candidate_cli import main


def test_candidate_source_cli_build_and_validate(tmp_path, capsys):
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "sample.arff").write_text("@relation x\n@data\n1\n", encoding="utf-8")
    manifest = tmp_path / "inventory.json"

    assert (
        main(
            [
                "build",
                "--dataset",
                "hollywood2em",
                "--root",
                str(root),
                "--output",
                str(manifest),
            ]
        )
        == 0
    )
    built = json.loads(capsys.readouterr().out)
    assert built["record_type"] == "candidate-source-inventory-v1"
    assert built["dataset_key"] == "hollywood2em"
    assert built["file_count"] == 1
    assert manifest.is_file()

    assert main(["validate", "--inventory", str(manifest), "--root", str(root)]) == 0
    validated = json.loads(capsys.readouterr().out)
    assert validated == built
