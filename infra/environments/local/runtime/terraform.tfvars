floci_image                = "floci/floci:2.4.0"
confluent_platform_version = "8.0.0"
kind_node_image            = "kindest/node:v1.37.0"

# Pin flink_operator and cmf after the first successful install:
# Chart versions, pinned. When one changes, update the image tags in
# scripts/preload_kind_images.sh (and the compute pool image for a new CMF minor).

chart_versions = {
  cert_manager   = "v1.21.3"
  flink_operator = "1.161.1" # image flink-kubernetes-operator-1.161.1
  cmf            = "2.5.0"   # image cp-cmf:2.5.0
}
