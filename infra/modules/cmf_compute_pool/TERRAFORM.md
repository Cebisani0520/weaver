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
| environment | Environment the pool belongs to. | `string` | n/a | yes |
| flink\_version | Flink version of the pool's clusters, for example v2\_3. Must match the image. | `string` | n/a | yes |
| image | cp-flink-sql image built for this CMF version, for example confluentinc/cp-flink-sql:2.3-cmf2.5-cp1. | `string` | n/a | yes |
| name | Compute pool name. | `string` | n/a | yes |
| flink\_configuration | Flink configuration for every cluster started from this pool. | `map(string)` | `{}` | no |
| job\_manager | JobManager resources. | <pre>object({<br/>    cpu    = number<br/>    memory = string<br/>  })</pre> | <pre>{<br/>  "cpu": 0.5,<br/>  "memory": "1024m"<br/>}</pre> | no |
| task\_manager | TaskManager resources. | <pre>object({<br/>    cpu    = number<br/>    memory = string<br/>  })</pre> | <pre>{<br/>  "cpu": 0.5,<br/>  "memory": "1536m"<br/>}</pre> | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| name | Compute pool name. |
<!-- END_TF_DOCS -->