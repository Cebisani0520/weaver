#!/usr/bin/env bash
# Run a command with the CMF REST API port-forwarded to localhost, then stop the
# port-forward. Terraform's CMF modules call the API at http://localhost:8080.
#
# Usage: scripts/with_cmf.sh <command> [args...]
#        CMF_PORT=8080 scripts/with_cmf.sh terraform -chdir=infra/environments/local apply
set -euo pipefail

PORT="${CMF_PORT:-8080}"
KUBECONFIG="${KUBECONFIG:-$(git rev-parse --show-toplevel)/.kube/weaver}"
export KUBECONFIG
FLINK_NAMESPACE="${FLINK_NAMESPACE:-default}"
URL="http://localhost:${PORT}/cmf/api/v1/environments"

if curl -fsS "$URL" >/dev/null 2>&1; then
  # Something (for example `mise run cmf`) already serves CMF on this port.
  exec "$@"
fi

kubectl -n "$FLINK_NAMESPACE" port-forward svc/cmf-service "${PORT}:80" >/tmp/weaver-cmf-port-forward.log 2>&1 &
forward=$!
trap 'kill "$forward" 2>/dev/null || true' EXIT

for _ in $(seq 1 30); do
  curl -fsS "$URL" >/dev/null 2>&1 && break
  if ! kill -0 "$forward" 2>/dev/null; then
    echo "kubectl port-forward exited:" >&2
    cat /tmp/weaver-cmf-port-forward.log >&2
    exit 1
  fi
  sleep 1
done
curl -fsS "$URL" >/dev/null || { echo "CMF did not answer on port ${PORT}" >&2; exit 1; }

"$@"
