# Local environment: Confluent Platform and CMF in place of Confluent Cloud,
# Floci in place of AWS. Stacks are added as they are built:
#
#   module "aws" { source = "../../stacks/aws" }
#   module "ml"  { source = "../../stacks/ml" }

module "confluent_local" {
  source = "../../stacks/confluent_local"

  topics              = local.topics
  schemas             = local.schemas
  schema_registry_url = var.schema_registry_url
}

module "flink_local" {
  source = "../../stacks/flink_local"

  cmf_url        = var.cmf_url
  ddl_statements = local.ddl_statements
  statements     = local.statements

  # Statements read topics whose tables are inferred from registered schemas.
  depends_on = [module.confluent_local]
}

# Buckets, model image repositories, the SageMaker role and, once a version is
# approved, the endpoint. Same stack as npr and prod; only the settings differ.
module "ml" {
  source = "../../stacks/ml"

  name_prefix          = "weaver"
  models               = var.models
  image_tag_mutability = "MUTABLE" # rebuild an image under the same VERSION while iterating
  keep_images          = null      # lifecycle policies are not needed on a laptop
  force_destroy        = true
  endpoint = {
    instance_type     = "ml.t2.medium"
    instance_count    = 1     # Floci serves one container per endpoint
    network_isolation = false # Floci reaches the container over the Docker network
    data_capture      = false # not emulated by Floci 2.4.0; on in npr and prod
  }
  tags = local.tags
}
