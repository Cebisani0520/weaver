#!/usr/bin/env bash
# Health checks for the local runtime. Exits non-zero on the first failure.
#
# Usage: scripts/wait_for_local.sh [timeout_seconds]
set -euo pipefail

TIMEOUT="${1:-180}"
KUBECONFIG="${KUBECONFIG:-$(git rev-parse --show-toplevel)/.kube/weaver}"
export KUBECONFIG
FLINK_NAMESPACE="${FLINK_NAMESPACE:-default}"

wait_for() {
  local name="$1" check="$2" deadline=$((SECONDS + TIMEOUT))
  printf '%-26s' "$name"
  until bash -c "$check" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      echo "FAILED (timed out after ${TIMEOUT}s)"
      echo "  check: $check" >&2
      return 1
    fi
    sleep 3
  done
  echo "ok"
}

wait_for "Floci" \
  "curl -fsS http://localhost:4566/_localstack/health"
wait_for "Floci S3 (state bucket)" \
  "AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=eu-west-1 \
   aws --endpoint-url http://localhost:4566 s3api head-bucket --bucket weaver-tfstate"
wait_for "Kafka broker" \
  "[ \"\$(docker inspect -f '{{.State.Health.Status}}' broker)\" = healthy ]"
wait_for "Schema Registry" \
  "curl -fsS http://localhost:8081/subjects"
wait_for "kind node" \
  "kubectl wait --for=condition=Ready nodes --all --timeout=5s"
wait_for "Flink operator" \
  "op=\$(kubectl -n $FLINK_NAMESPACE get deploy -o name | grep flink-kubernetes-operator) \
   && kubectl -n $FLINK_NAMESPACE rollout status \"\$op\" --timeout=5s"
# Ready when the service CMF's docs port-forward to has at least one ready pod.
wait_for "CMF" \
  "kubectl -n $FLINK_NAMESPACE get endpoints cmf-service -o jsonpath='{.subsets[*].addresses[*].ip}' | grep -q ."

echo "Local runtime is healthy."
