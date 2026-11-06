floci_image                = "floci/floci:2.4.0"
confluent_platform_version = "8.0.0"
kind_node_image            = "kindest/node:v1.37.0"

# Pin flink_operator and cmf after the first successful install:
#   helm repo add confluentinc https://packages.confluent.io/helm
#   helm search repo confluentinc --versions
chart_versions = {
  cert_manager   = "v1.21.3"
  flink_operator = null
  cmf            = null
}
