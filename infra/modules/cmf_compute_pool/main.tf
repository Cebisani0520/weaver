# A compute pool: the template for the Flink cluster each statement runs on.
module "this" {
  source = "../cmf_rest_resource"

  base_url        = var.base_url
  collection_path = "/cmf/api/v1/environments/${var.environment}/compute-pools"
  resource_path   = "/cmf/api/v1/environments/${var.environment}/compute-pools/${var.name}"

  body = jsonencode({
    apiVersion = "cmf.confluent.io/v1"
    kind       = "ComputePool"
    metadata   = { name = var.name }
    spec = {
      type = "DEDICATED"
      clusterSpec = {
        flinkVersion       = var.flink_version
        image              = var.image
        flinkConfiguration = var.flink_configuration
        jobManager         = { resource = var.job_manager }
        taskManager        = { resource = var.task_manager }
      }
    }
  })
}
