"""
Pattern: Task Dependencies
Demonstrates: wait_for, task_run_name, flow.with_options()

By default Prefect infers task dependencies from Python data flow — if Task B
consumes Task A's output, B waits for A automatically. Use wait_for explicitly
when Task B depends on Task A completing but doesn't consume its return value.

flow.with_options() creates a new version of a flow with overridden settings
(e.g. a custom run name) without modifying the original flow definition.

Run locally:
    uv run python examples/10_task_dependencies.py
"""

import time

from prefect import flow, get_run_logger, task


@task(task_run_name="setup-{label}", log_prints=True)
def setup_task(label: str) -> str:
    """Simulate a setup step that downstream tasks should wait for."""
    logger = get_run_logger()
    logger.info(f"Running setup: {label}")
    time.sleep(1)
    return f"setup-{label}-complete"


@task(task_run_name="process-{word}", log_prints=True)
def process_task(word: str) -> list[str]:
    """Process only after all setup tasks have finished."""
    logger = get_run_logger()
    logger.info(f"Processing: {word}")
    return [c.upper() for c in word]


@flow(log_prints=True)
def dependency_flow() -> None:
    labels = ["alpha", "beta", "gamma"]

    # Submit setup tasks concurrently
    setup_futures = [setup_task.submit(label) for label in labels]

    # process_task doesn't use setup output — use wait_for to express the dependency
    result = process_task(word="prefect", wait_for=setup_futures)
    print(f"Result: {result}")


if __name__ == "__main__":
    # Run once with a default name, once with a custom run name
    dependency_flow.with_options(flow_run_name="dependency-example-run-1")()
    dependency_flow()
