#!/usr/bin/env bash
# Expose the CMF REST API (and UI, when enabled) on localhost:8080.
# Point the Confluent CLI at it with:  confluent flink ... --url http://localhost:8080
#
# Usage: scripts/cmf_port_forward.sh [local_port]
set -euo pipefail

PORT="${1:-8080}"
KUBECONFIG="${KUBECONFIG:-$(git rev-parse --show-toplevel)/.kube/weaver}"
export KUBECONFIG
FLINK_NAMESPACE="${FLINK_NAMESPACE:-default}"

echo "CMF on http://localhost:${PORT} (Ctrl-C to stop)"
exec kubectl -n "$FLINK_NAMESPACE" port-forward svc/cmf-service "${PORT}:80"
