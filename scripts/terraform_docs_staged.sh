#!/usr/bin/env bash
# Regenerate TERRAFORM.md for every module or stack with staged .tf changes,
# then stage the result. Called by pre-commit.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

dirs=$(git diff --cached --name-only --diff-filter=ACMR -- 'infra/modules/*.tf' 'infra/stacks/*.tf' \
  | xargs -r -n1 dirname | sort -u)

for dir in $dirs; do
  [ -d "$dir" ] || continue
  terraform-docs --config .terraform-docs.yml "$dir"
  git add "$dir/TERRAFORM.md"
done
