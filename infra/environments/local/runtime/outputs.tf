output "endpoints" {
  description = "Addresses of the local services."
  value       = module.runtime.endpoints
}

output "kind" {
  description = "kind cluster details."
  value       = module.runtime.kind
}

output "cmf" {
  description = "Installed CMF and Flink operator releases."
  value       = module.runtime.cmf
}

output "terraform_backend" {
  description = "Floci S3 backend for the other local roots."
  value       = module.runtime.terraform_backend
}
