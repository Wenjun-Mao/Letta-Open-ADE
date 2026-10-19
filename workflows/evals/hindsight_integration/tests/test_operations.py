"""The safety stop must select exact owned containers and preserve the baseline."""

from dataclasses import replace
import json

import pytest

from workflows.evals.hindsight_integration.operations import (
    GIB,
    OWNER_LABEL,
    PROJECT_LABEL,
    SOURCE_LABEL,
    Lease,
    check_lease,
    prepare_lease,
    stop_owned,
    canonical_snapshot,
    DockerOperations,
)


REVISION = "a" * 40
CAPACITY = {"available_ram": 20 * GIB, "free_disk": 50 * GIB}


class DockerFake:
    def __init__(self):
        self.records = [{"id": "baseline", "state": "running", "labels": {}}]
        self.stopped = []

    def snapshot(self, identities=None):
        return sorted(
            [
                record
                for record in self.records
                if identities is None or record["id"] in identities
            ],
            key=lambda record: record["id"],
        )

    def owned(self, lease):
        return [record for record in self.records if lease.owns(record)]

    def stop(self, identity):
        assert identity != "baseline", "The baseline may never be stopped"
        self.stopped.append(identity)


def prepare(tmp_path, docker):
    return prepare_lease(
        tmp_path,
        docker=docker,
        project="ade-hindsight-integration",
        source_revision=REVISION,
        disk_path="/mnt/projects",
        duration=7_200,
        now=100,
    )


def owned_record(lease, identity="candidate", service="hindsight"):
    return {
        "id": identity,
        "state": "running",
        "labels": {
            PROJECT_LABEL: lease.project,
            OWNER_LABEL: lease.activation_id,
            SOURCE_LABEL: lease.source_revision,
            "com.docker.compose.service": service,
        },
    }


def test_lease_is_finite_sealed_and_create_only(tmp_path):
    docker = DockerFake()
    lease = prepare(tmp_path, docker)
    assert Lease.load(tmp_path) == lease
    assert lease.dispatch_deadline == 3_700
    assert lease.expires_at == 7_300
    with pytest.raises(FileExistsError):
        lease.save(tmp_path)
    value = json.loads((tmp_path / "lease.json").read_text())
    value["expires_at"] += 1
    (tmp_path / "lease.json").write_text(json.dumps(value))
    with pytest.raises(ValueError, match="changed"):
        Lease.load(tmp_path)


def test_new_activation_does_not_take_over_a_running_previous_owner(tmp_path):
    docker = DockerFake()
    lease = prepare(tmp_path / "first", docker)
    docker.records.append(owned_record(lease))
    with pytest.raises(ValueError, match="previous activation"):
        prepare(tmp_path / "second", docker)


def test_different_project_does_not_bypass_single_activation_owner(tmp_path):
    docker = DockerFake()
    lease = prepare(tmp_path / "first", docker)
    docker.records.append(owned_record(replace(lease, project=lease.project + "-old")))
    with pytest.raises(ValueError, match="previous activation"):
        prepare(tmp_path / "second", docker)


def test_mount_order_is_not_baseline_drift_but_mount_changes_are(tmp_path):
    docker = DockerFake()
    mounts = [{"Destination": "/a", "Source": "one"}, {"Destination": "/b"}]
    docker.records[0]["mounts"] = mounts
    lease = prepare(tmp_path, docker)
    docker.records[0] = {**docker.records[0], "mounts": list(reversed(mounts))}
    assert check_lease(lease, docker=docker, capacity=CAPACITY, now=101) == []
    docker.records[0]["mounts"] = [{"Destination": "/a", "Source": "other"}]
    assert check_lease(lease, docker=docker, capacity=CAPACITY, now=101) == [
        "baseline_changed"
    ]
    assert canonical_snapshot({"mounts": mounts}) == canonical_snapshot(
        {"mounts": list(reversed(mounts))}
    )


def test_only_explicit_auto_removing_oneoffs_have_a_transient_lifecycle(tmp_path):
    docker = DockerFake()
    job = {
        "id": "job",
        "state": "running",
        "auto_remove": True,
        "labels": {"com.docker.compose.oneoff": "True"},
    }
    docker.records.append(job)
    lease = prepare(tmp_path, docker)
    assert [item["id"] for item in lease.baseline] == ["baseline"]
    assert lease.transient_baseline == (job,)
    assert Lease.load(tmp_path).transient_baseline == (job,)
    docker.records.remove(job)
    assert check_lease(lease, docker=docker, capacity=CAPACITY, now=101) == []
    docker.records.clear()
    assert check_lease(lease, docker=docker, capacity=CAPACITY, now=101) == [
        "baseline_changed"
    ]


def test_oneoff_label_alone_cannot_exempt_a_persistent_container(tmp_path):
    docker = DockerFake()
    docker.records[0]["labels"]["com.docker.compose.oneoff"] = "True"
    lease = prepare(tmp_path, docker)
    assert lease.transient_baseline == ()
    docker.records.clear()
    assert check_lease(lease, docker=docker, capacity=CAPACITY, now=101) == [
        "baseline_changed"
    ]


def test_stopped_previous_candidates_are_not_baseline_services(tmp_path):
    docker = DockerFake()
    prior = prepare(tmp_path / "prior", docker)
    docker.records.append({**owned_record(prior), "state": "exited"})
    lease = prepare(tmp_path / "next", docker)
    assert [item["id"] for item in lease.baseline] == ["baseline"]


@pytest.mark.parametrize(
    "error",
    ["Error response from daemon: No such container: missing", "permission denied"],
)
def test_docker_inspection_race_is_narrow_and_does_not_hide_other_errors(
    monkeypatch, error
):
    from types import SimpleNamespace
    from workflows.evals.hindsight_integration import operations

    monkeypatch.setattr(
        operations.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(
            returncode=1,
            stdout='{"id":"alive"}\n',
            stderr=error,
        ),
    )
    if error.startswith("Error response from daemon: No such container"):
        assert DockerOperations().snapshot(["alive", "missing"]) == [{"id": "alive"}]
    else:
        with pytest.raises(RuntimeError, match="inspection_failed"):
            DockerOperations().snapshot(["alive", "missing"])


@pytest.mark.parametrize(
    "updates",
    [{"project": "teslamate"}, {"expires_at": 50_000}, {"minimum_available_ram": GIB}],
)
def test_invalid_scope_unbounded_duration_or_weakened_reserve_is_rejected(
    tmp_path, updates
):
    lease = prepare(tmp_path, DockerFake())
    with pytest.raises(ValueError):
        replace(lease, **updates)


def test_expiry_and_resource_pressure_close_admission(tmp_path):
    docker = DockerFake()
    lease = prepare(tmp_path, docker)
    assert check_lease(lease, docker=docker, capacity=CAPACITY, now=101) == []
    assert check_lease(lease, docker=docker, capacity=CAPACITY, now=3_700) == [
        "dispatch_window_closed"
    ]
    pressure = {"available_ram": 3 * GIB, "free_disk": GIB}
    assert check_lease(lease, docker=docker, capacity=pressure, now=101) == [
        "host_ram_reserve_breached",
        "host_disk_reserve_breached",
    ]


def test_baseline_drift_or_candidate_oom_stops_the_window(tmp_path):
    docker = DockerFake()
    lease = prepare(tmp_path, docker)
    docker.records[0] = {**docker.records[0], "state": "exited"}
    docker.records.append({**owned_record(lease), "oom": True})
    assert check_lease(lease, docker=docker, capacity=CAPACITY, now=101) == [
        "baseline_changed",
        "candidate_unhealthy",
    ]


def test_stop_owns_project_activation_source_and_stops_router_first(tmp_path):
    docker = DockerFake()
    lease = prepare(tmp_path, docker)
    docker.records.extend(
        [
            owned_record(lease, "db", "db"),
            owned_record(lease, "worker"),
            owned_record(lease, "router", "model-router"),
            owned_record(replace(lease, source_revision="b" * 40), "other-source"),
            owned_record(
                replace(lease, activation_id="8b4a7adb-18b7-4195-9df2-191a383675bf"),
                "other-lease",
            ),
        ]
    )
    receipt = stop_owned(lease, docker=docker, root=tmp_path, reason="test_expiry")
    assert docker.stopped == ["router", "other-source", "worker", "db"]
    assert receipt["failures"] == []
    assert len(list((tmp_path / "stops").glob("*.json"))) == 1
    assert (tmp_path / "closed.json").is_file()
    assert "activation_closed" in check_lease(
        lease, docker=docker, capacity=CAPACITY, now=101, closed=True
    )


def test_admission_is_closed_even_when_docker_is_unavailable(tmp_path):
    docker = DockerFake()
    lease = prepare(tmp_path, docker)

    class UnavailableDocker:
        def owned(self, lease):
            raise RuntimeError("unavailable")

    receipt = stop_owned(
        lease, docker=UnavailableDocker(), root=tmp_path, reason="supervision_failed"
    )
    assert receipt["failures"] == [{"id": None, "error_type": "RuntimeError"}]
    assert (tmp_path / "closed.json").is_file()


def test_wrong_candidate_source_is_owned_but_cannot_pass_health_admission(tmp_path):
    docker = DockerFake()
    lease = prepare(tmp_path, docker)
    docker.records.append(owned_record(replace(lease, source_revision="b" * 40)))
    assert check_lease(lease, docker=docker, capacity=CAPACITY, now=101) == [
        "candidate_source_mismatch"
    ]
