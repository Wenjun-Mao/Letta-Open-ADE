# Checkpoint 6 live diagnostic: external consultation packet

Status: prepared for maintainer review; not dispatched. The evidence is in a
local, unpushed worktree. A consultant with GitHub-only access cannot inspect
these revisions or mode-restricted provider captures until the maintainer
chooses an authorized sharing route. Do not paste raw captures containing
conversation data or provider metadata into an external service by default.

## Decision requested

Recommend a durable next design and verification strategy for ADE's current
one-call natural-memory reviewer. Explain how to make proposal validity and source
authority robust without weakening native validation, silently repairing model
outputs, rerolling a failed turn, changing the mutation scorer, or treating a
partial diagnostic as policy qualification. Rank at least two viable contract
or workflow designs by source ownership, complexity, expected failure modes,
and evidence needed before a frozen A/B comparison can restart. Identify what
requires a new ADR or evaluation-envelope amendment.

## System and constraints

ADE generates a candidate conversational reply, asks a separate DeepSeek
reviewer once for mixed add/revise/end/reassert/forget proposals, validates
those proposals against a typed contract and server-selected source bundle,
and commits reviewer-approved mutations and the candidate reply atomically.
The one-call shape and reply/memory coupling describe the current design;
challenge them if a small, safer alternative better satisfies the product
contract. Server-owned subject binding, current-user authority, exact
provenance, isolation, privacy, and no unauthorized write are nonnegotiable.
The subject is bound by the server. For a subject-kind add, `entity_ref` must
be null; related facts use an existing/new entity reference. Only the current
user assertion or endorsement can authorize writes. A prior assistant referent
may support an explicitly endorsed value; prior user turns are context, not a
second write authority. The runtime rejects invalid proposals without
commit or retry. The evaluation uses the native B policy and pinned
DeepSeek-flash (high thinking) and Qwen3 Embedding routes, with 6,759 visible
reviewer input tokens. The 4,096 completion allowance is a separate
nonqualifying diagnostic; the frozen comparison used 1,024.

Key local sources after sharing: reviewer prompt/request builder
`services/ade-api/src/ade_api/features/agent_runtime/natural_memory_reviewer.py`;
typed output and source binder `natural_memory_review.py`; preparation and
entity resolution `natural_memory_policy.py`; evaluation capacity
`natural_evaluation_capacity.py`; exact runner
`workflows/evals/character_memory_dev/natural_live_campaign.py`; frozen
cases/matrix and checkpoint-6 findings. The frozen cases and matrix hashes are
`abd244c17c5f2e6fe90f9a32bc50e1bb262d233f0dad62db4f682d65b615dcc3`
and `188148ea73facc1e2fbecd795d2172e5cb659e489ff792b42dcc0db704a356d8`.

## Observed sequence

| Campaign | Exact source | Attempted / planned | Observation | Atomic state |
| --- | --- | --- | --- | --- |
| Original frozen | `717ee809` | 1 of 30 frozen cells | Morning coffee proposal selected subject UUID, omitted morning scope. | Rejected; no write/reply. |
| Iteration 1 | `59478b4b` | 2 of 3 targeted cells; 2 frozen positions probed | Explicit subject/scope instruction made coffee pass; scoped tea reviewer hit 1,024-token `length` with empty JSON. | Coffee committed; tea rejected. |
| Iteration 2 | `11f86b5` | 3 of 3 targeted cells; 3 frozen positions probed | At 4,096 output tokens, coffee and independent scoped tea passed. Correction proposed correct `Roxy` revision but cited older Rocky user text as second `user_assertion`. | First two committed; correction rejected. |
| Iteration 3 | `a0ce572` | 1 of 3 targeted cells; 1 frozen position probed | Shared instruction clarified prior-user context versus current authority. Morning coffee proposal again selected subject UUID despite explicit subject rule. | Rejected; no write/reply. |

Iteration 2 is concrete improvement and establishes that the 1,024-token
reviewer envelope can truncate high-thinking output. Iteration 3 shows the
subject-binding failure can recur; three small diagnostics do not estimate a
failure rate. Each iteration used its own fresh database and source version;
the probed frozen positions are not cumulative progress through one campaign.
Neither original nor diagnostic run completed enough of the frozen matrix to
compare A/B or support release selection. There was no
observed privacy, isolation, or atomicity defect. Hard request caps were
96 generation/160 embedding; each diagnostic stopped on the required failure.

## Questions for the reviewer

1. Is the API asking the model to choose entity or source fields that the
   server already knows? Should subject-kind and related-kind additions be
   separate typed proposal variants, structurally constrained in the
   model-facing schema, or expressed with less model-owned identity data?
   Consider the current nullable `entity_ref` and router JSON-object mode.
2. Can the source bundle distinguish citable current-user spans, endorsed
   assistant referents, historical context, and mutation targets structurally
   enough to reduce invalid citations while retaining exact provenance? Is
   the authority mismatch structural, prompt-only, or both?
3. Is one high-thinking mixed review with a large schema and 6,759-token input
   envelope a sound architecture for these workloads? If changing task shape,
   specify the smallest durable contract change and how it preserves causation,
   no-save, contradiction veto, zero hidden retries, and safe visible reply/
   memory outcomes. Assess whether current all-or-nothing coupling is required
   or whether a safer explicit outcome contract exists.
4. What focused offline and live evidence would justify a future output-envelope
   amendment and a new frozen A/B campaign? State stop rules and failure
   classification; do not infer policy quality from the partial diagnostics.

Please distinguish observed causes from hypotheses, inspect the shared
validator before proposing relaxation, and return a concise recommendation
with rejected alternatives and required regression/acceptance tests. Do not
apply changes or contact providers as part of the review.
