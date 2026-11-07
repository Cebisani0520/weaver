# Local environment: Confluent Platform and CMF in place of Confluent Cloud,
# Floci in place of AWS. Stacks are added as they are built:
#
#   module "aws" { source = "../../stacks/aws" }  # later weeks
#   module "ml"  { source = "../../stacks/ml" }   # week 3

module "confluent_local" {
  source = "../../stacks/confluent_local"

  topics              = local.topics
  schemas             = local.schemas
  schema_registry_url = var.schema_registry_url
}

module "flink_local" {
  source = "../../stacks/flink_local"

  cmf_url    = var.cmf_url
  statements = local.statements

  # Statements read topics whose tables are inferred from registered schemas.
  depends_on = [module.confluent_local]
}
