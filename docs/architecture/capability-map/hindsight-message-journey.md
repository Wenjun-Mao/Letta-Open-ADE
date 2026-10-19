# Hindsight Message Journey

Current development-source guide, 2026-10-19. This describes the fresh Hindsight
path, not an incumbent deployment, general semantic qualification or release.
The [old animated tour](message-journey/README.md) and native fact/reviewer
inventory are explicitly historical. They do not define this runtime.

Authority: [PC-02/03/04/05/07/08/09/12/14](../../product-contract.md),
[ADR 0068](../../adr/0068-hindsight-default-memory.md) and the
[Stage-1 plan](../../plans/hindsight-integration.md).

## One Accepted Input, Two Persistence Authorities

1. **Accept once in ADE.** [RunService](../../../services/ade-api/src/ade_api/features/agent_runtime/run_service.py)
   validates the conversation's immutable definition and saves the user message,
   accepted run and immutable delivery intent in one ADE transaction. Retries
   cannot create a second accepted input. A cancelled/failed reply does not undo
   the user's source eligibility.
2. **Construct the actual attempt.** [TurnExecution](../../../services/ade-api/src/ade_api/features/agent_runtime/turn_execution.py)
   binds current-chat dialogue, optional local compaction and automatic Memory
   recall. [Memory snapshots](../../../services/ade-api/src/ade_api/features/agent_runtime/turn_memory_snapshot.py)
   and [context composition](../../../services/ade-api/src/ade_api/features/agent_runtime/hindsight_context.py)
   preserve scope, source/time context and component identity. Pending retention
   is not a reply barrier; successful empty recall is valid. A required lookup
   failure pauses rather than fabricating empty memories or a Character apology.
3. **Generate, without a second reviewer.** The
   [executor](../../../services/ade-api/src/ade_api/features/agent_runtime/executor.py)
   performs the finite Character request/tool loop. Character receives authored
   persona/instructions, current input, available local context and relevant
   memories. Discretionary `search_memory` uses the same relationship and failure
   contract. Complete serialized requests, including tool continuations, remain
   bounded. No native fact reviewer or duplicate semantic ADE pass executes.
4. **Commit the reply in ADE, not across two databases.** The
   [finalizer](../../../services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py)
   revalidates lease/ownership and atomically saves the committed assistant,
   successful outcome, eligible compaction and reply-delivery intent. Rejected
   stale candidates are not Memory sources. This ADE transaction does not claim
   a distributed atomic commit with Hindsight.
5. **Deliver independently.** The
   [Memory delivery worker](../../../services/ade-api/src/ade_api/features/agent_runtime/memory_delivery_worker.py)
   consumes immutable, relationship-ordered intents with separate leases.
   [Concrete Hindsight transport](../../../services/ade-api/src/ade_api/integrations/hindsight.py)
   retains attributed originals and reconciles the original operation identity
   after uncertain acknowledgement. No HTTP request runs inside the ADE product
   transaction. Hindsight owns extraction, correction, organization and automatic
   consolidation; acknowledgement/progress is not proof of semantic correctness.

## Scope, Retry And Inspection

One persisted bank belongs to `(workspace, subject, character root)`, selected by
ADE rather than browser/model bank IDs. New chats and ordinary immutable persona
versions keep that relationship; another subject, character or workspace does not.
Original message IDs, speaker, original time, relationship sequence and payload
hash stay attributable across delivery/retry. See
[bank policy](../../../services/ade-api/src/ade_api/integrations/hindsight_bank.py)
and [source construction](../../../services/ade-api/src/ade_api/integrations/hindsight_sources.py).

[Saved-input reply Retry](../../../services/ade-api/src/ade_api/features/agent_runtime/run_retry.py)
creates a fresh fenced attempt for the same input and recalls again. Cancel keeps
the accepted source. Incompatible version/archive/state changes reject Retry
explicitly. Delivery Retry reconciles Memory delivery, not a new user turn.

[Relationship inspection](../../../services/ade-api/src/ade_api/features/agent_runtime/memory_inspection.py)
and [Agent Studio](../../../apps/ade-web/src/features/agent-studio) load product
chat/run state independently from fallible Memory reads. An unavailable remote
read is an error, not an empty list. Source/operation/retry reads enforce the
selected relationship and API role; the UI rejects stale selection responses.
The new path has no one-store purge/reset or manual Memory-removal control.

## Observation Is Not Acceptance

[Private observations](../../../services/ade-api/src/ade_api/features/agent_runtime/private_observation_service.py)
and the [workflow collector](../../../workflows/evals/hindsight_integration/README.md)
join actual committed sources, recall snapshots, complete post-normalization
Character requests and outcomes. Full synthetic captures are opt-in and private;
ordinary UI activity is not a provider-body or hidden-reasoning export.

The [scoped finding](../../findings/hindsight-product-flow-2026-10-19.md) records
six complete real-product captures, eight representative safety cases, a native
browser journey and their retained failures. These do not establish general
Memory reliability or human Character acceptance. PC-12's grounding,
conversational judgment and character fidelity remain separately assessed;
all six human reviews are still `UNREVIEWED`. Source publication is not deployment
or paired-restore/release qualification.
