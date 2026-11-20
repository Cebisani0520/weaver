output "aws_account_id" {
  description = "Account ID Floci reports (000000000000 by default)."
  value       = data.aws_caller_identity.current.account_id
}

output "topics" {
  description = "Topic names and partition counts."
  value       = module.confluent_local.topics
}

output "subjects" {
  description = "Registered Schema Registry subjects."
  value       = module.confluent_local.subjects
}

output "flink" {
  description = "CMF environment, catalog, compute pool and running statements."
  value = {
    environment  = module.flink_local.environment
    catalog      = module.flink_local.catalog
    compute_pool = module.flink_local.compute_pool
    ddl          = module.flink_local.ddl_statements
    statements   = module.flink_local.statements
  }
}

output "ml" {
  description = "Buckets, image repositories, the SageMaker role and deployed endpoints."
  value = {
    data_bucket        = module.ml.data_bucket
    models_bucket      = module.ml.models_bucket
    ecr_repositories   = module.ml.ecr_repositories
    sagemaker_role_arn = module.ml.sagemaker_role_arn
    endpoints          = module.ml.endpoints
  }
}
