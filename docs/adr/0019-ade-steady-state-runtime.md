# ADR 0019: ADE Owns The Steady-State Agent Runtime

- Status: Accepted
- Date: 2026-09-07
- Supersedes the transitional deployment and rollback portions of ADRs 0013,
  0016, and 0017

## Context

ADE completed its fresh-start Agent Studio cutover, but the repository and local
stack retained Letta, Redis, a second API process, paired parity evaluation,
rollback rehearsals, and two model identities. Those assets reduced migration
risk before cutover. After cutover they created a second authority that product
traffic no longer used and made the current system difficult to understand.

The ADE-owned runtime already persists definitions, subjects, conversations,
messages, typed memory, runs, and events in PostgreSQL. It routes model and
embedding requests through Model Router and executes work through the ADE runtime
worker. Comment Lab and Label Lab also use Model Router directly.

## Decision

- ADE API is the single HTTP backend. It serves the existing lab and content
  APIs together with Agent Studio under `/api/v3`.
- PostgreSQL is the sole persistent Agent Studio authority. Model Router is the
  sole provider and model-identity authority.
- Letta, Redis, the native API sidecar, rollback-only v2 Agent Studio, arbitrary
  Tool Center execution, and paired Letta parity are removed.
- Agent Studio exposes only curated product tools. Evaluation-only deterministic
  tools are available only to resources created with `purpose=evaluation`.
- Behavior and qualification workflows provision resources through a focused
  evaluation-session boundary instead of public generic runtime CRUD.
- Release evidence qualifies the native runtime directly. It binds the deployment
  manifest, active route aliases, agent bundle, deterministic conformance, source
  identity, and explicit reviewer approval. Letta parity and Letta rollback are
  not release requirements.
- Recovery uses deployment rollback and PostgreSQL backup/restore. Historical
  Letta data is not imported.
- Public `/api/v3` remains the API version. Internal modules and settings use the
  steady-state `agent_runtime` name rather than retaining a migration-era `v3`
  suffix.

## Rejected Alternatives

### Keep Letta As A Dormant Rollback Runtime

This preserves a second database, API, model identity, dependency graph, and
operational procedure. A dormant application-level fallback is less reliable
than reverting a known image and restoring its authoritative database.

### Keep Generic Runtime CRUD For Test Harnesses

The broad surface exposes invalid product combinations and makes tests drive the
domain model directly. Focused evaluation sessions provide the needed isolation,
reuse, and cleanup without becoming a second product API.

### Preserve Tool Center Without A Runtime Consumer

An authoring UI without an execution and sandbox contract is misleading. Tool
authoring can return when a concrete product use case defines both contracts.

## Consequences And Guardrails

- The ordinary Compose graph contains PostgreSQL, Model Router, the migration job,
  the runtime worker, ADE API, and ADE Web.
- Existing ADE PostgreSQL data is preserved. Legacy Letta state may remain in old
  local volumes but is not read by the application.
- Changing governed runtime code, policy, prompts, personas, tools, deployment
  identities, or canonical qualification fixtures requires new release evidence.
- Unrelated documentation and frontend-only changes do not invalidate runtime
  qualification.
- Provider SDK retries remain disabled. ADE owns request timeout and additional
  retry counts.
- No compatibility aliases, Letta importer, arbitrary Python execution, or Redis
  requirement may be reintroduced without a new accepted decision.
