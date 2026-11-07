variable "base_url" {
  description = "CMF base URL as seen from the machine running Terraform."
  type        = string
}

variable "environment" {
  description = "Environment the pool belongs to."
  type        = string
}

variable "name" {
  description = "Compute pool name."
  type        = string
}

variable "flink_version" {
  description = "Flink version of the pool's clusters, for example v2_3. Must match the image."
  type        = string
}

variable "image" {
  description = "cp-flink-sql image built for this CMF version, for example confluentinc/cp-flink-sql:2.3-cmf2.5-cp1."
  type        = string
}

variable "flink_configuration" {
  description = "Flink configuration for every cluster started from this pool."
  type        = map(string)
  default     = {}
}

variable "job_manager" {
  description = "JobManager resources."
  type = object({
    cpu    = number
    memory = string
  })
  default = { cpu = 0.5, memory = "1024m" }
}

variable "task_manager" {
  description = "TaskManager resources."
  type = object({
    cpu    = number
    memory = string
  })
  default = { cpu = 0.5, memory = "1536m" }
}
