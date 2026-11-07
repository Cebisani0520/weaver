output "name" {
  description = "Database name."
  value       = var.name
  depends_on  = [module.this]
}
