output "aws_account_id" {
  description = "Account ID Floci reports (000000000000 by default)."
  value       = data.aws_caller_identity.current.account_id
}
