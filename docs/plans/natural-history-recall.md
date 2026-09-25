# Natural Historical Recall: Bounded Design And Plan

Status: Proposed for review, 2026-09-25. No implementation, model calls, default
change, or release promotion is authorized by this document.
Source inspected: `3f688cb` on the retained `codex/character-continuity` branch.
Product authority: [PC-01 through PC-10](../product-contract.md).

This is the single follow-on plan for historical source recovery. The
[compact-reviewer plan](natural-memory-implementation.md) explicitly excludes
transcript search; its evidence and open reliability work remain intact. This
plan does not reopen its comparison or select a production context policy.

## Outcome And Diagnosis

Let Lin Xiaotang recall relevant shared dialogue across chats and ordinary persona
versions without memory commands, invented experiences, or repetitive callbacks.
An earlier interview-anxiety discussion should support a relevant later follow-up
without necessarily becoming a new profile fact or episode record.

The missing capability is historical source recovery, not a missing message store.
ADE persists immutable messages, definition roots/versions, summaries, fact
revisions and source links. `search_memory` retrieves fact projections, not
transcripts. Natural context recipes supply bounded local dialogue and facts,
with summaries depending on recipe/capacity. General historical recall is unproven.

Separate known problem: the reviewer has lost temporal scope and exhausted output
capacity in live diagnostics. Two low-effort reviewer-only contrasts succeeded,
but did not qualify a native default. History retrieval does not fix inaccurate
fact extraction. Do not change reviewer settings mid-comparison to hide failures.

## Proposed Read Contract

### Ownership And Eligibility

ADE binds workspace, subject, definition root and purpose from the accepted run.
Model arguments cannot choose them. Join a conversation's immutable definition
version to its root; do not compare persona text or require identical versions.
Both search and exact read enforce this boundary, including guessed identifiers.
Archived conversations are eligible without restoration (PC-10). Another
character's dialogue is not shared experience even when profile facts are shared.
Evaluation history stays isolated from product history and other fixture cases.
Old bindings may supply readable history without being permitted to execute.

Only committed exchanges visible to the attempt's read snapshot are eligible.
Exclude rejected candidates, in-flight runs and future fixture turns. Message
creation timestamps alone do not establish commit order; local sequence does not
order different conversations. For the probe, materialize a bounded corpus of
eligible exchange IDs, content and hashes in a short PostgreSQL read snapshot,
then close it before provider calls. Search and read use that frozen corpus.
This is an evaluation constraint, not a proposed all-history production scan.

### Past Reports Versus Current Facts

The following interpretation is proposed, not an already approved amendment:

| Evidence | Appropriate reply | Must not happen |
| --- | --- | --- |
| Old morning coffee; current morning tea | Tea is the latest preference; coffee was reported earlier. | Present old coffee as current. |
| A statement later invalidated as mistaken | Attribute it as an earlier disputed report if relevant. | Certify it as a true past fact. |
| An ended preference/relationship | Describe the supported ending. | Invent an opposite preference or continuous state. |
| Removed fact with retained source dialogue | A relevant historical quotation remains possible; removal is not transcript erasure. | Reactivate the chain or save it again from retrieval alone. |
| Habit without a supported profile fact | Recall reported behavior with its source scope/time. | Convert drinking tea into liking tea. |
| Old dialogue with no linked current fact | Attribute what was said and qualify unknown current status. | Treat a missing current fact as proof the old statement still holds. |

Where revision provenance links a source span to a fact chain, accompany the
source with current lifecycle annotations. Include eligible current descriptors;
do not fetch forgotten revision values as model context. A retained transcript
is a distinct source. If essential annotations cannot fit, omit the source window
rather than show unqualified old text. These annotations are not write targets.

Not all dialogue has fact links; later corrections may use different wording.
Do not invent semantic linkage with regexes, keyword tables or another model call.
Supply chronological context and current lifecycle information, and measure the
reviewer's interpretation. Missing linkage means unknown status, not currency.
Historical truth repair and suppression of removed topics are not promised.
A fresh explicit current statement can still support a new fact under PC-07.

### Small Read Interface

Prototype internal operations, not generic public CRUD:

- `search_history(query, limit)`: ranked source-window references with role-labelled
  previews, source conversation/time, coverage and lifecycle annotations.
- `read_history(reference)`: the exact bounded contiguous exchange window.
  References must come from this attempt's search, not arbitrary database IDs.

Search previews are model-visible evidence too: apply the same annotation,
attribution and reviewer-visibility rules to them. Use whole exchanges; return
explicit oversized/omitted status instead of excerpts that hide negation or a
correction. Preserve verbatim text and roles; historical instructions are source
data, never system authority. Summaries may locate ranges, not replace exact
readback. No new summary-generation call is required.

Compare a simple literal-search baseline with semantic ranking using the existing
embedding route/space over the same bounded corpus. Mandarin paraphrase fixtures
decide adequacy; literal/full-text matching is not semantic retrieval. Select one
ranking implementation before comparing retrieval triggers. No permanent generic
ranking framework, hybrid service or production indexing migration is assumed.

### Retrieval Trigger Comparison

Freeze one natural-context recipe, reviewer configuration, routes, corpus and
ranking implementation. Preserve its lifecycle-overflow rules: if that recipe
withholds history, the extension cannot bypass the restriction. Report a capacity
failure rather than silently enlarging context.

| Arm | Behavior | Trade-off |
| --- | --- | --- |
| Baseline | Existing facts/local context, no historical recovery. | Establishes whether recovery helps. |
| Automatic | One search from the current message and bounded local context; read selected results before generation. | Supports spontaneous recall but may distract. |
| Discretionary | Model can search/read via curated tools, without phrase-based forcing. | Targeted recovery, but search may be omitted or poorly queried. |

Both retrieval arms share the same source store and maximum history allowance.
Actual passages may differ; retain them. Measure generation/review/embedding
dispatch counts, tool steps, context/output sizes and latency. Do not equalize
request counts artificially or reroll an arm. A combined production design is
not selected in advance. User dialogue should not need explicit search commands.

### One Reviewer, No New Write Authority

Keep mandatory prompt/persona/current turn, required lifecycle information and
existing local evidence ahead of optional history. Preflight actual serialized
generator and reviewer packets with output reserves. Tool continuations share
the cumulative history allowance, not a fresh allowance per call.

Give the generator and existing single reviewer identical model-visible history
with request-local `H` references, separate from writable `U`/`A` support and held
`F`/`E` targets. Retrieved history cannot become a current anchor, earlier write
support, or a fourth evidence mode. No background catch-up extraction.

Propose one narrow conflict-schema extension: exact candidate quotes may reference
held `H` source spans for reply review only. ADE binds handle, role, hash and quote;
the reviewer judges meaning. `H` references never authorize mutations. Grounded
conflict retains atomic rejection; lack of conflict is not semantic proof.
This requires an explicit ADR amendment and immutable evaluation policy binding,
not silent rebinding of existing definitions, fixtures or release fingerprints.

### Failure And Concurrency Semantics

Empty search is a successful empty result, not proof that no relevant history
exists. Proposed optional-read behavior: ordinary search unavailability before
delivery is nonfatal, recorded as unavailable, allowing existing-context response
or a natural clarification. It does not weaken mandatory retrieval/review failures.

Scope/hash mismatch or an inconsistent required evidence packet fails the attempt.
Cancellation/deadline abort normally; no extra retry, fallback or repair. Revalidate
source existence before delivery: a source purged since snapshot must not be served
from stale captured text. Archive changes alone do not change eligibility. Keep
existing subject-generation fencing for concurrent fact changes, not a second lock
scheme. Preserve supplied-source identity without claiming exhaustive latest history.

## Ordered Checkpoints

### H1: Freeze Contract And Baseline

After design approval, amend ADRs and bind the isolated policy. Freeze case outcomes,
packet capacities, ranking-test inputs and reviewer settings before calls. First
run a short native fact-only sequence for scope, correction, habit/no-write and
isolation. Separate any reviewer failure from historical-retrieval work. A low-effort
setting or A/A0/B recipe does not become a product default through this prerequisite.

### H2: Read Repository And Ranking Feasibility

Add one cohesive history-read module using existing persistence. Verify real
PostgreSQL scope boundaries, snapshots, archive/persona-version behavior, exact
reads, source purge, annotations and future-turn exclusion. Compare literal and
semantic ranking; retain source-hit results. If neither finds needed paraphrases,
stop before runtime integration and report the retrieval gap, not a dialogue failure.

### H3: Isolated Runtime Integration

Add evaluation-only automatic/discretionary paths sharing that reader. Extend
curated-tool allowlists for the isolated binding, not Agent Studio defaults. Add
read-only `H` review/conflict support and actual packet preflight. Fake-provider
and committed PostgreSQL tests cover rejected write references, atomic rejection,
capacity, retries, cancellation, stale generations and optional-read unavailability.
Test historical instruction text as attributed data, not an executable instruction;
search previews must not leak a source that exact read would reject.

### H4: Natural Dialogue Comparison

Run three arms from independently seeded equivalent state, chronologically.
Never retain future turns first or seed one arm from another's outputs. Distinguish
failed setup from scored probes. Record failures and unrun work; no midrun scorer,
prompt or parameter changes. Keep observational counts, not spending gates.

Required cases: distant same-character recall; persona-version update; archived
source; another character with shared facts; another subject/workspace; scoped
correction; invalidated report; ended state; operator removal with retained source;
habit versus preference; resolved concern; and ambiguous/unrelated dialogue where
a callback is inappropriate. Include paraphrases, long-history distractors and
user statements versus assistant suggestions. Add a fresh-restatement case distinct
from retrieval-only resurrection of a removed fact.

Score retrieval and dialogue separately. Deterministic checks cover scope, source
integrity, deltas and limits. Blind arm labels for human review of relevance, time,
scope, attribution and repetition; preserve quotes and disagreements. A model judge
is optional/advisory. Do not require a tool call when supplied context suffices.

### H5: Decision, Not Automatic Rollout

Recommend an arm only when history-dependent replies improve over baseline without
cross-boundary evidence, unauthorized writes, stale-current assertions or unacceptable
distraction/latency. Report every case, not just an aggregate. Small samples establish
feasibility, not population reliability. If neither helps, retain baseline and identify
the bottleneck; do not add episodes or combine arms to hide an inconclusive result.
Ties favor less code and fewer round trips. Once a winner is approved, remove losing
executable prototype paths while preserving fixtures and findings.

Production delivery requires a subsequent reviewed decision on indexing/backfill,
scale and freshness, exact source UI readback, defaults/bindings, and qualification.
This probe does not close M3/M4, promote release evidence or authorize deployment.

## Owners, Checks And Exclusions

- `services/ade-api/src/ade_api/features/agent_runtime/persistence/`: source reads,
  definition roots, provenance and the new cohesive reader.
- `agent_runtime/natural_context.py`, `turn_execution.py`, `executor.py`: context
  and curated reads. Split touched oversized responsibilities rather than adding
  to monoliths or creating a generic retrieval framework.
- `agent_runtime/natural_memory_reviewer.py`, `natural_memory_binding.py`,
  `natural_memory_review.py`: distinct read-only evidence and conflict schema.
- `workflows/evals/character_memory_dev/`: one chronological workflow, fixtures,
  settings and ignored captures; reuse native diagnostics, not a parallel harness.
- `services/ade-api/tests/agent_runtime/`: structural, protocol and PostgreSQL tests.

Run focused checks, full Python tests, Ruff/changed-file formatting and OpenAPI drift.
Run web tests/build if shared types or UI change; no new UI is needed for this probe.
If storage changes become necessary, test populated and fresh migrations before
proceeding. Keep the known release-freshness failure unwaived. No provider shopping,
global budget controls, new memory service, episode store, writable notebook, second
reviewer, privacy subsystem, semantic phrase rules, or unrelated refactoring.

## Review Before Implementation

The removal/history interpretation, optional-read failure policy and `H` conflict
extension above are proposed choices, not settled product amendments. Scrutinize
them before approval. Character scope and archive eligibility are already agreed.
