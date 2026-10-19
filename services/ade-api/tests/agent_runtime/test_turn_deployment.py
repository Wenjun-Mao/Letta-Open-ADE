"""Deployment helper coverage, not native-memory execution qualification."""

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.turn_deployment import (
    reviewer_max_model_requests,
)


def test_retained_reviewer_budget_helper_stays_with_its_owner():
    assert (
        reviewer_max_model_requests(
            {"fingerprint_payload": {"context_settings": {"reviewer_repair_count": 0}}}
        )
        == 1
    )
    assert (
        reviewer_max_model_requests({"fingerprint_payload": {"context_settings": {}}})
        == 2
    )
    with pytest.raises(RuntimeValidationError, match="repair budget"):
        reviewer_max_model_requests(
            {
                "fingerprint_payload": {
                    "context_settings": {"reviewer_repair_count": True}
                }
            }
        )
