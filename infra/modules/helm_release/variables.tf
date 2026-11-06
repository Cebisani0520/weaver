variable "name" {
  description = "Helm release name."
  type        = string
}

variable "repository" {
  description = "Chart repository URL."
  type        = string
}

variable "chart" {
  description = "Chart name in the repository."
  type        = string
}

variable "chart_version" {
  description = "Chart version or constraint. Null installs the latest; pin it once a version is proven."
  type        = string
  default     = null
}

variable "namespace" {
  description = "Namespace the release is installed into."
  type        = string
  default     = "default"
}

variable "create_namespace" {
  description = "Create the namespace if it does not exist."
  type        = bool
  default     = false
}

variable "values" {
  description = "Raw YAML values documents, applied in order."
  type        = list(string)
  default     = []
}

variable "set" {
  description = "Individual chart values, keyed by their dotted path."
  type        = map(string)
  default     = {}
}

variable "timeout" {
  description = "Seconds to wait for the release's resources to become ready."
  type        = number
  default     = 600
}
