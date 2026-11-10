variable "name" {
  description = "Repository name, e.g. weaver/fraud-score."
  type        = string
}

variable "image_tag_mutability" {
  description = "MUTABLE or IMMUTABLE. IMMUTABLE for npr and prod."
  type        = string
  default     = "IMMUTABLE"

  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.image_tag_mutability)
    error_message = "image_tag_mutability must be MUTABLE or IMMUTABLE."
  }
}

variable "scan_on_push" {
  description = "Scan images for vulnerabilities when pushed."
  type        = bool
  default     = true
}

variable "kms_key_arn" {
  description = "KMS key for image encryption. Null uses AES256."
  type        = string
  default     = null
}

variable "keep_images" {
  description = "Expire all but this many images. Null adds no lifecycle policy."
  type        = number
  default     = null
}

variable "force_delete" {
  description = "Allow deleting the repository while it holds images. True only for local and disposable environments."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags applied to the repository."
  type        = map(string)
  default     = {}
}
