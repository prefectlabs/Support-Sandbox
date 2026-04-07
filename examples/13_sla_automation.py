"""
Pattern: SLA Breach Notification
Demonstrates: Automation that fires a Slack notification when a deployment's
flow runs exceed their expected duration.

How it works (two-part setup):
    1. A Time-to-Completion SLA is added to the deployment in prefect.yaml:

           slas:
             - name: basic-flow-duration-sla
               severity: high
               duration: 300  # seconds — set to ~1.5x your typical run time

       When a flow run exceeds this duration, Prefect emits a
       `prefect.sla.violation` event automatically.

    2. This automation (defined here) listens for that event and sends a
       Slack notification. It fires for any deployment that has an SLA
       configured — scope it to a specific deployment by adding:

           match:
             "prefect.resource.name": "basic-flow/basic-flow"

       to the EventTrigger if you want per-deployment automation.

Run:
    uv run python examples/13_sla_automation.py
"""

from prefect import flow, get_run_logger, task
from prefect.automations import Automation
from prefect.blocks.notifications import SlackWebhook
from prefect.events.actions import SendNotification
from prefect.events.schemas.automations import EventTrigger

SLACK_BLOCK_NAME = "slack-test"
AUTOMATION_NAME = "sla-breach-slack-notification"

NOTIFICATION_BODY = """
*SLA Breach — {{ flow.name }}/{{ flow_run.name }}*
A flow run has exceeded its expected duration and not yet completed.

Flow run URL: {{ flow_run|ui_url }}
State: {{ flow_run.state.name }}
"""


@task
def load_slack_block(block_name: str) -> SlackWebhook:
    logger = get_run_logger()
    block: SlackWebhook = SlackWebhook.load(block_name)  # ty:ignore[invalid-assignment]
    logger.info(f"Loaded SlackWebhook block: '{block_name}'")
    return block


@task
def upsert_automation(automation: Automation) -> None:
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
def deploy_sla_automation(slack_block_name: str = SLACK_BLOCK_NAME) -> None:
    """Create or update the SLA breach notification automation.

    Pairs with any deployment that has `slas` configured in prefect.yaml.
    When a flow run violates its SLA, this automation sends a Slack alert.
    """
    block = load_slack_block(slack_block_name)

    automation = Automation(
        name=AUTOMATION_NAME,
        trigger=EventTrigger(
            expect={"prefect.sla.violation"},
            match={"prefect.resource.id": "prefect.flow-run.*"},
            for_each={"prefect.resource.id"},
            posture="Reactive",  # ty:ignore[invalid-argument-type]
            threshold=1,
        ),
        actions=[
            SendNotification(
                block_document_id=block._block_document_id,  # ty:ignore[invalid-argument-type]
                subject="Prefect SLA Breach",
                body=NOTIFICATION_BODY.strip(),
            )
        ],
    )
    upsert_automation(automation)


if __name__ == "__main__":
    deploy_sla_automation()
