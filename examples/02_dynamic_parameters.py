"""
Pattern: Dynamic Parameters
Demonstrates: Pydantic model + StrEnum as flow parameters

Pydantic models render as structured forms in the Prefect Cloud UI —
dropdowns for enums, date pickers for datetime fields. This lets operators
run flows with validated, type-safe inputs without touching code.

Run locally:
    uv run python examples/02_dynamic_parameters.py
"""

import datetime
import enum

from prefect import flow, get_run_logger, task
from pydantic import BaseModel, Field


class Environment(enum.StrEnum):
    dev = "dev"
    staging = "staging"
    prod = "prod"


class AssetSelection(enum.StrEnum):
    orders = "orders"
    customers = "customers"
    products = "products"


class RunConfig(BaseModel):
    date: datetime.datetime = Field(
        title="Run Date",
        default_factory=datetime.datetime.now,
    )
    environment: Environment = Environment.dev
    assets: list[AssetSelection] = list(AssetSelection)


@task(retries=2, log_prints=True)
def process_asset(asset: str, environment: str, date: datetime.datetime) -> str:
    logger = get_run_logger()
    logger.info(f"Processing {asset} in {environment} for {date.date()}")
    return f"{asset}:{environment}:{date.date()}"


@flow(log_prints=True)
def demo_flow(config: RunConfig | None = None) -> None:
    if config is None:
        config = RunConfig()
    logger = get_run_logger()
    logger.info(f"Starting run for {config.date.date()} in {config.environment}")

    futures = [
        process_asset.submit(str(asset), str(config.environment), config.date)
        for asset in config.assets
    ]
    results = [f.result() for f in futures]
    print(f"Completed: {results}")


if __name__ == "__main__":
    demo_flow()
