output "name" {
  description = "Environment name."
  value       = var.name
  depends_on  = [module.this]
}
