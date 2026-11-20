variable "endpoint_name" {
  description = "Stable endpoint name callers invoke, e.g. fraud-score."
  type        = string
}

variable "model_version" {
  description = "Released model version (the MLflow registry version). Names the model and endpoint config."
  type        = number
}

variable "image" {
  description = "Inference image URI with tag."
  type        = string
}

variable "model_data_url" {
  description = "s3:// URI of the released model.tar.gz."
  type        = string

  validation {
    condition     = can(regex("^s3://[^/]+/.+\\.tar\\.gz$", var.model_data_url))
    error_message = "model_data_url must be an s3:// URI of a .tar.gz."
  }
}

variable "execution_role_arn" {
  description = "Role SageMaker assumes to pull the image and read the artifact."
  type        = string
}

variable "instance_type" {
  description = "Instance type for an instance-backed endpoint."
  type        = string
  default     = "ml.c6i.large"
}

variable "instance_count" {
  description = "Instances behind the endpoint. 2 or more across AZs in prod; Floci supports 1."
  type        = number
  default     = 1
}

variable "serverless" {
  description = "Serverless inference instead of instances. Null for instance-backed."
  type = object({
    memory_size_in_mb       = number
    max_concurrency         = number
    provisioned_concurrency = optional(number)
  })
  default = null
}

variable "environment" {
  description = "Extra environment variables for the container."
  type        = map(string)
  default     = {}
}

variable "network_isolation" {
  description = "Run the container with no outbound network. True in npr and prod."
  type        = bool
  default     = true
}

variable "vpc_config" {
  description = "Subnets and security groups for the endpoint. Null outside a VPC (local)."
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

variable "data_capture" {
  description = "Capture requests and responses to S3 for Model Monitor. Null disables it."
  type = object({
    destination_s3_uri  = string
    sampling_percentage = optional(number, 100)
  })
  default = null
}

variable "kms_key_arn" {
  description = "KMS key for the endpoint's storage and captured data. Null uses AWS-managed keys."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags applied to the model, endpoint config and endpoint."
  type        = map(string)
  default     = {}
}
