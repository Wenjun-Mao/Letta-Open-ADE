# Native Generation Contract: Offline Instruction Review

Status: checkpoint 1–3 preparation, 2026-09-26. No new provider call,
semantic acceptance, default switch, deployment, or release rebind.

This review applies PC-01/03/04/05/07/09/10 and
[ADR 0044](../../adr/0044-native-generation-memory-contract-candidate.md).
The source conflict is observable in the old `chat_v20260516` template and the
shared `context.py` wording. Their causal contribution to the prior wrong-dog
and denied-tea replies remains unproven.

## Entire assembled instruction stack

The tested native generation packet is assembled in this order:

| Owner and packet position | Offline review |
| --- | --- |
| `chat_v20260926` base prompt | Persona immersion, Simplified Chinese and pure-dialogue rules remain. The old editable-block, immediate-write and searchable-transcript claims are replaced with ADE saved facts, separately reviewed writes and attributed dialogue. No success claim precedes commit. |
| Bound `chat_linxiaotang` persona | Unchanged hash `d78cf538395a685f960866a4ab3e9f375aeefb5aa94de8f6fcbae03ab152085b`. Its short Chinese conversational style is compatible with the candidate output rules. |
| Shared `context.py` memory instructions | Active facts describe the present; attributed dialogue can answer what was said without proving current truth. Ambiguous referents get neutral clarification, clear references a direct answer. This owner is assembled for old bindings too. |
| `natural_context.py` metadata, lifecycle views and suffix | Unchanged selection and formatting. Only active lifecycle views are current; inactive views remain historical. The ordinary no-H path and the H base path use the same candidate and shared instructions. |
| `history_admission.py` H section, when H-capable | H is attributed read-only source data. The added owner-level wording says an empty saved-fact search does not negate supplied dialogue and unavailable history must not be invented. The existing `HISTORY_LIFECYCLE_INSTRUCTION` is unchanged because the reviewer also consumes it. |
| `executor.py` tool policy and `search_memory` schema | Tool policy is unchanged. The schema now says the tool searches saved fact descriptors, not historical messages. A second generation request after an empty fact result retains the H text in the system message; its tool message contains `facts: []`. |

The [source-bound diagnostic binding](../../../workflows/evals/character_memory_dev/fixtures/history_recall/generation_contract_diagnostic.json)
records separate hashes for every changed or assembled generation owner. It also
pins the old prompt, prior seven-turn manifest, frozen schedule/source cases,
DeepSeek and Qwen identities, original per-turn limits, and unchanged reviewer
instruction/schema hashes (`c1c36c4e…` and `01b56de1…`). The runner checks the
complete binding before dispatch and verifies each new session's prompt and
persona hashes. Its new manifest compares admitted source text and capacity
omissions with the prior run, without assuming context remains matched.

## Capacity and verification limits

Using one synthetic archived tea exchange and the frozen 11,213-token generation
input limit, actual serialized requests measured 1,890 tokens without H and
2,248 with H under the old template plus changed shared instructions. The new
candidate measured 1,691 and 2,049 respectively. Both admitted that synthetic
exchange; the candidate uses 199 fewer serialized tokens in this sample. This
is a capacity smoke check, not a prediction of all seven turns. Each live turn
must still record its actual selected H windows and omissions.

The focused prompt, packet, continuation and runner tests passed (86 tests).
On migrated disposable PostgreSQL, the real definition snapshot test and nine
existing reviewer/history guard tests passed. The broader Agent Runtime suite
reported 307 passed, 56 skipped (database URL absent in that separate run).
Ruff passed, OpenAPI drift passed. The selected-candidate policy-freshness gate
still has its pre-existing failure (1 failed, 4 passed in its file); it has not
been waived or rebound. Fake responses establish wire and persistence mechanics,
not that DeepSeek will clarify correctly or interpret testimony correctly.
