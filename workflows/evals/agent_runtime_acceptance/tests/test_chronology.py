from types import SimpleNamespace

from workflows.evals.agent_runtime_acceptance.chronology import case_chronology


def test_chronology_attributes_existing_events_in_sequence_without_new_calls() -> None:
    case = SimpleNamespace(
        turns=(
            SimpleNamespace(
                run_id="run-1",
                conversation_key="old-chat",
                observation=SimpleNamespace(status="succeeded"),
            ),
        ),
        events=(
            SimpleNamespace(
                run_id="run-1",
                sequence=4,
                event_type="memory.committed",
                payload={"operation": "correct"},
            ),
            SimpleNamespace(
                run_id="run-1", sequence=1, event_type="context.built", payload={}
            ),
            SimpleNamespace(
                run_id="run-1",
                sequence=3,
                event_type="memory.proposed",
                payload={"operation": "correct"},
            ),
            SimpleNamespace(
                run_id="run-1",
                sequence=2,
                event_type="model.response.completed",
                payload={"role": "conversation"},
            ),
        ),
    )

    timeline = case_chronology(case)

    assert timeline[0]["event_order"] == [
        "context.built",
        "model.response.completed",
        "memory.proposed",
        "memory.committed",
    ]
    assert timeline[0]["stages"]["context"][0]["sequence"] == 1
    assert timeline[0]["stages"]["generation"][0]["sequence"] == 2
    assert timeline[0]["stages"]["extraction_and_validation"][0]["sequence"] == 3
    assert timeline[0]["stages"]["storage"][0]["sequence"] == 4
    assert timeline[0]["stages"]["provider"][0]["sequence"] == 2
