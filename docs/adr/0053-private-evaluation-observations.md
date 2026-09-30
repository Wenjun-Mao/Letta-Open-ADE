# ADR 0053: Private Isolated Evaluation Observations

Status: Accepted for offline readiness, 2026-09-30. No live authorization.
Applies to PC-01/03/04/05/09/10/11; changes no product memory semantics.

## Problem

Capture v1 retains terminal revision IDs/generation, not independent full state.
The public memory response omits orphan entities. The historical reader already
counts content, annotation and bounded-capacity omissions, but selection capture
drops them. Thus zero fact delta or reviewer approval cannot prove a character
story left user memory unchanged, or explain why a known source was not admitted.
The previous complete-state helper existed only in tests.

## Decision

Keep capture `schema_version: 1` and its existing fields/meanings. Add the optional
`private_observations` extension with named contract
`ade-private-evaluation-observations-v1`. Historical consumers need not require
it; the new PC-11 validator must. Never reinterpret/rebind old artifact hashes or
infer the extension from public projections. No public endpoint, memory schema,
retrieval recipe, source scope, prompt or reviewer mandate changes.

The runtime reads the before snapshot inside `load_turn_state`'s accepted-generation
repeatable-read transaction, alongside mandatory memory and bounded history. A
separate repeatable-read transaction after worker finalization reads terminal
state and the after snapshot coherently. Neither snapshot comes from reviewer
proposals or model output. The extension binds run, attempt, conversation,
immutable definition version, policy, workspace/subject/purpose/character root and
accepted generation. Canonical UTF-8 JSON uses sorted keys and compact separators;
SHA-256 seals cover each complete snapshot and the entire extension, excluding
only that object's `sha256` field. Timestamps use ISO 8601. This detects accidental
corruption/rebinding, not a malicious party rewriting an unsigned artifact.

State contains every persisted column/row in subject-scoped facts (all lifecycle
states), entities (including orphans), revisions, revision source links and
predecessor edges, plus subject generation. Facts remain shared across character
roots; only history is root-scoped. This is complete coverage of those components,
not a database dump or embedding-vector export. Only those allowlisted tables
are serialized; no auth, provider wire bodies, private reasoning or exceptions.

Each snapshot also retains bounded same-subject run identities/statuses, attempt
counts and lifecycle timestamps, with no dialogue text. Other active runs or
changed run inventories, attempt mismatch, generation mismatch, missing rows or
incomplete observations cannot qualify as isolated evidence. Exclusive ownership
of the fresh evaluation database remains an operational prerequisite; these
observations do not claim to detect arbitrary out-of-band writes later undone.

The reader inventory's explicitly named universe is `scoped_completed_pairs`,
using unchanged eligibility predicates. At most 128 candidates plus one overflow
sentinel are observed; `capacity_at_least` remains a lower bound, never a complete
inventory. Known candidates retain content/annotation/reader-capacity reasons.
Selection adds admitted, top-k, packet-capacity, selector-not-selected and
purged-before-exposure reasons. Empty-history arms are `not_read`, not complete;
reader failures are unavailable. No extra cross-user/history query is allowed.
PC-11 compares the inventory against its independent prior-source ledger; known
foreign-scope and unsuccessful sources are labeled exclusions from that ledger,
not discovered by broadening runtime access.

Capture keeps the existing explicit `ADE_NATURAL_MEMORY_CAPTURE=1`, development,
evaluation-purpose and loopback isolated-test-database gates. Disabled capture
performs no additional queries or provider calls. Snapshots are bounded to 512
rows per component/activity list and 600,000 serialized bytes; exceeding a bound
returns `truncated`, not partial full state. SQL/serialization errors return
`unavailable` without raw details; savepoints protect the mandatory turn snapshot.
The whole artifact remains capped at 2,000,000 bytes and written atomically with
private file permissions. Retention failure never changes authoritative run
outcome. PC-11 must stop qualification on missing/truncated/mismatched evidence,
even when a turn succeeded, and requires equal full before/after state for pure
story controls and rejected candidates.

## Alternatives And Guardrails

Reject projection-only equality, reviewer approval, test-only DB access and a new
public history API as substitutes. Raising reader bounds or admitting omitted
sources would alter the experiment rather than observe it. A top-level capture
version bump would unnecessarily invalidate historical consumers; the new named
extension gives PC-11 a strict opt-in requirement without relaxing old contracts.

Portable tests reject missing, corrupt, stale, concurrent and incomplete evidence.
Fresh PostgreSQL tests cover nonfact/orphan and lineage rows, scope exclusions,
same-RR coherence, independent after reads, failed-candidate equality, SQL failures,
row/byte/artifact limits and identical disabled-capture SQL/provider dispatches.
The full story sequence also verifies ADR 0051 HTTP version creation and ADR 0052's
parsed catalog. Preparation separately records governed-source fingerprint v2
(including router/shared-parser/platform/migrations) and model-profile hash.
Static readiness is not a live catalog receipt, model-quality result or release.
