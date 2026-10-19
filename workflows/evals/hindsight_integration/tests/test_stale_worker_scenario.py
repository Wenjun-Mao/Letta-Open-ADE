"""A recovered reply alone cannot stand in for an expired generated candidate."""

import asyncio
import copy

import pytest

from .. import stale_worker_scenario as scenario


@pytest.mark.parametrize(
    "damage", [None, "first_status", "candidate_missing", "attempt_count"]
)
def test_stale_case_requires_both_candidate_and_recovery_evidence(monkeypatch, damage):
    calls = []
    exported = {
        "saved_attempts": [
            {"id": "first", "attempt_number": 1, "status": "abandoned"},
            {"id": "second", "attempt_number": 2, "status": "succeeded"},
        ],
        "observations": [
            {
                "attempt_id": "first",
                "records": [
                    {
                        "type": "attempt_execution.finished",
                        "value": {"status": "candidate_produced"},
                    },
                ],
            }
        ],
    }
    if damage == "first_status":
        exported["saved_attempts"][0]["status"] = "succeeded"
    if damage == "candidate_missing":
        exported["observations"][0]["records"] = []

    class Context:
        async def session(self, label):
            return {
                "conversation": {"id": "conversation", "memory_subject_id": "subject"}
            }

        async def rule(self, session, **kwargs):
            assert kwargs == {"target": "router_chat", "mode": "hold_before_send"}
            return "fault"

        async def accept(self, session, content, *, retries):
            assert retries == 1
            return {"run_id": "run"}

        async def matched(self, fault):
            calls.append("held")

        async def host(self, action, details):
            calls.append(action)
            return {"status": "ok"}

        async def release(self, fault):
            calls.append("released")

        async def terminal(self, run, **kwargs):
            return {"attempt_count": 1 if damage == "attempt_count" else 2}

        async def messages(self, session, **kwargs):
            assert kwargs == {"users": 1, "assistants": 1}
            return {"saved": True}

        async def capture(self):
            return {"payload": {"runs": [{"private_export": copy.deepcopy(exported)}]}}

    async def reconcile(context, session):
        return {"retained": True}

    monkeypatch.setattr(scenario, "reconcile_delivery", reconcile)
    if damage:
        with pytest.raises(ValueError):
            asyncio.run(scenario.stale_worker(Context()))
    else:
        assert asyncio.run(scenario.stale_worker(Context()))["deliveries"]["retained"]
    assert calls == ["held", "lock-subject", "released", "expire-finalizer"]
