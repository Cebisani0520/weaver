variable "registry_url" {
  description = "Schema Registry base URL as seen from the machine running Terraform."
  type        = string
}

variable "subject" {
  description = "Subject name, {topic}-value or {topic}-key under TopicNameStrategy."
  type        = string
}

variable "schema" {
  description = "Schema definition as a string (the contents of the .avsc file)."
  type        = string
}

variable "schema_type" {
  description = "AVRO, JSON or PROTOBUF."
  type        = string
  default     = "AVRO"

  validation {
    condition     = contains(["AVRO", "JSON", "PROTOBUF"], var.schema_type)
    error_message = "schema_type must be AVRO, JSON or PROTOBUF."
  }
}

variable "compatibility" {
  description = "Compatibility level enforced on new versions."
  type        = string
  default     = "BACKWARD"
}
