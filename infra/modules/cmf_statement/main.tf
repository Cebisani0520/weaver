# A Flink SQL statement. Its SQL cannot change while it runs, so any change to
# the statement replaces it: the old job is deleted, then the new one submitted.
module "this" {
  source = "../cmf_rest_resource"

  base_url          = var.base_url
  collection_path   = "/cmf/api/v1/environments/${var.environment}/statements"
  resource_path     = "/cmf/api/v1/environments/${var.environment}/statements/${var.name}"
  replace_on_change = true

  body = jsonencode({
    apiVersion = "cmf.confluent.io/v1"
    kind       = "Statement"
    metadata   = { name = var.name }
    spec = {
      statement       = var.sql
      computePoolName = var.compute_pool
      parallelism     = var.parallelism
      stopped         = false
      properties = {
        "sql.current-catalog"  = var.catalog
        "sql.current-database" = var.database
      }
      flinkConfiguration = var.flink_configuration
    }
  })

  wait_for = {
    ok_phases       = var.ok_phases
    fail_phases     = ["FAILED", "FAILING"]
    timeout_seconds = var.wait_seconds
  }
}
