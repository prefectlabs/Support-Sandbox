"""
Pattern: Concurrent Tasks (CPU-bound)
Demonstrates: .map() + ProcessPoolTaskRunner

ProcessPoolTaskRunner runs each task in a separate OS process, bypassing Python's
GIL for true parallelism. Use it for CPU-bound work where threads would contend.

Differences from ThreadPoolTaskRunner (see 04_concurrent_tasks.py):
  - Each task runs in an isolated process — no shared state between tasks
  - All task inputs, outputs, and the task callable must be picklable
  - Uses the "spawn" start method on all platforms for consistency
  - Higher per-task overhead than threads — not worth it for fast or I/O-bound work
  - max_workers defaults to multiprocessing.cpu_count()

IMPORTANT: The if __name__ == "__main__" guard is required. Because ProcessPoolTaskRunner
uses "spawn", worker processes re-import this module. Without the guard, each worker
would attempt to launch the flow again, causing runaway process creation.

Run locally:
    uv run python examples/11_process_pool.py
"""

import hashlib
import multiprocessing

from prefect import flow, task
from prefect.task_runners import ProcessPoolTaskRunner


@task(log_prints=True)
def cpu_bound_task(payload: str) -> dict:
    """Simulate CPU-bound work: compute repeated SHA-256 hashes of a payload."""
    digest = payload
    for _ in range(200_000):
        digest = hashlib.sha256(digest.encode()).hexdigest()
    return {"payload": payload, "digest": digest[:16]}


@flow(
    task_runner=ProcessPoolTaskRunner(max_workers=multiprocessing.cpu_count()),
    log_prints=True,
)  # ty:ignore[no-matching-overload]
def process_pool_flow(items: list[str] | None = None) -> None:
    if items is None:
        items = [f"item-{i}" for i in range(8)]
    # .map() submits all tasks concurrently across worker processes.
    # Each process runs independently — no shared memory between tasks.
    futures = cpu_bound_task.map(items)
    results = [f.result() for f in futures]
    print(
        f"Processed {len(results)} items across {multiprocessing.cpu_count()} processes"
    )


if __name__ == "__main__":
    process_pool_flow()
