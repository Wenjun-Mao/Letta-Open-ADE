# ADR 0007: Router Authority For Router-Backed Models

- Status: Accepted
- Date: 2026-08-23

## Context

ADE creates router-backed agents with an explicit Letta `llm_config` containing the
router endpoint, model id, and handle. Letta's model list can lag behind the router or
omit soft-deleted rows after a provider disappears and returns. Live verification
confirmed that explicit agent creation still succeeds in that state.

Requiring a router model to also appear in Letta's list therefore hid healthy models
from Agent Studio even though ADE could use them.

## Decision

The model router is the source of truth for availability and compatibility of
router-backed LLMs. ADE exposes a model to Agent Studio when the router marks it
available and supplies a Letta handle. ADE continues to create the agent with an
explicit router `llm_config`.

Letta remains the source of truth for embedding handles and persisted agent state.
Model catalog responses report `letta_catalog_visible` as a diagnostic, but that value
does not gate router-backed model availability.

## Rejected Alternatives

- Keep the strict router/Letta catalog intersection. This turns stale external state
  into a false product outage.
- Repair Letta's database rows directly. This couples ADE to Letta's private schema
  and does not prevent recurrence.
- Add model-specific exceptions. This would create hidden source divergence.

## Consequences And Guardrails

- Router health and compatibility profiles must remain conservative because they now
  control Agent Studio model visibility.
- Model Router discovers enabled sources concurrently with one bounded request per
  source and warms the first catalog snapshot before application startup completes.
  Compose readiness therefore cannot precede the catalog contract used by ADE.
- Catalog transport failures at the ADE v3 boundary return a stable `503` rather
  than leaking an internal exception or reporting a behavioral model failure.
- Agent creation must continue passing explicit router `llm_config` for scoped model
  handles.
- Tests cover repository-relative profile loading and availability when the Letta
  catalog diagnostic is false.
