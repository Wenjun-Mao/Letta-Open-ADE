# ADR 0008: Test Center Owns Evaluation Read Models

- Status: Accepted
- Date: 2026-08-26

## Context

Chat-memory evaluations already execute as Test Center workflows and write durable
summary and per-round artifacts. Operators previously had to open those raw files to
understand deterministic scores, memory changes, tool calls, and cleanup results.
Moving execution into Agent Studio or rescoring artifacts in the browser would create
duplicate workflow ownership and inconsistent pass/fail semantics.

## Decision

Test Center remains the sole owner of evaluation execution and exposes typed read
models projected from its orchestrator-owned artifacts. Run manifests retain the
request options needed to describe queued and running evaluations before artifacts
exist. Completed read models combine the summary and JSONL artifacts into comparison
metrics and per-turn evidence without exposing unrestricted filesystem access.

Agent Studio may hand its current new-agent setup to Test Center through a documented
URL contract. It does not import Test Center internals, execute fixtures, or mutate the
currently selected persistent agent. Evaluation agents remain disposable and their
archive/purge outcome is part of the result.

Deterministic checks remain the official pass/fail authority. Optional LLM judge
output is advisory metadata and cannot override the deterministic result.

## Rejected Alternatives

- Execute the fixture directly inside Agent Studio. This duplicates Test Center's
  process, artifact, cancellation, and cleanup responsibilities.
- Parse JSONL and calculate scores in the browser. This creates a second scoring
  implementation and makes artifact compatibility a frontend concern.
- Return only raw artifacts. This preserves implementation detail as the primary user
  interface and prevents stable run comparison.
- Store a second evaluation database. The orchestrator manifest and immutable run
  artifacts already provide the required durable source material.

## Consequences And Guardrails

- Typed evaluation endpoints may evolve only with their Test Center response models,
  OpenAPI artifacts, and frontend contract tests.
- Artifact readers must remain confined to the Test Center runtime state root and
  tolerate historical or incomplete runs.
- Projection adapters normalize the workflow's reduced `status="error"` row into
  explicit deterministic failure signals; completed success rows remain strict.
- Read-model metrics are projections; the original artifacts remain available for
  diagnosis and provenance.
- Agent Studio-to-Test Center handoff parameters are covered by deterministic URL
  tests, and costly evaluations never auto-start from navigation alone.
