# One released model version behind a stable endpoint.
#
# The model and endpoint config are named by version and replaced when the
# version changes (create_before_destroy), so a release is: new model, new
# config, then UpdateEndpoint on the same endpoint name. Callers never see the
# name change; the old config is deleted only after the endpoint has moved.
#
# A version is immutable: a new image or artifact is a new version (the
# pipeline registers one per training job), never a change under the same name.

locals {
  versioned_name = "${var.endpoint_name}-v${var.model_version}"
  artifact       = regex("^s3://([^/]+)/(.+)$", var.model_data_url)
}

# Fails the plan if the release artifact is missing, rather than leaving an
# endpoint stuck in Creating while the container fails to load a model.
data "aws_s3_object" "artifact" {
  bucket = local.artifact[0]
  key    = local.artifact[1]
}

resource "aws_sagemaker_model" "this" {
  name                     = local.versioned_name
  execution_role_arn       = var.execution_role_arn
  enable_network_isolation = var.network_isolation

  primary_container {
    image          = var.image
    model_data_url = var.model_data_url
    mode           = "SingleModel"
    environment = merge(var.environment, {
      MODEL_NAME    = var.endpoint_name
      MODEL_VERSION = tostring(var.model_version)
    })
  }

  dynamic "vpc_config" {
    for_each = var.vpc_config == null ? [] : [var.vpc_config]
    content {
      subnets            = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }

  tags = merge(var.tags, {
    model_version = tostring(var.model_version)
    # S3 returns the ETag in quotes, which tag values may not contain.
    artifact_etag = replace(data.aws_s3_object.artifact.etag, "\"", "")
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_sagemaker_endpoint_configuration" "this" {
  name        = local.versioned_name
  kms_key_arn = var.kms_key_arn

  production_variants {
    variant_name           = "AllTraffic"
    model_name             = aws_sagemaker_model.this.name
    initial_variant_weight = 1
    # Instance-backed unless serverless is set.
    initial_instance_count = var.serverless == null ? var.instance_count : null
    instance_type          = var.serverless == null ? var.instance_type : null

    dynamic "serverless_config" {
      for_each = var.serverless == null ? [] : [var.serverless]
      content {
        memory_size_in_mb       = serverless_config.value.memory_size_in_mb
        max_concurrency         = serverless_config.value.max_concurrency
        provisioned_concurrency = serverless_config.value.provisioned_concurrency
      }
    }
  }

  dynamic "data_capture_config" {
    for_each = var.data_capture == null ? [] : [var.data_capture]
    content {
      enable_capture              = true
      initial_sampling_percentage = data_capture_config.value.sampling_percentage
      destination_s3_uri          = data_capture_config.value.destination_s3_uri
      kms_key_id                  = var.kms_key_arn

      capture_options {
        capture_mode = "Input"
      }
      capture_options {
        capture_mode = "Output"
      }

      capture_content_type_header {
        json_content_types = ["application/json"]
        csv_content_types  = ["text/csv"]
      }
    }
  }

  tags = merge(var.tags, { model_version = tostring(var.model_version) })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_sagemaker_endpoint" "this" {
  name                 = var.endpoint_name
  endpoint_config_name = aws_sagemaker_endpoint_configuration.this.name
  tags                 = var.tags
}
