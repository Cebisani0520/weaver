#!/usr/bin/env bash
# Build a model's image and push it to its ECR repository on Floci.
#
#   scripts/build_model_image.sh [model]      # default fraud-score
#
# The image is tagged with services/models/<model>/VERSION, both as
# weaver/<model>:<version> and with the full repository URI. The second tag
# lets Floci run training and endpoint containers straight from the host's
# image cache (FLOCI_SERVICES_ECR_PREFER_LOCAL_IMAGES), and the push makes the
# image visible to the ECR API as it would be on AWS.
set -euo pipefail

model="${1:-fraud-score}"
dir="services/models/${model//-/_}"
[ -f "$dir/Dockerfile" ] || { echo "no Dockerfile in $dir" >&2; exit 1; }
version="$(tr -d '[:space:]' < "$dir/VERSION")"

# Floci credentials for this script's commands only; nothing is exported to the shell.
floci_aws() {
  AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=eu-west-1 \
    aws --endpoint-url http://localhost:4566 "$@"
}

repo_uri="$(floci_aws ecr describe-repositories --repository-names "weaver/$model" \
  --query 'repositories[0].repositoryUri' --output text)" || {
  echo "ECR repository weaver/$model not found: apply the local root first (mise run up)" >&2
  exit 1
}
case "$repo_uri" in
  localhost:*) ;;
  *)
    echo "repository URI is $repo_uri, not path style." >&2
    echo "Recreate Floci with FLOCI_SERVICES_ECR_URI_STYLE=path (mise run up applies it)." >&2
    exit 1
    ;;
esac
registry="${repo_uri%%/*}"
image="$repo_uri:$version"

echo "building $image"
docker build --tag "weaver/$model:$version" --tag "$image" "$dir"

floci_aws ecr get-login-password | docker login --username AWS --password-stdin "$registry"
docker push "$image"
echo "pushed $image"
