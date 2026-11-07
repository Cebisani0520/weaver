provider "docker" {
  host = var.docker_host
}

provider "kind" {}

# Reads the kubeconfig the kind cluster writes. `mise run up` creates the
# cluster first, so the file exists before any Helm release is planned.
provider "helm" {
  kubernetes = {
    config_path = local.kubeconfig_path
  }
}

# Only the services this root uses: S3 and DynamoDB for the state backend.
# scripts/check_floci_endpoints.py fails CI if a module needs one that is missing.
provider "aws" {
  region                      = var.aws_region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    s3       = local.floci_endpoint
    dynamodb = local.floci_endpoint
    sts      = local.floci_endpoint
  }

  default_tags {
    tags = local.tags
  }
}
