variable "name" {
  description = "Role name."
  type        = string
}

variable "description" {
  description = "What the role is for."
  type        = string
  default     = null
}

variable "assume_role_policy" {
  description = "Trust policy JSON: who may assume the role."
  type        = string
}

variable "inline_policies" {
  description = "Inline policy JSON documents, by policy name."
  type        = map(string)
  default     = {}
}

variable "managed_policy_arns" {
  description = "Managed policies to attach. Prefer least-privilege inline policies."
  type        = list(string)
  default     = []
}

variable "max_session_duration" {
  description = "Maximum session length in seconds."
  type        = number
  default     = 3600
}

variable "tags" {
  description = "Tags applied to the role."
  type        = map(string)
  default     = {}
}
