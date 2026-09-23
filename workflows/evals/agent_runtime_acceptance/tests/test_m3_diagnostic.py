from pathlib import Path

from agent_runtime_eval_contracts import load_cases, study_cases_path

from workflows.evals.agent_runtime_acceptance.run import parse_args


FIXTURE = Path(__file__).resolve().parents[1] / "m3_profile_memory_diagnostic.json"


def test_m3_diagnostic_is_valid_and_does_not_change_canonical_matrix() -> None:
    cases = load_cases(FIXTURE)
    canonical_keys = {case.key for case in load_cases(study_cases_path())}
    assert len(cases) == 1
    assert cases[0].key not in canonical_keys
    assert len(cases[0].turns) == 8
    assert len({turn.conversation_key for turn in cases[0].turns}) == 5
    assert parse_args(["--diagnostic-fixture", str(FIXTURE)]).diagnostic_fixture == str(
        FIXTURE
    )
