#!/usr/bin/env bash
# Pull the large Confluent images once into the host's Docker cache, then load
# them into the kind node. `mise run down` deletes the node and its image cache;
# the host cache survives, so later runs skip the ~1.5 GB CMF download.
#
# Images are imported for the node's platform only. `kind load docker-image`
# imports --all-platforms, which fails with Docker Desktop's containerd image
# store (it keeps a multi-platform index but only your platform's layers).
#
# Never fatal: if a preload fails, the node pulls the image itself and the CMF
# Helm timeout (20 minutes) covers the cold pull.
#
# Image tags must match the chart versions pinned in
# infra/environments/local/runtime/terraform.tfvars. Override with KIND_PRELOAD_IMAGES.
#
# Usage: scripts/preload_kind_images.sh
set -uo pipefail

CLUSTER="${KIND_CLUSTER_NAME:-weaver}"
NODE="${CLUSTER}-control-plane"
read -r -a IMAGES <<< "${KIND_PRELOAD_IMAGES:-confluentinc/cp-cmf:2.5.0 confluentinc/cp-flink-kubernetes-operator:1.16.1-cp1 confluentinc/cp-flink-sql:2.3-cmf2.5-cp1}"

case "$(docker exec "$NODE" uname -m)" in
  x86_64 | amd64) PLATFORM="linux/amd64" ;;
  aarch64 | arm64) PLATFORM="linux/arm64" ;;
  *) echo "WARN: unknown node architecture; skipping preload" >&2; exit 0 ;;
esac

on_node() {
  local image="$1"
  docker exec "$NODE" crictl inspecti "$image" >/dev/null 2>&1 \
    || docker exec "$NODE" crictl inspecti "docker.io/$image" >/dev/null 2>&1
}

# Export one platform when this Docker supports `save --platform`; otherwise the
# whole image, with the import below still selecting one platform.
save_image() {
  local image="$1"
  docker save --platform "$PLATFORM" "$image" 2>/dev/null || docker save "$image"
}

preload() {
  local image="$1"
  if on_node "$image"; then
    echo "$image already on $NODE"
    return 0
  fi
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "Pulling $image for $PLATFORM (first time only)"
    docker pull --platform "$PLATFORM" "$image" || return 1
  fi
  echo "Loading $image into $NODE ($PLATFORM)"
  save_image "$image" \
    | docker exec -i "$NODE" ctr --namespace=k8s.io images import \
        --platform "$PLATFORM" --digests --snapshotter=overlayfs -
}

for image in "${IMAGES[@]}"; do
  if ! preload "$image"; then
    echo "WARN: could not preload $image; the node will pull it during the Helm install" >&2
  fi
done
exit 0
