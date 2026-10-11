"""End-to-end synthetic host-path exercise under Python -S."""

import hashlib
import json
import os
import shlex
import subprocess
import sys
import textwrap
import time

from workflows.evals.hindsight_memory_probe import restore_database
from workflows.evals.hindsight_memory_probe.campaign_clock import DEADLINE
from workflows.evals.hindsight_memory_probe.tests.restore_test_support import _rows, _selection, _snapshot
from workflows.evals.hindsight_memory_probe.validate import ROOT

REPOSITORY = ROOT.parents[2]

def test_full_restore_host_path_runs_under_python_no_site_with_real_docker_text(tmp_path):
    state = tmp_path / "private" / "receipts" / "supervisor"
    state.mkdir(parents=True, mode=0o700)
    restore_token = "1" * 32
    registry_sha = "b" * 64
    epoch_sha = "d" * 64
    release_sha = "a" * 40
    release = tmp_path / "release" / release_sha
    release.mkdir(parents=True)
    (release / "workflows").symlink_to(REPOSITORY / "workflows", target_is_directory=True)
    source_image = f"ade-hindsight-probe-db:{release_sha}"
    image_id = "sha256:" + "e" * 64
    workdir = str(release / "workflows/evals/hindsight_memory_probe")
    main_container = {
        "Id": "main-db", "Image": image_id,
        "State": {"StartedAt": "2026-10-11T06:00:00Z", "Status": "exited", "OOMKilled": False},
        "RestartCount": 0,
        "Config": {"Image": source_image, "Env": ["POSTGRES_DB=hindsight_probe"], "Labels": {
            "com.docker.compose.project": "ade-hindsight-probe", "com.docker.compose.service": "db",
            "com.docker.compose.project.working_dir": workdir,
            "com.docker.compose.project.config_files": workdir + "/compose.yaml",
            "com.docker.compose.oneoff": "False"}},
        "HostConfig": {"Memory": 1073741824, "NanoCpus": 250000000, "NetworkMode": "default"},
        "NetworkSettings": {"Ports": {}},
        "Mounts": [{"Name": "ade-hindsight-probe_db-data", "Destination": "/var/lib/postgresql/data", "RW": True}],
    }
    admission = {"release_path": str(release), "containers": [{
        "id": "main-db", "image_id": image_id, "started_at": "2026-10-11T06:00:00Z",
        "status": "running", "service": "db", "project": "ade-hindsight-probe",
        "working_dir": workdir, "config_files": workdir + "/compose.yaml", "oneoff": False,
    }]}
    registry = {"registry_sha256": registry_sha, "release": "/immutable/initial-release", "baseline": []}
    (state / "registry.json").write_text(json.dumps(registry))
    (state / "epoch-0001.finalize-admission.json").write_text(json.dumps(admission))
    finalized_path = state / "epoch-0001.finalized.json"
    finalized_path.write_text("{}")

    selection = _selection()
    selection["release_sha"] = release_sha
    selection["registry_sha256"] = registry_sha
    selection["before_epoch_sha256"] = "c" * 64
    selection_path = state.parent / "restart-selection.json"
    selection_path.write_text(json.dumps(selection, sort_keys=True))
    rows = _rows(selection)
    source_root = state / "finalization" / "final-token"
    source_root.parent.mkdir()
    original_snapshot = _snapshot(source_root, rows)
    scope_evidence = {"status": "public_readback_bound", "selection_sha256": "1" * 64,
        "selection_file_sha256": "2" * 64, "restart_readback_sha256": "3" * 64,
        "before_file_sha256": "4" * 64, "before_snapshot_sha256": "5" * 64,
        "after_file_sha256": "6" * 64, "after_snapshot_sha256": "7" * 64}
    scope_path = source_root / "scope-eligibility.json"
    scope_path.write_text(json.dumps(scope_evidence, sort_keys=True, separators=(",", ":")) + "\n")
    scope_bytes = scope_path.read_bytes()
    original_snapshot["tables"]["scope_eligibility"] = {
        "file": scope_path.name, "sha256": hashlib.sha256(scope_bytes).hexdigest(),
        "bytes": len(scope_bytes)}
    snapshot_path = state / "finalize-final-token-canonical-snapshot.json"
    snapshot_path.write_text(json.dumps(original_snapshot, sort_keys=True))
    archive = state / "finalization" / "final-token" / "candidate.dump"
    archive.write_bytes(b"PGDMP\x00synthetic-archive")
    compose = restore_database.write_compose(state / "restore" / restore_token, restore_token,
                                             source_image, image_id)
    now = time.time()
    operation = {
        "schema": 1, "status": "admitted", "token": restore_token,
        "registry_sha256": registry_sha, "epoch_sha256": epoch_sha,
        "parent_finalization_token": "final-token", "parent_stopped_epoch_sha256": epoch_sha,
        "release_path": str(release), "admitted_at": now, "deadline": now + 900,
        "cleanup_deadline": now + 1020, "hard_deadline": DEADLINE,
        "restore_memory_bytes": 1073741824, "restore_cpu": 0.25,
        "finalization": {"containers": admission["containers"], "release_path": str(release)},
        "archive": {"path": str(archive), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                    "bytes": archive.stat().st_size, "dump_result_sha256": "f" * 64},
        "snapshot": {"path": str(snapshot_path), "sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
                     "root": str(source_root)},
        "selection": {"path": str(selection_path), "sha256": hashlib.sha256(selection_path.read_bytes()).hexdigest(),
                      "restart_proof_sha256": "a" * 64},
        "compose": compose, "restore_root": str(state / "restore" / restore_token),
        "state_directory": str(state),
    }
    operation_path = state / "restore-operation.json"
    operation_path.write_text(json.dumps(operation, sort_keys=True))
    (state / "restore-operation-seal.json").write_text(json.dumps({
        "schema": 1, "token": restore_token,
        "sha256": hashlib.sha256(operation_path.read_bytes()).hexdigest(),
    }))

    docker_state_path = tmp_path / "docker-state.json"
    docker_state_path.write_text(json.dumps({
        "containers": {"main-db": main_container}, "volumes": {}, "images": {source_image: image_id},
        "tables": rows,
    }))
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    fake_docker = tmp_path / "fake_docker.py"
    fake_docker.write_text(textwrap.dedent(r'''
        import json, os, re, sys
        from pathlib import Path
        state_path = Path(os.environ["FAKE_DOCKER_STATE"])
        state = json.loads(state_path.read_text())
        args = sys.argv[1:]
        with Path(str(state_path) + ".commands").open("a") as log: log.write(repr(args) + "\\n")
        def save(): state_path.write_text(json.dumps(state))
        def out(value): sys.stdout.write(value)
        def emit(value): out(json.dumps(value))
        if args[:2] == ["ps", "-aq"]:
            if "--filter" in args:
                volume = args[args.index("--filter") + 1].removeprefix("volume=")
                ids = [key for key, row in state["containers"].items()
                       if any(m.get("Name") == volume for m in row.get("Mounts", []))]
            else: ids = list(state["containers"])
            out("".join(identifier + "\n" for identifier in ids))
        elif args[:1] == ["inspect"]:
            emit([state["containers"][identifier] for identifier in args[1:]])
        elif args[:2] == ["image", "inspect"]:
            emit([{"Id": state["images"][args[2]]}])
        elif args[:3] == ["volume", "ls", "-q"]:
            out("".join(name + "\n" for name in state["volumes"]))
        elif args[:2] == ["volume", "inspect"]:
            emit([state["volumes"][args[2]]])
        elif args[:2] == ["compose", "--project-name"] and "up" in args:
            project, config = args[2], args[4]
            config_text = Path(config).read_text()
            token = re.search(r'ade\.hindsight\.restore\.token: "([0-9a-f]{32})"', config_text).group(1)
            volume = re.search(r"(?m)^    name: ([^\n]+)$", config_text).group(1)
            image = re.search(r"    image: (.+)", config_text).group(1)
            state["volumes"][volume] = {"Name": volume, "Driver": "local", "Scope": "local", "Options": None,
                "Mountpoint": "/docker/volumes/"+volume, "CreatedAt": "2026-10-11T06:01:00Z",
                "Labels": {"com.docker.compose.project": project, "com.docker.compose.volume": "data",
                           "ade.hindsight.restore.token": token}}
            state["containers"]["restore-db"] = {"Id": "restore-db", "Image": state["images"][image],
                "RestartCount": 0, "State": {"StartedAt": "2026-10-11T06:01:01Z", "Status": "running", "OOMKilled": False},
                "Config": {"Image": image, "Env": ["POSTGRES_DB=hindsight_probe", "POSTGRES_USER=hindsight_probe"],
                    "Labels": {"ade.hindsight.restore.token": token, "com.docker.compose.project": project,
                        "com.docker.compose.service": "db", "com.docker.compose.project.config_files": config,
                        "com.docker.compose.project.working_dir": str(Path(config).parent)}},
                "HostConfig": {"NetworkMode": "none", "Memory": 1073741824, "NanoCpus": 250000000},
                "NetworkSettings": {"Ports": {}}, "Mounts": [{"Name": volume, "Destination": "/var/lib/postgresql/data", "RW": True}]}
            save()
        elif args[:2] == ["exec", "-i"]:
            command = args[3:]
            if command[0] == "pg_restore":
                assert sys.stdin.buffer.read().startswith(b"PGDMP")
            elif command[0] == "psql":
                query = command[-1]
                if query == "SELECT current_database()": out("hindsight_probe\n")
                elif " AS t" in query:
                    table = re.search(r"FROM public\.([a-z_]+) AS t", query).group(1)
                    for row in state["tables"][table]: out(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
                else: out(json.dumps(state["tables"]["schema_extensions"][0], separators=(",", ":")))
        elif args[:1] == ["stop"]:
            state["containers"][args[-1]]["State"]["Status"] = "exited"; save()
            out(args[-1] + "\n")
        elif args[:1] == ["rm"]:
            del state["containers"][args[-1]]; save(); out(args[-1] + "\n")
        elif args[:2] == ["volume", "rm"]:
            del state["volumes"][args[-1]]; save(); out(args[-1] + "\n")
        else:
            raise SystemExit("unsupported synthetic docker command: " + repr(args))
    '''), encoding="utf-8")
    docker_wrapper = fakebin / "docker"
    docker_wrapper.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " -S "
                              + shlex.quote(str(fake_docker)) + " \"$@\"\n")
    docker_wrapper.chmod(0o700)

    runner = tmp_path / "host_path.py"
    runner.write_text(textwrap.dedent(r'''
        import hashlib, json, os, sys
        from pathlib import Path
        sys.path.insert(0, sys.argv[2])
        from workflows.evals.hindsight_memory_probe import epochs, host_guard, restore, restore_controller, restore_process
        from workflows.evals.hindsight_memory_probe.host_guard import GIB
        state = Path(sys.argv[1]); token = "1" * 32
        epoch = {"index": 1, "sha256": "d" * 64, "release": json.loads((state/"restore-operation.json").read_text())["release_path"], "allocations": {}}
        epochs.active = lambda *_: epoch
        restore._verify_host = lambda *_args, **_kwargs: []
        host_guard.host_sample = lambda _release: {"memory_available": 8 * GIB, "disk_free": 50 * GIB, "cpus": 2}
        def identity(pid): return {"pid": pid, "start_ticks": "synthetic", "uid": os.getuid(), "cmd_sha256": "a" * 64}
        def alive(value, *_args):
            try: os.kill(value["pid"], 0); return True
            except OSError: return False
        host_guard.proc_identity = identity
        host_guard.identity_matches = alive
        host_guard.tagged_processes = lambda _token, *_args: []
        restore_process.host.proc_identity = identity
        restore_process.host.identity_matches = alive
        restore_process.host.tagged_processes = lambda _token, *_args: []
        os.environ["ADE_PROBE_PROCESS_OWNER"] = "controller-token"
        identity = host_guard.proc_identity(os.getpid())
        restore.ReceiptStore(state).write("restore-"+token+"-controller-controller-token.json", {
            "token": token, "controller_token": "controller-token", "identity": identity})
        code = restore_controller.Controller(state, token, "controller-token").run_guarded()
        if code:
            print(sorted(path.name for path in state.glob("restore-"+token+"-*.json")), file=sys.stderr)
            for path in state.glob("restore-"+token+"-*.json"):
                print(path.name + ":" + path.read_text(), file=sys.stderr)
            for path in state.glob("job-*.result.json"):
                print(path.name + ":" + path.read_text(), file=sys.stderr)
        assert code == 0
        result = json.loads((state/("restore-"+token+"-result.json")).read_text())
        cleanup = json.loads((state/("restore-"+token+"-cleanup.result.json")).read_text())
        comparison = json.loads((state/("restore-"+token+"-compare.result.json")).read_text())
        assert result["claim"] == "logical_persisted_state_restore_only"
        assert cleanup["status"] == "completed"
        assert comparison["scope_evidence"]["status"] == "public_readback_bound"
        assert comparison["table_counts"]["observation_history"] == {"before": 1, "after": 1}
        assert "httpx" not in sys.modules and "ade_api" not in sys.modules
        print("restore_host_path_stdlib_ok")
    '''), encoding="utf-8")
    environment = {**os.environ, "PATH": str(fakebin) + os.pathsep + os.environ["PATH"],
                   "FAKE_DOCKER_STATE": str(docker_state_path)}
    result = subprocess.run([sys.executable, "-S", str(runner), str(state), str(REPOSITORY)],
                            cwd=REPOSITORY, env=environment, capture_output=True, text=True,
                            timeout=120)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "restore_host_path_stdlib_ok"
