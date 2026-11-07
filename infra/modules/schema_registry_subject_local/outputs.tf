output "subject" {
  description = "Subject name."
  value       = var.subject
}

output "schema_sha256" {
  description = "Hash of the registered schema; changes when a new version is registered."
  value       = sha256(var.schema)
}

output "id" {
  description = "ID of the latest registration, for depends_on chains."
  value       = terraform_data.version.id
}
