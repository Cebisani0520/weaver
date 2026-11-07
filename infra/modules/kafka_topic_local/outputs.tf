output "name" {
  description = "Topic name."
  value       = kafka_topic.this.name
}

output "partitions" {
  description = "Number of partitions."
  value       = kafka_topic.this.partitions
}
