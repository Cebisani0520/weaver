output "resource_path" {
  description = "Path of the resource."
  value       = var.resource_path
}

output "id" {
  description = "ID of the managed resource, for depends_on chains."
  value       = terraform_data.resource.id
}
