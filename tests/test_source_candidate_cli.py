import json

from gazeforge.source_candidate_cli import main


def test_candidate_source_cli_build_validate_review_and_review_validate(tmp_path, capsys):
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "sample.arff").write_text("@relation x\n@data\n1\n", encoding="utf-8")
    manifest = tmp_path / "inventory.json"
    review = tmp_path / "review.json"

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

    assert (
        main(
            [
                "review",
                "--inventory",
                str(manifest),
                "--root",
                str(root),
                "--output",
                str(review),
            ]
        )
        == 0
    )
    scaffold = json.loads(capsys.readouterr().out)
    assert scaffold["record_type"] == "candidate-source-review-scaffold-v1"
    assert scaffold["source_review"]["dataset_status"] == "template"
    assert scaffold["files"][0]["role"] == "unresolved"
    assert review.is_file()

    assert (
        main(
            [
                "review-validate",
                "--review",
                str(review),
                "--inventory",
                str(manifest),
                "--root",
                str(root),
            ]
        )
        == 0
    )
    review_validated = json.loads(capsys.readouterr().out)
    assert review_validated == scaffold
