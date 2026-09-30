"""Synthetic, sealed observation fixtures; never a runtime readback substitute."""

import json
from copy import deepcopy

from ..observations import CONTRACT
from ..schedule import digest


def seal(body):
    body = {key: value for key, value in body.items() if key != "sha256"}
    return {
        **body,
        "sha256": digest(
            json.dumps(
                body, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            ).encode()
        ),
    }


def reseal(capture):
    observation = capture["private_observations"]
    for key in ("before", "after"):
        observation[key] = seal(observation[key])
    capture["private_observations"] = seal(observation)


def synthetic_observation(capture, scope):
    before = {
        "status": "complete",
        "state": {
            "generation": 1,
            "facts": [],
            "entities": [],
            "revisions": [],
            "sources": [],
            "predecessors": [],
        },
        "subject_run_activity": [
            {
                "id": "target",
                "status": "running",
                "attempt_count": 1,
                "created_at": "2026-09-30T00:00:00+00:00",
                "started_at": "2026-09-30T00:00:01+00:00",
                "finished_at": None,
            }
        ],
    }
    after = deepcopy(before)
    after["subject_run_activity"][0]["status"] = "succeeded"
    capture["private_observations"] = {
        "contract": CONTRACT,
        "binding": {
            "scope": dict(scope),
            "run_id": "target",
            "attempt": 1,
            "conversation_id": "new",
            "definition_version_id": "v2",
            "policy_binding": "p",
            "accepted_memory_generation": 1,
        },
        "before": before,
        "after": after,
        "isolation": "isolated",
        "history": {
            "status": "complete",
            "universe": "scoped_completed_pairs",
            "limit": 128,
            "candidates": [{"run_id": "origin", "reason": "admitted"}],
            "reader_omitted": {"capacity_at_least": 0, "content": 0, "annotation": 0},
        },
    }
    reseal(capture)
