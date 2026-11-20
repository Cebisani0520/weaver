"""Gate 3: the released fraud score model answers on its SageMaker endpoint (Floci).

Needs the full week 3 flow first:
  mise run build-model && mise run train && mise run approve <version>

Scores the plan's account-takeover journey and a sample of everyday payments
through InvokeEndpoint, checks the endpoint serves the version that was
approved, and reports single-call latency (the week 4 target is p95 < 1 s for
the whole decision, so the endpoint's share should be well under that).
"""

from __future__ import annotations

import json
import math
import socket
import time
from typing import Any

import boto3
import pytest
from botocore.exceptions import ClientError

from services.models.fraud_score.fraud_score_model.spec import load
from tests.model_cases import TAKEOVER_SIGNALS, build_cases, median, percentile

FLOCI = "http://localhost:4566"
ENDPOINT = "fraud-score"


def _listening(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not _listening("localhost", 4566), reason="local runtime is not up"),
]


def _client(service: str) -> Any:
    return boto3.client(
        service,
        endpoint_url=FLOCI,
        region_name="eu-west-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",  # noqa: S106 - Floci accepts any credentials  # nosec B106
    )


@pytest.fixture(scope="module")
def endpoint() -> dict[str, Any]:
    sagemaker = _client("sagemaker")
    try:
        described: dict[str, Any] = sagemaker.describe_endpoint(EndpointName=ENDPOINT)
    except ClientError as error:
        pytest.fail(f"no {ENDPOINT} endpoint ({error}); run mise run approve <version> first")
    deadline = time.monotonic() + 300
    while described["EndpointStatus"] != "InService":
        if described["EndpointStatus"] == "Failed" or time.monotonic() > deadline:
            pytest.fail(f"endpoint {described['EndpointStatus']}: {described.get('FailureReason')}")
        time.sleep(5)
        described = sagemaker.describe_endpoint(EndpointName=ENDPOINT)
    return described


def _invoke(body: str, content_type: str = "application/json") -> dict[str, Any]:
    response = _client("sagemaker-runtime").invoke_endpoint(
        EndpointName=ENDPOINT, ContentType=content_type, Accept="application/json", Body=body
    )
    loaded: dict[str, Any] = json.loads(response["Body"].read())
    return loaded


def test_endpoint_serves_the_approved_version(endpoint: dict[str, Any]) -> None:
    # Terraform names the endpoint config fraud-score-v<N> after the approved version.
    expected = endpoint["EndpointConfigName"].rsplit("-v", 1)[1]
    response = _invoke(json.dumps({"instances": build_cases(normal_sample=1).normal}))
    assert response["model_version"] == expected
    assert response["feature_version"] == load().feature_version


def test_takeover_scores_above_every_normal_payment(endpoint: dict[str, Any]) -> None:
    cases = build_cases()
    response = _invoke(json.dumps({"instances": cases.takeover + cases.normal}))
    predictions = response["predictions"]
    takeover = predictions[: len(cases.takeover)]
    normal = predictions[len(cases.takeover) :]
    takeover_scores = [p["score"] for p in takeover]
    normal_scores = [p["score"] for p in normal]
    print(f"\ntakeover scores {[round(s, 3) for s in takeover_scores]}")
    print(f"normal scores: median {median(normal_scores):.4f}, max {max(normal_scores):.4f}")

    assert median(takeover_scores) > 0.5
    assert median(normal_scores) < 0.1
    assert min(takeover_scores) > max(normal_scores)
    for prediction in takeover:
        assert {r["feature"] for r in prediction["reasons"]} & TAKEOVER_SIGNALS, prediction


def test_csv_rows_score_like_json(endpoint: dict[str, Any]) -> None:
    record = build_cases(normal_sample=1).takeover[0]
    row = ",".join("" if math.isnan(v) else repr(v) for v in load().vector(record))
    from_csv = _invoke(row, "text/csv")["predictions"][0]["score"]
    from_json = _invoke(json.dumps(record))["predictions"][0]["score"]
    assert from_csv == pytest.approx(from_json, abs=1e-6)


def test_single_call_latency(endpoint: dict[str, Any]) -> None:
    cases = build_cases(normal_sample=20)
    timings = []
    for record in cases.normal:
        start = time.perf_counter()
        _invoke(json.dumps(record))
        timings.append((time.perf_counter() - start) * 1000)
    p50, p95 = median(timings), percentile(timings, 0.95)
    print(f"\nInvokeEndpoint through Floci: p50 {p50:.0f} ms, p95 {p95:.0f} ms")
    # Generous: Floci proxies every call. This catches a broken or cold-starting
    # container, not a production latency budget.
    assert p95 < 2000
