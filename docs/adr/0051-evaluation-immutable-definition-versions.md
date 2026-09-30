# ADR 0051: Evaluation-Owned Immutable Definition Versions

Status: Accepted, 2026-09-30. Readiness item 1 only; no live-run authorization.

## Context

PC-04 and PC-11 require ordinary same-character version continuity; PC-01 and
PC-10 require natural recall across the archived-chat/version lifecycle. The
offline story probe could bind an existing version through HTTP but could not
create version 2: session creation intentionally accepts only new version-1
definitions, and the history-trial definitions API was read-only. Persistence
already supported immutable next versions. Repository-only test provisioning
therefore concealed a missing operator API, not a storage limitation.

## Decision

Add operator-authenticated `POST /api/v3/history-trial/definitions/{root_id}/versions`
behind the existing opt-in, development-only history-trial router. Reuse
`CreateAgentDefinitionRequest` and `AgentDefinitionResponse`; require a positive
`expected_current_version`. The root must already exist in the active workspace
with evaluation purpose, and its definition key must match. Missing/out-of-scope
roots return 404, invalid requests/configuration 422, and stale/archived roots 409.

Trial preparation retains exact prompt/persona/tool/route/fingerprint and capacity
guards. The definition service owns scoped version creation; existing persistence
owns locking, immutable insertion, and atomic current-pointer advancement. No
unrelated evaluation character can be converted: under workspace-then-root locks,
the service checks the expected current version and validates that prior snapshot
against the same trial binding before insertion. Both old and new bindings must
qualify; changing the display name is not a special-case exemption. No
conversation binding is rewritten. New sessions explicitly select the returned
version ID. A name-only edit is sufficient for the bounded non-biographical
turn-7 lifecycle probe; this adds no arbitrary biography-edit interface.

## Alternatives And Consequences

Do not loosen session provisioning, accept caller-specified purpose/workspace, or
provision versions through workflow repository imports. A root-addressed operation
also avoids accidentally creating a different character when a key is mistyped.
No schema change, catalog rebind, capture expansion, provider dispatch or new
production default is involved. This resolves only version provisioning; other
native-readiness and PC-11 quality gates remain open.

## Guardrails

Portable tests enforce auth, opt-in/release gating and fingerprint rejection.
Disposable PostgreSQL tests create version 2 through public HTTP, reject stale and
cross-purpose/workspace requests, verify prior rows and conversation bindings are
unchanged, and exercise archived prior-version history in the full scripted run.
Scripted replies/vectors remain mechanics evidence, not model-quality evidence.
