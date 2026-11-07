<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| terraform | >= 1.10 |
| helm | ~> 3.0 |

## Providers

| Name | Version |
| ---- | ------- |
| helm | ~> 3.0 |

## Resources

| Name | Type |
| ---- | ---- |
| [helm_release.this](https://registry.terraform.io/providers/hashicorp/helm/latest/docs/resources/release) | resource |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| chart | Chart name in the repository. | `string` | n/a | yes |
| name | Helm release name. | `string` | n/a | yes |
| repository | Chart repository URL. | `string` | n/a | yes |
| chart\_version | Chart version or constraint. Null installs the latest; pin it once a version is proven. | `string` | `null` | no |
| create\_namespace | Create the namespace if it does not exist. | `bool` | `false` | no |
| namespace | Namespace the release is installed into. | `string` | `"default"` | no |
| set | Individual chart values, keyed by their dotted path. | `map(string)` | `{}` | no |
| timeout | Seconds to wait for the release's resources to become ready. | `number` | `600` | no |
| values | Raw YAML values documents, applied in order. | `list(string)` | `[]` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| chart\_version | Chart version actually installed. |
| name | Helm release name. |
| namespace | Namespace of the release. |
<!-- END_TF_DOCS -->