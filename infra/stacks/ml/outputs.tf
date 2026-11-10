output "data_bucket" {
  description = "Bucket for training datasets."
  value       = module.data_bucket.name
}

output "models_bucket" {
  description = "Bucket for training output and released model artifacts."
  value       = module.models_bucket.name
}

output "ecr_repositories" {
  description = "Model image repositories: model name => repository URL."
  value       = { for name, repository in module.ecr : name => repository.url }
}

output "sagemaker_role_arn" {
  description = "Execution role for training jobs and endpoints."
  value       = module.sagemaker_role.arn
}

output "endpoints" {
  description = "Deployed endpoints: model name => endpoint name, version and config."
  value = {
    for name, endpoint in module.endpoint : name => {
      endpoint_name        = endpoint.endpoint_name
      model_version        = endpoint.model_version
      endpoint_config_name = endpoint.endpoint_config_name
    }
  }
}
