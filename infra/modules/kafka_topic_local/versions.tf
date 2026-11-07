terraform {
  required_version = ">= 1.10"

  required_providers {
    kafka = {
      source  = "Mongey/kafka"
      version = "~> 0.8"
    }
  }
}
