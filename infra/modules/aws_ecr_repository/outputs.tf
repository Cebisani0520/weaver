output "name" {
  description = "Repository name."
  value       = aws_ecr_repository.this.name
}

output "arn" {
  description = "Repository ARN."
  value       = aws_ecr_repository.this.arn
}

output "url" {
  description = "Repository URL, without a tag. Floci returns a localhost URL."
  value       = aws_ecr_repository.this.repository_url
}
