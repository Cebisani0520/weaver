from __future__ import annotations

from pathlib import Path

from scripts.check_stack_resources import find_violations, main


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_stack_with_only_modules_passes(tmp_path: Path) -> None:
    write(
        tmp_path / "infra/stacks/ml/main.tf",
        'module "bucket" {\n  source = "../../modules/aws_s3_bucket"\n  name = "x"\n}\n'
        'data "aws_caller_identity" "current" {}\n',
    )
    assert find_violations(tmp_path / "infra/stacks") == []


def test_resource_in_stack_is_reported(tmp_path: Path) -> None:
    write(
        tmp_path / "infra/stacks/ml/s3.tf",
        'resource "aws_s3_bucket" "raw" {\n  bucket = "x"\n}\n',
    )
    violations = find_violations(tmp_path / "infra/stacks")
    assert len(violations) == 1
    assert 'resource "aws_s3_bucket" "raw"' in violations[0]


def test_terraform_data_counts_as_a_resource(tmp_path: Path) -> None:
    write(
        tmp_path / "infra/stacks/flink_local/statements.tf",
        'resource "terraform_data" "submit" {\n  input = "x"\n}\n',
    )
    assert len(find_violations(tmp_path / "infra/stacks")) == 1


def test_main_exit_codes(tmp_path: Path) -> None:
    stacks = tmp_path / "infra/stacks"
    write(stacks / "aws/main.tf", 'module "x" {\n  source = "../../modules/x"\n}\n')
    assert main(["prog", str(stacks)]) == 0
    write(stacks / "aws/bad.tf", 'resource "aws_sns_topic" "t" {\n  name = "t"\n}\n')
    assert main(["prog", str(stacks)]) == 1


def test_repository_stacks_follow_the_rule(repo_root: Path) -> None:
    assert find_violations(repo_root / "infra/stacks") == []
