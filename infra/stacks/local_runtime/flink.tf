# Confluent Manager for Apache Flink (CMF) on a local kind cluster.
# Install order follows Confluent's guide: cert-manager, then the Confluent Flink
# Kubernetes operator, then CMF.
module "kind" {
  source = "../../modules/kind_cluster"

  name            = var.kind_cluster_name
  node_image      = var.kind_node_image
  kubeconfig_path = var.kubeconfig_path

  # The node joins var.network_name through KIND_EXPERIMENTAL_DOCKER_NETWORK,
  # so the network has to exist first.
  depends_on = [module.network]
}

module "cert_manager" {
  source = "../../modules/helm_release"

  name             = "cert-manager"
  repository       = "https://charts.jetstack.io"
  chart            = "cert-manager"
  chart_version    = var.chart_versions.cert_manager
  namespace        = "cert-manager"
  create_namespace = true
  set              = { "crds.enabled" = "true" }

  depends_on = [module.kind]
}

module "flink_operator" {
  source = "../../modules/helm_release"

  name          = "cp-flink-kubernetes-operator"
  repository    = "https://packages.confluent.io/helm"
  chart         = "flink-kubernetes-operator"
  chart_version = var.chart_versions.flink_operator
  namespace     = var.flink_namespace

  depends_on = [module.cert_manager]
}

module "cmf" {
  source = "../../modules/helm_release"

  name          = "cmf"
  repository    = "https://packages.confluent.io/helm"
  chart         = "confluent-manager-for-apache-flink"
  chart_version = var.chart_versions.cmf
  namespace     = var.flink_namespace
  set           = { "cmf.sql.production" = "false" }
  # The CMF image is ~1.5 GB. scripts/preload_kind_images.sh loads it into the
  # node before this runs; the longer timeout covers a cold pull if it did not.
  timeout = 1200

  depends_on = [module.flink_operator]
}
