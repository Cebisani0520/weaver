output "endpoint_name" {
  description = "Endpoint name to invoke."
  value       = aws_sagemaker_endpoint.this.name
}

output "endpoint_arn" {
  description = "Endpoint ARN, for invoke permissions."
  value       = aws_sagemaker_endpoint.this.arn
}

output "endpoint_config_name" {
  description = "Endpoint config currently deployed."
  value       = aws_sagemaker_endpoint_configuration.this.name
}

output "model_name" {
  description = "SageMaker model currently deployed."
  value       = aws_sagemaker_model.this.name
}

output "model_version" {
  description = "Released model version currently deployed."
  value       = var.model_version
}
