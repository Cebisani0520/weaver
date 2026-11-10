<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| terraform | >= 1.10 |
| aws | ~> 6.0 |

## Providers

| Name | Version |
| ---- | ------- |
| aws | ~> 6.0 |

## Resources

| Name | Type |
| ---- | ---- |
| [aws_sagemaker_endpoint.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_endpoint) | resource |
| [aws_sagemaker_endpoint_configuration.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_endpoint_configuration) | resource |
| [aws_sagemaker_model.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_model) | resource |
| [aws_s3_object.artifact](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/s3_object) | data source |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| endpoint\_name | Stable endpoint name callers invoke, e.g. fraud-score. | `string` | n/a | yes |
| execution\_role\_arn | Role SageMaker assumes to pull the image and read the artifact. | `string` | n/a | yes |
| image | Inference image URI with tag. | `string` | n/a | yes |
| model\_data\_url | s3:// URI of the released model.tar.gz. | `string` | n/a | yes |
| model\_version | Released model version (the MLflow registry version). Names the model and endpoint config. | `number` | n/a | yes |
| data\_capture | Capture requests and responses to S3 for Model Monitor. Null disables it. | <pre>object({<br/>    destination_s3_uri  = string<br/>    sampling_percentage = optional(number, 100)<br/>  })</pre> | `null` | no |
| environment | Extra environment variables for the container. | `map(string)` | `{}` | no |
| instance\_count | Instances behind the endpoint. 2 or more across AZs in prod; Floci supports 1. | `number` | `1` | no |
| instance\_type | Instance type for an instance-backed endpoint. | `string` | `"ml.c6i.large"` | no |
| kms\_key\_arn | KMS key for the endpoint's storage and captured data. Null uses AWS-managed keys. | `string` | `null` | no |
| network\_isolation | Run the container with no outbound network. True in npr and prod. | `bool` | `true` | no |
| serverless | Serverless inference instead of instances. Null for instance-backed. | <pre>object({<br/>    memory_size_in_mb       = number<br/>    max_concurrency         = number<br/>    provisioned_concurrency = optional(number)<br/>  })</pre> | `null` | no |
| tags | Tags applied to the model, endpoint config and endpoint. | `map(string)` | `{}` | no |
| vpc\_config | Subnets and security groups for the endpoint. Null outside a VPC (local). | <pre>object({<br/>    subnet_ids         = list(string)<br/>    security_group_ids = list(string)<br/>  })</pre> | `null` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| endpoint\_arn | Endpoint ARN, for invoke permissions. |
| endpoint\_config\_name | Endpoint config currently deployed. |
| endpoint\_name | Endpoint name to invoke. |
| model\_name | SageMaker model currently deployed. |
| model\_version | Released model version currently deployed. |
<!-- END_TF_DOCS -->