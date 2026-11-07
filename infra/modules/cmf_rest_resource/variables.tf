variable "base_url" {
  description = "CMF base URL as seen from the machine running Terraform, for example http://localhost:8080."
  type        = string
}

variable "collection_path" {
  description = "Path the resource is created under (POST), for example /cmf/api/v1/environments."
  type        = string
}

variable "resource_path" {
  description = "Path of the resource itself (GET, PUT, DELETE)."
  type        = string
}

variable "body" {
  description = "JSON body of the resource."
  type        = string
}

variable "replace_on_change" {
  description = "Delete and recreate the resource when the body changes, instead of updating it."
  type        = bool
  default     = false
}

variable "replace_triggers" {
  description = "Extra values that replace the resource when they change, for example DDL a statement depends on."
  type        = list(string)
  default     = []
}

variable "update_method" {
  description = "How a changed body is applied: PUT to the resource path, POST to the collection, or NONE."
  type        = string
  default     = "PUT"

  validation {
    condition     = contains(["PUT", "POST", "NONE"], var.update_method)
    error_message = "update_method must be PUT, POST or NONE."
  }
}

variable "wait_for" {
  description = "Wait after creation until status.phase is one of ok_phases; fail on fail_phases. Empty ok_phases skips the wait."
  type = object({
    ok_phases       = optional(list(string), [])
    fail_phases     = optional(list(string), [])
    timeout_seconds = optional(number, 600)
  })
  default = {}
}
