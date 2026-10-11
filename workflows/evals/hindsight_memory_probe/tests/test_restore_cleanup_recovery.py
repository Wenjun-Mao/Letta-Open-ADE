import pytest

from workflows.evals.hindsight_memory_probe import restore_cleanup_recovery, restore_process
from workflows.evals.hindsight_memory_probe.restore_retirement_archive import digest_file
from workflows.evals.hindsight_memory_probe.receipts import ReceiptStore


def test_cleanup_recovery_command_allowlist_is_bound_to_exact_container_and_volume():
    operation = {"token": "a" * 32, "compose": {"volume": "ade-hindsight-restore-aaaaaaaaaaaaaaaa_data"},
                 "_cleanup_recovery_container_id": "b" * 64}
    restore_process._validate_command(operation, ["docker", "stop", "--time", "20", "b" * 64])
    restore_process._validate_command(operation, ["docker", "volume", "rm", operation["compose"]["volume"]])
    with pytest.raises(RuntimeError, match="cleanup_recovery_command_not_allowed"):
        restore_process._validate_command(operation, ["docker", "stop", "--time", "20", "c" * 64])
    with pytest.raises(RuntimeError, match="cleanup_recovery_command_not_allowed"):
        restore_process._validate_command(operation, ["docker", "compose", "up", "-d"])
    with pytest.raises(RuntimeError, match="cleanup_recovery_command_not_allowed"):
        restore_process._validate_command(operation, ["docker", "exec", "-i", "b" * 64, "pg_restore"])


def test_failed_create_history_requires_sealed_byte_exact_files(tmp_path):
    token = "d" * 32
    tmp_path.chmod(0o700)
    root = tmp_path / "restore-cleanup-recovered" / token
    (root / "evidence").mkdir(parents=True)
    for directory in (root.parent, root, root / "evidence"):
        directory.chmod(0o700)
    evidence = root / "evidence" / "original-failure.json"
    evidence.write_bytes(b'{"original":true}\n')
    manifest = {"schema": 1, "kind": "failed_create_cleaned", "token": token,
                "operation_sha256": "e" * 64, "files": [{"path": "original-failure.json",
                "sha256": digest_file(evidence), "bytes": evidence.stat().st_size}], "created_at": 1}
    ReceiptStore(root).write("recovery.json", manifest)
    (root / "recovery.json").chmod(0o400)
    ReceiptStore(root).write("recovery-seal.json", {"schema": 1, "token": token,
        "sha256": digest_file(root / "recovery.json")})
    (root / "recovery-seal.json").chmod(0o400)

    restore_cleanup_recovery.validate_history(tmp_path)
    evidence.chmod(0o600)
    evidence.write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="history_hash_invalid"):
        restore_cleanup_recovery.validate_history(tmp_path)
