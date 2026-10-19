# Agent Runtime

This package owns Agent Studio and evaluation `/api/v3` product records and reply
orchestration. ADE PostgreSQL owns original messages, authored character versions,
conversation bindings, run/attempt state and delivery bookkeeping. Self-hosted
Hindsight owns learned Memory. Model Router owns provider forwarding.

The maintained source path is Hindsight-only and development-only. Existing
deployed ADE/trial images and databases are not changed by this source replacement.
Stage 1 browser, complete live capture and fault/closeout verification remain in
progress; this is not release or Character qualification.

## Product And Execution

- A conversation binds one immutable definition version to one subject. Ordinary
  persona-version updates preserve the character root and its relationship bank.
- One bank belongs to `(workspace, subject, character root)`. Neither a new chat,
  persona edit nor archive state silently starts another relationship.
- Acceptance atomically saves the user message and immutable delivery intent.
  Success atomically saves the assistant message, outcome, any summary and reply
  delivery intent. Failed/cancelled replies preserve accepted-user eligibility.
- Independent delivery consumers preserve per-relationship order and reconcile
  original native operations. A reply does not wait for retention.
- Every attempt normally recalls within its persisted relationship. Successful
  empty recall is valid. Required automatic/tool lookup failure pauses the saved
  input without a Character apology or an empty-memory substitute.
- `POST /api/v3/runs/{id}/retry` takes `idempotency_key` and
  `expected_attempt_count`; it performs fresh recall without another user insert.
  Retry and Cancel resolve the paused conversation's input guard. Stale workers
  cannot commit candidates or their delivery intents.

There is no maintained native reviewer, ADE fact-write step, SQL-only purge,
subject-wide Memory endpoint or manual reset/removal API in this path. Historical
tables, migrations, findings and frozen evaluation evidence remain preserved.
Archived original chats are still readable; archiving is not erasure.

## Owners

- `definition_service.py`, `agent_studio_sessions.py`, `session_resources.py` and
  `studio_catalog.py` own scoped authored resources and immutable bindings.
- `run_service.py`, `run_retry.py` and `persistence/run_lifecycle.py` own admission,
  conversation-first lifecycle locking and saved-input Retry receipts.
- `turn_execution.py`, `hindsight_context.py` and `turn_recall.py` own normal scoped
  lookup and Character context. Retrieved Memory remains contextual data.
- `executor.py` owns finite curated-tool execution. Required Memory errors escape
  the tool loop; ordinary non-Memory tool errors retain their explicit result.
- `compaction.py` and `compaction_executor.py` preserve summary prefix/provenance
  through the separately bound compaction deployment. Whole serialized initial,
  continuation and compaction payloads are checked against their input bounds.
- `turn_sources.py` appends delivery intent in its caller's product transaction.
  `memory_banks.py` and `memory_delivery_worker.py` own native availability and
  independent ordered scheduling. No native/provider HTTP runs inside ADE SQL.
- `memory_progress.py` allows only operational snapshot fields into bookkeeping;
  native error bodies, task payloads and private reasoning are not public activity.
- `memory_inspection.py`, `memory_inspection_api.py` and their SQL projection own
  `/api/v3/memory/subjects/{subject}/characters/{root}`. Saved delivery state does
  not depend on native availability; memories/sources/operations fail explicitly
  rather than return false empty state. See
  [ADR 0074](../../../../../../docs/adr/0074-relationship-memory-inspection.md).
- `worker.py` and `worker_*` own leases, cancellation, attempts and finalization.
  `turn_result.py` carries reply/compaction output, not a fake empty review.

## Configuration And Verification

Require an explicit non-`default` `ADE_API_AGENT_RUNTIME_WORKSPACE_KEY` and an
existing/new workspace marked `hindsight`; never convert an incumbent workspace.
Configure `ADE_API_HINDSIGHT_BASE_URL` and a private
`ADE_API_HINDSIGHT_API_KEY`. The API and worker must use the same workspace,
Memory endpoint, migration head and exact source identity.

Definitions bind only `model_key` and `compaction_model_key`; Hindsight manages
its own extraction/embedding bindings. The isolated candidate manifest defaults
to `workflows/evals/hindsight_integration/config/deployments.json`, overridden by
`ADE_API_AGENT_RUNTIME_DEPLOYMENT_MANIFEST`. This new candidate has no release
rounds and cannot inherit the incumbent release ledger.

The [integration runbook](../../../../../../workflows/evals/hindsight_integration/operations.md)
documents local PostgreSQL verification and authorized isolated activation.
[ADR 0072](../../../../../../docs/adr/0072-hindsight-outbox-and-saved-input-retry.md)
owns delivery/Retry; [ADR 0073](../../../../../../docs/adr/0073-hindsight-reply-runtime.md)
owns the replacement reply contract. The separate historical
[comparison CLI](HINDSIGHT_EVALUATION.md) and native capture findings are not this
normal product path or a qualification substitute.
