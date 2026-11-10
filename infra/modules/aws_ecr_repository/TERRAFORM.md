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
| [aws_ecr_lifecycle_policy.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecr_lifecycle_policy) | resource |
| [aws_ecr_repository.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecr_repository) | resource |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| name | Repository name, e.g. weaver/fraud-score. | `string` | n/a | yes |
| force\_delete | Allow deleting the repository while it holds images. True only for local and disposable environments. | `bool` | `false` | no |
| image\_tag\_mutability | MUTABLE or IMMUTABLE. IMMUTABLE for npr and prod. | `string` | `"IMMUTABLE"` | no |
| keep\_images | Expire all but this many images. Null adds no lifecycle policy. | `number` | `null` | no |
| kms\_key\_arn | KMS key for image encryption. Null uses AES256. | `string` | `null` | no |
| scan\_on\_push | Scan images for vulnerabilities when pushed. | `bool` | `true` | no |
| tags | Tags applied to the repository. | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| arn | Repository ARN. |
| name | Repository name. |
| url | Repository URL, without a tag. Floci returns a localhost URL. |
<!-- END_TF_DOCS -->