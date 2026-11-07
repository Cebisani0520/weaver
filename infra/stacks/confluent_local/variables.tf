variable "topics" {
  description = "Topics by name, decoded from the environment's topics/*.yaml."
  type = map(object({
    partitions = optional(number, 6)
    config     = optional(map(string), {})
  }))
}

variable "schemas" {
  description = "Schema definitions by subject ({topic}-value or {topic}-key), from the environment's schemas/ folder."
  type        = map(string)
  default     = {}
}

variable "schema_registry_url" {
  description = "Schema Registry URL as seen from the machine running Terraform."
  type        = string
}

variable "replication_factor" {
  description = "Replication factor for every topic. 1 on the single local broker."
  type        = number
  default     = 1
}

variable "compatibility" {
  description = "Compatibility level for every subject."
  type        = string
  default     = "BACKWARD"
}
