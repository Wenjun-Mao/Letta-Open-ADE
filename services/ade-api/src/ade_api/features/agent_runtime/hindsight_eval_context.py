"""Character-facing projection for structurally owned recalled context."""

from collections.abc import Sequence

from .hindsight_eval_contracts import RecalledMemory


def character_context_projection(
    memories: Sequence[RecalledMemory], *, character_root_id: str
) -> list[RecalledMemory]:
    """Keep attached context only when all structural owners name this root.

    A profile tag may make a fact portable across characters, but does not grant
    the fact's source-root reference window the same portability. Tags and the
    attribution projection are the only ownership inputs; freeform context is
    never parsed. Facts remain available when ownership is absent or ambiguous.
    """
    expected_owner = {character_root_id}
    projected = []
    for memory in memories:
        owners = {
            tag.removeprefix("character:")
            for tag in memory.tags
            if tag.startswith("character:")
        }
        if memory.metadata is not None and "character_root_id" in memory.metadata:
            owners.add(memory.metadata["character_root_id"])
        if owners != expected_owner:
            memory = memory.model_copy(update={"context": None})
        projected.append(memory)
    return projected
