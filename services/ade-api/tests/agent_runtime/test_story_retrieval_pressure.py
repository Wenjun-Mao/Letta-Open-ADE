"""Synthetic PC-11 evidence-loss controls, not native retrieval/model quality."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
from types import SimpleNamespace

import pytest

from ade_api.features.agent_runtime.context import BuiltContext
from ade_api.features.agent_runtime.history_admission import admit_history
from ade_api.features.agent_runtime.history_native_rank import (
    HISTORY_EMBEDDING_ROUTE,
    rank_native_history,
)
from ade_api.features.agent_runtime.history_observations import history_observation
from ade_api.features.agent_runtime.history_ranking import document_text, query_text
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    natural_review_request,
)


QUERY = "Tell me again about the cat you met after work."
CURRENT = {"id": "current", "role": "user", "content": QUERY, "sequence": 1}
RAIN = "I was alone, sheltering from rain outside the tailor shop when I met the cat."
SUN = "I was alone in the sunny flower shop when I met the cat."
# Rounded native turn-7 score shape, assigned to SYNTHETIC texts. These are not
# embeddings measured for these texts, nor replay of the private native capture.
SCORES = {
    "s1": 0.572538,
    "s2": 0.414709,
    "s3": 0.601849,
    "s4": 0.603110,
    "s5": 0.663228,
    "s6": 0.615990,
}
RECIPES = ["probe_local_qwen_cosine", "probe_local_qwen_cosine_v2"]


def _exchange(index: int, user: str, assistant: str, archived: bool) -> dict:
    messages = []
    for sequence, (role, content) in enumerate(
        [("user", user), ("assistant", assistant)], start=1
    ):
        messages.append(
            {
                "id": f"s{index}-{role}",
                "role": role,
                "content": content,
                "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                "created_at": f"2026-09-{index:02d}T12:00:00+00:00",
                "sequence": sequence,
            }
        )
    return {
        "run_id": f"s{index}",
        "conversation_id": f"chat-{index}",
        "definition_version_id": "prior-version",
        "archived": archived,
        "messages": messages,
        "annotations": {
            "links": [],
            "facts": [],
            "revisions": [],
            "predecessor_edges": [],
        },
    }


def _corpus(origin: str, retelling: str, archived: bool) -> list[dict]:
    return [
        _exchange(1, "Tell me a story from after work.", origin, archived),
        _exchange(2, "What music do you like?", "Quiet piano music.", archived),
        *[
            _exchange(
                index, f"Recall the cat episode, question {index}.", retelling, archived
            )
            for index in range(3, 7)
        ],
    ]


def _rank(corpus: list[dict], recipe: str):
    documents = {
        document_text(
            {
                "user": item["messages"][0]["content"],
                "assistant": item["messages"][1]["content"],
            }
        ): SCORES[item["run_id"]]
        for item in corpus
    }
    requests = []
    guards = []

    async def authorize(exchanges):
        guards.append([item["run_id"] for item in exchanges])
        return set()

    class SyntheticEmbeddings:
        async def embed(self, *, model_key, inputs, timeout_seconds):
            assert model_key == HISTORY_EMBEDDING_ROUTE
            assert timeout_seconds > 0
            requests.append(list(inputs))
            # Identical current/context vectors isolate selection from query mixing.
            return [
                [score, math.sqrt(1 - score * score), *([0.0] * 1022)]
                for text in inputs
                for score in [documents[text] if text in documents else 1.0]
            ]

    suffix = [{"role": "user", "content": "I was thinking about our last chat."}]
    result = asyncio.run(
        rank_native_history(
            exchanges=corpus,
            current_user=QUERY,
            local_suffix=suffix,
            recipe=recipe,
            embeddings=SyntheticEmbeddings(),
            model_key=HISTORY_EMBEDDING_ROUTE,
            deadline=time.monotonic() + 30,
            authorize_sources=authorize,
            mark_exposed=lambda: None,
        )
    )
    assert requests[0] == list(documents)
    assert requests[1] == (
        [query_text(QUERY, []), query_text(QUERY, suffix)]
        if recipe.endswith("_v2")
        else [query_text(QUERY, suffix)]
    )
    assert guards == [[item["run_id"] for item in corpus]] * 2
    assert result.embedding_dispatches == 2
    assert result.all_scores == pytest.approx(SCORES)
    assert [item["id"] for item in result.ranked] == ["s5", "s6", "s4", "s3"]
    return result


def _packets(exchanges: list[dict]):
    base = BuiltContext(
        messages=[
            {"role": "system", "content": "Stay in character."},
            {"role": "user", "content": QUERY},
        ],
        section_tokens={},
        omitted_message_ids=[],
        retrieved_fact_ids=[],
        estimated_input_tokens=0,
    )
    admission = admit_history(
        base=base,
        ranked_exchanges=exchanges,
        current_user=CURRENT,
        source_messages=[CURRENT],
        facts=[],
        entities=[],
        generation_model_key="deepseek::deepseek-flash",
        generation_adapter="deepseek_openai",
        generation_tools={},
        generation_input_limit=100_000,
        generation_max_output_tokens=512,
        reviewer_model_key="deepseek::deepseek-flash",
        reviewer_adapter="deepseek_openai",
        reviewer_input_limit=100_000,
        reviewer_max_output_tokens=4096,
    )
    assert not admission.omitted_capacity
    assert list(admission.exchanges) == exchanges
    review = natural_review_request(
        model_key="deepseek::deepseek-flash",
        provider_adapter="deepseek_openai",
        current_user_message=CURRENT,
        source_messages=[CURRENT],
        facts=[],
        entities=[],
        candidate_reply=SUN,
        history_exchanges=list(admission.exchanges),
        history_capable=True,
    )
    history = json.loads(review["messages"][1]["content"])["history"]
    wire = json.dumps(history, ensure_ascii=False, separators=(",", ":"))
    assert wire in admission.context.messages[0]["content"]
    return admission, review


@pytest.mark.parametrize("recipe", RECIPES)
@pytest.mark.parametrize("archived", [False, True])
def test_opposite_origins_collapse_to_identical_model_evidence(recipe, archived):
    faithful = _corpus(SUN, SUN, archived)
    misleading = _corpus(RAIN, SUN, archived)
    good_rank, bad_rank = _rank(faithful, recipe), _rank(misleading, recipe)
    # Private rank receipts distinguish the corpora; neither model gets that
    # omitted text. The same answer cannot faithfully recall both origins.
    assert good_rank.recipe_identity != bad_rank.recipe_identity
    assert good_rank.document_hashes["s1"] != bad_rank.document_hashes["s1"]
    assert good_rank.exchanges == bad_rank.exchanges
    good, good_review = _packets(good_rank.exchanges)
    bad, bad_review = _packets(bad_rank.exchanges)
    assert good.context.messages == bad.context.messages
    assert good_review == bad_review
    assert RAIN not in json.dumps(bad.context.messages)
    assert all(item["archived"] == archived for item in bad.exchanges)
    observation = history_observation(
        SimpleNamespace(
            corpus={
                "inventory": {
                    "status": "complete",
                    "candidates": [
                        {"run_id": item["run_id"], "reason": "eligible"}
                        for item in misleading
                    ],
                }
            },
            probe=SimpleNamespace(arm="automatic_history"),
            status="ranked",
            admitted_exchanges=bad.exchanges,
            ranked_exchanges=bad_rank.exchanges,
            purged_run_ids=[],
            omitted_capacity=bad.omitted_capacity,
        )
    )
    assert {item["run_id"]: item["reason"] for item in observation["candidates"]} == {
        "s1": "selector_not_selected",
        "s2": "selector_not_selected",
        "s3": "admitted",
        "s4": "admitted",
        "s5": "admitted",
        "s6": "admitted",
    }


@pytest.mark.parametrize("recipe", RECIPES)
def test_faithful_echoes_can_preserve_core_without_original(recipe):
    result = _rank(_corpus(RAIN, RAIN, True), recipe)
    admission, _ = _packets(result.exchanges)
    assert "s1" not in [item["run_id"] for item in admission.exchanges]
    assert all(item["messages"][1]["content"] == RAIN for item in admission.exchanges)


@pytest.mark.parametrize("recipe", RECIPES)
def test_earliest_source_reservation_still_can_lose_explicit_correction(recipe):
    original = "I met the cat after work on Saturday."
    correction = "I misspoke about the day: it was Friday, not Saturday."
    ordinary = _corpus(original, original, True)
    corrected = _corpus(original, original, True)
    corrected[1] = _exchange(2, "Was the day right?", correction, True)
    ordinary_rank = _rank(ordinary, recipe)
    corrected_rank = _rank(corrected, recipe)
    assert ordinary_rank.recipe_identity != corrected_rank.recipe_identity
    assert ordinary_rank.exchanges == corrected_rank.exchanges
    # Evaluator-only oracle intervention, NOT a candidate runtime selector:
    # even giving an algorithm the correct episode origin does not recover s2.
    before, before_review = _packets([ordinary[0], *ordinary_rank.exchanges[:3]])
    after, after_review = _packets([corrected[0], *corrected_rank.exchanges[:3]])
    assert before.context.messages == after.context.messages
    assert before_review == after_review
    assert original in json.dumps(after.context.messages)
    assert correction not in json.dumps(after.context.messages)
    visible, _ = _packets([corrected[0], corrected[1], *corrected_rank.exchanges[:2]])
    assert original in json.dumps(visible.context.messages)
    assert correction in json.dumps(visible.context.messages)


def test_oracle_origin_restores_conflict_visibility_not_semantic_resolution():
    corpus = _corpus(RAIN, SUN, True)
    result = _rank(corpus, RECIPES[0])
    admission, review = _packets([corpus[0], *result.exchanges[:3]])
    assert RAIN in json.dumps(admission.context.messages)
    assert SUN in json.dumps(admission.context.messages)
    assert RAIN in review["messages"][1]["content"]
    assert SUN in review["messages"][1]["content"]
    # No generated answer/reviewer decision: visible conflict is not a pass.
