<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| terraform | >= 1.10 |
| aws | ~> 6.0 |
| docker | ~> 3.0 |
| helm | ~> 3.0 |
| kind | ~> 0.8 |

## Modules

| Name | Source | Version |
| ---- | ------ | ------- |
| broker | ../../modules/docker_container | n/a |
| broker\_ready | ../../modules/local_wait | n/a |
| cert\_manager | ../../modules/helm_release | n/a |
| cmf | ../../modules/helm_release | n/a |
| flink\_operator | ../../modules/helm_release | n/a |
| floci | ../../modules/docker_container | n/a |
| floci\_ready | ../../modules/local_wait | n/a |
| kafka\_ui | ../../modules/docker_container | n/a |
| kind | ../../modules/kind_cluster | n/a |
| network | ../../modules/docker_network | n/a |
| schema\_registry | ../../modules/docker_container | n/a |
| schema\_registry\_ready | ../../modules/local_wait | n/a |
| tf\_lock\_table | ../../modules/aws_dynamodb_table | n/a |
| tf\_state\_bucket | ../../modules/aws_s3_bucket | n/a |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| kubeconfig\_path | Absolute path the kind kubeconfig is written to. | `string` | n/a | yes |
| aws\_region | Region Floci reports. Matches npr and prod. | `string` | `"eu-west-1"` | no |
| chart\_versions | Helm chart versions. Null installs the latest; pin each once proven (week 1 task). | <pre>object({<br/>    cert_manager   = optional(string, "v1.21.3")<br/>    flink_operator = optional(string)<br/>    cmf            = optional(string)<br/>  })</pre> | `{}` | no |
| confluent\_platform\_version | Confluent Platform image tag for the broker and Schema Registry. | `string` | `"8.0.0"` | no |
| docker\_socket\_path | Host path of the Docker socket mounted into Floci. | `string` | `"/var/run/docker.sock"` | no |
| flink\_namespace | Namespace for the Flink operator, CMF and Flink jobs. | `string` | `"default"` | no |
| floci\_image | Floci image, pinned. Upgrading is its own pull request (see README, Floci support baseline). | `string` | `"floci/floci:2.4.0"` | no |
| kafka\_cluster\_id | KRaft cluster ID: 22 characters of base64. Changing it requires wiping the Kafka volume. | `string` | `"MkU3OEVBNTcwNTJENDM2Qk"` | no |
| kafka\_ui\_enabled | Run the Kafka UI container. | `bool` | `true` | no |
| kafka\_ui\_image | Kafka UI image, pinned. | `string` | `"kafbat/kafka-ui:v1.5.0"` | no |
| kind\_cluster\_name | Name of the kind cluster that runs CMF. | `string` | `"weaver"` | no |
| kind\_node\_image | kindest/node image, pinned. | `string` | `"kindest/node:v1.37.0"` | no |
| network\_name | Docker network shared by every local container and the kind node. | `string` | `"weaver"` | no |
| ports | Host ports, all bound to 127.0.0.1. | <pre>object({<br/>    floci           = optional(number, 4566)<br/>    kafka           = optional(number, 9092)<br/>    schema_registry = optional(number, 8081)<br/>    kafka_ui        = optional(number, 9021)<br/>  })</pre> | `{}` | no |
| tags | Tags applied to AWS resources. | `map(string)` | `{}` | no |
| tf\_lock\_table | Floci DynamoDB table used for state locking. | `string` | `"weaver-tflock"` | no |
| tf\_state\_bucket | Floci S3 bucket holding state for the other local roots. | `string` | `"weaver-tfstate"` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| cmf | Installed CMF and operator releases. |
| endpoints | Addresses of the local services, from the laptop and from inside the network. |
| kind | kind cluster details. |
| network\_name | Docker network every local component shares. |
| terraform\_backend | Floci S3 backend for the other local roots. |
<!-- END_TF_DOCS -->