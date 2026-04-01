"""
Examples using httpx directly against the Prefect Cloud REST API.

Use for Cloud-only operations not exposed by the Python client:
ACLs, service accounts (bots), account roles.

URL structure:
  Workspace scope:  https://api.prefect.cloud/api/accounts/{account_id}/workspaces/{workspace_id}
  Account scope:    https://api.prefect.cloud/api/accounts/{account_id}

PREFECT_API_URL already contains the full workspace-scoped base URL.
Stripping everything from "/workspaces" onward gives the account-scoped base URL.
"""

import httpx
from prefect.settings import PREFECT_API_KEY, PREFECT_API_URL

# ---------------------------------------------------------------------------
# Client factories
# ---------------------------------------------------------------------------


def workspace_client() -> httpx.Client:
    """httpx client for workspace-scoped endpoints (deployments, flow runs, etc.)."""
    return httpx.Client(
        base_url=PREFECT_API_URL.value(),
        headers={"Authorization": f"Bearer {PREFECT_API_KEY.value()}"},
    )


def account_client() -> httpx.Client:
    """httpx client for account-scoped endpoints (service accounts, roles, etc.)."""
    account_base = PREFECT_API_URL.value().split("/workspaces")[0]
    return httpx.Client(
        base_url=account_base,
        headers={"Authorization": f"Bearer {PREFECT_API_KEY.value()}"},
    )


# ---------------------------------------------------------------------------
# Workspace-scoped: Deployments
# ---------------------------------------------------------------------------


def filter_deployments(
    tags: list[str] | None = None, operator: str = "and_"
) -> list[dict]:
    """Return deployments, optionally filtered by tags.

    Args:
        tags:     list of tag strings to filter on
        operator: "and_" (all tags must match) or "or_" (any tag matches)
    """
    body: dict = {}
    if tags:
        body["deployments"] = {"operator": operator, "tags": {"all_": tags}}

    with workspace_client() as client:
        r = client.post("/deployments/filter", json=body)
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# Workspace-scoped: Deployment ACLs
# ---------------------------------------------------------------------------


def set_deployment_access(deployment_id: str, access_control: dict) -> None:
    """Set access control on a deployment.

    Args:
        deployment_id:   UUID of the deployment
        access_control:  dict with actor/team ID lists, e.g.:
            {
                "manage_actor_ids": ["<actor-uuid>"],
                "run_actor_ids":    [],
                "view_actor_ids":   [],
                "manage_team_ids":  [],
                "run_team_ids":     [],
                "view_team_ids":    [],
            }
    """
    with workspace_client() as client:
        r = client.put(
            f"/deployments/{deployment_id}/access",
            json={"access_control": access_control},
        )
        r.raise_for_status()


def grant_service_account_deployment_access(
    deployment_id: str,
    service_account_name: str,
    level: str = "run",
) -> None:
    """Grant a service account access to a deployment.

    Args:
        level: "view", "run", or "manage"
    """
    sa = next(
        (b for b in list_service_accounts() if b["name"] == service_account_name), None
    )
    if not sa:
        raise ValueError(f"Service account '{service_account_name}' not found")

    actor_id = sa["actor_id"]
    access_control = {
        "manage_actor_ids": [actor_id] if level == "manage" else [],
        "run_actor_ids": [actor_id] if level == "run" else [],
        "view_actor_ids": [actor_id] if level == "view" else [],
        "manage_team_ids": [],
        "run_team_ids": [],
        "view_team_ids": [],
    }
    set_deployment_access(deployment_id, access_control)


# ---------------------------------------------------------------------------
# Account-scoped: Service Accounts
# ---------------------------------------------------------------------------


def list_service_accounts() -> list[dict]:
    """List all service accounts (bots) in the account."""
    with account_client() as client:
        r = client.post("/bots/filter")
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# Account-scoped: Account Roles
# ---------------------------------------------------------------------------


def list_account_roles() -> list[dict]:
    """List all account roles."""
    with account_client() as client:
        r = client.post("/account_roles/filter")
        r.raise_for_status()
        return r.json()


def update_service_account_role(service_account_name: str, role_name: str) -> None:
    """Assign an account role to a service account, looked up by name.

    Args:
        service_account_name: display name of the service account
        role_name:            account role name, e.g. "Admin", "Member"
    """
    with account_client() as client:
        bots = client.post("/bots/filter").json()
        roles = client.post("/account_roles/filter").json()

    sa = next((b for b in bots if b["name"] == service_account_name), None)
    role = next((r for r in roles if r["name"] == role_name), None)

    if not sa:
        raise ValueError(f"Service account '{service_account_name}' not found")
    if not role:
        raise ValueError(f"Role '{role_name}' not found")

    with account_client() as client:
        r = client.patch(f"/bots/{sa['id']}", json={"account_role_id": role["id"]})
        r.raise_for_status()


# ---------------------------------------------------------------------------
# Entrypoints
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Example: assign Admin role to a service account
    update_service_account_role(
        service_account_name="test-acl",
        role_name="Admin",
    )
