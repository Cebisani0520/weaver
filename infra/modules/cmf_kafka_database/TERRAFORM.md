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
| bootstrap\_servers | Kafka bootstrap servers as seen from Flink pods, for example broker:29092. | `string` | n/a | yes |
| catalog | Kafka catalog the database belongs to. | `string` | n/a | yes |
| name | Database name; the second part of a table's fully qualified name. | `string` | n/a | yes |
| ddl\_environments | Environments allowed to run DDL statements against this database. | `list(string)` | `[]` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| name | Database name. |
<!-- END_TF_DOCS -->