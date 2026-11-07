# AGENTS.md

Reference for coding agents (and people) working in this repository. Read this before changing anything under `infra/`.

## What this is

Weaver is a platform for real-time ML decisions on Kafka events: Flink computes features, a SageMaker model scores each event, and the decision goes back to Kafka. Fraud scoring is the first use case. The design and plan live in the project plan doc linked from `README.md`.

Environments:

| Environment | Kafka and Flink | AWS |
| --- | --- | --- |
| `local` | Confluent Platform in Docker, CMF on kind | Floci on `localhost:4566` |
| `npr`, `prod` | Confluent Cloud | Real AWS account, `eu-west-1` |

## Layout

- `infra/environments/<env>/` — Terraform roots. The **only** place providers are configured and stacks are called.
  - `local/runtime/` is its own root with local state. It creates the containers, kind + CMF, and the Floci S3 bucket and DynamoDB table that every other local root uses as its backend.
- `infra/stacks/<stack>/` — compositions of modules. **No `resource` blocks.**
- `infra/modules/<module>/` — the only place a `resource` (including `terraform_data`) may appear. Each has `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf`, and a generated `TERRAFORM.md`.
- `services/` — application code: models, Flink UDF and SQL, generators, dashboard.
- `scripts/` — health checks, smoke tests, repo-rule checks, helpers called by Terraform.
- `tests/unit`, `tests/integration`, `tests/e2e`.

## Rules (enforced by pre-commit)

1. **Stacks only call modules.** `scripts/check_stack_resources.py` fails on any `resource` block under `infra/stacks/`. Data sources, locals and outputs are fine in stacks.
2. **Providers are configured only in environment roots.** Modules and stacks declare `required_providers` and inherit configuration. A unit test fails on any `provider` block under `infra/modules` or `infra/stacks`.
3. **One AWS code path.** The same `aws` and `ml` stacks run against Floci and real AWS. Only `providers.tf` differs.
4. **Every AWS service used locally has a Floci endpoint.** `scripts/check_floci_endpoints.py` walks each local root's module tree and fails if a resource type has no matching key in that root's `endpoints` block. When adding a new AWS service, add the endpoint and, if needed, its prefix to `SERVICE_PREFIXES`.
5. **Floci gaps are variables, never environment checks.** For example `kms_key_arn = null` locally. Modules use `count` or `dynamic` blocks on those variables and never test `env == "local"`.
6. **Confluent implementations are chosen in the root.** `confluent` vs `confluent_local`, `flink` vs `flink_local`: paired stacks take the same inputs and expose the same outputs.
7. **Pin images and chart versions.** `docker_container` rejects `:latest` and untagged images. The Floci tag is upgraded in its own pull request (see README, Floci support baseline).
8. **Every variable and output has a description.** A unit test enforces it.
9. **No secrets in files.** Use fnox. Floci's `test` credentials are not secrets and are allow-listed for betterleaks.

## Running things

```bash
mise install            # tools
mise run setup          # uv sync + pre-commit install
mise run up             # local runtime + local root
mise run status         # health checks
mise run smoke          # pods in kind reach broker, schema-registry, floci
mise run deploy local   # topics, schemas, CMF objects, Flink statements
mise run takeover       # live traffic + account-takeover scenario
mise run gate2          # live features vs the reference
mise run test           # unit (+ integration when the runtime is up)
mise run test-flink     # Flink SQL on local PyFlink vs the reference
mise run lint           # all pre-commit hooks
mise run down           # tear down
eval "$(mise run floci-env)"   # point the AWS CLI at Floci in this shell
```

There is no Terraform binary or registry access in some sandboxes; when that is the case, `mise run test` still checks HCL syntax, module structure and the repo rules.

## Streaming conventions

- **Topics** come from `infra/environments/<env>/topics/*.yaml`, one file per use case. **Schemas** come from `schemas/<topic>/value.avsc` (subject `<topic>-value`). Only value schemas are registered; message keys are the hashed customer ID as plain bytes.
- **Producers never register schemas.** Terraform owns them; clients use `auto.register.schemas=false` and `use.latest.version=true`.
- **Event time is the Kafka record timestamp.** Producers set it to the event's `event_time`. CMF's default watermark allows no lateness, so send events in time order per partition.
- **Flink SQL lives in files** under `services/flink_sql/<use_case>/` and is passed to the `flink_local` stack from `local.statements` in the environment root. A statement's SQL cannot change while it runs: changing it replaces the job. Put a version in the statement name.
- **Every SQL feature has a plain-Python reference** (`reference_features.py`). `mise run test-flink` runs the SQL file unchanged on a local PyFlink and compares every row; `mise run gate2` does the same against the live stack.
- **Flink 2.3.** Compute pools run Flink 2.3 (`v2_3`, image `cp-flink-sql:2.3-cmf2.5-cp1`). A pool's Flink version cannot change while it has statements; upgrading means a new pool and new statements, which start with empty state. The pool image, `preload_kind_images.sh` and the PyFlink version in `test-flink` move together.
- **Python 3.12 compatibility.** `mise run test-flink` imports the generator and `reference_features.py` under PyFlink's Python 3.12. Keep those modules free of 3.13-only syntax.
- **CMF has no Terraform provider.** The `cmf_*` modules call its REST API through `cmf_rest_resource`; anything that applies the local root runs under `scripts/with_cmf.sh`, which port-forwards CMF.

## Adding things

- **A resource:** add or extend a module in `infra/modules`, then call it from a stack.
- **A local container:** call `modules/docker_container` from `stacks/local_runtime`; attach it to `module.network.name`; add a readiness check with `modules/local_wait` and to `scripts/wait_for_local.sh`.
- **An AWS service:** module first, then the Floci endpoint in `infra/environments/local/providers.tf`, then the stack call. Check the Floci support baseline in the README before relying on it locally.
- **A use case:** follow "Adding a use case" in the README.

## Conventions

- Region `eu-west-1` everywhere, including Floci.
- Container names double as hostnames on the `weaver` network: `floci`, `broker`, `schema-registry`, `kafka-ui`.
- Host ports bind to `127.0.0.1` only.
- Python 3.13, `uv`, `ruff`, `mypy --strict`. Scripts are run as modules: `python -m scripts.<name>`.
