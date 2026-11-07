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
| catalog | Current catalog for unqualified table names. | `string` | n/a | yes |
| compute\_pool | Compute pool the statement runs on. | `string` | n/a | yes |
| database | Current database for unqualified table names. | `string` | n/a | yes |
| environment | Environment the statement runs in. | `string` | n/a | yes |
| name | Statement name. Include a version, for example fraud-score-features-v1. | `string` | n/a | yes |
| sql | The SQL statement. | `string` | n/a | yes |
| flink\_configuration | Flink configuration for this statement, merged over the pool's. Streaming INSERTs need execution.checkpointing.interval. | `map(string)` | `{}` | no |
| ok\_phases | Phases that count as success: RUNNING for streaming statements, COMPLETED for DDL. | `list(string)` | <pre>[<br/>  "RUNNING",<br/>  "COMPLETED"<br/>]</pre> | no |
| parallelism | Statement parallelism. | `number` | `1` | no |
| wait\_seconds | Seconds to wait for the statement to reach an ok phase. The first run pulls the Flink SQL image. | `number` | `900` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| name | Statement name. |
<!-- END_TF_DOCS -->