variable "name" {
  description = "Name of the kind cluster."
  type        = string
}

variable "node_image" {
  description = "kindest/node image, pinned to a Kubernetes version supported by the Confluent Flink operator."
  type        = string
}

variable "kubeconfig_path" {
  description = "Absolute path the cluster's kubeconfig is written to. The Helm provider reads the same path."
  type        = string
}

variable "extra_port_mappings" {
  description = "Host ports mapped into the kind node (for NodePort services)."
  type = list(object({
    container_port = number
    host_port      = number
  }))
  default = []
}
