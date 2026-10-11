"""Character-facing context projection for the isolated Hindsight evaluation."""

from collections.abc import Sequence

from .hindsight_eval_contracts import RecalledMemory

PROFILE_TAG = "kind:profile"


def _structural_owners(memory: RecalledMemory) -> tuple[set[str], bool]:
    owners = set()
    malformed_owner = False
    for tag in memory.tags:
        if tag.startswith("character:"):
            owner = tag.removeprefix("character:")
            if owner:
                owners.add(owner)
            else:
                malformed_owner = True
    if memory.metadata is not None and "character_root_id" in memory.metadata:
        owner = memory.metadata["character_root_id"]
        if owner:
            owners.add(owner)
        else:
            malformed_owner = True
    return owners, malformed_owner


def _shared_profile_fact(memory: RecalledMemory) -> RecalledMemory:
    """Keep the subject fact while removing its other-root source trail."""
    return memory.model_copy(
        update={
            "tags": [PROFILE_TAG],
            "context": None,
            "mentioned_at": None,
            "document_id": None,
            "source_fact_ids": None,
            "metadata": None,
        }
    )


def character_context_projection(
    memories: Sequence[RecalledMemory], *, character_root_id: str
) -> dict[str, list[RecalledMemory]]:
    """Separate portable subject facts from this character's source history.

    Profile-tagged propositions can cross character roots, but their source
    attribution cannot. Other memories enter Character context only when their
    structural owners resolve to exactly the active root. Freeform context and
    fact text are never parsed to infer ownership.
    """
    shared_profile_facts = []
    same_character_history = []
    for memory in memories:
        owners, malformed_owner = _structural_owners(memory)
        owned_by_active_character = (
            owners == {character_root_id} and not malformed_owner
        )
        if owned_by_active_character:
            same_character_history.append(memory)
        elif PROFILE_TAG in memory.tags:
            shared_profile_facts.append(_shared_profile_fact(memory))

    return {
        "shared_profile_facts": shared_profile_facts,
        "same_character_history": same_character_history,
    }
