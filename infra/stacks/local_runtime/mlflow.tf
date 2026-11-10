# MLflow tracking server and model registry: runs, metrics and registered
# versions of every model. Stands in for SageMaker Experiments and the
# SageMaker Model Registry, which Floci 2.4.0 does not emulate (README,
# "SageMaker: best practice versus the POC"). AWS also offers managed MLflow
# on SageMaker, so the same client code carries to npr and prod.
#
# SQLite metadata and proxied artifacts (--serve-artifacts) on one named
# volume: clients upload artifacts through the server and need no S3 access.
module "mlflow" {
  source = "../../modules/docker_container"
  count  = var.mlflow_enabled ? 1 : 0

  name         = "mlflow"
  image        = var.mlflow_image
  network_name = module.network.name

  command = [
    "mlflow", "server",
    "--host", "0.0.0.0",
    "--port", "5000",
    "--backend-store-uri", "sqlite:////mlflow/mlflow.db",
    "--serve-artifacts",
    "--artifacts-destination", "/mlflow/artifacts",
  ]

  # 5000 inside, 5050 outside: macOS uses port 5000 for AirPlay Receiver.
  ports = [{ internal = 5000, external = var.ports.mlflow }]

  volumes = [
    { container_path = "/mlflow", volume_name = "weaver-mlflow-data" },
  ]
}

module "mlflow_ready" {
  source = "../../modules/local_wait"
  count  = var.mlflow_enabled ? 1 : 0

  name    = "MLflow"
  command = "curl -fsS http://localhost:${var.ports.mlflow}/health"
  trigger = module.mlflow[0].id
}
