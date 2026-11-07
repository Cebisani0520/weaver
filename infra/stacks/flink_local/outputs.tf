output "environment" {
  description = "CMF environment name."
  value       = module.environment.name
}

output "catalog" {
  description = "Catalog and database that expose the Kafka topics as tables."
  value       = { catalog = module.catalog.name, database = module.database.name }
}

output "compute_pool" {
  description = "Compute pool name."
  value       = module.compute_pool.name
}

output "statements" {
  description = "Running statement names."
  value       = [for s in module.statements : s.name]
}
