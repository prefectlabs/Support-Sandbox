# Support-Sandbox — Prefect Patterns

A reference repo of common Prefect patterns, each as a standalone, runnable example. Paired with Terraform infrastructure-as-code using the [PrefectHQ Terraform provider](https://registry.terraform.io/providers/PrefectHQ/prefect/latest/docs) and Helm values for deploying Prefect workers to Kubernetes.

## Examples

| File | Pattern | Key concepts |
|------|---------|--------------|
| `examples/01_basic_flow.py` | Basic Flow | `@flow`, `@task`, retries, `log_prints` |
| `examples/02_dynamic_parameters.py` | Dynamic Parameters | Pydantic model + `StrEnum` as flow params (UI forms) |
| `examples/03_task_caching.py` | Task Caching | `INPUTS` cache policy, S3 result storage |
| `examples/04_concurrent_tasks.py` | Concurrent Tasks | `.map()`, `ThreadPoolTaskRunner` |
| `examples/05_run_deployment_fanout.py` | Deployment Fan-out | `run_deployment()`, async polling, parent + child flows |
| `examples/06_custom_events.py` | Custom Events | `emit_event`, deployment event triggers |
| `examples/07_schema_validation.py` | Schema Validation | `validate_parameters=True`, Pydantic |
| `examples/08_state_hooks.py` | State Hooks | `on_failure`, `on_crashed`, Slack notification |
| `examples/09_automations.py` | Programmatic Automations | `Automation` SDK, infra-as-code |
| `examples/10_task_dependencies.py` | Task Dependencies | `wait_for`, `task_run_name`, `flow.with_options()` |
| `examples/11_process_pool.py` | Concurrent Tasks (CPU-bound) | `ProcessPoolTaskRunner`, spawn guard, picklability |
| `examples/14_flow_level_caching.py` | Flow Level Caching | `ThreadPoolTaskRunner`, result storage & caching, `run_deployment()` |

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — `brew install uv`
- [just](https://github.com/casey/just) — `brew install just`
- A Prefect Cloud account — [app.prefect.cloud](https://app.prefect.cloud)

## Setup

```bash
# Install dependencies and pre-commit hooks
just setup

# Copy env template and fill in your values
cp .env.example .env
```

**Credentials** can be provided two ways — use whichever fits your workflow:

| Method | How |
|--------|-----|
| `.env` | Set `PREFECT_API_KEY` and `PREFECT_API_URL` directly |
| `prefect.toml` | `cp prefect.toml.example prefect.toml` and fill in `[api]` section |

`prefect.toml` is resolved per-project and sits below env vars in precedence, so env vars always win. Neither file should be committed to source control as they contain credentials.

## Running Examples

```bash
# Run any example locally
just run examples/01_basic_flow.py

# Deploy all examples to Prefect Cloud
just deploy
```

## Development

```bash
just lint       # ruff check --fix
just format     # ruff format
just typecheck  # ty check
just check      # run all checks (matches CI)
```

Pre-commit hooks run automatically on `git commit`. To run manually:

```bash
uv run pre-commit run --all-files
```

## API Helpers (`helpers/`)

Standalone scripts showing two ways to interact with the Prefect API programmatically. Neither file is a flow — run them directly with `uv run helpers/<file>.py` or import the functions into your own code.

### `helpers/python_client.py` — Prefect Python client

Uses Prefect's built-in async client (`get_client`, `get_cloud_client`). Best for orchestration operations that map to first-class SDK methods.

| Function | What it does |
|----------|-------------|
| `read_deployment(flow_name, deployment_name)` | Fetch a deployment object by name |
| `update_deployment_pull_steps(dep_name, pull_steps)` | Replace the pull steps on an existing deployment |
| `get_deployment_flow_runs(deployment_id)` | List all flow runs for a deployment |
| `list_workspaces()` | List workspaces accessible to the current API key (Cloud management API) |

```python
import asyncio
from helpers.python_client import read_deployment

asyncio.run(read_deployment("my-flow", "my-deployment"))
```

### `helpers/rest_api.py` — Direct REST API via httpx

Calls the Prefect Cloud REST API directly using `httpx`. Covers Cloud-only endpoints not exposed by the Python client — ACLs, service accounts, and account roles.

Two client factories handle the URL scope split:
- `workspace_client()` — base URL is `PREFECT_API_URL` (workspace-scoped)
- `account_client()` — strips `/workspaces/...` from `PREFECT_API_URL` (account-scoped)

| Function | Scope | What it does |
|----------|-------|-------------|
| `filter_deployments(tags, operator)` | Workspace | Filter deployments by tag(s) |
| `set_deployment_access(deployment_id, access_control)` | Workspace | Set full ACL on a deployment |
| `grant_service_account_deployment_access(deployment_id, sa_name, level)` | Workspace | Grant view/run/manage access to a service account |
| `list_service_accounts()` | Account | List all service accounts (bots) |
| `list_account_roles()` | Account | List all account roles |
| `update_service_account_role(sa_name, role_name)` | Account | Assign an account role to a service account by name |

```python
from helpers.rest_api import filter_deployments, update_service_account_role

# Filter deployments tagged "example"
deployments = filter_deployments(tags=["example"])

# Promote a service account to Admin
update_service_account_role("my-worker-sa", "Admin")
```

> **Note:** Both helpers read credentials from your `.env` via `PREFECT_API_KEY` and `PREFECT_API_URL`. Run `cp .env.example .env` and fill in your values before using them.

## Infrastructure as Code

### Terraform (`terraform/`)

Manages Prefect Cloud resources via the [PrefectHQ provider](https://registry.terraform.io/providers/PrefectHQ/prefect/latest/docs):

| File | Resources |
|------|-----------|
| `main.tf` | Provider, work pool, work queues |
| `variables.tf` | Input variables |
| `automations.tf` | `prefect_automation` — Slack alerts, event triggers |
| `concurrency.tf` | `prefect_global_concurrency_limit`, task tag limits |
| `access.tf` | Service accounts, workspace roles |
| `webhooks.tf` | `prefect_webhook` for external event ingestion |
| `blocks.tf` | `prefect_block` for S3 result storage |

```bash
cd terraform
export TF_VAR_prefect_api_key=$PREFECT_API_KEY
export TF_VAR_prefect_account_id=$PREFECT_ACCOUNT_ID
export TF_VAR_prefect_workspace_handle=your-workspace-handle
terraform init && terraform apply
```

### Helm (`helm/`)

Deploys a Prefect worker to Kubernetes:

```bash
# Add the Prefect Helm repo
helm repo add prefect https://prefecthq.github.io/prefect-helm && helm repo update

# Copy and fill in values
cp helm/values.yaml helm/values.local.yaml
# edit helm/values.local.yaml with values from .env

helm install prefect-worker prefect/prefect-worker -f helm/values.local.yaml
```

## Environment Variables

All variables are documented in [`.env.example`](.env.example).
