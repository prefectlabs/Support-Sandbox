"""
Pattern: Custom Events
Demonstrates: emit_event from within a flow, event-driven deployment triggers

Emitting custom events decouples pipeline stages — Flow A emits an event on
completion and Flow B is triggered by that event via a deployment trigger,
rather than being called directly. This keeps flows independently deployable
and cancellable.

Corresponding deployment trigger config (in prefect.yaml):

    deployments:
      - name: downstream-flow
        triggers:
          - type: event
            event: "myorg.pipeline.item.completed"
            match:
              "prefect.resource.id": "myorg.pipeline.*"
            parameters:
              item: "{{ event.payload['item'] }}"
              input_path: "{{ event.payload['output_path'] }}"

Run locally:
    uv run python examples/06_custom_events.py
"""

from prefect import flow, task
from prefect.events import emit_event


@task(log_prints=True)
def do_work(item: str) -> str:
    print(f"Processing {item}")
    return f"s3://my-bucket/outputs/{item}.parquet"


@flow(log_prints=True)
def event_emitting_flow(item: str = "example-dataset") -> None:
    output_path = do_work(item)

    emit_event(
        event="myorg.pipeline.item.completed",
        resource={"prefect.resource.id": f"myorg.pipeline.{item}"},
        payload={"item": item, "output_path": output_path},
    )
    print(f"Emitted completion event for '{item}' → {output_path}")


if __name__ == "__main__":
    event_emitting_flow()
