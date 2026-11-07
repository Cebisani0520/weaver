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
    statements   = module.flink_local.statements
  }
}
