# The only place the local AWS provider is configured. Stacks and modules declare
# `aws` in required_providers and inherit this configuration.
#
# Every AWS service a stack uses needs an entry here; a missing one would send
# that call to real AWS with fake credentials. scripts/check_floci_endpoints.py
# enforces it in pre-commit.
provider "aws" {
  region                      = var.aws_region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    s3             = local.floci_endpoint
    iam            = local.floci_endpoint
    sts            = local.floci_endpoint
    sagemaker      = local.floci_endpoint
    ecr            = local.floci_endpoint
    glue           = local.floci_endpoint
    athena         = local.floci_endpoint
    secretsmanager = local.floci_endpoint
    ssm            = local.floci_endpoint
    sns            = local.floci_endpoint
    sqs            = local.floci_endpoint
    lambda         = local.floci_endpoint
    events         = local.floci_endpoint
    cloudwatchlogs = local.floci_endpoint
    dynamodb       = local.floci_endpoint
    kms            = local.floci_endpoint
  }

  default_tags {
    tags = local.tags
  }
}

# The local broker's host listener. No TLS or SASL locally; npr and prod use
# the confluent provider with service-account API keys instead.
provider "kafka" {
  bootstrap_servers = [var.kafka_bootstrap_servers]
  tls_enabled       = false
}
