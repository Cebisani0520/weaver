output "name" {
  description = "Compute pool name."
  value       = var.name
  depends_on  = [module.this]
}
