module "floci" {
  source = "../../modules/docker_container"

  name         = "floci"
  image        = var.floci_image
  network_name = module.network.name
  user         = "root" # needs the Docker socket to start SageMaker containers

  env = {
    FLOCI_HOSTNAME                = "floci"
    FLOCI_DEFAULT_REGION          = var.aws_region
    FLOCI_STORAGE_MODE            = "hybrid"
    FLOCI_STORAGE_PERSISTENT_PATH = "/app/data"
    # Containers Floci starts (training jobs, endpoints) join the same network.
    FLOCI_SERVICES_DOCKER_NETWORK = module.network.name


    # Path-style image URIs (localhost:4566/<account>/<region>/<repo>): the
    # default host-style URI (<account>.dkr.ecr.<region>.localhost:4566) does
    # not resolve with Docker's containerd image store.
    FLOCI_SERVICES_ECR_URI_STYLE = "path"

    # Run a model image straight from the host's image cache when it is there
    # (mise run build-model tags it with the repository URI), instead of pulling.
    FLOCI_SERVICES_ECR_PREFER_LOCAL_IMAGES = "true"
  }

  ports = [{ internal = 4566, external = var.ports.floci }]

  volumes = [
    { container_path = "/var/run/docker.sock", host_path = var.docker_socket_path },
    { container_path = "/app/data", volume_name = "weaver-floci-data" },
  ]
}

module "floci_ready" {
  source = "../../modules/local_wait"

  name    = "Floci"
  command = "curl -fsS http://localhost:${var.ports.floci}/_localstack/health"
  trigger = module.floci.id
}
