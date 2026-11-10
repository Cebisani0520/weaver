<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| terraform | >= 1.10 |
| aws | ~> 6.0 |

## Modules

| Name | Source | Version |
| ---- | ------ | ------- |
| data\_bucket | ../../modules/aws_s3_bucket | n/a |
| ecr | ../../modules/aws_ecr_repository | n/a |
| endpoint | ../../modules/aws_sagemaker_endpoint | n/a |
| models\_bucket | ../../modules/aws_s3_bucket | n/a |
| sagemaker\_role | ../../modules/aws_iam_role | n/a |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| name\_prefix | Prefix for bucket and role names: weaver locally, weaver-<env> elsewhere. | `string` | n/a | yes |
| endpoint | Endpoint settings for this environment. | <pre>object({<br/>    instance_type     = optional(string, "ml.c6i.large")<br/>    instance_count    = optional(number, 2)<br/>    network_isolation = optional(bool, true)<br/>    serverless = optional(object({<br/>      memory_size_in_mb       = number<br/>      max_concurrency         = number<br/>      provisioned_concurrency = optional(number)<br/>    }))<br/>    vpc_config = optional(object({<br/>      subnet_ids         = list(string)<br/>      security_group_ids = list(string)<br/>    }))<br/>    data_capture                = optional(bool, true)<br/>    capture_sampling_percentage = optional(number, 100)<br/>  })</pre> | `{}` | no |
| force\_destroy | Allow destroying non-empty buckets and repositories. True only locally. | `bool` | `false` | no |
| image\_tag\_mutability | ECR tag mutability: IMMUTABLE in npr and prod, MUTABLE locally. | `string` | `"IMMUTABLE"` | no |
| keep\_images | Images kept per repository. Null keeps all. | `number` | `20` | no |
| kms\_key\_arn | Customer-managed KMS key for buckets, images and endpoints. Null locally. | `string` | `null` | no |
| model\_names | Models the platform builds, one ECR repository each. | `list(string)` | <pre>[<br/>  "fraud-score"<br/>]</pre> | no |
| models | Released models to serve: name => approved version and image tag. Written by the pipeline's approve step. | <pre>map(object({<br/>    version   = number<br/>    image_tag = string<br/>  }))</pre> | `{}` | no |
| tags | Tags applied to every resource. | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| data\_bucket | Bucket for training datasets. |
| ecr\_repositories | Model image repositories: model name => repository URL. |
| endpoints | Deployed endpoints: model name => endpoint name, version and config. |
| models\_bucket | Bucket for training output and released model artifacts. |
| sagemaker\_role\_arn | Execution role for training jobs and endpoints. |
<!-- END_TF_DOCS -->