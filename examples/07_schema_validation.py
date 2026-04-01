"""
Pattern: Schema Validation
Demonstrates: validate_parameters=True with Pydantic model + Enum

When validate_parameters=True (the default), Prefect validates flow inputs
against the parameter schema at run time. Pydantic models and Enums in the
signature render as typed form fields in the Prefect Cloud UI.

Run locally:
    uv run python examples/07_schema_validation.py
"""

import datetime
import enum

from prefect import flow, get_run_logger
from pydantic import BaseModel


class Sentiment(enum.StrEnum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class AnalysisInput(BaseModel):
    keywords: list[str]
    date: datetime.datetime
    sentiment_filter: Sentiment = Sentiment.positive


@flow(name="schema-validation-example", validate_parameters=True, log_prints=True)
def test_flow(input: AnalysisInput | None = None) -> None:
    if input is None:
        input = AnalysisInput(
            keywords=["prefect", "workflow"],
            date=datetime.datetime(2025, 1, 1),
        )
    logger = get_run_logger()
    logger.info(f"Running analysis for: {input}")
    print(f"Keywords: {input.keywords}")
    print(f"Date: {input.date.date()}")
    print(f"Sentiment filter: {input.sentiment_filter}")


if __name__ == "__main__":
    test_flow.serve(name="schema-validation-ui-test")
