"""Guard-owned, ordered P4 drain, candidate dump and final stop."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path

from . import candidate_database, epochs, host_guard as host, lifecycle, p4_evidence, quiescence
from .finalization_process import run_monitored as supervise_process
from .receipts import ReceiptStore
from .campaign_clock import DEADLINE, WORK_CUTOFF
from .supervisor import jobs, record

SERVICES = ("runner", "hindsight", "model-router", "db")
FINALIZATION_FIXED_RESERVE = 600
FAILURE_CODES = {
    "finalization_process_identity_changed",
    "finalization_process_result_missing",
    "finalization_process_result_invalid",
    "finalization_process_descendant_active",
    "finalization_process_deadline_elapsed",
    "finalization_process_identity_missing",
}


def admission_path(directory: Path, epoch: dict) -> Path:
    return directory / f"epoch-{epoch['index']:04d}.finalize-admission.json"


def admit(directory: Path, drain_timeout: int = 600, dump_timeout: int = 120) -> dict:
    from .supervisor import load_registry

    registry = load_registry(directory)
    epoch = epochs.active(directory, registry)
    now = time.time()
    if not 1 <= drain_timeout <= 900 or not 1 <= dump_timeout <= 300:
        raise RuntimeError("finalization_timeout_invalid")
    if now >= WORK_CUTOFF or now + drain_timeout + dump_timeout + FINALIZATION_FIXED_RESERVE > WORK_CUTOFF:
        raise RuntimeError("finalization_reserve_unavailable")
    store = ReceiptStore(directory)
    path = admission_path(directory, epoch)
    with quiescence.bounded_lease(directory, "jobs.lock", 20):
        with quiescence.bounded_lease(directory, "admission.lock", 20):
            quiescence.require_open(directory, registry, epoch)
            if path.exists():
                raise RuntimeError("finalization_already_admitted")
            active_jobs = [job for job in jobs(directory) if job.get("epoch_sha256") == epoch["sha256"]]
            items = host.containers()
            candidates = host.candidate_containers(items, epochs.effective_registry(directory, registry))
            sample = host.host_sample(epoch["release"])
            view = lifecycle.classify(directory, epoch, candidates, now)
            reason, _ = host.guard_reason(
                epochs.effective_registry(directory, registry), items,
                sample["memory_available"], sample["disk_free"], None, now,
                epoch["allocations"], view,
            )
            if reason or sample["memory_available"] < 1.5 * host.GIB:
                raise RuntimeError("finalization_admission_safety_check_failed")
            running = {item["Config"]["Labels"]["com.docker.compose.service"] for item in candidates
                       if item["State"]["Status"] == "running"}
            if not {"db", "hindsight", "model-router"}.issubset(running):
                raise RuntimeError("finalization_candidate_stack_not_running")
            selection_ref = restart_selection_reference(directory, registry, epoch)
            restart_ref = restart_reference(directory, registry, epoch)
            if restart_ref["status"] == "completed" and selection_ref["status"] != "frozen":
                raise RuntimeError("restart_selection_missing_for_completed_readback")
            value = {
                "schema": 1,
                "registry_sha256": registry["registry_sha256"],
                "epoch_sha256": epoch["sha256"],
                "release_sha": Path(epoch["release"]).name,
                "release_path": str(epoch["release"]),
                "token": uuid.uuid4().hex,
                "admitted_at": now,
                "work_cutoff": WORK_CUTOFF,
                "hard_deadline": DEADLINE,
                "drain_timeout": drain_timeout,
                "dump_timeout": dump_timeout,
                "deadline": min(WORK_CUTOFF, now + drain_timeout + dump_timeout + FINALIZATION_FIXED_RESERVE),
                "jobs": [
                    {key: job.get(key) for key in (
                        "token", "kind", "operation", "service", "identity", "deadline"
                    )}
                    for job in active_jobs
                ],
                "containers": [identity_projection(item) for item in candidates],
                "restart_selection": selection_ref,
                "restart_readback": restart_ref,
            }
            store.write(path.name, value)
    return value


def identity_projection(container: dict) -> dict:
    labels = container.get("Config", {}).get("Labels") or {}
    return {
        "id": container["Id"], "image_id": container["Image"],
        "started_at": container["State"]["StartedAt"], "status": container["State"]["Status"],
        "service": labels.get("com.docker.compose.service"),
        "project": labels.get("com.docker.compose.project"),
        "working_dir": labels.get("com.docker.compose.project.working_dir"),
        "config_files": labels.get("com.docker.compose.project.config_files"),
        "oneoff": labels.get("com.docker.compose.oneoff") == "True",
    }


def restart_reference(directory: Path, registry: dict, epoch: dict) -> dict:
    release_sha = Path(epoch["release"]).name
    refs = {artifact: p4_evidence.reference(directory, release_sha, artifact)
            for artifact in ("selection", "before", "after", "completed")}
    path = p4_evidence.resolve_reference(directory, refs["completed"], release_sha, "completed")
    if not path.is_file():
        return {"status": "absent"}
    try:
        proof = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise RuntimeError("restart_readback_proof_invalid") from exc
    if not isinstance(proof, dict):
        raise RuntimeError("restart_readback_proof_invalid")
    selection_path = p4_evidence.resolve_reference(directory, refs["selection"], release_sha, "selection")
    before_path = p4_evidence.resolve_reference(directory, refs["before"], release_sha, "before")
    after_path = p4_evidence.resolve_reference(directory, refs["after"], release_sha, "after")
    proof_path = path
    try:
        from .restart_selection import hash_json, read_selection

        selection = read_selection(selection_path)
        selection_sha256 = hash_json(selection)
        before = json.loads(before_path.read_text())
        after = json.loads(after_path.read_text())
        if not isinstance(before, dict) or not isinstance(after, dict):
            raise ValueError("restart_snapshot_invalid")
        before_sha256, after_sha256 = hash_json(before), hash_json(after)
    except (OSError, ValueError) as exc:
        raise RuntimeError("restart_readback_evidence_invalid") from exc
    before_identity = before.get("run_identity")
    after_identity = after.get("run_identity")
    if not isinstance(before_identity, dict) or not isinstance(after_identity, dict):
        raise RuntimeError("restart_readback_proof_invalid")
    if (proof.get("status") != "completed"
            or proof.get("claim") != "bounded_restart_persistence_readback"
            or proof.get("selection_sha256") != selection_sha256
            or proof.get("selection_file_sha256") != sha256_file(selection_path)
            or proof.get("before_file_sha256") != sha256_file(before_path)
            or proof.get("after_file_sha256") != sha256_file(after_path)
            or proof.get("before_sha256") != before_sha256
            or proof.get("after_sha256") != after_sha256
            or before.get("selection_sha256") != selection_sha256
            or after.get("selection_sha256") != selection_sha256
            or before_identity.get("release_sha") != selection.get("release_sha")
            or after_identity.get("release_sha") != selection.get("release_sha")
            or before_identity.get("registry_sha256") != selection.get("registry_sha256")
            or after_identity.get("registry_sha256") != selection.get("registry_sha256")
            or before_identity.get("epoch_sha256") != selection.get("before_epoch_sha256")
            or after_identity.get("epoch_sha256") != proof.get("after_epoch_sha256")
            or selection.get("release_sha") != Path(epoch["release"]).name
            or selection.get("registry_sha256") != registry["registry_sha256"]
            or proof.get("registry_sha256") != registry["registry_sha256"]
            or proof.get("release_sha") != Path(epoch["release"]).name
            or proof.get("before_epoch_sha256") != selection["before_epoch_sha256"]
            or proof.get("after_epoch_sha256") != epoch["sha256"]
            or proof.get("before_epoch_sha256") == proof.get("after_epoch_sha256")
            or not valid_sha256(proof.get("selection_sha256"))):
        raise RuntimeError("restart_readback_proof_invalid")
    return {
        "status": "completed", **refs["completed"],
        "sha256": sha256_file(proof_path), "selection_sha256": selection_sha256,
        "selection_file_sha256": proof["selection_file_sha256"],
        "selection": {**refs["selection"], "sha256": proof["selection_file_sha256"]},
        "before": {**refs["before"], "sha256": proof["before_file_sha256"],
                   "content_sha256": proof["before_sha256"]},
        "after": {**refs["after"], "sha256": proof["after_file_sha256"],
                  "content_sha256": proof["after_sha256"]},
    }


def restart_selection_reference(directory: Path, registry: dict, epoch: dict) -> dict:
    release_sha = Path(epoch["release"]).name
    ref = p4_evidence.reference(directory, release_sha, "selection")
    path = p4_evidence.resolve_reference(directory, ref, release_sha, "selection")
    if not path.is_file():
        return {"status": "absent"}
    try:
        from .restart_selection import read_selection

        selection = read_selection(path)
    except (OSError, ValueError) as exc:
        raise RuntimeError("restart_selection_invalid") from exc
    if (selection.get("registry_sha256") != registry["registry_sha256"]
            or selection.get("release_sha") != Path(epoch["release"]).name
            or not valid_sha256(selection.get("before_epoch_sha256"))):
        raise RuntimeError("restart_selection_campaign_identity_mismatch")
    return {"status": "frozen", **ref, "sha256": sha256_file(path)}


def valid_sha256(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def planned_ids(directory: Path, epoch: dict) -> set[str]:
    admitted = json.loads(admission_path(directory, epoch).read_text())
    planned = set()
    prefix = f"finalize-{admitted['token']}-"
    for path in sorted(directory.glob(f"{prefix}*.intent.json")):
        candidate = json.loads(path.read_text())
        services = candidate.get("services", [])
        container_ids = candidate.get("container_ids", [])
        if not isinstance(services, list) or not isinstance(container_ids, list):
            raise RuntimeError("finalization_intent_identity_mismatch")
        allowed = {row["id"] for row in admitted["containers"] if row["service"] in services}
        if set(container_ids) - allowed:
            raise RuntimeError("finalization_intent_identity_mismatch")
        planned.update(container_ids)
    return planned


def runner_removal_proven(directory: Path, admitted: dict, row: dict) -> bool:
    if row.get("service") != "runner" or not row.get("oneoff"):
        return False
    for job in admitted["jobs"]:
        result_path = directory / f"job-{job['token']}.result.json"
        if (job.get("kind") == "work" and job.get("operation") == "run"
                and job.get("service") == "runner"
                and result_path.is_file() and json.loads(result_path.read_text()).get("exit_code") == 0
                and not host.tagged_processes(job["token"])):
            return True
    return False


def monitor(directory: Path, registry: dict, epoch: dict, admitted: dict, active_token: str | None = None) -> None:
    if (quiescence.stop_path(directory, epoch).exists()
            or (directory / f"epoch-{epoch['index']:04d}.pause-request.json").exists()):
        raise RuntimeError("finalization_preempted_by_emergency_stop")
    if time.time() >= min(WORK_CUTOFF, admitted["deadline"]):
        raise RuntimeError("finalization_deadline_elapsed")
    drain_complete = (directory / f"finalize-{admitted['token']}-drain.result.json").is_file()
    admitted_job_tokens = {job["token"] for job in admitted["jobs"]}
    for job in jobs(directory):
        alive = bool(host.tagged_processes(job["token"]))
        if not alive or job["token"] == active_token:
            continue
        if job["token"] not in admitted_job_tokens or drain_complete or time.time() >= job["deadline"]:
            raise RuntimeError("finalization_registered_process_unexpected")
    items = host.containers()
    candidates = host.candidate_containers(items, epochs.effective_registry(directory, registry))
    expected = {row["id"]: row for row in admitted["containers"]}
    planned = planned_ids(directory, epoch)
    seen = set()
    for item in candidates:
        row = expected.get(item["Id"])
        seen.add(item["Id"])
        if not row:
            raise RuntimeError("finalization_container_identity_changed")
        projection = identity_projection(item)
        if item["Id"] in planned and item["State"]["Status"] == "exited":
            if item["State"].get("ExitCode") != 0 or item["State"].get("OOMKilled"):
                raise RuntimeError("finalization_planned_exit_not_clean")
            projection["status"] = row["status"]
        elif item["State"]["Status"] != row["status"]:
            raise RuntimeError("finalization_unplanned_container_exit")
        if projection != row:
            raise RuntimeError("finalization_container_identity_changed")
    missing = set(expected) - seen
    if (seen - set(expected)) or any(
        not runner_removal_proven(directory, admitted, expected[identifier]) for identifier in missing
    ):
        raise RuntimeError("finalization_container_identity_missing")
    sample = host.host_sample(epoch["release"])
    safety_files = sorted(directory.glob(f"finalize-{admitted['token']}-safety-*.json"))
    low_since = json.loads(safety_files[-1].read_text()).get("low_memory_since") if safety_files else None
    reason, next_low_since = host.guard_reason(
        epochs.effective_registry(directory, registry), items,
        sample["memory_available"], sample["disk_free"], low_since, time.time(),
        epoch["allocations"], {"containers": {identity: "planned_stopped" for identity in planned}, "reason": None},
    )
    if reason:
        raise RuntimeError("finalization_safety_" + reason)
    ReceiptStore(directory).write(
        f"finalize-{admitted['token']}-safety-{time.time_ns()}.json",
        {"sampled_at": time.time(), "low_memory_since": next_low_since,
         "memory_available": sample["memory_available"], "disk_free": sample["disk_free"]},
    )


def record_stage(store: ReceiptStore, token: str, name: str, suffix: str, value: dict) -> Path:
    path = f"finalize-{token}-{name}.{suffix}.json"
    result = store.directory / path
    if result.exists():
        prior = json.loads(result.read_text())
        for key in ("token", "service", "services", "container_ids"):
            if key in value and prior.get(key) != value[key]:
                raise RuntimeError("finalization_stage_receipt_conflict")
        return result
    store.write(path, value)
    return result


def wait_until(directory: Path, registry: dict, epoch: dict, admitted: dict, timeout: int, predicate, failure: str, absolute_deadline: float | None = None) -> None:
    deadline = min(time.time() + timeout, admitted["deadline"], WORK_CUTOFF)
    if absolute_deadline is not None:
        deadline = min(deadline, absolute_deadline)
    while True:
        monitor(directory, registry, epoch, admitted)
        if predicate():
            return
        if time.time() >= deadline:
            raise RuntimeError(failure)
        time.sleep(min(5, max(0.05, deadline - time.time())))


def run_monitored(directory: Path, registry: dict, epoch: dict, admitted: dict,
                  command: list[str], timeout: int, *, stdout, stderr,
                  stdin=subprocess.DEVNULL) -> int:
    return supervise_process(directory, registry, epoch, admitted, command, timeout,
                             monitor_callback=monitor, stdout=stdout, stderr=stderr,
                             stdin=stdin)


def failure_code(error: Exception) -> str:
    if (type(error) is RuntimeError and len(error.args) == 1
            and isinstance(error.args[0], str) and error.args[0] in FAILURE_CODES):
        return error.args[0]
    return "finalization_stage_failed"


def stop_service(directory: Path, registry: dict, admitted: dict, epoch: dict, store: ReceiptStore, service: str) -> None:
    result_path = store.directory / f"finalize-{admitted['token']}-{service}-stop.result.json"
    if result_path.exists():
        result = json.loads(result_path.read_text())
        admitted_by_id = {row["id"]: row for row in admitted["containers"]}
        for identifier in result["container_ids"]:
            current = subprocess.run(["docker", "inspect", identifier], capture_output=True, timeout=5, check=True)
            inspected = json.loads(current.stdout)[0]
            original = admitted_by_id.get(identifier)
            if (original is None or identity_projection(inspected) | {"status": original["status"]} != original
                    or inspected["State"]["Status"] != "exited"
                    or inspected["State"].get("ExitCode") != 0):
                raise RuntimeError("finalization_stopped_identity_resurrected")
        return
    current_by_id = {item["Id"]: item for item in host.candidate_containers(
        host.containers(), epochs.effective_registry(directory, registry)
    )}
    exact = []
    for row in admitted["containers"]:
        if row["service"] != service or row["status"] != "running":
            continue
        current = current_by_id.get(row["id"])
        if service == "runner" and runner_removal_proven(directory, admitted, row):
            continue
        if current is None or current["State"]["Status"] != "running":
            raise RuntimeError("finalization_service_identity_not_running")
        exact.append(row)
    intent = {"token": admitted["token"], "service": service, "services": [service],
              "container_ids": [row["id"] for row in exact], "started_at": time.time()}
    record_stage(store, admitted["token"], f"{service}-stop", "intent", intent)
    for row in exact:
        current = subprocess.run(["docker", "inspect", row["id"]], capture_output=True, timeout=5, check=True)
        try:
            fresh = json.loads(current.stdout)[0]
        except (ValueError, IndexError) as exc:
            raise RuntimeError("finalization_stop_readback_invalid") from exc
        if (identity_projection(fresh) | {"status": row["status"]} != row
                or fresh["State"]["Status"] != "running"):
            raise RuntimeError("finalization_stop_identity_mismatch")
        stop_status = run_monitored(
            directory, registry, epoch, admitted,
            ["docker", "stop", "--time", "35" if service == "hindsight" else "10", row["id"]],
            45 if service == "hindsight" else 20,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if stop_status != 0:
            raise RuntimeError("finalization_service_stop_failed")
    wait_until(directory, registry, epoch, admitted, 20, lambda: all(
        next((item["State"]["Status"] == "exited" for item in host.containers() if item["Id"] == row["id"]), False)
        for row in exact), "planned_service_stop_timeout")
    for row in exact:
        inspected = json.loads(subprocess.run(["docker", "inspect", row["id"]], capture_output=True, timeout=5, check=True).stdout)[0]
        if (identity_projection(inspected) | {"status": row["status"]} != row
                or inspected["State"]["Status"] != "exited"
                or inspected["State"].get("ExitCode") != 0):
            raise RuntimeError("planned_service_stop_not_clean")
    record_stage(store, admitted["token"], f"{service}-stop", "result",
                 {"container_ids": intent["container_ids"], "stopped_at": time.time(), "readback": "stopped"})


def execute(directory: Path, registry: dict, epoch: dict, store: ReceiptStore) -> None:
    admitted = json.loads(admission_path(directory, epoch).read_text())
    if admitted["registry_sha256"] != registry["registry_sha256"] or admitted["epoch_sha256"] != epoch["sha256"]:
        raise RuntimeError("finalization_admission_identity_mismatch")
    try:
        drain_result = store.directory / f"finalize-{admitted['token']}-drain.result.json"
        if not drain_result.exists():
            record_stage(store, admitted["token"], "drain", "intent", {"token": admitted["token"], "started_at": time.time(), "services": list(SERVICES)})
            drain_deadline = admitted["admitted_at"] + admitted["drain_timeout"]
            wait_until(directory, registry, epoch, admitted, admitted["drain_timeout"], lambda: all(
                not host.tagged_processes(job["token"]) and (directory / f"job-{job['token']}.result.json").exists()
                for job in admitted["jobs"]), "registered_jobs_did_not_drain", drain_deadline)
            wait_until(directory, registry, epoch, admitted, admitted["drain_timeout"], lambda: candidate_database.operation_count(directory, registry, admitted, run_monitored) == 0,
                       "hindsight_async_operations_did_not_drain", drain_deadline)
            operation_statuses = candidate_database.operation_status_counts(
                directory, registry, admitted, run_monitored
            )
            record_stage(store, admitted["token"], "drain", "result", {
                "token": admitted["token"], "completed_at": time.time(),
                "registered_jobs": len(admitted["jobs"]),
                "async_operation_status_counts": operation_statuses,
            })
        stop_service(directory, registry, admitted, epoch, store, "runner")
        stop_service(directory, registry, admitted, epoch, store, "hindsight")
        record_stage(store, admitted["token"], "canonical-snapshot", "intent",
                     {"token": admitted["token"], "started_at": time.time()})
        snapshot = candidate_database.snapshot_database(directory, registry, admitted, store, run_monitored)
        record_stage(store, admitted["token"], "canonical-snapshot", "result",
                     {"token": admitted["token"], "result": snapshot, "completed_at": time.time()})
        record_stage(store, admitted["token"], "dump", "intent",
                     {"token": admitted["token"], "started_at": time.time()})
        dump = candidate_database.dump_database(directory, registry, admitted, snapshot, store, run_monitored)
        record_stage(store, admitted["token"], "dump", "result",
                     {"token": admitted["token"], "result": dump, "completed_at": time.time()})
        record(store, "finalization_dump_preserved", token=admitted["token"])
        stop_service(directory, registry, admitted, epoch, store, "model-router")
        stop_service(directory, registry, admitted, epoch, store, "db")
    except Exception as exc:
        # Preserve error shape as a fixed code; the supervisor performs bounded full cleanup.
        store.write(f"finalize-{admitted['token']}-failure.json", {
            "reason": "finalization_stage_failed", "error_code": failure_code(exc),
            "stage": current_stage(directory, admitted), "time": time.time(),
        })
        raise


def complete_stop(directory: Path, registry: dict, epoch: dict, store: ReceiptStore) -> None:
    admitted = json.loads(admission_path(directory, epoch).read_text())
    stopped_path = epochs.stopped_path(directory, epoch)
    if not stopped_path.is_file():
        raise RuntimeError("finalization_stop_proof_missing")
    stopped = json.loads(stopped_path.read_text())
    if stopped.get("epoch_sha256") != epoch["sha256"]:
        raise RuntimeError("finalization_stop_proof_conflict")
    items = host.containers()
    host.ensure_stopped(items, epochs.effective_registry(directory, registry), jobs(directory))
    ids = {container["Id"] for container in host.candidate_containers(items, epochs.effective_registry(directory, registry))}
    admitted_ids = {row["id"] for row in admitted["containers"]}
    removed = {identifier for identifier in admitted_ids - ids
               if runner_removal_proven(directory, admitted, next(row for row in admitted["containers"] if row["id"] == identifier))}
    if ids | removed != admitted_ids:
        raise RuntimeError("finalization_stopped_identity_set_changed")
    baseline = {item["Id"]: host.baseline_projection(item) for item in items}
    for original in registry["baseline"]:
        if baseline.get(original["id"]) != original:
            raise RuntimeError("finalization_baseline_changed")
    sample = host.host_sample(registry["release"])
    if sample["memory_available"] < 1.5 * host.GIB or sample["disk_free"] < 15 * host.GIB:
        raise RuntimeError("finalization_post_stop_headroom_low")
    dump_result = store.directory / f"finalize-{admitted['token']}-dump-result.json"
    if not dump_result.is_file():
        raise RuntimeError("finalization_dump_result_missing")
    missing_restart = admitted["restart_readback"]["status"] != "completed"
    store.write(f"epoch-{epoch['index']:04d}.finalized.json", {
        "token": admitted["token"], "registry_sha256": registry["registry_sha256"],
        "epoch_sha256": epoch["sha256"], "dump_result": dump_result.name,
        "dump_result_sha256": sha256_file(dump_result), "restart_readback": admitted["restart_readback"],
        "p4_complete": not missing_restart, "restart_readback_absent": missing_restart,
        "baseline_unchanged": True, "all_candidate_services_stopped": True,
        "headroom_after_stop": {"memory_available": sample["memory_available"], "disk_free": sample["disk_free"]},
        "stopped_at": time.time(),
    })


def current_stage(directory: Path, admitted: dict) -> str:
    intents = sorted(directory.glob(f"finalize-{admitted['token']}-*.intent.json"))
    return intents[-1].name.split("-")[-1].split(".")[0] if intents else "drain"
