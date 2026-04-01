"""
Pattern: Programmatic Automations
Demonstrates: Creating Automation objects via the Python SDK

Use the Python SDK when you want to manage automations as code alongside your
flow definitions. Use the Terraform provider (terraform/automations.tf) when
automations are part of broader infrastructure managed by IaC pipelines.

The two approaches are equivalent — choose based on where your team wants
automation config to live (application code vs infrastructure repo).

Set SLACK_WEBHOOK_URL to your Slack incoming webhook URL.

Run locally:
    uv run python examples/09_automations.py
"""

import os

from prefect import flow, get_run_logger, task
from prefect.automations import Automation
from prefect.blocks.notifications import SlackWebhook
from prefect.events.actions import SendNotification
from prefect.events.schemas.automations import EventTrigger

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_BLOCK_NAME = "python-managed-slack-webhook"
AUTOMATION_NAME = "flow-failure-slack-notification"

NOTIFICATION_BODY = """
Flow run {{ flow.name }}/{{ flow_run.name }} entered state `{{ flow_run.state.name }}`.
Flow run ID: {{ flow_run.id }}
Flow run URL: {{ flow_run|ui_url }}
State message: {{ flow_run.state.message }}
"""


@task
def upsert_slack_block(url: str, block_name: str) -> SlackWebhook:
    """Create or overwrite the SlackWebhook block."""
    logger = get_run_logger()
    block = SlackWebhook(url=url)  # ty:ignore[invalid-argument-type]
    block.save(block_name, overwrite=True)
    logger.info(f"Saved SlackWebhook block: '{block_name}'")
    return block


@task
def upsert_automation(automation: Automation) -> None:
    """Recreate the automation (delete if exists, then create)."""
    logger = get_run_logger()
    try:
        existing = Automation.read(name=automation.name)
        existing.delete()  # ty:ignore[unresolved-attribute]
        logger.info(f"Deleted existing automation: '{automation.name}'")
    except ValueError:
        pass
    automation.create()
    logger.info(f"Created automation: '{automation.name}'")


@flow(log_prints=True)
def deploy_slack_notifications() -> None:
    block = upsert_slack_block(url=SLACK_WEBHOOK_URL, block_name=SLACK_BLOCK_NAME)

    automation = Automation(
        name=AUTOMATION_NAME,
        trigger=EventTrigger(
            expect={
                "prefect.flow-run.Failed",
                "prefect.flow-run.Crashed",
                "prefect.flow-run.TimedOut",
            },
            match={"prefect.resource.id": "prefect.flow-run.*"},
            for_each={"prefect.resource.id"},
            posture="Reactive",  # ty:ignore[invalid-argument-type]
            threshold=1,
        ),
        actions=[
            SendNotification(
                block_document_id=block._block_document_id,  # ty:ignore[invalid-argument-type]
                subject="Prefect flow run issue",
                body=NOTIFICATION_BODY.strip(),
            )
        ],
    )
    upsert_automation(automation)


if __name__ == "__main__":
    if not SLACK_WEBHOOK_URL:
        raise ValueError("Set SLACK_WEBHOOK_URL before running this example")
    deploy_slack_notifications()
