output "name" {
  description = "Name of the kind cluster."
  value       = kind_cluster.this.name
}

output "endpoint" {
  description = "Kubernetes API server endpoint."
  value       = kind_cluster.this.endpoint
}

output "kubeconfig_path" {
  description = "Path of the kubeconfig written for the cluster."
  value       = kind_cluster.this.kubeconfig_path
}
