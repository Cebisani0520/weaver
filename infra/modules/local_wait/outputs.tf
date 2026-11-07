output "id" {
  description = "ID of the wait, for use in depends_on chains."
  value       = terraform_data.this.id
}
