output "name" {
  description = "Container name, which is also its hostname on the network."
  value       = docker_container.this.name
}

output "id" {
  description = "Container ID."
  value       = docker_container.this.id
}

output "image" {
  description = "Image reference the container runs."
  value       = var.image
}
