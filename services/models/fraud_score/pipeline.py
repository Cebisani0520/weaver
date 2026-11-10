"""Training pipeline for the fraud score model, run from the laptop (or CI).

    python -m services.models.fraud_score.pipeline dataset          # build, upload to S3
    python -m services.models.fraud_score.pipeline train            # SageMaker training job
    python -m services.models.fraud_score.pipeline list             # registered versions
    python -m services.models.fraud_score.pipeline approve 3        # release version 3

The shape follows AWS's recommended flow, with each step done the way Floci
2.4.0 allows (README, "SageMaker: best practice versus the POC"):

  step      AWS target                               here
  data      Glue/Athena tables, Feature Store        CSV in S3, from the reference features
  train     SageMaker Pipelines -> training job      a training job, created by this script
  evaluate  Processing job                           on the host, with the serving code
  register  SageMaker Model Registry, approval       MLflow registry and tags
  deploy    EventBridge on approval -> Terraform/CI  approve records it, Terraform deploys it

Training jobs are created here, not by Terraform: a job is a run, not
infrastructure. The endpoint, model and endpoint config are Terraform, keyed by
the approved version that `approve` writes to the environment's
models.auto.tfvars.json.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tarfile
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
import numpy as np

from services.models.fraud_score.dataset import DatasetConfig, build, write
from services.models.fraud_score.fraud_score_model.metrics import evaluate
from services.models.fraud_score.fraud_score_model.serve import Model
from services.models.fraud_score.fraud_score_model.train import read_channel

REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = Path(__file__).resolve().parent
MODEL_NAME = "fraud-score"

# Promotion needs at least this average precision on the held-out test split.
QUALITY_GATE_TEST_AUC_PR = 0.70


@dataclass(frozen=True, slots=True)
class Settings:
    """Names shared with the ml Terraform stack. Override with WEAVER_* variables."""

    env: str
    data_bucket: str
    models_bucket: str
    ecr_repository: str
    role_name: str
    instance_type: str
    mlflow_uri: str
    floci_endpoint: str
    region: str

    @classmethod
    def from_env(cls, env: str) -> Settings:
        prefix = "weaver" if env == "local" else f"weaver-{env}"
        return cls(
            env=env,
            data_bucket=os.environ.get("WEAVER_DATA_BUCKET", f"{prefix}-data"),
            models_bucket=os.environ.get("WEAVER_MODELS_BUCKET", f"{prefix}-models"),
            ecr_repository=os.environ.get("WEAVER_ECR_REPOSITORY", f"weaver/{MODEL_NAME}"),
            role_name=os.environ.get("WEAVER_SAGEMAKER_ROLE", f"{prefix}-sagemaker-exec"),
            instance_type=os.environ.get("WEAVER_TRAINING_INSTANCE", "ml.m5.large"),
            mlflow_uri=os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5050"),
            floci_endpoint=os.environ.get("WEAVER_FLOCI_ENDPOINT", "http://localhost:4566"),
            region=os.environ.get("WEAVER_AWS_REGION", "eu-west-1"),
        )

    def client(self, service: str) -> Any:
        """boto3 client: Floci for local, the default credential chain otherwise.

        Credentials are passed here rather than through AWS_* variables, so a shell
        never points real AWS tooling at Floci (or the reverse) by accident.
        """
        if self.env == "local":
            return boto3.client(
                service,
                endpoint_url=self.floci_endpoint,
                region_name=self.region,
                aws_access_key_id="test",
                # Floci accepts any credentials; these are not secrets.
                aws_secret_access_key="test",  # noqa: S106  # nosec B106
            )
        return boto3.client(service, region_name=self.region)


def image_tag() -> str:
    return (MODEL_DIR / "VERSION").read_text(encoding="utf-8").strip()


# --- dataset ----------------------------------------------------------------


def dataset_step(settings: Settings, config: DatasetConfig, out_dir: Path) -> dict[str, Any]:
    """Build the dataset locally and upload it under datasets/<dataset_id>/."""
    manifest = write(build(config), out_dir)
    root = out_dir / config.dataset_id
    s3 = settings.client("s3")
    prefix = f"{MODEL_NAME}/datasets/{config.dataset_id}"
    for path in sorted(root.rglob("*")):
        if path.is_file():
            s3.upload_file(str(path), settings.data_bucket, f"{prefix}/{path.relative_to(root)}")
    manifest["s3_prefix"] = f"s3://{settings.data_bucket}/{prefix}"
    print(f"dataset {config.dataset_id} -> {manifest['s3_prefix']}")
    for name, split in manifest["splits"].items():
        print(f"  {name:<10} {split['rows']:>7} rows  {split['positives']:>5} fraud")
    return manifest


# --- train ------------------------------------------------------------------


def _wait_for_training(sagemaker: Any, job_name: str, timeout_s: int = 1800) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    last = ""
    while True:
        job: dict[str, Any] = sagemaker.describe_training_job(TrainingJobName=job_name)
        status = f"{job['TrainingJobStatus']}/{job.get('SecondaryStatus', '')}"
        if status != last:
            print(f"  {datetime.now(UTC):%H:%M:%S} {status}")
            last = status
        if job["TrainingJobStatus"] in ("Completed", "Failed", "Stopped"):
            return job
        if time.monotonic() > deadline:
            raise TimeoutError(f"{job_name} still {status} after {timeout_s}s")
        time.sleep(5)


def _download_model(s3: Any, uri: str, target: Path) -> Path:
    bucket, key = uri.removeprefix("s3://").split("/", 1)
    path = target / "model.tar.gz"
    s3.download_file(bucket, key, str(path))
    return path


def evaluate_test(model_tarball: Path, test_csv_dir: Path) -> dict[str, float]:
    """Score the held-out test split with the serving code, as the endpoint will."""
    with tempfile.TemporaryDirectory() as scratch:
        unpack = Path(scratch)
        (unpack / model_tarball.name).write_bytes(model_tarball.read_bytes())
        model = Model(unpack)
        features, labels = read_channel(test_csv_dir, model.spec)
        scores = np.asarray([p["score"] for p in model.score(features)], dtype=np.float64)
    return evaluate(labels.astype(np.float64), scores, "test")


def train_step(
    settings: Settings,
    config: DatasetConfig,
    data_dir: Path,
    hyperparameters: dict[str, str],
) -> dict[str, Any]:
    # Rebuilt and uploaded every time: it takes seconds, is deterministic for a
    # config, and survives a Floci reset that emptied the bucket.
    manifest = dataset_step(settings, config, data_dir)

    sagemaker = settings.client("sagemaker")
    s3 = settings.client("s3")
    repository = settings.client("ecr").describe_repositories(
        repositoryNames=[settings.ecr_repository]
    )["repositories"][0]
    image = f"{repository['repositoryUri']}:{image_tag()}"
    role_arn = settings.client("iam").get_role(RoleName=settings.role_name)["Role"]["Arn"]

    job_name = f"{MODEL_NAME}-{datetime.now(UTC):%Y%m%d-%H%M%S}"
    data_prefix = f"s3://{settings.data_bucket}/{MODEL_NAME}/datasets/{config.dataset_id}"
    channels = [
        {
            "ChannelName": name,
            "ContentType": "text/csv",
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": f"{data_prefix}/{name}/",
                    "S3DataDistributionType": "FullyReplicated",
                }
            },
        }
        for name in ("train", "validation")
    ]
    print(f"training job {job_name}\n  image {image}\n  data  {data_prefix}")
    sagemaker.create_training_job(
        TrainingJobName=job_name,
        AlgorithmSpecification={"TrainingImage": image, "TrainingInputMode": "File"},
        RoleArn=role_arn,
        HyperParameters=hyperparameters,
        InputDataConfig=channels,
        OutputDataConfig={"S3OutputPath": f"s3://{settings.models_bucket}/{MODEL_NAME}/training"},
        ResourceConfig={
            "InstanceType": settings.instance_type,
            "InstanceCount": 1,
            "VolumeSizeInGB": 10,
        },
        StoppingCondition={"MaxRuntimeInSeconds": 1800},
        Tags=[{"Key": "project", "Value": "weaver"}, {"Key": "model", "Value": MODEL_NAME}],
    )
    job = _wait_for_training(sagemaker, job_name)
    if job["TrainingJobStatus"] != "Completed":
        raise RuntimeError(f"{job_name} {job['TrainingJobStatus']}: {job.get('FailureReason')}")

    artifact = job.get("ModelArtifacts", {}).get("S3ModelArtifacts") or (
        f"s3://{settings.models_bucket}/{MODEL_NAME}/training/{job_name}/output/model.tar.gz"
    )
    with tempfile.TemporaryDirectory() as scratch:
        tarball = _download_model(s3, artifact, Path(scratch))
        metadata = _member_json(tarball, "metadata.json")
        test_metrics = evaluate_test(tarball, data_dir / config.dataset_id / "test")
        version = register(
            settings,
            tarball=tarball,
            manifest=manifest,
            metadata=metadata,
            test_metrics=test_metrics,
            tags={"training_job": job_name, "artifact": artifact, "image": image},
        )
    gate = "passed" if test_metrics["test_auc_pr"] >= QUALITY_GATE_TEST_AUC_PR else "failed"
    print(
        f"\nregistered {MODEL_NAME} version {version}: test AUC-PR "
        f"{test_metrics['test_auc_pr']:.3f}, recall at 90% precision "
        f"{test_metrics['test_p90_recall']:.3f}, quality gate {gate}"
    )
    if gate == "passed":
        print(f"release it with: mise run approve {version}")
    return {"version": version, "training_job": job_name, "quality_gate": gate}


def _member_json(tarball: Path, name: str) -> dict[str, Any]:
    with tarfile.open(tarball, "r:gz") as archive:
        for member in archive.getmembers():
            if member.isfile() and Path(member.name).name == name:
                handle = archive.extractfile(member)
                if handle is not None:
                    loaded: dict[str, Any] = json.load(handle)
                    return loaded
    raise FileNotFoundError(f"{name} not in {tarball.name}")


# --- register (MLflow) ------------------------------------------------------


def _mlflow(settings: Settings) -> Any:
    from mlflow.tracking import MlflowClient

    return MlflowClient(tracking_uri=settings.mlflow_uri, registry_uri=settings.mlflow_uri)


def register(
    settings: Settings,
    *,
    tarball: Path,
    manifest: dict[str, Any],
    metadata: dict[str, Any],
    test_metrics: dict[str, float],
    tags: dict[str, str],
) -> int:
    """Log the run to MLflow and register it as a new model version."""
    from mlflow.exceptions import MlflowException

    client = _mlflow(settings)
    experiment = client.get_experiment_by_name(MODEL_NAME)
    experiment_id = experiment.experiment_id if experiment else client.create_experiment(MODEL_NAME)
    run = client.create_run(experiment_id, run_name=tags["training_job"])
    run_id = run.info.run_id
    params = {
        "dataset_id": manifest["dataset_id"],
        "feature_version": manifest["feature_version"],
        "xgboost_version": metadata.get("xgboost_version", ""),
        "best_iteration": metadata.get("best_iteration", ""),
        **{f"hp_{k}": v for k, v in metadata.get("hyperparameters", {}).items()},
    }
    for key, value in params.items():
        client.log_param(run_id, key, str(value))
    for key, value in {**metadata.get("metrics", {}), **test_metrics}.items():
        client.log_metric(run_id, key, float(value))
    for key, value in tags.items():
        client.set_tag(run_id, key, value)

    with tempfile.TemporaryDirectory() as scratch:
        unpack = Path(scratch) / "model"
        unpack.mkdir()
        with tarfile.open(tarball, "r:gz") as archive:
            archive.extractall(unpack, filter="data")
        client.log_artifacts(run_id, str(unpack), artifact_path="model")
        manifest_file = Path(scratch) / "dataset_manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        client.log_artifact(run_id, str(manifest_file))
    client.set_terminated(run_id)

    try:
        client.get_registered_model(MODEL_NAME)
    except MlflowException:
        client.create_registered_model(
            MODEL_NAME, description="Real-time payment fraud score (XGBoost on SageMaker)."
        )
    gate = "passed" if test_metrics["test_auc_pr"] >= QUALITY_GATE_TEST_AUC_PR else "failed"
    version = client.create_model_version(
        MODEL_NAME,
        source=f"{run.info.artifact_uri}/model",
        run_id=run_id,
        tags={**tags, "quality_gate": gate, "test_auc_pr": f"{test_metrics['test_auc_pr']:.4f}"},
    )
    return int(version.version)


def list_step(settings: Settings) -> None:
    client = _mlflow(settings)
    champion = _alias_version(client, "champion")
    versions = client.search_model_versions(f"name='{MODEL_NAME}'")
    print(f"{'version':>7}  {'test AUC-PR':>11}  {'gate':<7} training job")
    for version in sorted(versions, key=lambda v: int(v.version)):
        marker = "  <- champion" if version.version == champion else ""
        print(
            f"{version.version:>7}  {version.tags.get('test_auc_pr', '?'):>11}  "
            f"{version.tags.get('quality_gate', '?'):<7} {version.tags.get('training_job', '')}"
            f"{marker}"
        )


def _alias_version(client: Any, alias: str) -> str | None:
    from mlflow.exceptions import MlflowException

    try:
        return str(client.get_model_version_by_alias(MODEL_NAME, alias).version)
    except MlflowException:
        return None


# --- approve ----------------------------------------------------------------


def release_tarball(training_tarball: Path, version: int, image: str) -> bytes:
    """The training artifact plus model_version.json, which the endpoint reports."""
    release = json.dumps(
        {"model": MODEL_NAME, "version": version, "image": image, "released_at": _now()}
    ).encode("utf-8")
    buffer = io.BytesIO()
    with (
        tarfile.open(training_tarball, "r:gz") as source,
        tarfile.open(fileobj=buffer, mode="w:gz") as target,
    ):
        home = "."
        for member in source.getmembers():
            if Path(member.name).name == "model_version.json":
                continue
            if Path(member.name).name == "model.json":
                home = str(Path(member.name).parent)
            target.addfile(member, source.extractfile(member) if member.isfile() else None)
        # Next to model.json, wherever the training job packed it.
        info = tarfile.TarInfo(str(Path(home) / "model_version.json"))
        info.size = len(release)
        info.mtime = int(time.time())
        target.addfile(info, io.BytesIO(release))
    return buffer.getvalue()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def tfvars_path(env: str) -> Path:
    return REPO_ROOT / "infra" / "environments" / env / "models.auto.tfvars.json"


def write_release(env: str, version: int, tag: str) -> Path:
    """Record the approved version for Terraform; other models' entries are kept."""
    path = tfvars_path(env)
    current: dict[str, Any] = (
        json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"models": {}}
    )
    current.setdefault("models", {})[MODEL_NAME] = {"version": version, "image_tag": tag}
    path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    return path


def approve_step(settings: Settings, version: int, force: bool) -> None:
    client = _mlflow(settings)
    model_version = client.get_model_version(MODEL_NAME, str(version))
    gate = model_version.tags.get("quality_gate")
    if gate != "passed" and not force:
        raise SystemExit(
            f"version {version} quality gate is {gate!r}; pass --force to release it anyway"
        )
    artifact = model_version.tags["artifact"]
    image = model_version.tags["image"]
    s3 = settings.client("s3")
    key = f"{MODEL_NAME}/v{version}/model.tar.gz"
    with tempfile.TemporaryDirectory() as scratch:
        tarball = _download_model(s3, artifact, Path(scratch))
        s3.put_object(
            Bucket=settings.models_bucket,
            Key=key,
            Body=release_tarball(tarball, version, image),
        )
    client.set_registered_model_alias(MODEL_NAME, "champion", str(version))
    client.set_model_version_tag(MODEL_NAME, str(version), "approved_at", _now())
    path = write_release(settings.env, version, image.rsplit(":", 1)[1])
    print(f"released s3://{settings.models_bucket}/{key}")
    print(f"alias champion -> version {version}")
    shown = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
    print(f"wrote {shown}; Terraform deploys it to the endpoint next")


# --- CLI --------------------------------------------------------------------


def _hyperparameters(pairs: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit(f"--hp expects key=value, got {pair!r}")
        result[key] = value
    return result


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m services.models.fraud_score.pipeline",
        description="Fraud score training pipeline: dataset, train, list, approve.",
    )
    parser.add_argument("--env", default="local", help="local, npr or prod")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data" / MODEL_NAME)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("dataset", help="build the labelled dataset and upload it to S3")
    train = commands.add_parser("train", help="run a training job and register the result")
    train.add_argument(
        "--hp", action="append", default=[], metavar="KEY=VALUE", help="hyperparameter"
    )
    commands.add_parser("list", help="registered versions and the champion")
    approve = commands.add_parser("approve", help="release a registered version")
    approve.add_argument("version", type=int)
    approve.add_argument("--force", action="store_true", help="release despite a failed gate")
    args = parser.parse_args(argv)

    settings = Settings.from_env(args.env)
    config = DatasetConfig()
    if args.command == "dataset":
        dataset_step(settings, config, args.data_dir)
    elif args.command == "train":
        result = train_step(settings, config, args.data_dir, _hyperparameters(args.hp))
        return 0 if result["quality_gate"] == "passed" else 3
    elif args.command == "list":
        list_step(settings)
    elif args.command == "approve":
        approve_step(settings, args.version, args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
