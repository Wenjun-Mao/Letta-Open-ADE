"""Expire a real finalizer behind an owned row lock, without changing product data."""

import json
import re
import subprocess
import time
from uuid import UUID, uuid4

from .operations import create_record
from .paired_backup import owned_service, sql


def identifiers(details, keys):
    if set(details) != set(keys):
        raise ValueError("invalid_finalizer_control_fields")
    return {key: str(UUID(details[key])) for key in keys}


class StaleFinalizer:
    def __init__(self, controls, workspace):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,120}", workspace):
            raise ValueError("invalid_owned_workspace_key")
        self.controls, self.workspace = controls, workspace
        self.database = owned_service(controls.docker, controls.lease, "ade-db")
        self.process, self.log, self.subject, self.conversation = None, None, None, None
        self.paused = False
        self.application = "ade-stage1-finalizer-" + uuid4().hex

    def read(self, query):
        current = owned_service(self.controls.docker, self.controls.lease, "ade-db")
        if any(current[key] != self.database[key] for key in ("id", "image", "mounts")):
            raise ValueError("owned_finalizer_database_changed")
        return sql(current["id"], "ade_integration_admin", "ade_integration", query)

    def until(self, read, predicate, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.controls.fence()
            value = read()
            if predicate(value):
                return value
            time.sleep(0.5)
        raise TimeoutError("owned_finalizer_checkpoint_missing")

    def lock(self, details):
        ids = identifiers(details, ("subject_id", "conversation_id"))
        if self.process is not None:
            raise ValueError("owned_subject_lock_already_started")
        self.subject, self.conversation = ids["subject_id"], ids["conversation_id"]
        exists = self.read(
            "SELECT count(*) FROM ade.conversations c JOIN ade.workspaces w "
            "ON w.id=c.workspace_id WHERE "
            f"c.id='{self.conversation}' AND c.memory_subject_id='{self.subject}' "
            f"AND w.workspace_key='{self.workspace}' AND w.memory_backend='hindsight';"
        )
        if exists != "1":
            raise ValueError("subject_lock_outside_owned_workspace")
        self.log = (self.controls.output / "subject-lock.log").open("x")
        (self.controls.output / "subject-lock.log").chmod(0o600)
        self.process = subprocess.Popen(
            [
                "docker",
                "exec",
                "-i",
                self.database["id"],
                "psql",
                "-XqAt",
                "-v",
                "ON_ERROR_STOP=1",
                "-U",
                "ade_integration_admin",
                "-d",
                "ade_integration",
            ],
            stdin=subprocess.PIPE,
            stdout=self.log,
            stderr=self.log,
            text=True,
        )
        self.process.stdin.write(
            "BEGIN; SET LOCAL statement_timeout='30s'; "
            "SET LOCAL idle_in_transaction_session_timeout='180s'; "
            f"SET LOCAL application_name='{self.application}'; "
            f"SELECT id FROM ade.memory_subjects WHERE id='{self.subject}' FOR UPDATE;\n"
        )
        self.process.stdin.flush()
        self.pid = int(
            self.until(
                lambda: self.read(
                    "SELECT pid FROM pg_stat_activity WHERE "
                    f"application_name='{self.application}' "
                    "AND state='idle in transaction';"
                ),
                bool,
                30,
            )
        )
        return {**ids, "lock_backend_pid": self.pid, "data_mutated": False}

    def expire(self, details):
        run = identifiers(details, ("run_id",))["run_id"]
        if self.process is None or self.process.poll() is not None:
            raise ValueError("owned_subject_lock_not_active")
        row = self.read(
            "SELECT count(*) FROM ade.runs WHERE "
            f"id='{run}' AND conversation_id='{self.conversation}' "
            "AND status='running' AND attempt_count=1;"
        )
        if row != "1":
            raise ValueError("finalizer_run_not_owned_first_attempt")
        blocked = self.until(
            lambda: self.read(
                "SELECT coalesce(json_agg(json_build_object('pid',pid,'query',query,"
                "'wait_event',wait_event)), '[]') FROM pg_stat_activity WHERE "
                f"{self.pid}=ANY(pg_blocking_pids(pid)) "
                "AND usename='ade_integration_app' AND query ILIKE '%memory_subjects%' "
                "AND query ILIKE '%FOR UPDATE%';"
            ),
            lambda value: bool(json.loads(value)),
            90,
        )
        create_record(
            self.controls.output / "blocked-finalizer.json", json.loads(blocked)
        )
        worker = self.controls.current("ade-worker")
        self.controls.fence()
        self.controls.docker._run(["pause", worker["id"]])
        self.paused = True
        expired = self.until(
            lambda: self.read(
                "SELECT json_build_object('expired',expires_at<=clock_timestamp(),"
                "'expires_at',expires_at,'observed_at',clock_timestamp(),'run_id',run_id) "
                f"FROM ade.conversation_leases WHERE run_id='{run}' AND released_at IS NULL;"
            ),
            lambda value: bool(value) and json.loads(value)["expired"],
            90,
        )
        self.unlock()
        result = {
            "blocked_finalizer": json.loads(blocked),
            "lease": json.loads(expired),
            "run_id": run,
            "worker_id": worker["id"],
        }
        create_record(self.controls.output / "expired-finalizer.json", result)
        self.resume()
        return result

    def unlock(self):
        if self.process is not None:
            try:
                if self.process.poll() is None:
                    self.process.stdin.write("ROLLBACK;\n\\q\n")
                    self.process.stdin.flush()
                    try:
                        self.process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        self.process.terminate()
                        self.process.wait(timeout=5)
                        raise
            finally:
                self.log.close()

    def verify(self, details):
        run = identifiers(details, ("run_id",))["run_id"]
        if (
            self.read(
                "SELECT count(*) FROM ade.runs WHERE "
                f"id='{run}' AND conversation_id='{self.conversation}' "
                "AND status='succeeded' AND attempt_count=2;"
            )
            != "1"
        ):
            raise ValueError("owned_finalizer_recovery_not_complete")
        attempts = json.loads(
            self.read(
                "SELECT json_agg(json_build_object('number',attempt_number,'status',status,"
                "'error_code',provider_outcome->>'error_code') ORDER BY attempt_number) "
                f"FROM ade.run_attempts WHERE run_id='{run}';"
            )
        )
        if [(row["number"], row["status"], row["error_code"]) for row in attempts] != [
            (1, "failed", "worker_lease_expired"),
            (2, "succeeded", None),
        ]:
            raise ValueError("owned_finalizer_attempt_outcome_mismatch")
        if (
            self.read(
                "SELECT count(*) FROM ade.messages WHERE "
                f"run_id='{run}' AND role='assistant';"
            )
            != "1"
        ):
            raise ValueError("owned_finalizer_committed_duplicate_reply")
        result = {"run_id": run, "attempts": attempts, "committed_assistants": 1}
        create_record(self.controls.output / "finalizer-recovery.json", result)
        return result

    def resume(self):
        if self.paused:
            self.controls.fence()
            worker = self.controls.current("ade-worker")
            self.controls.docker._run(["unpause", worker["id"]])
            self.paused = False

    def close(self):
        try:
            self.unlock()
        finally:
            self.resume()
