variable "base_url" {
  description = "CMF base URL as seen from the machine running Terraform."
  type        = string
}

variable "environment" {
  description = "Environment the statement runs in."
  type        = string
}

variable "name" {
  description = "Statement name. Include a version, for example fraud-score-features-v1."
  type        = string
}

variable "sql" {
  description = "The SQL statement."
  type        = string
}

variable "compute_pool" {
  description = "Compute pool the statement runs on."
  type        = string
}

variable "catalog" {
  description = "Current catalog for unqualified table names."
  type        = string
}

variable "database" {
  description = "Current database for unqualified table names."
  type        = string
}

variable "parallelism" {
  description = "Statement parallelism."
  type        = number
  default     = 1
}

variable "flink_configuration" {
  description = "Flink configuration for this statement, merged over the pool's. Streaming INSERTs need execution.checkpointing.interval."
  type        = map(string)
  default     = {}
}

variable "replace_triggers" {
  description = "Values that restart the statement when they change, such as the DDL its tables depend on."
  type        = list(string)
  default     = []
}

variable "ok_phases" {
  description = "Phases that count as success: RUNNING for streaming statements, COMPLETED for DDL."
  type        = list(string)
  default     = ["RUNNING", "COMPLETED"]
}

variable "wait_seconds" {
  description = "Seconds to wait for the statement to reach an ok phase. The first run pulls the Flink SQL image."
  type        = number
  default     = 900
}
