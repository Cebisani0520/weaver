"""Checks against the running local runtime (`mise run up` first).

Skipped automatically when Floci is not listening on localhost:4566, so the
unit suite stays runnable anywhere.
"""

from __future__ import annotations

import json
import socket
import urllib.request

import boto3
import pytest

FLOCI = "http://localhost:4566"
SCHEMA_REGISTRY = "http://localhost:8081"


def _listening(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _listening("localhost", 4566), reason="local runtime is not up"),
]


@pytest.fixture
def floci_session() -> boto3.session.Session:
    # Floci accepts any non-empty credentials; these are not secrets.
    credentials = {"aws_access_key_id": "test", "aws_secret_access_key": "test"}
    return boto3.session.Session(region_name="eu-west-1", **credentials)


def _get_json(url: str) -> object:
    with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310 - fixed localhost URLs
        return json.load(response)


def test_floci_is_healthy() -> None:
    assert _get_json(f"{FLOCI}/_localstack/health")


def test_state_backend_exists(floci_session: boto3.session.Session) -> None:
    s3 = floci_session.client("s3", endpoint_url=FLOCI)
    dynamodb = floci_session.client("dynamodb", endpoint_url=FLOCI)
    s3.head_bucket(Bucket="weaver-tfstate")
    table = dynamodb.describe_table(TableName="weaver-tflock")["Table"]
    assert table["KeySchema"][0]["AttributeName"] == "LockID"


def test_sagemaker_api_answers(floci_session: boto3.session.Session) -> None:
    sagemaker = floci_session.client("sagemaker", endpoint_url=FLOCI)
    assert "Endpoints" in sagemaker.list_endpoints()


def test_kafka_listener_is_open() -> None:
    assert _listening("localhost", 9092)


def test_schema_registry_answers() -> None:
    assert isinstance(_get_json(f"{SCHEMA_REGISTRY}/subjects"), list)
