"""Check that every AWS service used by a local root has a Floci endpoint.

For each Terraform root under infra/environments/local, this walks the module
tree from the root (root -> stacks -> modules), collects the AWS resource types
it uses, maps them to AWS provider endpoint keys, and compares them with the
`endpoints` block in that root's providers.tf. A missing entry would send the
call to real AWS with fake credentials.

Usage: python scripts/check_floci_endpoints.py [local_env_dir]
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from scripts.tfparse import load, module_sources, resource_types, tf_files, unquote

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCAL_ENV = REPO_ROOT / "infra" / "environments" / "local"

# Resource type prefix -> AWS provider endpoint keys that satisfy it.
# Longest prefix wins, so aws_cloudwatch_log_ beats aws_cloudwatch_.
SERVICE_PREFIXES: dict[str, set[str]] = {
    "aws_s3_": {"s3"},
    "aws_s3control_": {"s3control"},
    "aws_dynamodb_": {"dynamodb"},
    "aws_iam_": {"iam"},
    "aws_sagemaker_": {"sagemaker"},
    "aws_ecr_": {"ecr"},
    "aws_glue_": {"glue"},
    "aws_athena_": {"athena"},
    "aws_lakeformation_": {"lakeformation"},
    "aws_secretsmanager_": {"secretsmanager"},
    "aws_ssm_": {"ssm"},
    "aws_sns_": {"sns"},
    "aws_sqs_": {"sqs"},
    "aws_lambda_": {"lambda"},
    "aws_cloudwatch_event_": {"events", "eventbridge", "cloudwatchevents"},
    "aws_cloudwatch_log_": {"cloudwatchlogs", "logs"},
    "aws_cloudwatch_metric_alarm": {"cloudwatch"},
    "aws_kms_": {"kms"},
    "aws_sfn_": {"sfn", "stepfunctions"},
    "aws_kinesis_": {"kinesis"},
}


def endpoint_keys_for(resource_type: str) -> set[str] | None:
    """Endpoint keys that cover a resource type, or None if it is unmapped."""
    matches = [p for p in SERVICE_PREFIXES if resource_type.startswith(p)]
    if not matches:
        return None
    return SERVICE_PREFIXES[max(matches, key=len)]


def aws_resource_types(root: Path) -> dict[str, set[Path]]:
    """AWS resource types used anywhere in a root's local module tree."""
    found: dict[str, set[Path]] = {}
    seen: set[Path] = set()
    pending = [root.resolve()]
    while pending:
        directory = pending.pop()
        if directory in seen or not directory.is_dir():
            continue
        seen.add(directory)
        for path, rtype, _ in resource_types(directory):
            if rtype.startswith("aws_"):
                found.setdefault(rtype, set()).add(path)
        for _, source in module_sources(directory):
            if source.startswith(("./", "../")):
                pending.append((directory / source).resolve())
    return found


def configured_endpoints(root: Path) -> set[str]:
    """Endpoint keys set in any aws provider block of a root."""
    keys: set[str] = set()
    for path in tf_files(root):
        for block in load(path).get("provider", []):
            for name, body in block.items():
                if unquote(name) != "aws":
                    continue
                configs: list[Any] = body if isinstance(body, list) else [body]
                for config in configs:
                    for endpoints in config.get("endpoints", []):
                        keys.update(unquote(k) for k in endpoints if not k.startswith("__"))
    return keys


def check_root(root: Path) -> list[str]:
    """Messages for AWS services a root uses without a Floci endpoint."""
    endpoints = configured_endpoints(root)
    problems: list[str] = []
    for rtype, files in sorted(aws_resource_types(root).items()):
        keys = endpoint_keys_for(rtype)
        where = ", ".join(sorted(str(_rel(f)) for f in files))
        if keys is None:
            problems.append(
                f"{_rel(root)}: {rtype} is not mapped to an endpoint; "
                f"add it to SERVICE_PREFIXES ({where})"
            )
        elif not keys & endpoints:
            wanted = " or ".join(sorted(keys))
            problems.append(f"{_rel(root)}: {rtype} needs endpoint '{wanted}' ({where})")
    return problems


def local_roots(local_env: Path) -> list[Path]:
    """The local environment root and any nested roots (such as runtime/)."""
    candidates = [local_env, *sorted(p for p in local_env.iterdir() if p.is_dir())]
    return [p for p in candidates if (p / "providers.tf").is_file()]


def _rel(path: Path) -> Path:
    try:
        return path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return path


def main(argv: list[str]) -> int:
    local_env = Path(argv[1]) if len(argv) > 1 else DEFAULT_LOCAL_ENV
    problems = [msg for root in local_roots(local_env) for msg in check_root(root)]
    for message in problems:
        print(message, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
