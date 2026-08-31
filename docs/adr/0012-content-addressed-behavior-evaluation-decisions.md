# ADR 0012: Behavior Decisions Use Content-Addressed Evaluation Evidence

- Status: Accepted
- Date: 2026-08-30

## Context

ADE's chat-memory workflow could already replay representative conversations and
show deterministic behavior evidence. It did not, however, preserve enough exact
input identity to support a durable baseline decision. A model alias, prompt key,
or persona key can keep the same name while its effective deployment or content
changes. Historical output files also cannot establish which Test Center run
created them unless that relationship is explicit.

An optional LLM judge is useful diagnosis, but it is not deterministic and cannot
own promotion. Test Center also exposes complete prompt and persona snapshots, so
its authority must not be weaker than Prompt Center's admin boundary.

## Decision

- A behavior run captures its exact prompt and persona text, content hashes,
  selected model and embedding option snapshots, deployment metadata, fixture,
  effective controls, evaluator source identity, and orchestrator run ID before
  the first round.
- The stable configuration digest excludes capture time and run ID so equivalent
  runs remain comparable. A separate provenance digest includes the run identity
  and complete snapshot.
- Test Center passes its allocated run ID to the workflow. The summary, provenance,
  and every JSONL round bind to that ID, and the read model rejects re-homed or
  internally inconsistent artifacts.
- Agent creation uses hash preconditions to reject selection drift, then reads the
  created Letta agent back and verifies its effective model, embedding, system
  prompt, and persona memory. A mismatched creation is purged and cannot contribute
  evidence.
- The workflow owns no hidden transport retry and requires `retry_count=0`. Agent
  Studio message requests do not yet have server-owned idempotency, so replaying an
  ambiguous timeout would invalidate the evidence rather than improve reliability.
- Historical runs without the new provenance remain readable but cannot be compared
  or receive a keep, promote, or reject decision.
- A decision binds both candidate and optional baseline provenance digests plus an
  artifact-set digest over the exact summary, JSONL, and provenance files reviewed.
  Decisions are append-only in the run manifest; the latest still-verifiable decision
  is the current projection.
- Promotion requires a terminal `passed` Test Center run, every round passing, every
  stored round outcome matching its deterministic score, zero errors, and verified
  provenance. The advisory judge never affects this gate.
- The latest currently promoted run whose provenance and artifact-set digest still
  verify is the preferred comparison baseline. A later keep or reject decision
  supersedes that run's promoted status without deleting history.
- Chat-memory launch, evidence, comparison, artifacts, and decisions require admin
  authority because they expose the same full content governed by Prompt Center.

## Trust Boundary

The artifacts are content-addressed and treated as immutable by ADE. Independent
recalculation detects accidental drift, partial replacement, stale decisions, and
re-homing between run directories. This is not tamper-proof storage against an
actor who controls the local host, runtime directory, and application secrets. ADE
is a local-first development product; host compromise is outside this evidence
contract. A future multi-user or remote deployment must move the decision ledger
and signed evidence receipts to a transactional authority with a separately managed
signing key.

The current Test Center process executor and decision ledger are intentionally a
single-process local service. Horizontal API workers are not supported for this
filesystem-backed run store. Moving Test Center to multiple writers requires a
PostgreSQL ledger or an equivalent transactional compare-and-swap design first.

## Rejected Alternatives

### Compare Keys And Aliases Only

Stable names are convenient selectors but do not identify mutable content or model
deployments. They are retained for readability, not evidence identity.

### Let The LLM Judge Promote A Candidate

This would make the official decision non-reproducible and sensitive to judge-model
drift. Judge output remains advisory.

### Transparently Retry Workflow HTTP Requests

Retrying an agent-creation or message POST after an ambiguous timeout can duplicate
state and invalidate memory evidence. ADE retries must be explicit and enforced at
an idempotent product boundary.

### Call Self-Hashed Files Tamper-Proof

Adding an HMAC whose key lives in the same local host environment would overstate
the security boundary. The UI and documentation use “verified content-addressed”
for the implemented guarantee.

## Consequences And Guardrails

- Exact snapshots increase artifact size but make a decision independently
  understandable.
- A run whose provenance or deterministic evidence cannot be verified fails closed
  for comparison and decisions.
- Changing any execution-relevant catalog option changes its identity even when its
  display label or route alias does not.
- Do not add a transport retry around non-idempotent evaluation calls without first
  adding and testing a server-owned idempotency contract.
- Do not lower Test Center's authority while it returns full prompt or persona text.
- Do not describe content-addressed local evidence as protection from host control.
- Do not run multiple ADE API writers against the filesystem-backed Test Center
  ledger.
