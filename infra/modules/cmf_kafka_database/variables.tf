variable "base_url" {
  description = "CMF base URL as seen from the machine running Terraform."
  type        = string
}

variable "catalog" {
  description = "Kafka catalog the database belongs to."
  type        = string
}

variable "name" {
  description = "Database name; the second part of a table's fully qualified name."
  type        = string
}

variable "bootstrap_servers" {
  description = "Kafka bootstrap servers as seen from Flink pods, for example broker:29092."
  type        = string
}

variable "ddl_environments" {
  description = "Environments allowed to run DDL statements against this database."
  type        = list(string)
  default     = []
}
