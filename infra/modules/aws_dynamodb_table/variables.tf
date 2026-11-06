variable "name" {
  description = "Table name."
  type        = string
}

variable "hash_key" {
  description = "Partition key attribute name."
  type        = string
}

variable "hash_key_type" {
  description = "Partition key type: S, N or B."
  type        = string
  default     = "S"

  validation {
    condition     = contains(["S", "N", "B"], var.hash_key_type)
    error_message = "hash_key_type must be S, N or B."
  }
}

variable "point_in_time_recovery" {
  description = "Enable point-in-time recovery."
  type        = bool
  default     = false
}

variable "kms_key_arn" {
  description = "Customer-managed KMS key. Null uses the AWS-owned key."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags applied to the table."
  type        = map(string)
  default     = {}
}
