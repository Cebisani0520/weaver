# Flink SQL on Confluent Manager for Apache Flink (CMF) in the local kind cluster:
# an environment, a Kafka catalog and database that expose every topic as a
# table, a compute pool, and the use cases' statements.
#
# Same inputs and outputs as the Confluent Cloud `flink` stack.
module "environment" {
  source = "../../modules/cmf_environment"

  base_url             = var.cmf_url
  name                 = var.environment_name
  kubernetes_namespace = var.kubernetes_namespace
}

module "catalog" {
  source = "../../modules/cmf_kafka_catalog"

  base_url            = var.cmf_url
  name                = var.catalog_name
  schema_registry_url = var.schema_registry_url
}

module "database" {
  source = "../../modules/cmf_kafka_database"

  base_url          = var.cmf_url
  catalog           = module.catalog.name
  name              = var.database_name
  bootstrap_servers = var.bootstrap_servers
  ddl_environments  = [module.environment.name]
}

module "compute_pool" {
  source = "../../modules/cmf_compute_pool"

  base_url            = var.cmf_url
  environment         = module.environment.name
  name                = var.compute_pool.name
  flink_version       = var.compute_pool.flink_version
  image               = var.compute_pool.image
  flink_configuration = var.compute_pool.flink_configuration
  job_manager         = var.compute_pool.job_manager
  task_manager        = var.compute_pool.task_manager
}

# DDL first, such as watermark changes on the inferred tables. ALTER TABLE
# does not affect running statements, so the statements below restart
# whenever any DDL changes.
module "ddl" {
  source   = "../../modules/cmf_statement"
  for_each = var.ddl_statements

  base_url            = var.cmf_url
  environment         = module.environment.name
  name                = each.key
  sql                 = each.value
  compute_pool        = module.compute_pool.name
  catalog             = module.catalog.name
  database            = module.database.name
  flink_configuration = var.statement_defaults
  ok_phases           = ["COMPLETED"]
}

module "statements" {
  source   = "../../modules/cmf_statement"
  for_each = var.statements

  base_url            = var.cmf_url
  environment         = module.environment.name
  name                = each.key
  sql                 = each.value.sql
  compute_pool        = module.compute_pool.name
  catalog             = module.catalog.name
  database            = module.database.name
  parallelism         = each.value.parallelism
  flink_configuration = merge(var.statement_defaults, each.value.flink_configuration)
  replace_triggers    = [sha256(jsonencode(var.ddl_statements))]

  depends_on = [module.ddl]
}
