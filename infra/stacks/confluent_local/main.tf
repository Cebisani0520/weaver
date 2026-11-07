# Topics and schemas on the local Confluent Platform broker and Schema Registry.
# Same inputs and outputs as the Confluent Cloud `confluent` stack, so the
# environment root picks one or the other and nothing downstream changes.
module "topics" {
  source   = "../../modules/kafka_topic_local"
  for_each = var.topics

  name               = each.key
  partitions         = each.value.partitions
  replication_factor = var.replication_factor
  config             = each.value.config
}

module "schemas" {
  source   = "../../modules/schema_registry_subject_local"
  for_each = var.schemas

  registry_url  = var.schema_registry_url
  subject       = each.key
  schema        = each.value
  compatibility = var.compatibility
}
