resource "helm_release" "this" {
  name             = var.name
  repository       = var.repository
  chart            = var.chart
  version          = var.chart_version
  namespace        = var.namespace
  create_namespace = var.create_namespace
  values           = var.values
  wait             = true
  timeout          = var.timeout
  atomic           = true # a failed install is rolled back, so the name is free on the next apply
  cleanup_on_fail  = true

  set = [for key, value in var.set : { name = key, value = value }]
}
