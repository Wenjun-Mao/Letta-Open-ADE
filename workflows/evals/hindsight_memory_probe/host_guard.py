"""Linux/Docker observations and positive ownership; stdlib only."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

GIB = 1024**3
PROJECT = "ade-hindsight-probe"
SERVICES = {"db", "model-router", "hindsight", "runner"}
CONTAINER_READER = None


def command_json(arguments):
    result = subprocess.run(arguments, check=True, capture_output=True, timeout=5)
    return json.loads(result.stdout)


def containers():
    if CONTAINER_READER is not None:
        return CONTAINER_READER()
    result = subprocess.run(
        ["docker", "ps", "-aq"], check=True, capture_output=True, timeout=5
    )
    ids = result.stdout.decode().split()
    return command_json(["docker", "inspect", *ids]) if ids else []


def baseline_projection(container):
    state = container["State"]
    return {
        "id": container["Id"],
        "image": container["Image"],
        "started": state["StartedAt"],
        "status": state["Status"],
        "health": state.get("Health", {}).get("Status"),
        "restarts": container["RestartCount"],
    }


def owned(container, registry):
    labels = container.get("Config", {}).get("Labels") or {}
    releases = [
        Path(p) for p in registry.get("authorized_releases", [registry["release"]])
    ]
    return any(
        labels.get("com.docker.compose.project") == PROJECT
        and labels.get("com.docker.compose.service") in SERVICES
        and labels.get("com.docker.compose.project.working_dir")
        == str(release / "workflows/evals/hindsight_memory_probe")
        and labels.get("com.docker.compose.project.config_files")
        == str(release / "workflows/evals/hindsight_memory_probe/compose.yaml")
        for release in releases
    )


def candidate_containers(items, registry):
    for container in items:
        labels = container.get("Config", {}).get("Labels") or {}
        if labels.get("com.docker.compose.project") == PROJECT and not owned(
            container, registry
        ):
            raise RuntimeError("conflicting_project_ownership")
    return [c for c in items if owned(c, registry)]


def memory_available():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("memory_readback_failed")


def cpu_capacity():
    return len(os.sched_getaffinity(0))


def proc_identity(pid, proc_root=Path("/proc")):
    try:
        directory = proc_root / str(pid)
        stat = (directory / "stat").read_text()
        fields = stat[stat.rfind(")") + 2 :].split()
        return {
            "pid": pid,
            "start_ticks": fields[19],
            "uid": directory.stat().st_uid,
            "cmd_sha256": hashlib.sha256(
                (directory / "cmdline").read_bytes()
            ).hexdigest(),
        }
    except (OSError, ValueError, IndexError):
        return None


def identity_matches(identity, proc_root=Path("/proc")):
    return proc_identity(identity["pid"], proc_root) == identity


def tagged_processes(token, proc_root=Path("/proc")):
    marker = ("ADE_PROBE_PROCESS_OWNER=" + token).encode()
    result = []
    for directory in proc_root.iterdir():
        if not directory.name.isdigit():
            continue
        try:
            if marker in (directory / "environ").read_bytes().split(b"\0"):
                identity = proc_identity(int(directory.name), proc_root)
                if identity and identity["uid"] == os.getuid():
                    result.append(identity)
        except OSError:
            continue
    return result


def stop_processes(job, proc_root=Path("/proc"), kill=os.kill):
    # Root identity plus inherited unique marker prevents PID reuse and unrelated group kills.
    root = job["identity"]
    if identity_matches(root, proc_root) and root not in tagged_processes(
        job["token"], proc_root
    ):
        raise RuntimeError("process_ownership_failed")
    for identity in tagged_processes(job["token"], proc_root):
        if identity_matches(identity, proc_root):
            try:
                kill(identity["pid"], signal.SIGTERM)
            except ProcessLookupError:
                pass
    return tagged_processes(job["token"], proc_root)


def stop_containers(items, registry):
    candidates = candidate_containers(items, registry)
    # Preserve evidence/volumes. Reinspect identity immediately before explicit-ID stop.
    for service in ["runner", "hindsight", "model-router", "db"]:
        for candidate in candidates:
            if (
                candidate["Config"]["Labels"]["com.docker.compose.service"] != service
                or candidate["State"]["Status"] != "running"
            ):
                continue
            fresh = command_json(["docker", "inspect", candidate["Id"]])[0]
            if fresh["Id"] != candidate["Id"] or not owned(fresh, registry):
                raise RuntimeError("container_ownership_changed")
            grace, wall = (35, 45) if service == "hindsight" else (10, 20)
            subprocess.run(
                ["docker", "stop", "--time", str(grace), candidate["Id"]],
                check=True,
                capture_output=True,
                timeout=wall,
            )


def guard_reason(
    registry,
    items,
    available,
    disk_free,
    low_since,
    now,
    allocations=None,
    lifecycle_view=None,
):
    by_id = {c["Id"]: c for c in items}
    for original in registry["baseline"]:
        current = by_id.get(original["id"])
        if current is None or baseline_projection(current) != original:
            return "baseline_identity_or_health_changed", low_since
    candidates = candidate_containers(items, registry)
    lifecycle_states = {
        "active", "dormant", "replacement_pending", "unadmitted",
        "startup_pending", "planned_stopped",
    }
    if lifecycle_view is not None and (
        not isinstance(lifecycle_view, dict)
        or "reason" not in lifecycle_view
        or not isinstance(lifecycle_view.get("containers"), dict)
        or lifecycle_view.get("reason") is not None
        and (
            not isinstance(lifecycle_view.get("reason"), str)
            or not lifecycle_view["reason"]
        )
        or any(
            not isinstance(identifier, str)
            or not isinstance(status, str)
            or status not in lifecycle_states
            for identifier, status in lifecycle_view.get("containers", {}).items()
        )
    ):
        return "candidate_lifecycle_view_invalid", low_since
    if lifecycle_view is not None and lifecycle_view["reason"]:
        return lifecycle_view["reason"], low_since
    for candidate in candidates:
        lifecycle_status = (
            lifecycle_view["containers"].get(candidate["Id"])
            if lifecycle_view is not None
            else None
        )
        if lifecycle_status in {
            "dormant",
            "replacement_pending",
        }:
            continue
        state = candidate["State"]
        if allocations is not None:
            expected = allocations[
                candidate["Config"]["Labels"]["com.docker.compose.service"]
            ]
            effective = candidate["HostConfig"]
            if effective.get("Memory") != expected["memory"] or effective.get(
                "NanoCpus"
            ) != int(expected["cpu"] * 1e9):
                return "candidate_resource_limits_drift", low_since
        if state.get("OOMKilled") or candidate["RestartCount"] > 0:
            return "candidate_oom_or_restart", low_since
        service = candidate["Config"]["Labels"]["com.docker.compose.service"]
        oneoff = (
            candidate["Config"]["Labels"].get("com.docker.compose.oneoff") == "True"
        )
        planned_stop_clean = (
            lifecycle_status == "planned_stopped"
            and state["Status"] == "exited"
            and state.get("ExitCode") == 0
            and not state.get("OOMKilled")
        )
        if (
            service != "runner"
            and not oneoff
            and state["Status"] in {"dead", "exited"}
            and not planned_stop_clean
        ):
            return "candidate_service_exited", low_since
        if (
            state.get("Health", {}).get("Status") == "unhealthy"
            and not planned_stop_clean
        ):
            return "candidate_unhealthy", low_since
    if disk_free < 15 * GIB:
        return "project_disk_below_floor", low_since
    low_since = (
        (now if low_since is None else low_since) if available < 1.5 * GIB else None
    )
    if low_since is not None and now - low_since >= 30:
        return "memory_below_floor_30_seconds", low_since
    return None, low_since


def host_sample(release):
    return {
        "memory_available": memory_available(),
        "cpus": cpu_capacity(),
        "disk_free": shutil.disk_usage(release).free,
        "loadavg": list(os.getloadavg()),
        "pressure": {
            name: Path("/proc/pressure", name).read_text()
            for name in ("cpu", "io", "memory")
            if Path("/proc/pressure", name).is_file()
        },
    }


def cgroup_sample(items, registry):
    result = []
    for container in candidate_containers(items, registry):
        row = {
            "id": container["Id"],
            "restarts": container["RestartCount"],
            "oom_killed": container["State"].get("OOMKilled", False),
        }
        # OCI systemd cgroup v2; absence remains explicit rather than inventing peaks.
        directory = (
            Path("/sys/fs/cgroup/system.slice") / f"docker-{container['Id']}.scope"
        )
        for name in (
            "memory.current",
            "memory.peak",
            "memory.events",
            "cpu.stat",
            "io.stat",
        ):
            path = directory / name
            row[name] = path.read_text() if path.is_file() else None
        result.append(row)
    return result


def ensure_stopped(items, registry, registered_jobs):
    if any(
        c["State"]["Status"] == "running" for c in candidate_containers(items, registry)
    ):
        raise RuntimeError("owned_shutdown_container_readback_failed")
    until = time.monotonic() + 5
    while any(tagged_processes(j["token"]) for j in registered_jobs):
        if time.monotonic() >= until:
            raise RuntimeError("owned_shutdown_process_readback_failed")
        time.sleep(0.1)
