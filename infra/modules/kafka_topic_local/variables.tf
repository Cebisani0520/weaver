variable "name" {
  description = "Topic name."
  type        = string
}

variable "partitions" {
  description = "Number of partitions. Can only be increased after creation."
  type        = number
  default     = 6
}

variable "replication_factor" {
  description = "Replication factor. 1 on the single local broker."
  type        = number
  default     = 1
}

variable "config" {
  description = "Topic configuration, for example cleanup.policy and retention.ms."
  type        = map(string)
  default     = {}
}
