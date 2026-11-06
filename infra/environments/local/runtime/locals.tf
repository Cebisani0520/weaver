locals {
  repo_root       = abspath("${path.root}/../../../..")
  kubeconfig_path = "${local.repo_root}/.kube/weaver"
  floci_endpoint  = "http://localhost:4566"

  tags = {
    project     = "weaver"
    environment = "local"
    managed_by  = "terraform"
  }
}
