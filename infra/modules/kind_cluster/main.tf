# The kind node joins the Docker network named in KIND_EXPERIMENTAL_DOCKER_NETWORK
# (set in .mise.toml), so pods can reach the broker, Schema Registry and Floci by
# container name. The network must exist before this resource is created.
resource "kind_cluster" "this" {
  name            = var.name
  node_image      = var.node_image
  kubeconfig_path = var.kubeconfig_path
  wait_for_ready  = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"

      dynamic "extra_port_mappings" {
        for_each = var.extra_port_mappings
        content {
          container_port = extra_port_mappings.value.container_port
          host_port      = extra_port_mappings.value.host_port
          listen_address = "127.0.0.1"
        }
      }
    }
  }
}
