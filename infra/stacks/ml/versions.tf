terraform {
  required_version = ">= 1.10"

  # Configured by the environment root (Floci locally, real AWS in npr and prod).
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
