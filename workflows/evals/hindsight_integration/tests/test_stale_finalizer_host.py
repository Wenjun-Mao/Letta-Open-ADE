"""SQL lock faults must be scope-bound, finite and reversible."""

import io
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from .. import stale_finalizer_host as host


@pytest.mark.parametrize(
    "details", [{}, {"run_id": "not-uuid"}, {"run_id": str(uuid4()), "sql": "DROP"}]
)
def test_host_control_accepts_only_declared_uuid_fields(details):
    with pytest.raises(ValueError):
        host.identifiers(details, ("run_id",))


def test_subject_lock_refuses_a_different_workspace_before_starting_sql(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(host, "owned_service", lambda *args: {"id": "owned"})
    control = SimpleNamespace(docker=None, lease=None, output=tmp_path)
    fault = host.StaleFinalizer(control, "owned-workspace")
    queries = []

    def read(query):
        queries.append(query)
        return "0"

    fault.read = read
    with pytest.raises(ValueError, match="outside_owned"):
        fault.lock({"subject_id": str(uuid4()), "conversation_id": str(uuid4())})
    assert "w.workspace_key='owned-workspace'" in queries[0]
    assert fault.process is None


def test_expiry_wait_is_real_database_time_then_rollback_before_resume(tmp_path):
    events = []
    control = SimpleNamespace(
        output=tmp_path,
        fence=lambda: events.append("fence"),
        current=lambda name: {"id": "owned-worker"},
        docker=SimpleNamespace(_run=lambda command: events.append(command)),
    )
    fault = host.StaleFinalizer.__new__(host.StaleFinalizer)
    fault.controls, fault.conversation, fault.pid = control, str(uuid4()), 123
    fault.process = SimpleNamespace(poll=lambda: None)
    fault.paused = False
    fault.read = lambda query: "1"
    predicates = []

    def until(read, predicate, seconds):
        predicates.append(predicate)
        return (
            '[{"query":"SELECT memory_subjects FOR UPDATE"}]'
            if len(predicates) == 1
            else '{"expired":true}'
        )

    fault.until = until
    fault.unlock = lambda: events.append("rollback")
    result = fault.expire({"run_id": str(uuid4())})
    assert result["lease"]["expired"] is True
    assert not predicates[1]('{"expired":false}')
    assert events.index(["pause", "owned-worker"]) < events.index("rollback")
    assert events.index("rollback") < events.index(["unpause", "owned-worker"])
    assert not fault.paused
    assert json.loads((tmp_path / "expired-finalizer.json").read_text()) == result


def test_cleanup_always_resumes_owned_worker_even_if_unlock_fails():
    fault = host.StaleFinalizer.__new__(host.StaleFinalizer)
    events = []
    fault.unlock = lambda: (_ for _ in ()).throw(OSError("controlled"))
    fault.resume = lambda: events.append("resume")
    with pytest.raises(OSError):
        fault.close()
    assert events == ["resume"]


def test_lock_process_uses_rollback_not_product_mutation():
    fault = host.StaleFinalizer.__new__(host.StaleFinalizer)
    commands = io.StringIO()
    fault.process = SimpleNamespace(
        stdin=commands, poll=lambda: None, wait=lambda **kwargs: None
    )
    fault.log = io.StringIO()
    fault.unlock()
    assert commands.getvalue() == "ROLLBACK;\n\\q\n"
