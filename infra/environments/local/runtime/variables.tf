variable "docker_host" {
  description = "Docker daemon address."
  type        = string
  default     = "unix:///var/run/docker.sock"
}

variable "aws_region" {
  description = "Region Floci and the AWS provider use. Matches npr and prod."
  type        = string
  default     = "eu-west-1"
}

variable "floci_image" {
  description = "Floci image, pinned."
  type        = string
}

variable "confluent_platform_version" {
  description = "Confluent Platform image tag."
  type        = string
}

variable "kind_node_image" {
  description = "kindest/node image, pinned."
  type        = string
}

variable "chart_versions" {
  description = "Helm chart versions for cert-manager, the Flink operator and CMF."
  type = object({
    cert_manager   = optional(string, "v1.17.2")
    flink_operator = optional(string)
    cmf            = optional(string)
  })
  default = {}
}

variable "kafka_ui_enabled" {
  description = "Run the Kafka UI container."
  type        = bool
  default     = true
}
