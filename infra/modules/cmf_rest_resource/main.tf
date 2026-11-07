# One resource in Confluent Manager for Apache Flink, managed over its REST API.
# There is no Terraform provider for CMF, so the typed cmf_* modules wrap this.
#
#   - resource: POSTs the body on create (409 Conflict counts as already there),
#     optionally waits for status.phase, DELETEs on destroy. Replaced when its
#     identity changes, or when the body changes if replace_on_change is set
#     (statements: their SQL is immutable once running).
#   - update: re-sends the body when it changes, with update_method, for
#     resources CMF can update in place (environments, catalogs, pools).
resource "terraform_data" "resource" {
  triggers_replace = concat(
    [var.base_url, var.resource_path],
    var.replace_on_change ? [sha256(var.body)] : [],
    var.replace_triggers,
  )

  input = {
    base_url      = var.base_url
    resource_path = var.resource_path
  }

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      response=$(mktemp)
      trap 'rm -f "$response"' EXIT
      code=$(curl -sS -o "$response" -w '%%{http_code}' -X POST \
        -H 'Content-Type: application/json' --data "$BODY" "$BASE_URL$COLLECTION_PATH")
      case "$code" in
        2??) echo "Created $RESOURCE_PATH" ;;
        409) echo "$RESOURCE_PATH already exists" ;;
        *)   echo "POST $COLLECTION_PATH failed with HTTP $code:" >&2; cat "$response" >&2; exit 1 ;;
      esac

      if [ -n "$OK_PHASES" ]; then
        deadline=$((SECONDS + WAIT_SECONDS))
        while :; do
          phase=$(curl -sS "$BASE_URL$RESOURCE_PATH" \
            | python3 -c 'import json,sys; print((json.load(sys.stdin).get("status") or {}).get("phase", ""))' \
            || true)
          case " $OK_PHASES " in *" $phase "*) echo "$RESOURCE_PATH is $phase"; break ;; esac
          case " $FAIL_PHASES " in
            *" $phase "*)
              echo "$RESOURCE_PATH is $phase:" >&2
              curl -sS "$BASE_URL$RESOURCE_PATH" >&2 || true
              exit 1 ;;
          esac
          if (( SECONDS >= deadline )); then
            echo "Timed out after $${WAIT_SECONDS}s; $RESOURCE_PATH is '$phase'" >&2
            exit 1
          fi
          sleep 5
        done
      fi
    EOT
    environment = {
      BASE_URL        = var.base_url
      COLLECTION_PATH = var.collection_path
      RESOURCE_PATH   = var.resource_path
      BODY            = var.body
      OK_PHASES       = join(" ", var.wait_for.ok_phases)
      FAIL_PHASES     = join(" ", var.wait_for.fail_phases)
      WAIT_SECONDS    = tostring(var.wait_for.timeout_seconds)
    }
  }

  provisioner "local-exec" {
    when        = destroy
    interpreter = ["bash", "-c"]
    command     = <<-EOT
      set -uo pipefail
      code=$(curl -sS -o /dev/null -w '%%{http_code}' -X DELETE "$BASE_URL$RESOURCE_PATH")
      case "$code" in
        2??|404) echo "Deleted $RESOURCE_PATH" ;;
        *) echo "DELETE $RESOURCE_PATH failed with HTTP $code" >&2; exit 1 ;;
      esac
    EOT
    environment = {
      BASE_URL      = self.input.base_url
      RESOURCE_PATH = self.input.resource_path
    }
  }
}

resource "terraform_data" "update" {
  count            = var.update_method == "NONE" || var.replace_on_change ? 0 : 1
  triggers_replace = [sha256(var.body)]

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      target="$RESOURCE_PATH"
      [ "$METHOD" = POST ] && target="$COLLECTION_PATH"
      response=$(mktemp)
      trap 'rm -f "$response"' EXIT
      code=$(curl -sS -o "$response" -w '%%{http_code}' -X "$METHOD" \
        -H 'Content-Type: application/json' --data "$BODY" "$BASE_URL$target")
      case "$code" in
        2??) echo "Up to date: $RESOURCE_PATH" ;;
        *)   echo "$METHOD $target failed with HTTP $code:" >&2; cat "$response" >&2; exit 1 ;;
      esac
    EOT
    environment = {
      BASE_URL        = var.base_url
      COLLECTION_PATH = var.collection_path
      RESOURCE_PATH   = var.resource_path
      METHOD          = var.update_method
      BODY            = var.body
    }
  }

  depends_on = [terraform_data.resource]
}
