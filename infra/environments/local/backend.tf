# State lives in Floci S3, locked with a Floci DynamoDB table. Both are created
# by infra/environments/local/runtime, so run `mise run up` before `init`.
terraform {
  backend "s3" {
    bucket         = "weaver-tfstate"
    key            = "local/weaver.tfstate"
    region         = "eu-west-1"
    dynamodb_table = "weaver-tflock"
    use_lockfile   = true

    access_key = "test"
    secret_key = "test"

    endpoints = {
      s3       = "http://localhost:4566"
      dynamodb = "http://localhost:4566"
      sts      = "http://localhost:4566"
    }

    use_path_style              = true
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
  }
}
