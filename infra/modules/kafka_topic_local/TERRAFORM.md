<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| terraform | >= 1.10 |
| kafka | ~> 0.8 |

## Providers

| Name | Version |
| ---- | ------- |
| kafka | ~> 0.8 |

## Resources

| Name | Type |
| ---- | ---- |
| [kafka_topic.this](https://registry.terraform.io/providers/Mongey/kafka/latest/docs/resources/topic) | resource |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| name | Topic name. | `string` | n/a | yes |
| config | Topic configuration, for example cleanup.policy and retention.ms. | `map(string)` | `{}` | no |
| partitions | Number of partitions. Can only be increased after creation. | `number` | `6` | no |
| replication\_factor | Replication factor. 1 on the single local broker. | `number` | `1` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| name | Topic name. |
| partitions | Number of partitions. |
<!-- END_TF_DOCS -->