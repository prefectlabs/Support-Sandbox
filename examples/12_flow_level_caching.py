"""
Pattern: Flow Level Caching
Demonstrates: Flow level caching with ThreadPoolTaskRunner and GCS result storage

Leverage caching and subflows to generate a report that is computationally expensive
to acquire, while preserving the ability to re-run individual components.

Set GCS_RESULT_BUCKET to the name of a Prefect GCSBucket block.

Run locally (the transform flow must be registered as a deployment):
    uv run python examples/12_flow_level_caching.py
"""

import os
from datetime import timedelta
from random import randint
from time import sleep

from prefect import flow, get_run_logger, runtime, task
from prefect.cache_policies import INPUTS
from prefect.deployments import run_deployment
from prefect.task_runners import ThreadPoolTaskRunner
from prefect_gcp import GcsBucket

GCS_RESULT_BUCKET = os.getenv("GCS_RESULT_BUCKET", "your-gcs-bucket-block-name")
storage_block: GcsBucket = GcsBucket.load(name=GCS_RESULT_BUCKET, _sync=True)  # ty: ignore[invalid-assignment, unknown-argument]


@task(
    cache_policy=INPUTS,
    cache_expiration=timedelta(minutes=15),
)
def execute_query(
    source: str,
    query: str,
) -> str:
    """
    Expensive query execution. Simulates executing a query in BigQuery where the
    query results are exported to GCS. Returns the URI of the exported parquet file.
    """
    logger = get_run_logger()
    logger.info("Executing query `%s` for source '%s'", query, source)

    # simulate expensive query execution
    sleep(randint(10, 20))
    logger.info("Query completed for source '%s'", source)

    return f"gs://your-gcs-bucket/report_queries/{source}.parquet"


@flow(
    persist_result=True,
    result_storage=storage_block,
    task_runner=ThreadPoolTaskRunner(),
)  # ty: ignore[no-matching-overload]
def transform_data(result_uri: str) -> str:
    """
    Subflow to transform the data in the exported parquet file. Separated to spin up
    additional compute for transforming the data. Returns the URI of the transformed
    parquet file.
    """
    logger = get_run_logger()
    logger.info("Starting transform for %s", result_uri)

    # simulate expensive transformation
    sleep(randint(10, 20))
    logger.info("Transform completed for %s", result_uri)

    # grab the source name from the result URI to use as the output file name
    source = result_uri.split("/")[-1].split(".")[0]
    return f"gs://your-gcs-bucket/transform_results/{source}.parquet"


@task(cache_policy=INPUTS, cache_expiration=timedelta(minutes=15))
def run_transform(result_uri: str) -> str:
    """Task wrapper to run transform subflow."""
    logger = get_run_logger()
    logger.info("Kicking off subflow to transform data for %s", result_uri)

    # run another deployment to use additional compute for transforming the data
    transform_data_uri: str = run_deployment(
        "transform-data/transform-gcs-report-data",
        parameters={"result_uri": result_uri},
    ).state.result()  # ty: ignore[invalid-assignment, unresolved-attribute]
    return transform_data_uri


@task
def update_dashboard(transform_results: list) -> None:
    """
    Task to update the dashboard with the transform results. Simulates a failure on
    the first flow run to demonstrate the advantage of caching.
    """
    # simulate a failure to demonstrate how caching previous tasks helps
    if runtime.flow_run.run_count == 1:  # ty: ignore[possibly-missing-submodule]
        raise Exception("Hit a 503 trying to update the dashboard! Retrying...")
    logger = get_run_logger()
    logger.info("Updating dashboard with transform results %s", transform_results)
    return None


@flow(
    retries=3,
    persist_result=True,
    result_storage=storage_block,
    task_runner=ThreadPoolTaskRunner(),
)  # ty: ignore[no-matching-overload]
def generate_report() -> None:
    """
    Parent flow to generate a report. Executes two expensive queries, transforms
    the data, and updates a dashboard.
    """
    logger = get_run_logger()
    logger.info("Starting report generation")

    query_a_future = execute_query.submit(source="A", query="SELECT * FROM A;")
    query_b_future = execute_query.submit(source="B", query="SELECT * FROM B;")
    logger.info("Queries completed successfully, kicking off transforms")

    transform_futures = run_transform.map([query_a_future, query_b_future])
    transform_results = transform_futures.result()
    logger.info("Transforms completed successfully, updating dashboard")

    update_dashboard.submit(transform_results).result()
    logger.info("Dashboard updated successfully. Exiting...")


if __name__ == "__main__":
    generate_report()
