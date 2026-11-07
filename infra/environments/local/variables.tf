variable "aws_region" {
  description = "Region Floci and the AWS provider use. Matches npr and prod."
  type        = string
  default     = "eu-west-1"
}

variable "kafka_bootstrap_servers" {
  description = "Kafka bootstrap server as seen from the machine running Terraform."
  type        = string
  default     = "localhost:9092"
}

variable "schema_registry_url" {
  description = "Schema Registry URL as seen from the machine running Terraform."
  type        = string
  default     = "http://localhost:8081"
}

variable "cmf_url" {
  description = "CMF REST API as seen from the machine running Terraform; scripts/with_cmf.sh port-forwards it."
  type        = string
  default     = "http://localhost:8080"
}
