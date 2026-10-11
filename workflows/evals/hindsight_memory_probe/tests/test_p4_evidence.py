"""Release-scoped path, reference and legacy-rejection contracts."""

import pytest

from workflows.evals.hindsight_memory_probe import finalization, p4_evidence


def test_attempts_use_distinct_release_namespaces_and_hash_bound_references(tmp_path):
    supervisor = tmp_path / "receipts" / "supervisor"
    supervisor.mkdir(parents=True)
    first, second = "a" * 40, "b" * 40
    first_path = p4_evidence.path_for(supervisor, first, "selection")
    second_path = p4_evidence.path_for(supervisor, second, "selection")
    assert first_path != second_path
    assert p4_evidence.reference(supervisor, first, "selection") == {
        "path": f"../p4/{first}/restart-selection.json", "release_sha": first}
    assert p4_evidence.resolve_reference(
        supervisor, p4_evidence.reference(supervisor, first, "selection"), first, "selection"
    ) == first_path
    with pytest.raises(RuntimeError, match="reference_invalid"):
        p4_evidence.resolve_reference(
            supervisor, p4_evidence.reference(supervisor, first, "selection"), second, "selection")


def test_old_global_proof_is_not_adopted_as_new_release_evidence(tmp_path):
    receipts = tmp_path / "receipts"
    supervisor = receipts / "supervisor"
    supervisor.mkdir(parents=True)
    (receipts / "restart-selection.json").write_text('{"schema":1}')
    (receipts / "restart-readback.completed.json").write_text('{"status":"completed"}')
    release_sha = "c" * 40
    result = finalization.restart_reference(
        supervisor, {"registry_sha256": "d" * 64},
        {"release": f"/release/{release_sha}", "sha256": "e" * 64})
    assert result == {"status": "absent"}
    selection = finalization.restart_selection_reference(
        supervisor, {"registry_sha256": "d" * 64},
        {"release": f"/release/{release_sha}", "sha256": "e" * 64})
    assert selection == {"status": "absent"}


def test_release_namespace_symlink_is_rejected(tmp_path):
    supervisor = tmp_path / "receipts" / "supervisor"
    supervisor.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    p4_root = supervisor.parent / "p4"
    p4_root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(RuntimeError, match="path_invalid"):
        p4_evidence.resolve_reference(
            supervisor, p4_evidence.reference(supervisor, "f" * 40, "selection"),
            "f" * 40, "selection")
