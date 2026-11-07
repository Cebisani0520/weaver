# Blocks the apply until a readiness command succeeds on the machine running
# Terraform. Used to hold dependants (for example the state bucket) until a
# container is actually serving, not just started.
resource "terraform_data" "this" {
  triggers_replace = [var.name, var.command, var.trigger]

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    command     = <<-EOT
      set -u
      deadline=$((SECONDS + TIMEOUT))
      until bash -c "$CHECK" >/dev/null 2>&1; do
        if (( SECONDS >= deadline )); then
          echo "Timed out after $${TIMEOUT}s waiting for $NAME" >&2
          exit 1
        fi
        sleep "$INTERVAL"
      done
      echo "$NAME is ready"
    EOT

    environment = {
      NAME     = var.name
      CHECK    = var.command
      TIMEOUT  = tostring(var.timeout_seconds)
      INTERVAL = tostring(var.interval_seconds)
    }
  }
}
