# Week 3 file changes

Two folders, laid out at repository paths.

## 1. `new/`: 39 new files, copy them in as they are

From the repository root:

    cp -R /path/to/w3/new/. .
    chmod +x scripts/build_model_image.sh services/models/fraud_score/bin/train services/models/fraud_score/bin/serve

None of these files exist in week 2, so copying them overwrites nothing.

## 2. `modified/`: 17 changed files

`modified/` has the full week 3 version of each file. The diffs below show the
exact changes against week 2, so you can paste just those edits wherever your
copy differs from mine.

| File | How to apply |
| --- | --- |
| `.mise.toml` | **Paste the edits.** Your `[tools]` section differs from mine; the changes are only in tasks (gate2 path, five new tasks before `[tasks.lint]`, one comment) |
| `pyproject.toml` | **Paste the edits** (three dev dependencies), then `uv sync`, which rewrites `uv.lock`. Do not copy uv.lock |
| `.gitignore` | Paste the edits (two entries) |
| `README.md`, `AGENTS.md` | Replace, or paste the edits if you changed them |
| everything else | Replace the whole file, unless you edited it after week 2 |

Then:

    uv sync
    mise run test      # 63 passed expected, integration tests skip while the runtime is down

---

## Diffs against week 2

### `.gitignore`

```diff
--- a/.gitignore
+++ b/.gitignore
@@ -10,6 +10,13 @@
 # kind kubeconfig written by the runtime root
 .kube/

+# Locally approved model versions: they point at the local MLflow registry,
+# which a fresh clone does not have. npr and prod commit theirs.
+infra/environments/local/models.auto.tfvars.json
+
+# Generated training data (rebuilt from a seed by the pipeline)
+data/
+
 # Python
 __pycache__/
 *.py[cod]
```

### `.mise.toml`

```diff
--- a/.mise.toml
+++ b/.mise.toml
@@ -75,7 +75,7 @@
 description = "Destroy the local environment root, then the local runtime"
 run = [
   "scripts/with_cmf.sh terraform -chdir=infra/environments/local destroy -input=false -auto-approve || true",
-  # Containers Floci started itself (floci-ui, later SageMaker containers) would
+  # Containers Floci started itself (floci-ui, SageMaker training and endpoint containers) would
   # otherwise keep the network from being deleted.
   "scripts/cleanup_network_containers.sh",
   "terraform -chdir=infra/environments/local/runtime destroy -input=false -auto-approve",
@@ -102,7 +102,7 @@

 [tasks.gate2]
 description = "Gate 2: live events through Kafka and CMF produce the reference features"
-run = "uv run pytest -m e2e tests/e2e -v"
+run = "uv run pytest -m e2e tests/e2e/test_features_live.py -v"

 [tasks.feed]
 description = "Send live synthetic payments to Kafka (extra args go to the generator, e.g. -- --rate 20 --live 300)"
@@ -116,6 +116,56 @@
 description = "Tail txn-features with the Avro console consumer inside the Schema Registry container"
 run = "docker exec -it schema-registry kafka-avro-console-consumer --bootstrap-server broker:29092 --topic txn-features --property schema.registry.url=http://localhost:8081"

+[tasks.build-model]
+description = "Build a model image and push it to its ECR repository on Floci"
+usage = 'arg "[model]" default="fraud-score" help="model directory under services/models, dashes for underscores"'
+run = 'scripts/build_model_image.sh "${usage_model}"'
+
+[tasks.dataset]
+description = "Build the labelled training dataset and upload it to S3 on Floci"
+usage = 'arg "[model]" default="fraud-score"'
+run = """
+#!/usr/bin/env bash
+set -euo pipefail
+uv run python -m "services.models.${usage_model//-/_}.pipeline" dataset
+"""
+
+[tasks.train]
+description = "Run a SageMaker training job on Floci, evaluate it and register it in MLflow"
+usage = 'arg "[model]" default="fraud-score"'
+run = """
+#!/usr/bin/env bash
+set -euo pipefail
+uv run python -m "services.models.${usage_model//-/_}.pipeline" train
+"""
+
+[tasks.models]
+description = "Registered versions of a model, with test metrics and the champion"
+usage = 'arg "[model]" default="fraud-score"'
+run = """
+#!/usr/bin/env bash
+set -euo pipefail
+uv run python -m "services.models.${usage_model//-/_}.pipeline" list
+"""
+
+[tasks.approve]
+description = "Release a registered version, then apply the local root to deploy it to the endpoint"
+usage = '''
+arg "<version>" help="MLflow registry version, from mise run models"
+flag "--model <model>" default="fraud-score"
+'''
+run = """
+#!/usr/bin/env bash
+set -euo pipefail
+uv run python -m "services.models.${usage_model//-/_}.pipeline" approve "${usage_version}"
+# Shows the plan (new model and endpoint config, endpoint updated) and asks first.
+scripts/with_cmf.sh terraform -chdir=infra/environments/local apply -input=false
+"""
+
+[tasks.gate3]
+description = "Gate 3: the released model scores on its SageMaker endpoint (Floci)"
+run = "uv run pytest -m e2e tests/e2e/test_fraud_score_endpoint.py -v -s"
+
 [tasks.lint]
 description = "Every pre-commit hook against every file"
 run = "pre-commit run --all-files"
```

### `AGENTS.md`

```diff
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -46,6 +46,11 @@
 mise run deploy local   # topics, schemas, CMF objects, Flink statements
 mise run takeover       # live traffic + account-takeover scenario
 mise run gate2          # live features vs the reference
+mise run build-model    # model image -> ECR on Floci
+mise run train          # SageMaker training job on Floci, evaluate, register in MLflow
+mise run models         # registered versions, test metrics, champion
+mise run approve <n>    # release version n, then apply: endpoint fraud-score serves it
+mise run gate3          # the endpoint scores the takeover above normal traffic
 mise run test           # unit (+ integration when the runtime is up)
 mise run test-flink     # Flink SQL on local PyFlink vs the reference
 mise run lint           # all pre-commit hooks
@@ -66,6 +71,16 @@
 - **Python 3.12 compatibility.** `mise run test-flink` imports the generator and `reference_features.py` under PyFlink's Python 3.12. Keep those modules free of 3.13-only syntax.
 - **CMF has no Terraform provider.** The `cmf_*` modules call its REST API through `cmf_rest_resource`; anything that applies the local root runs under `scripts/with_cmf.sh`, which port-forwards CMF.

+## Model conventions
+
+- **One directory per model** under `services/models/<model>/` (dashes in the model name, underscores in the directory). It holds the container (`Dockerfile`, `requirements.txt`, `bin/train`, `bin/serve`, the `<model>_model` package), `VERSION` (the image tag), `dataset.py` and `pipeline.py`.
+- **Container code runs on Python 3.12** (`python:3.12-slim`) and imports only its own package, numpy and xgboost. Use relative imports inside the package; never import `services.*` from it. The unit tests run it on 3.13, so keep it free of 3.13-only syntax.
+- **The feature spec is the contract.** `feature_spec.json` lists the model's inputs in vector order, named as in the `txn-features` Avro schema. It ships in the image and in every artifact. Changing the inputs is a new model (or a new `feature_version` with new SQL), not a new version of this one.
+- **Training data comes from the reference features**, never from a second implementation, so training and serving cannot skew. Datasets are deterministic for a config and split by time.
+- **Training jobs are runs, not infrastructure.** The pipeline creates them; Terraform owns buckets, ECR repositories, the SageMaker role and the endpoint.
+- **Release = approved version.** `pipeline approve` copies the training artifact to `s3://<prefix>-models/<model>/v<N>/model.tar.gz` with `model_version.json` added, moves the MLflow `champion` alias and writes `models.auto.tfvars.json` in the environment root. Terraform then creates model and endpoint config `<model>-v<N>` and updates the stable endpoint `<model>`. The local file is git-ignored; npr and prod commit theirs through a pull request. A version is immutable: a new image or artifact is a new version.
+- **Floci unknowns are handled in code, not assumed.** The server loads an extracted artifact or a `model.tar.gz`, and reads its version from `model_version.json` rather than relying on the endpoint's `Environment`.
+
 ## Adding things

 - **A resource:** add or extend a module in `infra/modules`, then call it from a stack.
@@ -76,6 +91,6 @@
 ## Conventions

 - Region `eu-west-1` everywhere, including Floci.
-- Container names double as hostnames on the `weaver` network: `floci`, `broker`, `schema-registry`, `kafka-ui`.
+- Container names double as hostnames on the `weaver` network: `floci`, `broker`, `schema-registry`, `kafka-ui`, `mlflow`.
 - Host ports bind to `127.0.0.1` only.
 - Python 3.13, `uv`, `ruff`, `mypy --strict`. Scripts are run as modules: `python -m scripts.<name>`.
```

### `README.md`

```diff
--- a/README.md
+++ b/README.md
@@ -11,8 +11,8 @@
 | Phase | Scope | Status |
 | --- | --- | --- |
 | Week 1: Foundations | Repo, tooling, local runtime (Floci, Kafka, Schema Registry, Kafka UI, kind + CMF), Floci state backend, health checks, kind network smoke test | **Done** (Gate 1 met) |
-| Week 2: Streaming | Topics and Avro schemas, transaction generator with the account-takeover scenario, CMF environment, catalog and pool, feature statement writing `txn-features` | **In this repo** |
-| Week 3: Model | Training data, XGBoost image, training job, endpoint, MLflow | Planned |
+| Week 2: Streaming | Topics and Avro schemas, transaction generator with the account-takeover scenario, CMF environment, catalog and pool, feature statement writing `txn-features` | **Done** (Gate 2 met) |
+| Week 3: Model | Labelled training data, XGBoost image, training job on Floci, MLflow tracking and registry, approval, endpoint | **In this repo** |
 | Week 4: Inference | `FRAUD_SCORE` UDF, scoring and decision statements, load test | Planned |
 | Week 5: Harden and demo | Model v2 rollout, dashboard, runbook | Planned |

@@ -94,25 +94,27 @@

     subgraph FLOCI["Floci (localhost:4566)"]
         S3[("S3<br/>weaver-data, weaver-models")]
-        GLUE["Glue catalog + Athena<br/>Iceberg feature table"]
-        ECR["ECR<br/>model image"]
+        GLUE["Glue catalog + Athena<br/>Iceberg feature table (planned)"]
+        ECR["ECR<br/>weaver/fraud-score"]
         TRAIN["SageMaker training job"]
-        EP["SageMaker endpoint<br/>fraud-score-v1"]
+        EP["SageMaker endpoint fraud-score<br/>config fraud-score-v&lt;N&gt;"]
     end

-    MLF["MLflow<br/>(open source)"]
+    DS["Dataset builder<br/>generator + reference features"]
+    MLF["MLflow<br/>tracking + registry"]

     GEN --> TIN --> FEAT --> TFEAT --> SCORE
     SR -. schemas .-> FEAT
     SCORE -- InvokeEndpoint --> EP
     EP -- score + reason codes --> SCORE
     SCORE --> DEC --> TOUT --> DASH
-    TFEAT -. Iceberg sink .-> S3
-    S3 --> GLUE
-    GLUE -- training set --> TRAIN
-    ECR --> TRAIN --> S3
-    TRAIN -. metrics .-> MLF
-    S3 -- approved model --> EP
+    TFEAT -. Iceberg sink, planned .-> GLUE
+    DS -- train / validation / test CSV --> S3
+    S3 --> TRAIN
+    ECR --> TRAIN -- model.tar.gz --> S3
+    TRAIN -. metrics, version .-> MLF
+    MLF -. approve .-> EP
+    S3 -- released model --> EP
 ```

 | Layer | Local implementation | UI |
@@ -120,7 +122,7 @@
 | Kafka and Schema Registry | Confluent Platform broker (KRaft) and Schema Registry containers | Kafka UI, `localhost:9021` (swap for Control Center if licensed) |
 | Stream processing | Confluent Manager for Apache Flink (CMF) on a kind cluster; Flink SQL statements; Java async UDF | CMF UI and Flink Web UI (port-forward) |
 | AWS | Floci: S3, Glue, Athena, ECR, IAM, Secrets Manager, CloudWatch Logs, SageMaker training and hosting | Floci console, `localhost:4566/_floci/ui` |
-| Experiment tracking | Open-source MLflow container, artefacts in Floci S3 | MLflow UI |
+| Experiment tracking and registry | Open-source MLflow container; SQLite and artefacts on a named volume | MLflow UI, `localhost:5050` |
 | Demo | Fraud dashboard reading `fraud-scores` and `fraud-alerts` | Dashboard |

 **Laptop sizing (estimate):** 32 GB RAM and 8 cores recommended, 16 GB minimum. Give Docker at least 10–12 GB.
@@ -251,7 +253,6 @@
 │   │   ├── aws_iam · aws_ssm · aws_sns · aws_lambda · ...
 │   │   ├── aws_s3_bucket · aws_ecr_repository · aws_secretsmanager_secret
 │   │   ├── aws_sagemaker_endpoint          # model + endpoint config + endpoint
-│   │   ├── aws_sagemaker_training_job      # wraps scripts/train.py
 │   │   ├── aws_sagemaker_feature_group     # npr
 │   │   ├── aws_sagemaker_model_package_group  # npr
 │   │   ├── aws_sagemaker_pipeline          # npr
@@ -272,11 +273,11 @@
 │       └── local_runtime/            # docker network + containers, kind, Helm (CMF), MLflow
 ├── scripts
 │   ├── terraform_docs_staged.sh
-│   ├── train.py                      # CreateTrainingJob (no native Terraform resource)
+│   ├── build_model_image.sh          # model image -> ECR (Floci locally)
 │   └── wait_for_local.sh             # health checks: Floci, broker, SR, CMF
 ├── services
-│   ├── models/fraud_score/           # Dockerfile, train, serve, data_gen, pipeline.py,
-│   │                                 #   evaluate.py, MODEL_CARD.md
+│   ├── models/fraud_score/           # Dockerfile, bin/{train,serve}, fraud_score_model/,
+│   │                                 #   VERSION, dataset.py, pipeline.py, MODEL_CARD.md
 │   ├── flink_udf/                    # Java async UDF calling SageMaker Runtime (local)
 │   ├── flink_sql/fraud_score/        # features.sql, scoring.sql.tftpl, alerts.sql
 │   ├── generators/transactions/      # synthetic ZAR events + fraud scenarios
@@ -339,10 +340,24 @@

 **Event time and ordering.** Tables use CMF's default watermark: the Kafka record timestamp (`$rowtime`) with no lateness allowance. The generator sets the record timestamp to each event's `event_time` and sends one time-ordered stream, keyed by customer, so nothing is late. Back-dated history (`--history-hours`) is only safe on fresh topics: on a partition that already holds newer events it arrives late and Flink drops it.

+### Week 3: the model
+
+```bash
+mise run up             # again: adds MLflow, switches Floci ECR to path-style URIs, applies the ml stack
+mise run build-model    # build services/models/fraud_score, push to ECR on Floci (tag = VERSION)
+mise run train          # dataset to S3, training job on Floci, test-split evaluation, MLflow run + version
+mise run models         # registered versions with test AUC-PR and quality gate
+mise run approve 1      # release version 1, then terraform apply (shows the plan, asks first)
+mise run gate3          # Gate 3: the endpoint scores the takeover journey above every normal payment
+```
+
+The pipeline (`services/models/fraud_score/pipeline.py`) runs on the laptop and talks to Floci and MLflow: it builds the labelled dataset (synthetic, from a seed: normal traffic plus fraud scenarios and benign look-alikes, featurised by the reference implementation, split by time), uploads it to `weaver-data`, creates a SageMaker training job with the model image, waits for it, scores the held-out test split with the serving code and registers the result in MLflow with a `quality_gate` tag (test AUC-PR at least 0.70). `approve` publishes the artifact to `weaver-models/fraud-score/v<N>/` and writes `infra/environments/local/models.auto.tfvars.json`; Terraform turns that into model and endpoint config `fraud-score-v<N>` behind the stable endpoint `fraud-score`. Approving a later version updates the same endpoint.
+
+Training without the cluster: `uv run python -m services.models.fraud_score.dataset` writes the CSVs to `data/`, and `mise run test` trains and serves a small model in-process with the container code.
+
 ### Later weeks

 ```bash
-mise run train fraud-score        # week 3: build the model image, run the training job on Floci
 mise run demo fraud-score         # week 5: dashboard + scripted demo
 ```

@@ -372,12 +387,17 @@
 | `mise run takeover` | Live traffic plus the account-takeover scenario | Now |
 | `mise run features` | Tail `txn-features` | Now |
 | `mise run gate2` | Live features compared with the reference implementation | Now |
+| `mise run build-model [model]` | Model image built and pushed to ECR on Floci | Now |
+| `mise run dataset [model]` | Labelled dataset built and uploaded to S3 | Now |
+| `mise run train [model]` | Training job on Floci, evaluation, MLflow run and registered version | Now |
+| `mise run models [model]` | Registered versions, test metrics, champion | Now |
+| `mise run approve <version>` | Release a version, then apply the local root to deploy it | Now |
+| `mise run gate3` | Endpoint scores, version and latency | Now |
 | `mise run test-flink` | Feature SQL on a local PyFlink against the reference | Now |
 | `mise run floci-env` | Prints `AWS_*` exports for Floci: `eval "$(mise run floci-env)"` | Now |
 | `mise run test` | Unit tests; integration tests when the runtime is up | Now |
 | `mise run lint` | Every pre-commit hook on every file | Now |
 | `mise run down` | Destroys the `local` root, then `local/runtime` | Now |
-| `mise run train <use-case> [env]` | Model image to ECR, then the training pipeline | Week 3 |
 | `mise run demo <use-case>` | Generator and scripted scenario | Week 5 |

 `AWS_*` variables are deliberately not set by `.mise.toml`, so a shell in this repo never points real AWS tooling at Floci by accident.
@@ -435,14 +455,15 @@
 | Capability | AWS target (`npr` / `prod`) | POC |
 | --- | --- | --- |
 | Data lake and catalog | S3 Iceberg tables, Glue Data Catalog, Lake Formation, Athena | Built on Floci (Lake Formation grants stored, not enforced) |
-| Data preparation | SageMaker Processing jobs | Container on the Processing contract, run by a mise task |
+| Data preparation | SageMaker Processing jobs | `dataset.py` on the host: generator plus reference features, CSV to S3, split by time |
 | Offline feature store | Feature Store offline store | Flink sinks `txn-features` to an Iceberg table in Floci S3, registered in Glue |
 | Online feature store | Feature Store online store, Standard tier | Not needed: features travel in the request |
 | Experiment tracking | Managed MLflow, synced to Model Registry | Open-source MLflow container |
 | Training | Training jobs, automatic model tuning | Built on Floci (no tuning jobs) |
-| Orchestration | SageMaker Pipelines | `pipeline.py`, one function per pipeline step |
-| Model registry | Model package group, approval, EventBridge on approval | MLflow `approved` alias |
-| Bias and explainability | SageMaker Clarify | `shap` in the evaluate step; top 3 reason codes per score |
+| Orchestration | SageMaker Pipelines | `pipeline.py`, one function per pipeline step: dataset, train, evaluate, register, approve |
+| Evaluation | Processing job, model quality check step | On the host with the serving code; test split metrics and a quality gate in MLflow |
+| Model registry | Model package group, approval, EventBridge on approval | MLflow registry: one version per training job, `quality_gate` tag, `champion` alias; `approve` writes the version for Terraform |
+| Bias and explainability | SageMaker Clarify | XGBoost SHAP contributions in the container; top 3 reason codes per score |
 | Governance | Model Cards, Model Dashboard, Lineage Tracking | `MODEL_CARD.md`; lineage tags (git SHA, Iceberg snapshot, MLflow run) |
 | Hosting | Real-time endpoint, autoscaling, deployment guardrails | Built on Floci (CPU only, no autoscaling) |
 | Monitoring | Data capture, Model Monitor, CloudWatch alarms | Nightly drift job over `txn-features` and `fraud-scores` |
@@ -463,6 +484,8 @@
 | Step Functions | No SageMaker integration | `pipeline.py` |
 | Application Auto Scaling | Policies stored but inert | Single endpoint instance |

+**Assumed in week 3, to confirm on Floci 2.4.0.** The code tolerates each case, but the first run settles it: whether training channel files keep their key names (the trainer reads every `*.csv` under a channel); whether an endpoint gets `model.tar.gz` extracted (the server handles both); whether the endpoint `Environment` reaches the container (the version comes from `model_version.json` instead); and whether `FLOCI_SERVICES_ECR_PREFER_LOCAL_IMAGES` runs the image from the host cache or pulls it from Floci's registry.
+
 The Floci image tag is pinned in `infra/environments/local/runtime/terraform.tfvars`, never `latest`. Floci releases on the 15th and last day of each month: upgrading is its own pull request that bumps the tag, runs `mise run test`, and updates this table.

 ---
@@ -499,14 +522,16 @@
 | --- | --- | --- |
 | Unit | Generator, reference feature definitions, repo rules, Terraform layout | Python only |
 | Flink SQL | `features.sql` unchanged, in streaming mode, against the reference on generated history plus the takeover | Local PyFlink 2.3 (`mise run test-flink`) |
-| Integration | Train → endpoint → invoke | Floci via testcontainers |
-| End to end | Gate 2: live events in, `txn-features` out, compared with the reference; later event in → score out and p95 latency | Full local stack (`mise run gate2`) |
+| Unit, model | Feature spec against the Avro schema, metrics, dataset split and reproducibility, `train` and `serve` from the container code, release packaging | Python only (xgboost) |
+| Integration | Runtime health, MLflow, ml stack resources | Running local runtime (`mise run test`) |
+| End to end | Gate 2: live events in, `txn-features` out, compared with the reference | Full local stack (`mise run gate2`) |
+| End to end | Gate 3: the approved version answers on the endpoint; takeover above every normal payment; latency | Floci endpoint (`mise run gate3`) |

 **POC success criteria**

 - [ ] `mise install` then `mise run up` builds every layer on a clean laptop with no cloud accounts
 - [ ] Training job completes on Floci and writes `model.tar.gz` to S3
-- [ ] Endpoint `fraud-score-v1` reaches `InService` and answers `InvokeEndpoint`
+- [ ] Endpoint `fraud-score` (config `fraud-score-v1`) reaches `InService` and answers `InvokeEndpoint`
 - [ ] Every event on `transactions` gets a row on `fraud-scores` with score, decision and model version
 - [ ] p95 end-to-end latency under 1 second at 50 events per second
 - [ ] Changing the model version variable rolls the endpoint to v2 with no Flink restart
```

### `infra/environments/local/main.tf`

```diff
--- a/infra/environments/local/main.tf
+++ b/infra/environments/local/main.tf
@@ -2,7 +2,6 @@
 # Floci in place of AWS. Stacks are added as they are built:
 #
 #   module "aws" { source = "../../stacks/aws" }  # later weeks
-#   module "ml"  { source = "../../stacks/ml" }   # week 3

 module "confluent_local" {
   source = "../../stacks/confluent_local"
@@ -22,3 +21,22 @@
   # Statements read topics whose tables are inferred from registered schemas.
   depends_on = [module.confluent_local]
 }
+
+# Buckets, model image repositories, the SageMaker role and, once a version is
+# approved, the endpoint. Same stack as npr and prod; only the settings differ.
+module "ml" {
+  source = "../../stacks/ml"
+
+  name_prefix          = "weaver"
+  models               = var.models
+  image_tag_mutability = "MUTABLE" # rebuild an image under the same VERSION while iterating
+  keep_images          = null      # lifecycle policies are not needed on a laptop
+  force_destroy        = true
+  endpoint = {
+    instance_type     = "ml.t2.medium"
+    instance_count    = 1     # Floci serves one container per endpoint
+    network_isolation = false # Floci reaches the container over the Docker network
+    data_capture      = false # not emulated by Floci 2.4.0; on in npr and prod
+  }
+  tags = local.tags
+}
```

### `infra/environments/local/outputs.tf`

```diff
--- a/infra/environments/local/outputs.tf
+++ b/infra/environments/local/outputs.tf
@@ -23,3 +23,14 @@
     statements   = module.flink_local.statements
   }
 }
+
+output "ml" {
+  description = "Buckets, image repositories, the SageMaker role and deployed endpoints."
+  value = {
+    data_bucket        = module.ml.data_bucket
+    models_bucket      = module.ml.models_bucket
+    ecr_repositories   = module.ml.ecr_repositories
+    sagemaker_role_arn = module.ml.sagemaker_role_arn
+    endpoints          = module.ml.endpoints
+  }
+}
```

### `infra/environments/local/runtime/main.tf`

```diff
--- a/infra/environments/local/runtime/main.tf
+++ b/infra/environments/local/runtime/main.tf
@@ -8,5 +8,6 @@
   kubeconfig_path            = local.kubeconfig_path
   chart_versions             = var.chart_versions
   kafka_ui_enabled           = var.kafka_ui_enabled
+  mlflow_image               = var.mlflow_image
   tags                       = local.tags
 }
```

### `infra/environments/local/runtime/terraform.tfvars`

```diff
--- a/infra/environments/local/runtime/terraform.tfvars
+++ b/infra/environments/local/runtime/terraform.tfvars
@@ -1,6 +1,7 @@
 floci_image                = "floci/floci:2.4.0"
 confluent_platform_version = "8.0.0"
 kind_node_image            = "kindest/node:v1.32.2"
+mlflow_image               = "ghcr.io/mlflow/mlflow:v3.18.0" # match mlflow-skinny in pyproject.toml

 # Chart versions, pinned. When one changes, update the image tags in
 # scripts/preload_kind_images.sh (and the compute pool image for a new CMF minor).
```

### `infra/environments/local/runtime/variables.tf`

```diff
--- a/infra/environments/local/runtime/variables.tf
+++ b/infra/environments/local/runtime/variables.tf
@@ -40,3 +40,8 @@
   type        = bool
   default     = true
 }
+
+variable "mlflow_image" {
+  description = "MLflow image, pinned."
+  type        = string
+}
```

### `infra/environments/local/variables.tf`

```diff
--- a/infra/environments/local/variables.tf
+++ b/infra/environments/local/variables.tf
@@ -21,3 +21,12 @@
   type        = string
   default     = "http://localhost:8080"
 }
+
+variable "models" {
+  description = "Released models: name => version and image tag. `mise run approve` writes models.auto.tfvars.json (git-ignored locally)."
+  type = map(object({
+    version   = number
+    image_tag = string
+  }))
+  default = {}
+}
```

### `infra/stacks/local_runtime/floci.tf`

```diff
--- a/infra/stacks/local_runtime/floci.tf
+++ b/infra/stacks/local_runtime/floci.tf
@@ -13,6 +13,15 @@
     FLOCI_STORAGE_PERSISTENT_PATH = "/app/data"
     # Containers Floci starts (training jobs, endpoints) join the same network.
     FLOCI_SERVICES_DOCKER_NETWORK = module.network.name
+
+    # Path-style image URIs (localhost:4566/<account>/<region>/<repo>): the
+    # default host-style URI (<account>.dkr.ecr.<region>.localhost:4566) does
+    # not resolve with Docker's containerd image store.
+    FLOCI_SERVICES_ECR_URI_STYLE = "path"
+
+    # Run a model image straight from the host's image cache when it is there
+    # (mise run build-model tags it with the repository URI), instead of pulling.
+    FLOCI_SERVICES_ECR_PREFER_LOCAL_IMAGES = "true"
   }

   ports = [{ internal = 4566, external = var.ports.floci }]
```

### `infra/stacks/local_runtime/outputs.tf`

```diff
--- a/infra/stacks/local_runtime/outputs.tf
+++ b/infra/stacks/local_runtime/outputs.tf
@@ -20,6 +20,7 @@
       network = "http://${module.schema_registry.name}:8081"
     }
     kafka_ui = var.kafka_ui_enabled ? "http://localhost:${var.ports.kafka_ui}" : null
+    mlflow   = var.mlflow_enabled ? "http://localhost:${var.ports.mlflow}" : null
   }
 }

```

### `infra/stacks/local_runtime/variables.tf`

```diff
--- a/infra/stacks/local_runtime/variables.tf
+++ b/infra/stacks/local_runtime/variables.tf
@@ -46,6 +46,18 @@
   default     = "kafbat/kafka-ui:v1.1.0"
 }

+variable "mlflow_enabled" {
+  description = "Run the MLflow tracking server and model registry."
+  type        = bool
+  default     = true
+}
+
+variable "mlflow_image" {
+  description = "MLflow image, pinned. Keep its version in step with mlflow-skinny in pyproject.toml."
+  type        = string
+  default     = "ghcr.io/mlflow/mlflow:v3.18.0"
+}
+
 variable "kind_cluster_name" {
   description = "Name of the kind cluster that runs CMF."
   type        = string
@@ -86,6 +98,7 @@
     kafka           = optional(number, 9092)
     schema_registry = optional(number, 8081)
     kafka_ui        = optional(number, 9021)
+    mlflow          = optional(number, 5050)
   })
   default = {}
 }
```

### `mypy.ini`

```diff
--- a/mypy.ini
+++ b/mypy.ini
@@ -7,6 +7,9 @@
 [mypy-hcl2.*]
 ignore_missing_imports = True

+[mypy-botocore.*]
+ignore_missing_imports = True
+
 [mypy-boto3.*]
 ignore_missing_imports = True

```

### `pyproject.toml`

```diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -10,10 +10,15 @@
 dev = [
   "boto3>=1.35",
   "confluent-kafka[avro,schemaregistry]>=2.6",
+  # Client for the local MLflow server; keep the minor in step with mlflow_image.
+  "mlflow-skinny>=3.18,<3.19",
   "mypy>=1.13",
+  # Same versions as services/models/fraud_score/requirements.txt (the container).
+  "numpy==2.5.3",
   "pytest>=8.3",
   "python-hcl2>=7.0",
   "ruff>=0.8",
+  "xgboost-cpu==3.4.1",
 ]

 [tool.uv]
```

### `scripts/wait_for_local.sh`

```diff
--- a/scripts/wait_for_local.sh
+++ b/scripts/wait_for_local.sh
@@ -32,6 +32,8 @@
   "[ \"\$(docker inspect -f '{{.State.Health.Status}}' broker)\" = healthy ]"
 wait_for "Schema Registry" \
   "curl -fsS http://localhost:8081/subjects"
+wait_for "MLflow" \
+  "curl -fsS http://localhost:5050/health"
 wait_for "kind node" \
   "kubectl wait --for=condition=Ready nodes --all --timeout=5s"
 wait_for "Flink operator" \
```

### `tests/integration/test_local_runtime.py`

```diff
--- a/tests/integration/test_local_runtime.py
+++ b/tests/integration/test_local_runtime.py
@@ -15,6 +15,7 @@

 FLOCI = "http://localhost:4566"
 SCHEMA_REGISTRY = "http://localhost:8081"
+MLFLOW = "http://localhost:5050"


 def _listening(host: str, port: int) -> bool:
@@ -66,3 +67,21 @@

 def test_schema_registry_answers() -> None:
     assert isinstance(_get_json(f"{SCHEMA_REGISTRY}/subjects"), list)
+
+
+def test_mlflow_answers() -> None:
+    with urllib.request.urlopen(f"{MLFLOW}/health", timeout=5) as response:  # noqa: S310
+        assert response.status == 200
+
+
+def test_ml_stack_is_applied(floci_session: boto3.session.Session) -> None:
+    """Buckets, image repository and SageMaker role from the ml stack (week 3)."""
+    s3 = floci_session.client("s3", endpoint_url=FLOCI)
+    for bucket in ("weaver-data", "weaver-models"):
+        s3.head_bucket(Bucket=bucket)
+    ecr = floci_session.client("ecr", endpoint_url=FLOCI)
+    repository = ecr.describe_repositories(repositoryNames=["weaver/fraud-score"])
+    # Path style (FLOCI_SERVICES_ECR_URI_STYLE=path), which Docker can push to.
+    assert repository["repositories"][0]["repositoryUri"].startswith("localhost:4566/")
+    iam = floci_session.client("iam", endpoint_url=FLOCI)
+    assert iam.get_role(RoleName="weaver-sagemaker-exec")["Role"]["Arn"]
```
