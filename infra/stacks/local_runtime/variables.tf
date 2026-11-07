variable "network_name" {
  description = "Docker network shared by every local container and the kind node."
  type        = string
  default     = "weaver"
}

variable "aws_region" {
  description = "Region Floci reports. Matches npr and prod."
  type        = string
  default     = "eu-west-1"
}

variable "docker_socket_path" {
  description = "Host path of the Docker socket mounted into Floci."
  type        = string
  default     = "/var/run/docker.sock"
}

variable "floci_image" {
  description = "Floci image, pinned. Upgrading is its own pull request (see README, Floci support baseline)."
  type        = string
  default     = "floci/floci:2.4.0"
}

variable "confluent_platform_version" {
  description = "Confluent Platform image tag for the broker and Schema Registry."
  type        = string
  default     = "8.0.0"
}

variable "kafka_cluster_id" {
  description = "KRaft cluster ID: 22 characters of base64. Changing it requires wiping the Kafka volume."
  type        = string
  default     = "MkU3OEVBNTcwNTJENDM2Qk"
}

variable "kafka_ui_enabled" {
  description = "Run the Kafka UI container."
  type        = bool
  default     = true
}

variable "kafka_ui_image" {
  description = "Kafka UI image, pinned."
  type        = string
  default     = "kafbat/kafka-ui:v1.5.0"
}

variable "kind_cluster_name" {
  description = "Name of the kind cluster that runs CMF."
  type        = string
  default     = "weaver"
}

variable "kind_node_image" {
  description = "kindest/node image, pinned."
  type        = string
  default     = "kindest/node:v1.37.0"
}

variable "kubeconfig_path" {
  description = "Absolute path the kind kubeconfig is written to."
  type        = string
}

variable "flink_namespace" {
  description = "Namespace for the Flink operator, CMF and Flink jobs."
  type        = string
  default     = "default"
}

variable "chart_versions" {
  description = "Helm chart versions. Null installs the latest; pin each once proven (week 1 task)."
  type = object({
    cert_manager   = optional(string, "v1.21.3")
    flink_operator = optional(string)
    cmf            = optional(string)
  })
  default = {}
}

variable "ports" {
  description = "Host ports, all bound to 127.0.0.1."
  type = object({
    floci           = optional(number, 4566)
    kafka           = optional(number, 9092)
    schema_registry = optional(number, 8081)
    kafka_ui        = optional(number, 9021)
  })
  default = {}
}

variable "tf_state_bucket" {
  description = "Floci S3 bucket holding state for the other local roots."
  type        = string
  default     = "weaver-tfstate"
}

variable "tf_lock_table" {
  description = "Floci DynamoDB table used for state locking."
  type        = string
  default     = "weaver-tflock"
}

variable "tags" {
  description = "Tags applied to AWS resources."
  type        = map(string)
  default     = {}
}
