terraform {
  required_version = ">= 1.10"

  # Configured by the environment root.
  required_providers {
    kafka = {
      source  = "Mongey/kafka"
      version = "~> 0.8"
    }
  }
}
