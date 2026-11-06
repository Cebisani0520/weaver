locals {
  floci_endpoint = "http://localhost:4566"

  tags = {
    project     = "weaver"
    environment = "local"
    managed_by  = "terraform"
  }
}
