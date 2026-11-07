variable "name" {
  description = "What is being waited for, used in log messages."
  type        = string
}

variable "command" {
  description = "Bash command that exits 0 once the dependency is ready."
  type        = string
}

variable "trigger" {
  description = "Value that re-runs the wait when it changes, typically the container ID."
  type        = string
  default     = ""
}

variable "timeout_seconds" {
  description = "Seconds to keep retrying before failing the apply."
  type        = number
  default     = 180
}

variable "interval_seconds" {
  description = "Seconds between attempts."
  type        = number
  default     = 3
}
