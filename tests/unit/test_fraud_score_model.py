"""The fraud score model: feature spec, dataset, training, serving and release.

Trains a small model in-process with the same code the SageMaker container
runs, then serves it over HTTP on a random local port.
"""

from __future__ import annotations

import io
import json
import math
import tarfile
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import fields
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from services.flink_sql.fraud_score.reference_features import Features
from services.models.fraud_score import pipeline
from services.models.fraud_score.dataset import SPLITS, DatasetConfig, build, write
from services.models.fraud_score.fraud_score_model import metrics, spec
from services.models.fraud_score.fraud_score_model.serve import Model, make_server
from services.models.fraud_score.fraud_score_model.train import (
    hyperparameters,
    read_channel,
    train,
)
from tests.model_cases import TAKEOVER_SIGNALS, build_cases, median

SMALL = DatasetConfig(customers=60, days=10, fraud_scenarios=20, benign_scenarios=20, seed=3)
TRAINING = DatasetConfig(customers=200, days=21, fraud_scenarios=140, benign_scenarios=220, seed=4)


# --- feature spec -----------------------------------------------------------


def test_spec_inputs_are_txn_features_fields(repo_root: Path) -> None:
    schema = json.loads(
        (repo_root / "infra/environments/local/schemas/txn-features/value.avsc").read_text()
    )
    avro_fields = {f["name"] for f in schema["fields"]}
    reference_fields = {f.name for f in fields(Features)}
    names = spec.load().names
    assert set(names) <= avro_fields
    assert set(names) <= reference_fields
    assert len(names) == len(set(names))


def test_spec_vectorises_with_one_hot_channel_and_nan_for_missing() -> None:
    feature_spec = spec.load()
    vector = feature_spec.vector({"channel": "PAYSHAP", "sim_swap_72h": "true"})
    columns = feature_spec.columns
    assert len(vector) == len(columns)
    assert vector[columns.index("channel=PAYSHAP")] == 1.0
    assert vector[columns.index("channel=EFT")] == 0.0
    assert vector[columns.index("sim_swap_72h")] == 1.0
    assert math.isnan(vector[columns.index("amount_cents")])


def test_spec_round_trips_through_json() -> None:
    feature_spec = spec.load()
    assert spec.parse(feature_spec.to_json()) == feature_spec


def test_spec_rejects_unknown_kind() -> None:
    bad = {"model": "m", "feature_version": "v1", "features": [{"name": "x", "kind": "text"}]}
    with pytest.raises(ValueError, match="unknown feature kind"):
        spec.parse(json.dumps(bad))


# --- metrics ----------------------------------------------------------------


def test_roc_auc_matches_pairwise_definition() -> None:
    rng = np.random.default_rng(1)
    labels = (rng.random(300) < 0.2).astype(np.float64)
    scores = np.round(rng.random(300) + labels * 0.3, 2)  # rounded, so there are ties
    positives, negatives = scores[labels == 1], scores[labels == 0]
    pairs = (positives[:, None] > negatives[None, :]).sum() + 0.5 * (
        positives[:, None] == negatives[None, :]
    ).sum()
    expected = pairs / (len(positives) * len(negatives))
    assert metrics.roc_auc(labels, scores) == pytest.approx(expected)


def test_average_precision_is_one_for_a_perfect_ranking() -> None:
    labels = np.array([0, 0, 1, 1, 0], dtype=np.float64)
    scores = np.array([0.1, 0.2, 0.9, 0.8, 0.3])
    assert metrics.average_precision(labels, scores) == pytest.approx(1.0)
    point = metrics.threshold_for_precision(labels, scores, 0.9)
    assert point == {"threshold": pytest.approx(0.8), "precision": 1.0, "recall": 1.0}


# --- dataset ----------------------------------------------------------------


def test_dataset_splits_by_time_and_labels_fraud(tmp_path: Path) -> None:
    manifest = write(build(SMALL), tmp_path)
    splits = manifest["splits"]
    assert list(splits) == list(SPLITS)
    assert splits["train"]["to"] < splits["validation"]["from"]
    assert splits["validation"]["to"] < splits["test"]["from"]
    assert splits["train"]["positives"] > 0
    header = (tmp_path / SMALL.dataset_id / "train/train.csv").read_text().splitlines()[0]
    assert header.split(",") == ["label", *spec.load().columns]


def test_dataset_is_reproducible(tmp_path: Path) -> None:
    first = write(build(SMALL), tmp_path / "a")
    second = write(build(SMALL), tmp_path / "b")
    assert {k: v["sha256"] for k, v in first["splits"].items()} == {
        k: v["sha256"] for k, v in second["splits"].items()
    }


# --- training ---------------------------------------------------------------


def _sagemaker_layout(base: Path, dataset_root: Path) -> None:
    """Lay the dataset out as SageMaker (and Floci) present channels to `train`."""
    for channel in ("train", "validation"):
        target = base / "input" / "data" / channel
        target.mkdir(parents=True)
        source = dataset_root / channel / f"{channel}.csv"
        (target / source.name).write_bytes(source.read_bytes())
    (base / "input" / "config").mkdir(parents=True)


@pytest.fixture(scope="module")
def trained(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("training")
    write(build(TRAINING), root / "data")
    base = root / "opt_ml"
    _sagemaker_layout(base, root / "data" / TRAINING.dataset_id)
    (base / "input" / "config" / "hyperparameters.json").write_text(
        json.dumps({"num_round": "200", "max_depth": "4"})
    )
    metadata = train(base)
    return {"metadata": metadata, "model_dir": base / "model", "data": root / "data"}


def test_training_writes_the_model_directory(trained: dict[str, Any]) -> None:
    model_dir: Path = trained["model_dir"]
    assert {p.name for p in model_dir.iterdir()} == {
        "model.json",
        "feature_spec.json",
        "metadata.json",
    }
    metadata = trained["metadata"]
    assert metadata["hyperparameters"]["num_round"] == 200
    assert metadata["metrics"]["validation_auc_pr"] > 0.5
    assert metadata["metrics"]["validation_auc_roc"] > 0.9


def test_hyperparameters_reject_unknown_keys(tmp_path: Path) -> None:
    (tmp_path / "hyperparameters.json").write_text(json.dumps({"depth": "3"}))
    with pytest.raises(ValueError, match="unknown hyperparameter"):
        hyperparameters(tmp_path)


def test_training_data_must_match_the_spec(tmp_path: Path) -> None:
    (tmp_path / "train.csv").write_text("label,amount_cents\n0,100\n")
    with pytest.raises(ValueError, match="header does not match"):
        read_channel(tmp_path, spec.load())


# --- serving ----------------------------------------------------------------


def test_model_scores_the_takeover_journey_high(trained: dict[str, Any]) -> None:
    model = Model(trained["model_dir"])
    cases = build_cases()
    takeover = model.score(model.spec.matrix(cases.takeover))
    normal = model.score(model.spec.matrix(cases.normal))
    assert median([p["score"] for p in takeover]) > 0.5
    assert median([p["score"] for p in normal]) < 0.1
    for prediction in takeover:
        top = {reason["feature"] for reason in prediction["reasons"]}
        assert top & TAKEOVER_SIGNALS, prediction


def test_model_loads_from_a_tarball_and_reports_the_release(
    trained: dict[str, Any], tmp_path: Path
) -> None:
    training_tarball = tmp_path / "training.tar.gz"
    with tarfile.open(training_tarball, "w:gz") as archive:
        for path in trained["model_dir"].iterdir():
            archive.add(path, arcname=path.name)
    released = pipeline.release_tarball(training_tarball, 7, "repo/fraud-score:0.1.0")

    model_dir = tmp_path / "opt_ml_model"
    model_dir.mkdir()
    (model_dir / "model.tar.gz").write_bytes(released)
    model = Model(model_dir)
    assert model.describe() == {
        "model": "fraud-score",
        "model_version": "7",
        "feature_version": "v1",
    }


def test_release_tarball_puts_the_version_beside_a_nested_model(
    trained: dict[str, Any], tmp_path: Path
) -> None:
    nested = tmp_path / "nested.tar.gz"
    with tarfile.open(nested, "w:gz") as archive:
        for path in trained["model_dir"].iterdir():
            archive.add(path, arcname=f"model/{path.name}")
    with tarfile.open(fileobj=io.BytesIO(pipeline.release_tarball(nested, 2, "i:t"))) as archive:
        assert "model/model_version.json" in archive.getnames()


@pytest.fixture(scope="module")
def server(trained: dict[str, Any]) -> Iterator[str]:
    httpd = make_server(Model(trained["model_dir"]), "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def _call(url: str, body: bytes | None = None, content_type: str = "") -> tuple[int, Any]:
    method = "POST" if body is not None else "GET"
    request = urllib.request.Request(url, data=body, method=method)  # noqa: S310 - local server
    if content_type:
        request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 - local test server
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def test_ping(server: str) -> None:
    status, body = _call(f"{server}/ping")
    assert status == 200
    assert body["model"] == "fraud-score"


def test_invocations_json(server: str) -> None:
    cases = build_cases(normal_sample=3)
    payload = json.dumps({"instances": cases.takeover[:2] + cases.normal}).encode()
    status, body = _call(f"{server}/invocations", payload, "application/json")
    assert status == 200
    assert len(body["predictions"]) == 5
    assert all(0 <= p["score"] <= 1 for p in body["predictions"])
    assert body["feature_version"] == "v1"


def test_invocations_single_object_and_csv_agree(server: str) -> None:
    record = build_cases(normal_sample=1).takeover[0]
    _, from_json = _call(f"{server}/invocations", json.dumps(record).encode(), "application/json")
    row = ",".join("" if math.isnan(v) else repr(v) for v in spec.load().vector(record))
    _, from_csv = _call(f"{server}/invocations", row.encode(), "text/csv")
    assert from_json["predictions"][0]["score"] == pytest.approx(
        from_csv["predictions"][0]["score"], abs=1e-6
    )


@pytest.mark.parametrize(
    ("body", "content_type", "message"),
    [
        (b"1,2,3", "text/csv", "expected"),
        (b"[1, 2]", "application/json", "objects"),
        (b"<x/>", "application/xml", "unsupported content type"),
    ],
)
def test_bad_requests_are_400(server: str, body: bytes, content_type: str, message: str) -> None:
    status, response = _call(f"{server}/invocations", body, content_type)
    assert status == 400
    assert message in response["error"]


# --- pipeline helpers -------------------------------------------------------


def test_write_release_keeps_other_models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "models.auto.tfvars.json"
    path.write_text(json.dumps({"models": {"credit-uptake": {"version": 2, "image_tag": "1.0"}}}))
    monkeypatch.setattr(pipeline, "tfvars_path", lambda env: path)
    pipeline.write_release("local", 4, "0.1.0")
    assert json.loads(path.read_text())["models"] == {
        "credit-uptake": {"version": 2, "image_tag": "1.0"},
        "fraud-score": {"version": 4, "image_tag": "0.1.0"},
    }


def test_settings_names_match_the_ml_stack() -> None:
    local = pipeline.Settings.from_env("local")
    npr = pipeline.Settings.from_env("npr")
    assert (local.data_bucket, local.models_bucket, local.role_name) == (
        "weaver-data",
        "weaver-models",
        "weaver-sagemaker-exec",
    )
    assert npr.data_bucket == "weaver-npr-data"
    assert local.ecr_repository == "weaver/fraud-score"
