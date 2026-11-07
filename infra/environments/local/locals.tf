locals {
  floci_endpoint = "http://localhost:4566"
  repo_root      = abspath("${path.root}/../../..")

  tags = {
    project     = "weaver"
    environment = "local"
    managed_by  = "terraform"
  }

  # Every topics/*.yaml file contributes its topics (one file per use case).
  topic_files = fileset("${path.module}/topics", "*.yaml")
  topics = merge([
    for file_name in local.topic_files : yamldecode(file("${path.module}/topics/${file_name}")).topics
  ]...)

  # schemas/<topic>/value.avsc -> subject <topic>-value (TopicNameStrategy).
  schema_files = fileset("${path.module}/schemas", "*/*.avsc")
  schemas = {
    for file_name in local.schema_files :
    "${dirname(file_name)}-${trimsuffix(basename(file_name), ".avsc")}" => file("${path.module}/schemas/${file_name}")
  }

  # Flink statements per use case. The SQL files are shared with npr and prod.
  statements = {
    "fraud-score-features-v1" = {
      sql = file("${local.repo_root}/services/flink_sql/fraud_score/features.sql")
    }
  }
}
