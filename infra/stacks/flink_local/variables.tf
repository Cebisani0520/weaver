variable "cmf_url" {
  description = "CMF REST API as seen from the machine running Terraform (scripts/with_cmf.sh port-forwards it)."
  type        = string
  default     = "http://localhost:8080"
}

variable "environment_name" {
  description = "CMF environment for Weaver's statements."
  type        = string
  default     = "weaver-local"
}

variable "kubernetes_namespace" {
  description = "Namespace the environment's Flink clusters run in."
  type        = string
  default     = "default"
}

variable "catalog_name" {
  description = "Kafka catalog name."
  type        = string
  default     = "weaver"
}

variable "database_name" {
  description = "Kafka database name; tables are `<catalog>`.`<database>`.`<topic>`."
  type        = string
  default     = "local"
}

variable "schema_registry_url" {
  description = "Schema Registry URL as seen from Flink pods."
  type        = string
  default     = "http://schema-registry:8081"
}

variable "bootstrap_servers" {
  description = "Kafka bootstrap servers as seen from Flink pods."
  type        = string
  default     = "broker:29092"
}

variable "compute_pool" {
  description = "The compute pool every statement runs on."
  type = object({
    name                = optional(string, "default")
    flink_version       = optional(string, "v2_3")
    image               = optional(string, "confluentinc/cp-flink-sql:2.3-cmf2.5-cp1")
    flink_configuration = optional(map(string), {})
    job_manager         = optional(object({ cpu = number, memory = string }), { cpu = 0.5, memory = "1024m" })
    task_manager        = optional(object({ cpu = number, memory = string }), { cpu = 0.5, memory = "1536m" })
  })
  default = {}
}

variable "statement_defaults" {
  description = "Flink configuration applied to every statement, under each statement's own."
  type        = map(string)
  default = {
    "execution.checkpointing.interval" = "10 s" # required for streaming INSERTs
    "table.local-time-zone"            = "UTC"  # the SQL converts to SAST explicitly
    "table.exec.source.idle-timeout"   = "5 s"  # quiet partitions must not hold the watermark back
  }
}

variable "ddl_statements" {
  description = "DDL statements by name, run before the streaming statements (for example ALTER TABLE ... MODIFY WATERMARK)."
  type        = map(string)
  default     = {}
}

variable "statements" {
  description = "Statements by name. Changing a statement's SQL replaces its job."
  type = map(object({
    sql                 = string
    parallelism         = optional(number, 1)
    flink_configuration = optional(map(string), {})
  }))
  default = {}
}
