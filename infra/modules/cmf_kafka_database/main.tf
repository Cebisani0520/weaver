# A Kafka database: exposes every topic of one Kafka cluster as a table.
module "this" {
  source = "../cmf_rest_resource"

  base_url        = var.base_url
  collection_path = "/cmf/api/v1/catalogs/kafka/${var.catalog}/databases"
  resource_path   = "/cmf/api/v1/catalogs/kafka/${var.catalog}/databases/${var.name}"

  body = jsonencode({
    apiVersion = "cmf.confluent.io/v1"
    kind       = "KafkaDatabase"
    metadata   = { name = var.name }
    spec = {
      kafkaCluster = {
        connectionConfig = { "bootstrap.servers" = var.bootstrap_servers }
      }
      # Environments allowed to run DDL (ALTER TABLE, CREATE TABLE) here.
      ddlEnvironments = var.ddl_environments
    }
  })
}
