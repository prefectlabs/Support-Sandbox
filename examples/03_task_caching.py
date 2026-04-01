"""
Pattern: Task Caching
Demonstrates: INPUTS cache policy with S3 result storage

Tasks decorated with cache_policy=INPUTS will skip re-execution and return
the cached result when called with the same inputs. This avoids re-running
expensive computations (API calls, transforms, model inference) across runs.

Set S3_RESULT_BUCKET to the name of a Prefect S3Bucket block.
Set REFRESH_CACHE=True to force re-computation and overwrite the cache.

Run locally:
    uv run python examples/03_task_caching.py
"""

import os
import time
from typing import cast

from prefect import flow, get_run_logger, task
from prefect.cache_policies import INPUTS
from prefect_aws import S3Bucket

S3_RESULT_BUCKET = os.getenv("S3_RESULT_BUCKET", "your-s3-bucket-block-name")
REFRESH_CACHE = os.getenv("REFRESH_CACHE", "False").lower() == "true"


@task(cache_policy=INPUTS, refresh_cache=REFRESH_CACHE, log_prints=True)
def compute(value: int) -> int:
    """
    Expensive computation. On the first call with a given input this runs
    and stores the result. Subsequent calls with the same input return the
    cached result instantly without executing the function body.
    """
    logger = get_run_logger()
    logger.info(f"Computing for input={value} (not cached)")
    time.sleep(2)  # simulate expensive work
    return value * 10


@flow(persist_result=True, log_prints=True)
def main_flow(values: list[int] | None = None) -> None:
    if values is None:
        values = [1, 2, 3]
    # Result storage is configured on the flow; tasks inherit it.
    # Load your S3Bucket block — create it once via the Prefect UI or CLI:
    #   prefect block create s3-bucket --name your-s3-bucket-block-name
    result_storage = cast(S3Bucket, S3Bucket.load(S3_RESULT_BUCKET))
    result_storage.bucket_folder = "task-cache"

    futures = compute.map(values)
    results = [f.result() for f in futures]
    print(f"Results: {results}")


if __name__ == "__main__":
    main_flow()
