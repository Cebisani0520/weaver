module "runtime" {
  source = "../../../stacks/local_runtime"

  aws_region                 = var.aws_region
  floci_image                = var.floci_image
  confluent_platform_version = var.confluent_platform_version
  kind_node_image            = var.kind_node_image
  kubeconfig_path            = local.kubeconfig_path
  chart_versions             = var.chart_versions
  kafka_ui_enabled           = var.kafka_ui_enabled
  tags                       = local.tags
}
