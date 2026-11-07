# A Kafka catalog: points CMF at the Schema Registry that table schemas come from.
module "this" {
  source = "../cmf_rest_resource"

  base_url        = var.base_url
  collection_path = "/cmf/api/v1/catalogs/kafka"
  resource_path   = "/cmf/api/v1/catalogs/kafka/${var.name}"

  body = jsonencode({
    apiVersion = "cmf.confluent.io/v1"
    kind       = "KafkaCatalog"
    metadata   = { name = var.name }
    spec = {
      srInstance = {
        connectionConfig = { "schema.registry.url" = var.schema_registry_url }
      }
    }
  })
}
