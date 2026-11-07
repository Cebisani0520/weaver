# A Schema Registry subject on a self-managed registry, over its REST API.
# npr and prod use confluent_schema instead.
#
# Two pieces, so that changing the schema registers a new version instead of
# deleting the subject:
#   - subject: sets the compatibility level; deletes the subject on destroy
#   - version: registers the schema; re-runs when the schema changes, and the
#     registry rejects it if it breaks the compatibility level
resource "terraform_data" "subject" {
  triggers_replace = [var.registry_url, var.subject]

  input = {
    registry_url = var.registry_url
    subject      = var.subject
  }

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      curl -sS --fail-with-body -X PUT \
        -H 'Content-Type: application/vnd.schemaregistry.v1+json' \
        --data "{\"compatibility\": \"$COMPATIBILITY\"}" \
        "$REGISTRY/config/$SUBJECT" >/dev/null
      echo "Subject $SUBJECT: compatibility $COMPATIBILITY"
    EOT
    environment = {
      REGISTRY      = var.registry_url
      SUBJECT       = var.subject
      COMPATIBILITY = var.compatibility
    }
  }

  provisioner "local-exec" {
    when        = destroy
    interpreter = ["bash", "-c"]
    command     = <<-EOT
      set -uo pipefail
      curl -sS -X DELETE "$REGISTRY/subjects/$SUBJECT" >/dev/null || true
      curl -sS -X DELETE "$REGISTRY/subjects/$SUBJECT?permanent=true" >/dev/null || true
      echo "Subject $SUBJECT deleted"
    EOT
    environment = {
      REGISTRY = self.input.registry_url
      SUBJECT  = self.input.subject
    }
  }
}

resource "terraform_data" "version" {
  triggers_replace = [sha256(var.schema), var.subject, var.registry_url]

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      response=$(curl -sS --fail-with-body -X POST \
        -H 'Content-Type: application/vnd.schemaregistry.v1+json' \
        --data "$BODY" "$REGISTRY/subjects/$SUBJECT/versions")
      echo "Subject $SUBJECT: registered $response"
    EOT
    environment = {
      REGISTRY = var.registry_url
      SUBJECT  = var.subject
      BODY     = jsonencode({ schemaType = var.schema_type, schema = var.schema })
    }
  }

  depends_on = [terraform_data.subject]
}
