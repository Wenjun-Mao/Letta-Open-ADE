# ADR 0044: Native Generation Memory Contract Candidate

Status: Accepted for offline diagnostic preparation on 2026-09-26. Live
evaluation, default adoption and release qualification remain pending.

## Problem

The 2026-05 chat prompt claims editable memory blocks and searchable conversation
recall. Native ADE instead presents saved facts, optional attributed historical
exchanges, a separate reviewer for proposed writes, and structural commit checks.
The shared `context.py` instruction to use only committed facts could also cause
a generator to deny admitted testimony. The seven-turn H4 follow-up observed a
wrong-dog reply and a denial of admitted tea dialogue, but does not prove which
instruction caused either answer (PC-01/03/05/07/10).

## Decision

Add `chat_v20260926` as an explicitly selected generation candidate. Preserve
the old file and persona binding. Replace the obsolete block and transcript
claims in the new template with the native division of work: generator speaks,
reviewer interprets potential writes, ADE validates and commits. No reply may
claim a write already succeeded.

Clarify the shared `context.py` rule: active saved facts can describe the present;
attributed dialogue can establish what was said, without proving current truth.
Ask for clarification when materially plausible referents remain; answer clear
references directly. Clarify the H-only `history_admission.py` instruction that
an empty saved-fact search does not negate supplied dialogue. The
`executor.py` tool description explicitly limits `search_memory` to saved fact
descriptors. `tool_policy.py`, `natural_context.py`, reviewer instructions/schema,
retrieval, and persistence remain unchanged.

## Consequences and guardrails

The shared `context.py` and tool-description changes affect assembled generation
packets for existing bindings too. This diagnostic therefore records separate
hashes for the candidate and shared instruction owners and cannot be read as a
prompt-only causal contrast. The H-only instruction is read-only; it does not
authorize persistence. Existing definitions and conversations retain immutable
prompt/persona snapshots; defaults do not switch. Rejecting an ambiguous target
is the reviewer's semantic duty under ADR 0043; ADE keeps structural validation.

Rejected an additive override to the old prompt, phrase-specific dog/tea rules,
new retrieval or reviewer mechanisms, and treating absence from saved facts as
absence from dialogue (PC-06/09). Packet, binding and persistence tests guard the
mechanics. The frozen seven-turn diagnostic is a bounded observation, not proof
of general model reliability or release readiness.
