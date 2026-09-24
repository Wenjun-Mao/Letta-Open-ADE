# Natural Memory: Bounded Implementation Plan

Status: revision 4, proposed for Pro review on 2026-09-24. Planning only.
This revision is not implementation, live-call, deployment, or release approval.
It replaces the next-work instructions in revision 3, not its historical evidence.
Source inspected: `aea2719c1e2310d0c5c1a10b9fe75c0d0e3c14e5`.
[Previous plan and completed checkpoints](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/aea2719c1e2310d0c5c1a10b9fe75c0d0e3c14e5/docs/plans/natural-memory-implementation.md).
[Reviewer-interface assessment](../findings/natural-memory-consultation/reviewer-interface-assessment.md)
links the unchanged independent reports. This is the single active plan for this
natural-memory scope; do not create a competing implementation plan.

## Outcome And Boundaries

Make the native reviewer reliably express supported natural updates without asking
it to reproduce persistence metadata. Keep ADE's PostgreSQL foundation, immutable
messages, typed lifecycle, explicit subjects, snapshot/version fencing, exact
provenance, curated tools, cancellation/leases, and synchronous atomic finalization.

The current sequence remains: generate candidate, obtain one review, bind and
validate, atomically commit reply and effective memory mutations. A legitimate
no-change/defer can deliver a checked candidate without a memory-generation advance.
Invalid/incomplete review or a grounded contradiction delivers neither candidate
nor memory. No automatic repair, fallback, background catch-up, or partial salvage.

Replace monetary/request-budget enforcement with simple observational counts.
Keep context/input/output limits, timeouts, cancellation, explicit retries, and
finite tool-loop execution. These serve correctness rather than cost control.

Out of scope: replacement memory service/framework, general schema compiler,
graph/event memory, historical transcript search, two-reviewer stages, changed
call ordering, degraded reply delivery, provider/model shopping, production
cutover, policy winner, legacy importer, broad refactoring, and new billing UI.

## What The Evidence Establishes

Revision-3 offline mechanics passed, but the original live comparison stopped
after its first mutation. Three subsequent, separately versioned diagnostics
showed scoped coffee/tea successes, one output truncation, invalid historical
authority citation, and recurrence of invalid subject selection. They establish
neither an A/B result nor a failure-rate estimate.

Director offline reproduction confirmed that a bare current "Roxy" plus an
assistant "Is Roxy a Husky?" can prepare a breed operation through the current
binder. It also confirmed that an empty object parses as no-change. No database
write/provider call was needed for these reproductions. Fix these boundaries
before another live diagnostic; stronger prompt wording alone is insufficient.

The 4,096-output diagnostic progressed beyond a 1,024-token truncation, but is
not a production default or a proven universally sufficient output allowance.

## Proposed Reviewer Contract

### Input And Snapshot Ownership

Build one immutable request-local binding map from the accepted run snapshot.
Use separate sections, with bounded complete-message context:

- Current user: the sole current write-authority message, with full text.
- Context: admitted prior conversation messages; not freely citable authority.
- Eligible support: local handles to earlier user assertions or assistant
  propositions in the same admitted clarification suffix.
- Targets: handles to active/inactive facts with truthful lifecycle descriptors.
- Related identities: handles derived from eligible identity facts, not raw
  entity labels. Subject identity is implicit and never an offered choice.
- Candidate reply: reference-only text for the consistency decision.

Reuse the existing shared, complete-message suffix and current lifecycle view.
No extra retrieval, larger historical window, hidden source, or summary/tool
authority. Forgotten facts/identity descriptors never enter target/identity maps.
Retained historical dialogue remains attributed history under the existing
limited-removal contract; removing a saved fact does not erase prior messages.

Handles such as F1, E1, U1, A1 are local to this exact request. They resolve only
against its held map, not current database state fetched after review. Record the
map with opt-in evidence so the decision remains explainable. The final write
still checks accepted generation and original target versions transactionally.
Unknown, wrong-kind, foreign, ambiguous, and stale references fail; no remapping.

Do not use a model call to preselect support handles. The server supplies bounded
eligible messages by known role/chronology; the reviewer chooses their semantic
relationship. Merely including a handle does not certify an assertion or consent.

### Output Shape

Require a top-level object with a required `decisions` array, maximum 20 items,
and forbid unknown fields throughout. `{"decisions":[]}` is explicit no-change;
`{}`, missing arrays, null, and truncated content are not.

Use one discriminated list, not parallel proposals/dispositions joined by IDs:

| Item | Model-owned fields | Server-owned fields omitted from output |
| --- | --- | --- |
| Subject add | Fact type, supported scoped value, registry qualifier, evidence | Subject/entity selector, IDs, versions, source roles |
| Related add | Fact type, value, qualifier, offered entity handle or local new-entity reference, evidence | Persistent IDs, independent entity label |
| Revise/end/reassert/forget | Target handle, operation and existing closed reason/value rules, evidence | Fact ID, expected version, entity identity |
| Defer | Current exact quote, reason: unresolved/uncertain/nonasserted/no-save | Guessed entity, target, value, executable mutation |
| Conflict | Grounded interpretation/evidence and exact candidate-reply quote | Mandatory executable write |

Keep existing lifecycle meanings: correct versus supersede, inactive versus
forgotten, and fresh add after forgetting. Reassert cannot revive a forgotten
chain. No-save is not a new deletion operation.

Related new entities use a local reference only where needed to join identity
and dependent facts. An accepted identity assertion (for example pet.name)
creates it; derive its label from that assertion. Unresolved/deferred identities
cannot leave entities or embeddings behind. Same-name pets are not auto-merged.
Subject-add variants have no entity field in the actual generated schema,
including schema embedded in DeepSeek JSON-object instructions.

These are new wire shapes compiled deterministically to ADE-owned mutation
records, not tolerant parsing of old proposals. Use existing typed domain objects
where suitable. No dual live parser, generic adapter framework, or schema compiler.
Keep semantic value/scope interpretation with the model; removing clerical fields
cannot prove that it preserved morning/evening, frequency, condition, or negation.

### Evidence Modes

Every item requiring authority has one exact, nonempty current-message anchor.
The model never emits a message UUID, source-role enum, offsets, hash, or duplicated
evidence_quote. Derive them from the chosen mode and held map.

| Mode | Additional selectable support | Meaning |
| --- | --- | --- |
| Direct | None | Current user's own assertion/correction/removal supplies the claim; a targeted prior fact identifies what changes, not new authority |
| Resolve-user | Earlier-user handle and exact quote, plus any intervening clarification context handle needed to identify the question | Current answer completes an earlier user's assertion; earlier support is not independent write authority |
| Endorse-assistant | Prior assistant proposition handle/quote | Explicit current assent endorses that particular proposition, not all assistant text |

Quotes must match one exact span in the selected message; ambiguous duplicates,
missing quotes, out-of-bundle handles, and role/chronology mismatches fail.
Do not implement fuzzy repair or choose an arbitrary duplicate occurrence.

Direct mode cannot use assistant text as factual support. Resolve-user requires
a real earlier user assertion and a current answer tied to that unresolved claim;
it cannot extract unrelated historical facts. Endorse-assistant requires locally
affirmative assent tied to the proposition and rejects negated/quoted/hypothetical
assent and bare names. The model's mode label is not itself proof of endorsement.

Required contrast: earlier user says "one dog is a Husky", assistant asks "Rocky
or Roxy?", user says "Roxy": allow bounded user-antecedent resolution. Assistant
alone asks "Is Roxy a Husky?", user says "Roxy": do not save breed. Explicit
"Yes, Roxy is a Husky" can authorize it. Ambiguous multi-proposition "yes" defers.

Use the existing affirmative/uncertainty helpers where their semantics fit and
add narrow negative tests, not a broad yes-word heuristic. Some interpretation
remains semantic; exact citation matching is necessary, not sufficient for truth.
If the implementation cannot enforce these distinctions without inventing a new
semantic model stage, stop for review rather than claiming the mode tag solves it.

Persist current authority and supporting provenance distinctly. Propose adding
`user_resolution` (current anchor) and `user_antecedent` (support-only) to the
existing source-role contract. Keep `user_assertion`, `user_endorsement`, and
`assistant_referent`. Update DB check constraints, readback verification, presenters,
API schema and UI role display together; do not relabel old evidence. Assistant
context in a resolution is not licensed to add assistant-origin facts.

### Dispositions And Atomicity

Validate output shape and exact evidence bindings first. Defer/conflict do not
pass through executable-mutation entity/value requirements. Complete writes do.
Do not transform an invalid write into a defer, silently drop sources, or salvage
valid siblings from malformed output.

No-save applies at claim scope and dominates equivalent writes in either order.
A no-save item carries its exact current scope, not a invented target. Retain
the independent native no-save check on every proposed write; a defer declaration
cannot hide a contradictory sibling. Clear removal of an existing fact requires
an authorized forget operation; "do not save this" does not by itself delete it.
Unrelated supported writes survive legitimate deferrals.

A grounded conflict can exist without a new write. Require the current claim/
permitted support and a uniquely bound conflicting candidate span; an unrelated
question is not conflict. A validated conflict vetoes the whole attempt. Semantic
contradiction remains reviewer judgment subject to fixtures, not string matching.

After filtering genuine deferrals, derive the effective write set and dependent
new entities/embeddings once. All-deferred/no-change must not create entities,
write embeddings, or advance memory generation. Query embeddings for retrieval,
if already used, are not mutation embeddings and must be reported separately.

### Completion And Failure Classes

Check provider completion status before parsing: `length` cannot be accepted even
if partial JSON parses. Distinguish truncation, refusal/unsupported finish,
malformed JSON/schema, invalid handle/source, semantic rejection/conflict,
embedding failure, and finalization failure in existing typed run events/errors.
No guessed success for an absent status; establish supported adapter fixtures.

Preserve timeout/cancellation and exact retry behavior. Reviewer repair remains
zero for this diagnostic. Retain candidate and decision evidence without secrets
or private reasoning; report committed/rejected/unconfirmed separately. Do not
allow a telemetry/capture failure to rewrite an authoritative commit outcome.

## Counter-Only Accounting

Delete `request_budget.py` cap/reservation/limit-binding functionality rather
than leave dormant budget aliases. Remove associated settings/environment flags,
worker-readiness budget identity, Compose wiring, per-scope spending allocations,
CLI cap flags, `exhausted()` checks and budget-triggered scheduling branches from
active workflows. Preserve other failure/stop conditions.

Reuse `provider_tracing.py` request IDs and start/completion/failure events as
the normal-run source of counts. Cover setup/indexing, query/write embeddings,
generation, reviewer, compactor and tool continuations in workflow summaries.
Count once at the shared outbound ADE-to-router dispatch boundary, not again in
nested stage/capture wrappers. Catalog discovery is separate from model usage.
Use stable request IDs to aggregate API/worker events without shared in-memory
counters or a new accounting database/service.

Report attempted, completed, failed, and unresolved counts by kind/model/stage
and run/iteration. These are ADE outbound attempts, not provider billing or a
guarantee of network receipt. Timeouts may have reached the provider; do not
record them as zero. Surface expected versus observed counts as diagnostics,
never a spending veto or a reason to silently omit remaining cases.

For workflow setup outside a run, use the same small event shape in its existing
artifact writer. If process death/capture loss makes coverage incomplete, label
counts incomplete/unknown; never manufacture zero or claim exact billing.
Ordinary telemetry failure must not prevent a product request or alter its result.
An evaluation may remain unscorable because evidence is missing, distinct from
a monetary stop. Do not build durable pre-request reservations again.

Keep existing historical ledgers/frozen files byte-for-byte. Active commands stop
enforcing old monetary schedules; docs mark those schedules historical. Remove
active imports/validation of old caps, while retained fixtures still specify their
semantic cases. Current context/iteration/tool-call bounds remain explicit.
Do not silently remove the 180-second timeout clamp formerly embedded in the
budget wrapper: locate intended timeout ownership and preserve each documented
runtime/diagnostic timeout at that layer, with regression tests.

## Implementation Checkpoints After Approval

Default serial work on the retained implementation branch, with reviewable commits.
No concurrent writers or broad parallel rewrite.

### 1. Freeze New Contracts And Failing Regressions

Amend the existing design and write one concise proposed ADR for this interface,
source-role extension and counter-only direction; mark accepted only with actual
implementation approval. Supersede relevant model-facing parts of ADRs 0029,
0032 and 0034 explicitly; preserve their history. ADRs 0031/0033 describe prior
capacity experiments, not proof for the new envelope.

Freeze input/output examples and negative cases before code. Reproduce bare-name
assistant support, missing-shape no-op, genuine unresolved deferral, subject UUID
selection, stale/cross-subject handles and time-scoped correction. Separate
mechanical checks from semantic accuracy claims. Exit: reviewers can trace each
decision field to model work or server binding; no unresolved authority shortcut.

### 2. Remove Spending Gates, Retain Observation

Refactor the shared transport factory and active acceptance/development runners
to event-based counts; delete cap-specific settings/readiness/tests. Retain
transport, route validation, exact retries, timeouts and behavioral stops.
Exit: fake transport tests cover failed sends, continuations, retries, setup and
API/worker aggregation with no double counts; exceeding an expected count does
not block a request. Missing telemetry is explicit and does not veto product work.

### 3. Implement Compact Review And Provenance

Implement discriminated decisions and request-local binding, safe identity views,
three evidence modes, genuine no-write outcomes, strict completion handling and
effective-set preparation. Thread exact output allowance through existing request
construction/preflight without changing other generation behavior. Use cohesive
modules, preferably below 400 lines; split responsibilities before adding to
files over 500 lines. No general policy engine.

Add a forward migration for provenance-role constraints only if needed by the
final typed contract; update readers/UI/OpenAPI in the same checkpoint. Test
fresh and existing disposable DB migrations non-destructively. Existing messages,
facts/revisions and receipts must remain readable unchanged.

Use a new immutable reviewer/policy binding for new semantics. Old conversations
remain readable, with unsupported fresh sends rejected rather than silently
switching their reviewer contract. Preserve idempotent terminal replay. Do not
retain an old model-facing parser just to keep obsolete diagnostics executable;
historical fixtures remain inspectable and active runners target the new contract.
Exit: isolated PostgreSQL tests verify exact provenance, sibling deferral,
no-save ordering, stale-snapshot rejection, effective writes and atomic outcomes.

### 4. Integration And Offline Acceptance

Run the smallest tests first, then full Python, Ruff, changed-file formatting,
OpenAPI drift, web tests/lint/build and Compose rendering. Supply both disposable
database URLs, explain skips, and keep the known release-policy freshness failure
unwaived; no additional failure may hide behind it.

Exercise real isolated API/worker/PostgreSQL and built-in browser with a fake
provider: new session, scoped add/correction, user-antecedent clarification,
endorsement rejection, removal, archived citation, old-policy read-only behavior,
and displayed source roles/counts where already exposed. Do not add a new metrics
page. Preserve cancellation, lease-loss, precommit/postcommit fault and lost-ack
tests. Confirm byte-identical preservation of historical ledgers/fixtures.
Exit: evidence demonstrates mechanisms, not live model reliability.

### 5. Proposed Live Diagnostic, Separately Authorized

Freeze one source/interface revision, the same DeepSeek route/high-thinking
setting, Qwen embeddings and a named output envelope. Proposed reviewer output
allowance: 4,096 tokens; exact admitted input bound and envelope must be recomputed
from the new serialized request before approval. Do not truncate required evidence
to retain obsolete numeric totals. Mark any pressure point adjustment explicitly;
the old padded A/B results cannot be transferred to the new schema.

Proposed fixed diagnostic: three subject-add trials with distinct predeclared
contexts; chronological scoped tea and typo correction; related-entity creation;
user-antecedent clarification; positive and bare-name negative endorsement;
genuine unresolved deferral beside an independent update; same-turn no-save;
explicit removal followed by fresh restatement. Publish exact case counts/order,
source-linked setup, expected state and permitted reply claims before execution.

No financial request caps or reservation ledgers. Use counters and a fixed finite
case list, timeout and tool-loop bounds. Repetitions are scheduled observations,
not retries to erase failures. Stop for isolation/provenance/atomicity breach,
required state failure, invalid infrastructure/evidence, or lost authorization.
Preserve semantic-equivalent wording for explicit source review rather than
changing the scorer mid-run. No auto-repair or fourth patch loop.

Report useful replies and correct committed outcomes over scheduled and attempted
cases, plus rejected/unrun counts and exact evidence limits. Passing diagnostics
permit proposing a newly frozen A/A0/B comparison, not policy adoption or release.
If mechanical errors decline but semantic errors persist, bring the findings back
for model/task-shape review rather than more metadata or permissive validation.

## Release Boundary And Pro Review Questions

No merge/push/deployment/promotion, source-fingerprint rebind, or production data
change is part of writing or reviewing this plan. Publication is a separate
review checkpoint. Eventual release still requires fresh evidence, approved
policy/envelope, matched builds and non-destructive migration/recovery checks.

Ask the Pros to scrutinize: whether three evidence modes truly separate authority
from support; whether current/antecedent roles are sufficient without semantic
loopholes; whether write/defer/conflict shapes preserve no-save and contradiction
behavior; whether identity maps leak forgotten facts; whether counter aggregation
is honest without recreating budget infrastructure; and whether the new diagnostic
can falsify the intended improvement without weakening the original product goal.
