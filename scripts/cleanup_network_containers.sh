#!/usr/bin/env bash
# Remove containers attached to the weaver network that Terraform does not
# manage: ones Floci starts itself (the floci-ui console sidecar, and from week 3
# SageMaker training and endpoint containers). Without this, destroying the
# network times out because it still has endpoints.
#
# Kept: containers labelled project=weaver (Terraform-managed) and the kind node.
#
# Usage: scripts/cleanup_network_containers.sh [network]
set -euo pipefail

NETWORK="${1:-weaver}"

if ! docker network inspect "$NETWORK" >/dev/null 2>&1; then
  echo "Network $NETWORK not found; nothing to clean up"
  exit 0
fi

mapfile -t attached < <(docker network inspect "$NETWORK" --format '{{range .Containers}}{{.Name}}{{"\n"}}{{end}}' | sed '/^$/d')

for name in "${attached[@]}"; do
  project=$(docker inspect -f '{{index .Config.Labels "project"}}' "$name" 2>/dev/null || true)
  kind_cluster=$(docker inspect -f '{{index .Config.Labels "io.x-k8s.kind.cluster"}}' "$name" 2>/dev/null || true)
  if [[ "$project" == "weaver" || -n "$kind_cluster" ]]; then
    continue
  fi
  echo "Removing $name (started outside Terraform)"
  docker rm -f "$name" >/dev/null
done
