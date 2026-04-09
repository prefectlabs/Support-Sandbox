"""
Examples using Prefect's Python client.

Two client types:
  get_client()       — async, workspace-scoped orchestration API (deployments, flow runs, etc.)
  get_cloud_client() — async, Prefect Cloud management API (account/workspace admin operations)

Both are async context managers. Use `async with` or call `.aclose()` when done.
"""

import asyncio
from uuid import UUID

from prefect import get_client
from prefect.client.cloud import Workspace, get_cloud_client
from prefect.client.schemas.filters import FlowRunFilter, FlowRunFilterDeploymentId
from prefect.client.schemas.objects import DeploymentResponse, FlowRun

# ---------------------------------------------------------------------------
# Deployments
# ---------------------------------------------------------------------------


async def read_deployment(flow_name: str, deployment_name: str) -> DeploymentResponse:
    """Read a deployment by flow/deployment name."""
    async with get_client() as client:
        return await client.read_deployment_by_name(f"{flow_name}/{deployment_name}")


async def update_deployment_pull_steps(dep_name: str, pull_steps: list[dict]) -> None:
    """Replace the pull steps on an existing deployment.

    Args:
        dep_name:    "flow-name/deployment-name"
        pull_steps:  list of pull step dicts, e.g.
                     [{"prefect.deployments.steps.git_clone": {"repository": "...", "branch": "main"}}]
    """
    # Keys that the create_deployment API rejects if present
    _READONLY_KEYS = [
        "id",
        "created",
        "updated",
        "created_by",
        "updated_by",
        "global_concurrency_limit",
        "last_polled",
        "work_queue_id",
        "status",
    ]
    async with get_client() as client:
        d = await client.read_deployment_by_name(name=dep_name)
        d.pull_steps = pull_steps
        d_json = d.model_dump()
        for key in _READONLY_KEYS:
            d_json.pop(key, None)
        await client.create_deployment(**d_json)


# ---------------------------------------------------------------------------
# Flow Runs
# ---------------------------------------------------------------------------


async def get_deployment_flow_runs(deployment_id: str) -> list[FlowRun]:
    """Return all flow runs for a given deployment ID."""
    async with get_client() as client:
        return await client.read_flow_runs(
            flow_run_filter=FlowRunFilter(
                deployment_id=FlowRunFilterDeploymentId(any_=[UUID(deployment_id)])
            )
        )


# ---------------------------------------------------------------------------
# Cloud Management (account/workspace admin — requires Prefect Cloud)
# ---------------------------------------------------------------------------


async def list_workspaces() -> list[Workspace]:
    """List all workspaces the current API key has access to."""
    async with get_cloud_client() as client:
        return await client.read_workspaces()


# ---------------------------------------------------------------------------
# Entrypoints
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Example: update pull steps on a deployment
    pull_steps = [
        {
            "prefect.deployments.steps.git_clone": {
                "repository": "https://github.com/prefectlabs/Support-Sandbox.git",
                "branch": "main",
            }
        }
    ]
    asyncio.run(update_deployment_pull_steps("demo-flow/ecs-demo-test", pull_steps))
