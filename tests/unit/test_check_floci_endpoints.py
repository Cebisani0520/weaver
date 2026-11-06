from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_floci_endpoints import (
    check_root,
    configured_endpoints,
    endpoint_keys_for,
    local_roots,
    main,
)

PROVIDER = """
provider "aws" {
  region = "eu-west-1"
  endpoints {
%s
  }
}
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_repo(tmp_path: Path, endpoints: list[str]) -> Path:
    """A root -> stack -> module chain using S3 and SageMaker."""
    lines = "\n".join(f'    {key} = "http://localhost:4566"' for key in endpoints)
    root = tmp_path / "infra/environments/local"
    write(root / "providers.tf", PROVIDER % lines)
    write(root / "main.tf", 'module "ml" {\n  source = "../../stacks/ml"\n}\n')
    write(
        tmp_path / "infra/stacks/ml/main.tf",
        'module "bucket" {\n  source = "../../modules/aws_s3_bucket"\n}\n'
        'module "endpoint" {\n  source = "../../modules/aws_sagemaker_endpoint"\n}\n',
    )
    write(
        tmp_path / "infra/modules/aws_s3_bucket/main.tf",
        'resource "aws_s3_bucket" "this" {\n  bucket = "x"\n}\n',
    )
    write(
        tmp_path / "infra/modules/aws_sagemaker_endpoint/main.tf",
        'resource "aws_sagemaker_endpoint" "this" {\n  name = "x"\n}\n',
    )
    return root


@pytest.mark.parametrize(
    ("resource_type", "expected"),
    [
        ("aws_s3_bucket", {"s3"}),
        ("aws_cloudwatch_log_group", {"cloudwatchlogs", "logs"}),
        ("aws_cloudwatch_event_rule", {"events", "eventbridge", "cloudwatchevents"}),
        ("aws_sagemaker_endpoint_configuration", {"sagemaker"}),
        ("aws_unknown_thing", None),
    ],
)
def test_endpoint_keys_for(resource_type: str, expected: set[str] | None) -> None:
    assert endpoint_keys_for(resource_type) == expected


def test_all_endpoints_present(tmp_path: Path) -> None:
    root = make_repo(tmp_path, ["s3", "sagemaker"])
    assert configured_endpoints(root) == {"s3", "sagemaker"}
    assert check_root(root) == []


def test_missing_endpoint_is_reported_through_the_module_tree(tmp_path: Path) -> None:
    root = make_repo(tmp_path, ["s3"])
    problems = check_root(root)
    assert len(problems) == 1
    assert "aws_sagemaker_endpoint needs endpoint 'sagemaker'" in problems[0]


def test_unmapped_resource_type_is_reported(tmp_path: Path) -> None:
    root = make_repo(tmp_path, ["s3", "sagemaker"])
    write(
        tmp_path / "infra/modules/aws_s3_bucket/extra.tf",
        'resource "aws_quantum_widget" "x" {\n  name = "x"\n}\n',
    )
    problems = check_root(root)
    assert len(problems) == 1
    assert "not mapped" in problems[0]


def test_nested_runtime_root_is_checked(tmp_path: Path) -> None:
    root = make_repo(tmp_path, ["s3", "sagemaker"])
    runtime = root / "runtime"
    write(runtime / "providers.tf", PROVIDER % '    s3 = "http://localhost:4566"')
    write(runtime / "main.tf", 'module "b" {\n  source = "../../../modules/aws_s3_bucket"\n}\n')
    assert local_roots(root) == [root, runtime]
    assert main(["prog", str(root)]) == 0


def test_repository_local_roots_have_their_endpoints(repo_root: Path) -> None:
    assert main(["prog", str(repo_root / "infra/environments/local")]) == 0
