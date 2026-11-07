resource "docker_network" "this" {
  name   = var.name
  driver = "bridge"

  labels {
    label = "project"
    value = var.project
  }
}
