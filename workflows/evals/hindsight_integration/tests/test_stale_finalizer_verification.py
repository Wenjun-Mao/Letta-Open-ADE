"""Host readback proves the real recovery reason, not a made-up attempt state."""

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ..stale_finalizer_host import StaleFinalizer


@pytest.mark.parametrize("error", ["worker_lease_expired", "other_error"])
def test_recovery_requires_real_failed_lease_outcome_and_single_assistant(
    tmp_path, error
):
    fault = StaleFinalizer.__new__(StaleFinalizer)
    fault.controls = SimpleNamespace(output=tmp_path)
    fault.conversation = str(uuid4())
    attempts = [
        {"number": 1, "status": "failed", "error_code": error},
        {"number": 2, "status": "succeeded", "error_code": None},
    ]
    fault.read = lambda query: json.dumps(attempts) if "run_attempts" in query else "1"
    if error == "worker_lease_expired":
        assert fault.verify({"run_id": str(uuid4())})["committed_assistants"] == 1
    else:
        with pytest.raises(ValueError, match="outcome_mismatch"):
            fault.verify({"run_id": str(uuid4())})
        assert not (tmp_path / "finalizer-recovery.json").exists()
