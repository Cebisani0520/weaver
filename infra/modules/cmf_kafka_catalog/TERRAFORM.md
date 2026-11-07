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
| name | Catalog name; the first part of a table's fully qualified name. | `string` | n/a | yes |
| schema\_registry\_url | Schema Registry URL as seen from Flink pods (inside kind), for example http://schema-registry:8081. | `string` | n/a | yes |

## Outputs

| Name | Description |
| ---- | ----------- |
| name | Catalog name. |
<!-- END_TF_DOCS -->