"""
Pattern: State Change Hooks
Demonstrates: on_failure / on_crashed hooks with Slack notification

State change hooks run when a flow transitions into a specific state.
Use on_failure for caught exceptions, on_crashed for infrastructure failures
(OOM kills, container crashes). Both receive the flow, flow_run, and state
objects so you can extract parameters, IDs, and error messages for alerts.

Requires a SlackCredentials block. Create it once:
    prefect block create slack-credentials --name $SLACK_CREDENTIALS_BLOCK

Set SLACK_CREDENTIALS_BLOCK to the block name (default: "slack-creds").

Run locally:
    uv run python examples/08_state_hooks.py
"""

import asyncio
import os

from prefect import flow
from prefect.client.schemas.objects import FlowRun
from prefect.flows import Flow
from prefect.states import State
from prefect_slack import SlackCredentials

SLACK_CREDENTIALS_BLOCK = os.getenv("SLACK_CREDENTIALS_BLOCK", "slack-creds")


async def notify_slack(flow: Flow, flow_run: FlowRun, state: State) -> None:
    """Send a Slack message when the flow enters a failure or crashed state."""
    slack_channel = flow_run.parameters.get("slack_channel", "#alerts")
    creds = await SlackCredentials.load(SLACK_CREDENTIALS_BLOCK)  # ty:ignore[invalid-await]
    client = creds.get_client()
    await client.chat_postMessage(
        channel=slack_channel,
        text=(
            f":red_circle: *Flow run {state.name.lower()}*\n"  # ty:ignore[unresolved-attribute]
            f"Flow: `{flow.name}`\n"
            f"Run: `{flow_run.name}` ({flow_run.id})\n"
            f"State message: {state.message or 'none'}"
        ),
    )


@flow(on_failure=[notify_slack], log_prints=True)
async def failing_flow(slack_channel: str = "#alerts") -> None:
    """Raises an exception — triggers on_failure hook."""
    raise ValueError("Intentional failure to demonstrate on_failure hook")


@flow(on_crashed=[notify_slack], log_prints=True)
async def crashing_flow(slack_channel: str = "#alerts") -> None:
    """Simulates a crash — triggers on_crashed hook."""
    print("Flow running normally...")


if __name__ == "__main__":
    asyncio.run(failing_flow())
