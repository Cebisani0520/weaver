<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| terraform | >= 1.10 |

## Providers

| Name | Version |
| ---- | ------- |
| terraform | n/a |

## Resources

| Name | Type |
| ---- | ---- |
| [terraform_data.subject](https://registry.terraform.io/providers/hashicorp/terraform/latest/docs/resources/data) | resource |
| [terraform_data.version](https://registry.terraform.io/providers/hashicorp/terraform/latest/docs/resources/data) | resource |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| registry\_url | Schema Registry base URL as seen from the machine running Terraform. | `string` | n/a | yes |
| schema | Schema definition as a string (the contents of the .avsc file). | `string` | n/a | yes |
| subject | Subject name, {topic}-value or {topic}-key under TopicNameStrategy. | `string` | n/a | yes |
| compatibility | Compatibility level enforced on new versions. | `string` | `"BACKWARD"` | no |
| schema\_type | AVRO, JSON or PROTOBUF. | `string` | `"AVRO"` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| id | ID of the latest registration, for depends\_on chains. |
| schema\_sha256 | Hash of the registered schema; changes when a new version is registered. |
| subject | Subject name. |
<!-- END_TF_DOCS -->