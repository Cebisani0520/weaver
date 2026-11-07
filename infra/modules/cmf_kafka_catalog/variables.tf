variable "base_url" {
  description = "CMF base URL as seen from the machine running Terraform."
  type        = string
}

variable "name" {
  description = "Catalog name; the first part of a table's fully qualified name."
  type        = string
}

variable "schema_registry_url" {
  description = "Schema Registry URL as seen from Flink pods (inside kind), for example http://schema-registry:8081."
  type        = string
}
