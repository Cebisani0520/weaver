# State bucket and lock table for every other local root, created in Floci.
# This stack itself keeps local state, because these do not exist until it runs.
module "tf_state_bucket" {
  source = "../../modules/aws_s3_bucket"

  name          = var.tf_state_bucket
  versioning    = true
  force_destroy = true
  tags          = var.tags

  depends_on = [module.floci_ready]
}

module "tf_lock_table" {
  source = "../../modules/aws_dynamodb_table"

  name     = var.tf_lock_table
  hash_key = "LockID"
  tags     = var.tags

  depends_on = [module.floci_ready]
}
