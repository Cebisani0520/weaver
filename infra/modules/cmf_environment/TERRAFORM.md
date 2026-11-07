<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| terraform | >= 1.10 |

## Modules

| Name | Source | Version |
| ---- | ------ | ------- |
| this | ../cmf_rest_resource | n/a |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| base\_url | CMF base URL as seen from the machine running Terraform. | `string` | n/a | yes |
| name | Environment name. | `string` | n/a | yes |
| kubernetes\_namespace | Namespace the environment's Flink clusters run in. | `string` | `"default"` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| name | Environment name. |
<!-- END_TF_DOCS -->