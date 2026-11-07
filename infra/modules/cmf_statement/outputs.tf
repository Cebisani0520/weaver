output "name" {
  description = "Statement name."
  value       = var.name
  depends_on  = [module.this]
}
