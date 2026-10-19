"""Versioned native Memory instructions, independent of Character's persona."""

import hashlib

from .hindsight_sources import canonical_bytes


BANK_CONFIGURATION_VERSION = "character-local-memory-v1"
RETAIN_MISSION = """Retain source-supported meaning for this one user-character relationship.
The current source is an attributed original message: user means the user and
assistant means this bank's character. Preserve its speaker, original time,
conversation and definition binding. Earlier messages marked earlier_context_only
provide referents; they are earlier attributed statements, not new assertions.
Distinguish an earlier mistaken statement later corrected from a genuine change
over time and from a temporary choice. Preserve what was said without inventing
a former preference, date or reason. Keep uncertainty, hypotheses, imagined
settings, solo experiences and shared experiences distinct. An assistant's solo
fiction is not a user fact or a shared event. Do not infer participation or
unsupported missing details. All facts and experiences belong to this bank;
there is no portable profile classification or sharing with another character."""

OBSERVATIONS_MISSION = """Organize supported memories for the same user and character.
Preserve speaker and temporal meaning, including whether a later statement
corrected an earlier mistake or described a genuine subsequent change.
A corrected utterance may remain part of what was said without becoming a real
former preference. Preserve explicit uncertainty and distinguish hypotheses,
solo fiction and shared history. Do not turn an unknown detail into recollection
or a solo experience into the user's participation. Do not invent missing dates,
causes, preferences or events while consolidating."""


def bank_configuration() -> dict:
    return {
        "retain_mission": RETAIN_MISSION,
        "observations_mission": OBSERVATIONS_MISSION,
        "enable_observations": True,
        "enable_auto_consolidation": True,
    }


def bank_configuration_sha256() -> str:
    return hashlib.sha256(
        canonical_bytes(
            {
                "version": BANK_CONFIGURATION_VERSION,
                "updates": bank_configuration(),
            }
        )
    ).hexdigest()
