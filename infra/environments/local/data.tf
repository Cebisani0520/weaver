# Proves the provider reaches Floci: `terraform apply` fails here if it does not.
data "aws_caller_identity" "current" {}
