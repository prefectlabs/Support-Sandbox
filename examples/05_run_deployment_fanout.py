"""
Pattern: Run Deployment Fan-out
Demonstrates: Parent flow fans out work to child deployments and polls for completion

Use run_deployment() (not subflows) when:
- Child processes have different resource requirements (e.g., GPU workers)
- You need to cancel a child run independently of the parent
- You're fanning out to many parameterized variants at scale

This file defines both flows. Deploy both before running the parent:
    prefect --no-prompt deploy --all

Run locally (skips deployment, calls child_flow directly):
    uv run python examples/05_run_deployment_fanout.py
"""

import asyncio
from datetime import datetime, timedelta

from prefect import flow, get_run_logger
from prefect.deployments import run_deployment

# Matches the deployment name defined in prefect.yaml for child_flow
CHILD_DEPLOYMENT_NAME = "child-flow/child-flow"


# ---------------------------------------------------------------------------
# Child flow — deployed independently, accepts a single date to process
# ---------------------------------------------------------------------------


@flow(log_prints=True)
def child_flow(date: str) -> dict:
    """Process data for a single date. Deployed and invoked by parent_flow."""
    logger = get_run_logger()
    logger.info(f"Processing date: {date}")

    # Simulate work
    result = {"date": date, "records_processed": 42}

    logger.info(f"Completed: {result}")
    return result


# ---------------------------------------------------------------------------
# Parent flow — submits one child deployment run per date, polls for completion
# ---------------------------------------------------------------------------


@flow(log_prints=True)
async def parent_flow(start_date: str = "01-01-2025", n_days: int = 5) -> None:
    """Fan out to child_flow deployments, one per date, and wait for all to finish.

    run_deployment timeout behaviour:
      timeout=None  — wait indefinitely for the child run to complete (default)
      timeout=0     — fire-and-forget; submit the run and move on without waiting
      timeout=N     — wait up to N seconds, then raise if not yet complete
    """
    logger = get_run_logger()

    start = datetime.strptime(start_date, "%m-%d-%Y")
    dates = [start.date() + timedelta(days=x) for x in range(n_days)]

    # Submit all child runs concurrently and wait for each to finish.
    # Swap timeout=None for timeout=0 to fire-and-forget instead.
    await asyncio.gather(
        *[
            run_deployment(
                name=CHILD_DEPLOYMENT_NAME,
                parameters={"date": str(d)},
                timeout=None,
            )
            for d in dates
        ]
    )  # ty:ignore[no-matching-overload]

    logger.info("All child runs complete")


if __name__ == "__main__":
    # Runs the parent locally — calls child_flow directly without going through deployments
    asyncio.run(parent_flow())
