"""
Pattern: Event-Triggered Flow Chaining
Demonstrates: upstream_flow emits a custom event; downstream_flow is deployed
with a trigger that fires automatically when that event is received.

Compare with example 05 (run_deployment fan-out):
- 05: tight coupling — parent directly invokes child by deployment name
- 12: loose coupling — flows communicate only through an event payload;
  each can be deployed, paused, or replaced independently

Corresponding prefect.yaml trigger for downstream_flow:

    - name: event-triggered-downstream
      triggers:
        - type: event
          enabled: true
          name: upstream-stage-completed
          expect:
            - "myorg.pipeline.stage.completed"
          match:
            "prefect.resource.id": "myorg.pipeline.*"
          parameters:
            dataset: "{{ event.payload['dataset'] }}"
            upstream_output: "{{ event.payload['output_path'] }}"

Deploy both flows:
    prefect --no-prompt deploy --all

Run upstream locally (emits the event, does not wait for downstream):
    uv run python examples/12_event_triggered_flow.py
"""

from prefect import flow, task
from prefect.events import emit_event


@task(log_prints=True)
def process_dataset(dataset: str) -> str:
    """Simulate work that produces an output artifact."""
    print(f"Processing dataset: {dataset}")
    return f"s3://my-bucket/outputs/{dataset}.parquet"


@flow(log_prints=True)
def upstream_flow(dataset: str = "sales-2025-01-01") -> None:
    """Upstream stage: process data and emit a completion event.

    The event payload carries everything the downstream flow needs —
    no direct import or deployment name coupling required.
    """
    output_path = process_dataset(dataset)

    emit_event(
        event="myorg.pipeline.stage.completed",
        resource={"prefect.resource.id": f"myorg.pipeline.{dataset}"},
        payload={"dataset": dataset, "output_path": output_path},
    )
    print(f"Emitted completion event → {output_path}")


@flow(log_prints=True)
def downstream_flow(
    dataset: str = "sales-2025-01-01",
    upstream_output: str = "",
) -> None:
    """Downstream stage: triggered by the event emitted by upstream_flow.

    Parameters are populated automatically from the event payload via the
    deployment trigger in prefect.yaml — no code change needed to update
    what gets passed through.
    """
    print(f"Received dataset: '{dataset}'")
    print(f"Upstream output path: {upstream_output}")
    print("Running downstream processing...")


if __name__ == "__main__":
    upstream_flow()
