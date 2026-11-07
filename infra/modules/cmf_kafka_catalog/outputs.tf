output "name" {
  description = "Catalog name."
  value       = var.name
  depends_on  = [module.this]
}
