"""
Pattern: Concurrent Tasks (I/O-bound)
Demonstrates: .map() + ThreadPoolTaskRunner

For high-throughput, low-resource workloads (API calls, small record processing,
lightweight syncs), batch all work into a single flow run and parallelize within
it using .map(). Do NOT schedule one flow run per item — each run carries
orchestration overhead and creates noisy observability.

ThreadPoolTaskRunner (the default) is sufficient for I/O-bound work.
Use ProcessPoolTaskRunner for CPU-bound work instead.

Run locally:
    uv run python examples/04_concurrent_tasks.py
"""

import time

from prefect import flow, task
from prefect.task_runners import ThreadPoolTaskRunner


@task(log_prints=True)
def process_item(item: int) -> dict:
    """Simulate an I/O-bound operation (API call, DB query, file read)."""
    time.sleep(0.5)
    return {"item": item, "result": item * 2}


@flow(task_runner=ThreadPoolTaskRunner(max_workers=10), log_prints=True)  # ty: ignore[no-matching-overload]
def concurrent_tasks_flow(items: list[int] | None = None) -> None:
    if items is None:
        items = list(range(20))
    # .map() submits all tasks concurrently — the task runner controls parallelism.
    # All 20 items run with up to 10 concurrent workers instead of sequentially.
    futures = process_item.map(items)
    results = [f.result() for f in futures]
    print(f"Processed {len(results)} items concurrently")


if __name__ == "__main__":
    concurrent_tasks_flow()
