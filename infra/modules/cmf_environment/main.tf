module "this" {
  source = "../cmf_rest_resource"

  base_url        = var.base_url
  collection_path = "/cmf/api/v1/environments"
  resource_path   = "/cmf/api/v1/environments/${var.name}"
  # CMF creates or updates an environment with the same POST.
  update_method = "POST"

  body = jsonencode({
    name                = var.name
    kubernetesNamespace = var.kubernetes_namespace
  })
}
