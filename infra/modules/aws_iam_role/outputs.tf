output "name" {
  description = "Role name."
  value       = aws_iam_role.this.name
}

output "arn" {
  description = "Role ARN."
  value       = aws_iam_role.this.arn
}
