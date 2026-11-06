module "network" {
  source = "../../modules/docker_network"

  name = var.network_name
}
