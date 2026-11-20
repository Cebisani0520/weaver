variable "name_prefix" {
  description = "Prefix for bucket and role names: weaver locally, weaver-<env> elsewhere."
  type        = string
}

variable "model_names" {
  description = "Models the platform builds, one ECR repository each."
  type        = list(string)
  default     = ["fraud-score"]
}

variable "models" {
  description = "Released models to serve: name => approved version and image tag. Written by the pipeline's approve step."
  type = map(object({
    version   = number
    image_tag = string
  }))
  default = {}

  validation {
    condition     = alltrue([for name in keys(var.models) : contains(var.model_names, name)])
    error_message = "Every released model must be listed in model_names, which creates its ECR repository."
  }
}

variable "endpoint" {
  description = "Endpoint settings for this environment."
  type = object({
    instance_type     = optional(string, "ml.c6i.large")
    instance_count    = optional(number, 2)
    network_isolation = optional(bool, true)
    serverless = optional(object({
      memory_size_in_mb       = number
      max_concurrency         = number
      provisioned_concurrency = optional(number)
    }))
    vpc_config = optional(object({
      subnet_ids         = list(string)
      security_group_ids = list(string)
    }))
    data_capture                = optional(bool, true)
    capture_sampling_percentage = optional(number, 100)
  })
  default = {}
}

variable "image_tag_mutability" {
  description = "ECR tag mutability: IMMUTABLE in npr and prod, MUTABLE locally."
  type        = string
  default     = "IMMUTABLE"
}

variable "keep_images" {
  description = "Images kept per repository. Null keeps all."
  type        = number
  default     = 20
}

variable "kms_key_arn" {
  description = "Customer-managed KMS key for buckets, images and endpoints. Null locally."
  type        = string
  default     = null
}

variable "force_destroy" {
  description = "Allow destroying non-empty buckets and repositories. True only locally."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default     = {}
}
