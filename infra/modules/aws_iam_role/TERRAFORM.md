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
| [aws_iam_role.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_iam_role_policy_attachment.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| assume\_role\_policy | Trust policy JSON: who may assume the role. | `string` | n/a | yes |
| name | Role name. | `string` | n/a | yes |
| description | What the role is for. | `string` | `null` | no |
| inline\_policies | Inline policy JSON documents, by policy name. | `map(string)` | `{}` | no |
| managed\_policy\_arns | Managed policies to attach. Prefer least-privilege inline policies. | `list(string)` | `[]` | no |
| max\_session\_duration | Maximum session length in seconds. | `number` | `3600` | no |
| tags | Tags applied to the role. | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| arn | Role ARN. |
| name | Role name. |
<!-- END_TF_DOCS -->