variable "name" {
  description = "Name of the Docker network. Every local container and the kind node join it."
  type        = string
}

variable "project" {
  description = "Value of the project label set on the network."
  type        = string
  default     = "weaver"
}
