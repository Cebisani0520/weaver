#!/usr/bin/env bash
# smoke test: from a pod inside the kind cluster, resolve and reach the
# broker, Schema Registry and Floci by container name. If this passes, Flink
# jobs running in CMF can reach Kafka and the SageMaker endpoint.
#
# Usage: scripts/smoke_kind_network.sh
set -euo pipefail

KUBECONFIG="${KUBECONFIG:-$(git rev-parse --show-toplevel)/.kube/weaver}"
export KUBECONFIG
IMAGE="${SMOKE_IMAGE:-busybox:1.37}"
POD="weaver-net-smoke"

kubectl delete pod "$POD" --ignore-not-found --wait=true >/dev/null

# shellcheck disable=SC2016  # the script body runs inside the pod, not here
kubectl run "$POD" --image="$IMAGE" --restart=Never --attach --rm --quiet -- sh -c '
  set -e
  fail=0
  check() {
    if eval "$2" >/dev/null 2>&1; then echo "ok    $1"; else echo "FAIL  $1"; fail=1; fi
  }
  # Each check connects by container name, so it proves DNS and reachability.
  # (busybox nslookup is not used: it fails on search-domain and AAAA lookups
  # inside Kubernetes even when the name resolves.)
  check "broker:29092 (tcp)"           "nc -z -w 5 broker 29092"
  check "schema-registry:8081 (http)"  "wget -q -O - http://schema-registry:8081/subjects"
  check "floci:4566 (http)"            "wget -q -O - http://floci:4566/_localstack/health"
  exit $fail
'
echo "Pods in kind can reach Kafka, Schema Registry and Floci."
