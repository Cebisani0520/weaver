variable "base_url" {
  description = "CMF base URL as seen from the machine running Terraform."
  type        = string
}

variable "name" {
  description = "Environment name."
  type        = string
}

variable "kubernetes_namespace" {
  description = "Namespace the environment's Flink clusters run in."
  type        = string
  default     = "default"
}
