# ML platform resources shared by every model, plus one endpoint per released
# model. Training jobs are not here: the pipeline creates them per run
# (services/models/<model>/pipeline.py).
#
# The same stack runs on Floci (local) and real AWS (npr, prod); environments
# differ only in variables: names, encryption keys, instance types, isolation.

locals {
  data_bucket   = "${var.name_prefix}-data"
  models_bucket = "${var.name_prefix}-models"
  role_name     = "${var.name_prefix}-sagemaker-exec"

  sagemaker_trust = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sagemaker.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  # Least privilege for training jobs and endpoints: read datasets, read and
  # write model artifacts, pull the model images, write logs.
  sagemaker_permissions = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid      = "ReadDatasets"
          Effect   = "Allow"
          Action   = ["s3:GetObject", "s3:ListBucket"]
          Resource = [module.data_bucket.arn, "${module.data_bucket.arn}/*"]
        },
        {
          Sid      = "ModelArtifacts"
          Effect   = "Allow"
          Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
          Resource = [module.models_bucket.arn, "${module.models_bucket.arn}/*"]
        },
        {
          Sid      = "PullModelImages"
          Effect   = "Allow"
          Action   = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"]
          Resource = [for repository in module.ecr : repository.arn]
        },
        {
          Sid      = "EcrAuth"
          Effect   = "Allow"
          Action   = ["ecr:GetAuthorizationToken"]
          Resource = ["*"]
        },
        {
          Sid      = "Logs"
          Effect   = "Allow"
          Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams"]
          Resource = ["arn:aws:logs:*:*:log-group:/aws/sagemaker/*"]
        },
      ],
      var.kms_key_arn == null ? [] : [{
        Sid      = "Encryption"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:GenerateDataKey", "kms:CreateGrant"]
        Resource = [var.kms_key_arn]
      }],
    )
  })
}

module "data_bucket" {
  source = "../../modules/aws_s3_bucket"

  name          = local.data_bucket
  kms_key_arn   = var.kms_key_arn
  force_destroy = var.force_destroy
  tags          = var.tags
}

module "models_bucket" {
  source = "../../modules/aws_s3_bucket"

  name          = local.models_bucket
  kms_key_arn   = var.kms_key_arn
  force_destroy = var.force_destroy
  tags          = var.tags
}

# One repository per model, whether or not a version is released yet: the
# image is pushed and trained on before anything is deployed.
module "ecr" {
  source   = "../../modules/aws_ecr_repository"
  for_each = toset(var.model_names)

  name                 = "weaver/${each.key}"
  image_tag_mutability = var.image_tag_mutability
  kms_key_arn          = var.kms_key_arn
  keep_images          = var.keep_images
  force_delete         = var.force_destroy
  tags                 = merge(var.tags, { model = each.key })
}

module "sagemaker_role" {
  source = "../../modules/aws_iam_role"

  name               = local.role_name
  description        = "Assumed by SageMaker training jobs and endpoints for Weaver models."
  assume_role_policy = local.sagemaker_trust
  inline_policies    = { sagemaker = local.sagemaker_permissions }
  tags               = var.tags
}

# Released models only. `approve` in the pipeline writes the version to the
# environment's models.auto.tfvars.json; until then a model has no endpoint.
module "endpoint" {
  source   = "../../modules/aws_sagemaker_endpoint"
  for_each = var.models

  endpoint_name      = each.key
  model_version      = each.value.version
  image              = "${module.ecr[each.key].url}:${each.value.image_tag}"
  model_data_url     = "s3://${module.models_bucket.name}/${each.key}/v${each.value.version}/model.tar.gz"
  execution_role_arn = module.sagemaker_role.arn
  instance_type      = var.endpoint.instance_type
  instance_count     = var.endpoint.instance_count
  serverless         = var.endpoint.serverless
  network_isolation  = var.endpoint.network_isolation
  vpc_config         = var.endpoint.vpc_config
  kms_key_arn        = var.kms_key_arn
  data_capture = var.endpoint.data_capture ? {
    destination_s3_uri  = "s3://${module.models_bucket.name}/${each.key}/capture"
    sampling_percentage = var.endpoint.capture_sampling_percentage
  } : null
  tags = merge(var.tags, { model = each.key })
}
