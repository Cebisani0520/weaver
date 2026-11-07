<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| terraform | >= 1.10 |

## Modules

| Name | Source | Version |
| ---- | ------ | ------- |
| catalog | ../../modules/cmf_kafka_catalog | n/a |
| compute\_pool | ../../modules/cmf_compute_pool | n/a |
| database | ../../modules/cmf_kafka_database | n/a |
| ddl | ../../modules/cmf_statement | n/a |
| environment | ../../modules/cmf_environment | n/a |
| statements | ../../modules/cmf_statement | n/a |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| bootstrap\_servers | Kafka bootstrap servers as seen from Flink pods. | `string` | `"broker:29092"` | no |
| catalog\_name | Kafka catalog name. | `string` | `"weaver"` | no |
| cmf\_url | CMF REST API as seen from the machine running Terraform (scripts/with\_cmf.sh port-forwards it). | `string` | `"http://localhost:8080"` | no |
| compute\_pool | The compute pool every statement runs on. | <pre>object({<br/>    name                = optional(string, "default")<br/>    flink_version       = optional(string, "v2_3")<br/>    image               = optional(string, "confluentinc/cp-flink-sql:2.3-cmf2.5-cp1")<br/>    flink_configuration = optional(map(string), {})<br/>    job_manager         = optional(object({ cpu = number, memory = string }), { cpu = 0.5, memory = "1024m" })<br/>    task_manager        = optional(object({ cpu = number, memory = string }), { cpu = 0.5, memory = "1536m" })<br/>  })</pre> | `{}` | no |
| database\_name | Kafka database name; tables are `<catalog>`.`<database>`.`<topic>`. | `string` | `"local"` | no |
| ddl\_statements | DDL statements by name, run before the streaming statements (for example ALTER TABLE ... MODIFY WATERMARK). | `map(string)` | `{}` | no |
| environment\_name | CMF environment for Weaver's statements. | `string` | `"weaver-local"` | no |
| kubernetes\_namespace | Namespace the environment's Flink clusters run in. | `string` | `"default"` | no |
| schema\_registry\_url | Schema Registry URL as seen from Flink pods. | `string` | `"http://schema-registry:8081"` | no |
| statement\_defaults | Flink configuration applied to every statement, under each statement's own. | `map(string)` | <pre>{<br/>  "execution.checkpointing.interval": "10 s",<br/>  "table.exec.source.idle-timeout": "5 s",<br/>  "table.local-time-zone": "UTC"<br/>}</pre> | no |
| statements | Statements by name. Changing a statement's SQL replaces its job. | <pre>map(object({<br/>    sql                 = string<br/>    parallelism         = optional(number, 1)<br/>    flink_configuration = optional(map(string), {})<br/>  }))</pre> | `{}` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| catalog | Catalog and database that expose the Kafka topics as tables. |
| compute\_pool | Compute pool name. |
| ddl\_statements | DDL statement names. |
| environment | CMF environment name. |
| statements | Running statement names. |
<!-- END_TF_DOCS -->