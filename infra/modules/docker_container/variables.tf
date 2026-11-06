variable "name" {
  description = "Container name. Also used as the hostname, so other containers on the network reach it by this name."
  type        = string
}

variable "image" {
  description = "Image reference, pinned to a tag (never latest)."
  type        = string

  validation {
    condition     = !endswith(var.image, ":latest") && length(split(":", var.image)) > 1
    error_message = "Pin the image to an explicit tag; ':latest' and untagged images are not allowed."
  }
}

variable "network_name" {
  description = "Docker network to attach the container to."
  type        = string
}

variable "aliases" {
  description = "Extra DNS names for the container on the network."
  type        = list(string)
  default     = []
}

variable "env" {
  description = "Environment variables passed to the container."
  type        = map(string)
  default     = {}
}

variable "command" {
  description = "Command override. Null keeps the image's default command."
  type        = list(string)
  default     = null
}

variable "user" {
  description = "User the container runs as. Null keeps the image default."
  type        = string
  default     = null
}

variable "ports" {
  description = "Ports published on the host."
  type = list(object({
    internal = number
    external = number
  }))
  default = []
}

variable "bind_ip" {
  description = "Host interface published ports bind to. Loopback by default so nothing is exposed to the LAN."
  type        = string
  default     = "127.0.0.1"
}

variable "volumes" {
  description = "Mounts. Set host_path for a bind mount or volume_name for a named volume the module creates."
  type = list(object({
    container_path = string
    host_path      = optional(string)
    volume_name    = optional(string)
    read_only      = optional(bool, false)
  }))
  default = []

  validation {
    condition     = alltrue([for v in var.volumes : (v.host_path == null) != (v.volume_name == null)])
    error_message = "Each volume needs exactly one of host_path or volume_name."
  }
}

variable "healthcheck" {
  description = "Docker healthcheck. Null disables it."
  type = object({
    test         = list(string)
    interval     = optional(string, "10s")
    timeout      = optional(string, "5s")
    retries      = optional(number, 12)
    start_period = optional(string, "10s")
  })
  default = null
}

variable "restart" {
  description = "Docker restart policy."
  type        = string
  default     = "unless-stopped"
}

variable "project" {
  description = "Value of the project label set on the container and its volumes."
  type        = string
  default     = "weaver"
}
