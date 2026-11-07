output "topics" {
  description = "Topic names and partition counts."
  value       = { for name, topic in module.topics : name => topic.partitions }
}

output "subjects" {
  description = "Registered subjects and the hash of their current schema."
  value       = { for subject, s in module.schemas : subject => s.schema_sha256 }
}
