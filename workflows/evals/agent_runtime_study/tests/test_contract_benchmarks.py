from __future__ import annotations

import asyncio

from workflows.evals.agent_runtime_study.contract_benchmarks import (
    run_contract_benchmarks,
)


def test_custom_loop_passes_all_mandatory_fake_model_contracts() -> None:
    result = asyncio.run(run_contract_benchmarks(("custom_loop",)))
    assert result["custom_loop"]["mandatory_pass"] is True
    assert result["custom_loop"]["failed"] == 0


def test_pydantic_ai_zero_retry_limitation_is_reproducible() -> None:
    result = asyncio.run(run_contract_benchmarks(("pydantic_ai",)))
    checks = {item["name"]: item for item in result["pydantic_ai"]["checks"]}
    assert checks["zero_retry_is_exact"]["pass"] is True
    assert checks["one_additional_retry_is_exact"]["pass"] is True
    assert checks["malformed_arguments_recover"]["pass"] is False
    assert result["pydantic_ai"]["mandatory_pass"] is False
