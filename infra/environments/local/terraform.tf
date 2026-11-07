terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    # Added in week 2 with the confluent_local and flink_local stacks:
    # kafka = { source = "Mongey/kafka" }
    # http  = { source = "hashicorp/http" }
  }
}
