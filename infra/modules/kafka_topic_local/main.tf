# A topic on a self-managed Kafka cluster (the local Confluent Platform broker).
# npr and prod use confluent_kafka_topic instead, from the same topics/*.yaml.
resource "kafka_topic" "this" {
  name               = var.name
  partitions         = var.partitions
  replication_factor = var.replication_factor
  config             = var.config
}
