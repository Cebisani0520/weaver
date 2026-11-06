terraform {
  required_version = ">= 1.10"

  # Local state on purpose: this root creates the Floci S3 bucket and lock
  # table that every other local root uses as its backend.
  backend "local" {
    path = "terraform.tfstate"
  }

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
    kind = {
      source  = "tehcyx/kind"
      version = "~> 0.8"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 3.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
