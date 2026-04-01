"""
Pattern: Basic Flow
Demonstrates: @flow, @task, retries, log_prints

Run locally:
    uv run python examples/01_basic_flow.py
"""

import random
import time

from prefect import flow, task


@task(retries=3, retry_delay_seconds=10, log_prints=True)
def fetch_records(n: int) -> list[dict]:
    """Simulate an API call that occasionally fails transiently."""
    time.sleep(1)
    if random.random() < 0.3:
        raise ValueError("Transient API error — will retry automatically")
    return [{"id": i, "value": i * 2} for i in range(n)]


@task(log_prints=True)
def process_records(records: list[dict]) -> list[dict]:
    """Transform raw records into the desired output shape."""
    return [{"id": r["id"], "result": r["value"] + 1} for r in records]


@flow(log_prints=True)
def basic_flow(n: int = 10) -> None:
    records = fetch_records(n)
    results = process_records(records)
    print(f"Processed {len(results)} records")


if __name__ == "__main__":
    basic_flow()
