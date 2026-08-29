from __future__ import annotations

from collections.abc import Iterable


def is_eligible_primary_matrix(
    rounds: Iterable[object],
    *,
    canonical_case_keys: tuple[str, ...],
    required_rounds: int,
) -> bool:
    """Fail closed: only exact complete live primary matrices can qualify."""
    values = tuple(rounds)
    if required_rounds != 3 or len(values) != required_rounds:
        return False
    expected_indices = tuple(range(1, required_rounds + 1))
    return all(
        int(getattr(round_result, "index", 0)) == index
        and getattr(round_result, "kind", None) == "primary"
        and getattr(round_result, "execution_mode", None) == "live-api"
        and bool(getattr(round_result, "complete_matrix", False))
        and bool(getattr(round_result, "passed", False))
        and tuple(getattr(round_result, "case_keys", ())) == canonical_case_keys
        for index, round_result in zip(expected_indices, values, strict=True)
    )
