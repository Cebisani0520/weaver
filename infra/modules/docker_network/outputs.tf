output "name" {
  description = "Name of the Docker network."
  value       = docker_network.this.name
}

output "id" {
  description = "ID of the Docker network."
  value       = docker_network.this.id
}
