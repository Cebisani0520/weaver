<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| terraform | >= 1.10 |
| kafka | ~> 0.8 |

## Modules

| Name | Source | Version |
| ---- | ------ | ------- |
| schemas | ../../modules/schema_registry_subject_local | n/a |
| topics | ../../modules/kafka_topic_local | n/a |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| schema\_registry\_url | Schema Registry URL as seen from the machine running Terraform. | `string` | n/a | yes |
| topics | Topics by name, decoded from the environment's topics/*.yaml. | <pre>map(object({<br/>    partitions = optional(number, 6)<br/>    config     = optional(map(string), {})<br/>  }))</pre> | n/a | yes |
| compatibility | Compatibility level for every subject. | `string` | `"BACKWARD"` | no |
| replication\_factor | Replication factor for every topic. 1 on the single local broker. | `number` | `1` | no |
| schemas | Schema definitions by subject ({topic}-value or {topic}-key), from the environment's schemas/ folder. | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| subjects | Registered subjects and the hash of their current schema. |
| topics | Topic names and partition counts. |
<!-- END_TF_DOCS -->