output "network_name" {
  description = "Docker network every local component shares."
  value       = module.network.name
}

output "endpoints" {
  description = "Addresses of the local services, from the laptop and from inside the network."
  value = {
    floci = {
      host    = "http://localhost:${var.ports.floci}"
      network = "http://${module.floci.name}:4566"
      console = "http://localhost:${var.ports.floci}/_floci/ui"
    }
    kafka = {
      host    = "localhost:${var.ports.kafka}"
      network = "${module.broker.name}:29092"
    }
    schema_registry = {
      host    = "http://localhost:${var.ports.schema_registry}"
      network = "http://${module.schema_registry.name}:8081"
    }
    kafka_ui = var.kafka_ui_enabled ? "http://localhost:${var.ports.kafka_ui}" : null
  }
}

output "kind" {
  description = "kind cluster details."
  value = {
    name            = module.kind.name
    kubeconfig_path = module.kind.kubeconfig_path
  }
}

output "cmf" {
  description = "Installed CMF and operator releases."
  value = {
    namespace              = module.cmf.namespace
    cmf_chart_version      = module.cmf.chart_version
    operator_chart_version = module.flink_operator.chart_version
  }
}

output "terraform_backend" {
  description = "Floci S3 backend for the other local roots."
  value = {
    bucket     = module.tf_state_bucket.name
    lock_table = module.tf_lock_table.name
  }
}
