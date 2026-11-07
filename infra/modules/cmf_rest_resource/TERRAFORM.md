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
| [terraform_data.resource](https://registry.terraform.io/providers/hashicorp/terraform/latest/docs/resources/data) | resource |
| [terraform_data.update](https://registry.terraform.io/providers/hashicorp/terraform/latest/docs/resources/data) | resource |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| base\_url | CMF base URL as seen from the machine running Terraform, for example http://localhost:8080. | `string` | n/a | yes |
| body | JSON body of the resource. | `string` | n/a | yes |
| collection\_path | Path the resource is created under (POST), for example /cmf/api/v1/environments. | `string` | n/a | yes |
| resource\_path | Path of the resource itself (GET, PUT, DELETE). | `string` | n/a | yes |
| replace\_on\_change | Delete and recreate the resource when the body changes, instead of updating it. | `bool` | `false` | no |
| replace\_triggers | Extra values that replace the resource when they change, for example DDL a statement depends on. | `list(string)` | `[]` | no |
| update\_method | How a changed body is applied: PUT to the resource path, POST to the collection, or NONE. | `string` | `"PUT"` | no |
| wait\_for | Wait after creation until status.phase is one of ok\_phases; fail on fail\_phases. Empty ok\_phases skips the wait. | <pre>object({<br/>    ok_phases       = optional(list(string), [])<br/>    fail_phases     = optional(list(string), [])<br/>    timeout_seconds = optional(number, 600)<br/>  })</pre> | `{}` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| id | ID of the managed resource, for depends\_on chains. |
| resource\_path | Path of the resource. |
<!-- END_TF_DOCS -->