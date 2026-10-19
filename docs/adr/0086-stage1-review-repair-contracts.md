# ADR 0086: Stage-1 Review Repair Contracts

Status: Accepted for the user-approved offline review repairs, 2026-10-19.
This refines ADR 0073/0075 under PC-03/05/09/12/14; it does not change product
direction, authorize live runs or qualify the repaired runtime.

## Root Causes

The focused review of `4c354cde6f5fff22d05abd13adb785c1fb730751` found:

- Bank access performs required ADE SQL, but lookup translated only native/bank
  and timeout errors. A database availability error escaped saved-input pausing;
  the generic tool handler could turn it into a Character apology continuation.
- The compaction planner budgeted `role: content`, while the Hindsight composer
  budgeted JSON envelopes and independently discarded raw history. Two prior
  5,966-character messages cost 2,988 versus 3,001 tokens, losing an unsummarized
  user message. The serialized-total trimming loop had the same coverage defect.
- Tool capture checked membership in a union of memory IDs, not per-call native
  objects. Changed text/time and dropped rows could pass with the same IDs.

These belong at the lookup boundary, context partition and capture validator,
not in downstream apology handling, larger arbitrary windows or answer-specific
Memory/Character rules.

## Decision

### Lookup Availability

Normalize known database availability errors to `MemoryLookupError` with the safe
detail `memory_lookup_database_unavailable`: operational/interface failures,
invalidated DBAPI connections, pool disconnection/timeout and connection errors.
Automatic and discretionary lookup then share the existing paused saved-input
contract. Do not expose SQL/provider error bodies or automatically retry Character.
Cancellation and non-invalidated programming/integrity errors remain distinct;
do not broadly classify every exception as a recoverable lookup outage.

### Complete Dialogue Coverage

Keep the established raw-message token formula, count limits and compaction
policy. The planner alone partitions a summary-covered prefix and complete raw
suffix. Its `recent_message_tokens` helper also validates the composer's suffix.
The ten-message retention limit applies only after compaction triggers, not to
every conversation.

The composer never independently discards that suffix. A missing required
compaction fails explicitly; serialized pressure removes optional recall first,
then fails if intact instructions, current input, summary and complete dialogue
still cannot fit. No bigger default context, mandatory-text truncation or silent
history omission is substituted. Structural coverage does not establish faithful
summary meaning or general Memory recall.

### Serial Per-Call Native Provenance

Private lookup lifecycle records use `ade-memory-lookup-v2`. An attempt-local
monotonic, positive integer `lookup_number`, phase, bank, effective query and local
selection limit appear unchanged on started and completed/failed records.
Default/stripped tool arguments keep their existing meaning. Model input, public
tools and unrelated tool-handler signatures do not acquire evidence fields.

The maintained executor is sequential: private `model_request.finished` is recorded
before its response is returned, then only that attempt's `search_memory` handler
owns `phase=tool` lookups, awaited in response-call order. The validator binds each
call by `(attempt, parent request, call index)` to one ordered lifecycle pair
strictly after the received response and before its next bound conversation
dispatch. Contiguous scope-checked records, monotonic pairs, non-overlap and a
bijection are required; timestamps, pooled IDs or query equality are not identity.
Parallel tools or another owner of these lookups require a revised contract.

Verify the complete tool suffix and exact, ordered native `response.results[:limit]`
objects with type-sensitive JSON equality, including all attribution/time/nested
fields. Selected IDs must match that same slice. Successful empty output requires
a matched completed native response and explicit successful empty envelope.
No failed, missing or unmatched lookup may become an empty success or a new
Character dispatch. A failed/interrupted attempt may stop before later emitted
calls execute, during a lookup with only its start recorded, or after a lookup
without dispatch. Validate the observed prefix; a terminal in-flight lookup must
still match its parent/call arguments and cannot have a later dispatch or gain
completed-result provenance. Do not invent unseen work or a terminal event.
Non-Memory tool results are not labelled recall.
Component provenance gains the verified call/lookup binding only after validation.

## Rejected Alternatives And Guardrails

Reject catch-all outage normalization, changing generic tool apologies, separate
compaction/composer suffix selectors and merely enlarging context limits. Reject
union-ID validation, ID-keyed object reconstruction, implicit call-identity repair
and adding a new generic invocation framework when complete serial chronology
already supplies an unambiguous boundary.

Keep historical captures/seals and live source bindings unchanged. The six
retained probes had no discretionary lookup; their automatic-recall observations
remain readable, but do not qualify this new tool binding. Legacy tool records
without v2 metadata fail closed rather than receive inferred provenance.
Regenerate only the unqualified development candidate manifest for changed policy
sources; never rebind historical release ledgers or relabel the old live image.

Portable regressions cover outages/recovery, paused finalization, no apology
continuation, UTF-8/escaping budget boundaries, complete summary/raw coverage,
serialized overflow, actual executor/recall observations and adversarial per-call
capture mutations. Local substitutes prove mechanics, not a new live baseline,
paired restore, human Character judgment or semantic acceptance.
