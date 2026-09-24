# Natural Memory: Bounded Implementation Plan

Status: revision 5 plan with an offline reviewer/ADE amendment implemented on
2026-09-24. This document grants no live-call, deployment, or release approval.
It replaces the next-work instructions in revision 3, not its historical evidence.
Source inspected: `aea2719c1e2310d0c5c1a10b9fe75c0d0e3c14e5`.
[Previous plan and completed checkpoints](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/aea2719c1e2310d0c5c1a10b9fe75c0d0e3c14e5/docs/plans/natural-memory-implementation.md).
[Reviewer-interface assessment](../findings/natural-memory-consultation/reviewer-interface-assessment.md)
links the unchanged independent reports. This is the single active plan for this
natural-memory scope; do not create a competing implementation plan.
Revision 5 incorporates the [compact-plan review assessment](../findings/natural-memory-consultation/compact-plan-review-assessment.md):
inherited restrictions, operation-specific assent, read-only conflict grounding,
canonical non-vetoing request observations, and complete-delta acceptance.
The amendment below supersedes its semantic restriction and assent clauses.

## Reviewer/ADE Responsibility Amendment (2026-09-24)

The user directed removal of conversational privacy-policy features and
phrase-specific semantic regex fixes from the active natural-memory path. This
supersedes the privacy and semantic-authority clauses of revision 5 and ADR 0035.
The provisional Mandarin omitted-object prototype is discarded. Historical
fixtures and observations remain evidence of the earlier contract, not current
acceptance tests. This amendment authorizes offline implementation only.

ADE guarantees the closed wire shape, exact current/support quote binding,
role and chronology eligibility, held subject/target/identity handles, source
integrity, target version and generation fencing, and all-or-nothing persistence.
The single reviewer judges factual assertion, negation, temporal scope,
correction, requested factual lifecycle operation and reply contradiction.
Exact provenance proves where words came from; it does not prove entailment.
Explicit operator fact removal remains available. There is no conversational
privacy/no-save/consent subsystem or phrase-matching permission gate.

### Implementation Boundary

Remove `natural_memory_authority.py` and its natural-path call, `no_save` from
the natural review wire shape and preparation, semantic equivalence vetoes in
conflict handling, and privacy/consent commands in the reviewer prompt. Retain
the structural binders, schema and entity checks, factual lifecycle status
checks, source and version revalidation, and atomic commit. Syntactic handle
regexes remain. New natural sessions use the v4 binding; v3 definitions remain
readable but cannot execute new turns. The reachable default typed reviewer
also uses one mixed
operation schema and structural preparation. Its former phrase-selected schemas
and `memory_intent.py` rules are removed; new definitions bind
`typed-user-facts-v2`, while v1 remains readable and replayable but cannot run
new turns. Frozen historical campaign data is not rewritten. The fact registry
remains unchanged: `person.preference` means a
preference, not a report of drinking behavior. Durable habit recall requires a
separate typed-schema decision.

[ADR 0036](../adr/0036-discretionary-curated-tools-and-structured-requirements.md)
also removes phrase-based mandatory tool selection from the turn dispatcher.
Enabled curated tools remain discretionary with result and argument checks;
direct callers can still supply a structured requirement. Existing evaluation
cases continue to fail when an expected discretionary tool call is absent.

### Factual Evaluation Deltas

Start with one active `person.preference` drink fact F1, `prefers coffee in the
morning`, version 1 and subject generation G. `∅` means zero
fact/entity/revision/write-embedding changes and no generation advance.
A valid nonempty atomic review advances generation once; a rejected review
commits neither candidate reply nor mutation. These rows are reviewer
evaluation expectations, not deterministic semantic guarantees.

| Preceding sequence and current turn | Complete delta and reply boundary | Forbidden extra delta |
| --- | --- | --- |
| F1; `最近喝咖啡总睡不着，早上也改喝茶了` | ∅ under the current registry. Reply may use the current drinking habit; same-conversation follow-up may use dialogue. Cross-conversation habit recall is not guaranteed. | Revise F1 to liking tea; invent all-day dislike |
| F1; `现在早上更喜欢茶了` | Revise F1 to active v2 `prefers tea in the morning`, reason supersede; G→G+1, one revision. | All-day tea, extra preference, lost v1 history |
| After that revision, new conversation asks `我早上现在更喜欢喝什么？` | ∅; answer morning tea from active preference; generation stays G+1. | Rewrite memory or claim all-day preference |
| F1; `早上还是更喜欢咖啡，晚上更喜欢茶了` | Keep F1; add one evening-tea preference v1, G→G+1. | Change morning coffee or add all-day tea |
| F1; `可能早上更喜欢茶吧` | ∅; reply may discuss uncertainty. | Definite tea revision |
| F1; `早上不喜欢咖啡了` | End F1 inactive v2, reason ended, G→G+1. | Forget history or invent tea |
| F1 active v2 morning tea; `不对，我说的是晚上更喜欢茶，早上仍喜欢咖啡` | Revise still-active F1 to morning coffee v3, reason correct; add evening tea v1; G+1→G+2 atomically. | Revive ended/forgotten F1 or erase v1/v2 |

The correction row applies only to the still-active target. An ended target needs
its own factual lifecycle decision; a forgotten chain cannot be reasserted.
Do not convert `喝茶` into `喜欢茶` to make a fixture pass.

### Verification Gate

Use paired semantic evaluation cases for wrong scope, unsupported value,
negation, correction and false conflict; these measure the reviewer and must
not be relabeled as ADE guarantees. Unit and isolated PostgreSQL tests verify
shape, provenance, versions, held handles and atomic deltas, including invalid
siblings in both orders. Scripted browser/router tests verify integration only.
Later authorized live diagnostics must measure natural meaning, answer
usefulness and recall; fake choices cannot qualify that behavior. Keep the
known policy-fingerprint freshness failure unwaived.

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
- Eligible support: local handles to earlier user assertions/requests or assistant
  propositions/action requests in the same admitted clarification suffix.
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
Serialize each complete message once; context/support sections reference that
message by handle and role eligibility rather than duplicate its full text.

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
| Conflict | Current claim or query/context, permitted support or read-only snapshot handles, exact candidate-reply quote | Mandatory executable write or invented assertion |

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
| Resolve-user | Earlier-user handle and exact quote, plus intervening clarification context if needed | Current answer completes an earlier user's assertion or explicit lifecycle request; earlier support is not independent authority |
| Endorse-assistant | Prior assistant proposition/action-request handle and quote | Explicit current assent endorses that particular factual proposition or action, not all assistant text |

Quotes must match one exact span in the selected message; ambiguous duplicates,
missing quotes, out-of-bundle handles, and role/chronology mismatches fail.
Do not implement fuzzy repair or choose an arbitrary duplicate occurrence.

Direct mode cannot use assistant text as factual support. Resolve-user requires
a real earlier user assertion/request and a current answer tied to its unresolved
part; it cannot extract unrelated historical facts. Endorse-assistant requires locally
affirmative assent tied to the proposition and rejects negated/quoted/hypothetical
assent and bare names. The model's mode label is not itself proof of endorsement.

Required contrast: earlier user says "one dog is a Husky", assistant asks "Rocky
or Roxy?", user says "Roxy": allow bounded user-antecedent resolution. Assistant
alone asks "Is Roxy a Husky?", user says "Roxy": do not save breed. A clear short
"Yes" to that single proposition can authorize it; test this separately from the
self-contained "Yes, Roxy is a Husky". Ambiguous multi-proposition "yes" defers.
Inject the bare-name attempted write under every mode: switching mode must not
provide an escape. Never pool all bound quotes as interchangeable value support;
only that mode's permitted factual sources may contribute factual properties.

Resolution completes only the missing part. It retains uncertainty, quoted or
fictional framing, conditions and no-save restrictions attached to the antecedent.
Eligibility considers the admitted surrounding exchange and intervening corrections,
withdrawals or restrictions, not just the chosen substring. "Might be a Husky"
followed by "Roxy" does not become a definite breed. "Don't save that" followed
by a name does not become saving permission. A fresh self-contained current
assertion or explicit change of saving intent is evaluated separately. This is
bounded assertion scope, not persistent topic suppression beyond the admitted text.

Authorization is operation-specific. A current target answer completing an explicit
user removal request can authorize forget; affirmative assent to an assistant's
specific proposed removal can too. "Remove one drink preference" / "Coffee or
tea?" / "The morning-coffee one" and "Shall I remove saved morning coffee?" /
"Yes, please" are positive cases. "Is morning coffee no longer your preference?"
/ "Yes" can support ending, not forgetting. Identifying an old record alone
authorizes neither. Bind the exact action, target and current assent; no free-form
"authorized" flag or extra classifier call. Earlier-user requests remain support
only; the current resolution/endorsement is the authority anchor. Cancellation,
negation and unresolved target ambiguity defer rather than guess an action.

Use the existing affirmative/uncertainty helpers where their semantics fit and
add narrow negative tests, not a broad yes-word heuristic. Some interpretation
remains semantic; exact citation matching is necessary, not sufficient for truth.
Native checks establish binding and permitted combinations, not universal semantic
entailment. Freeze the concrete contrasts as tests; measure broader interpretation
quality live. Escalate an unimplementable contract, not the absence of a theorem
about natural language; do not introduce another judge to manufacture certainty.

Persist current authority and supporting provenance distinctly. Propose adding
`user_resolution` (current anchor) and `user_antecedent` (support-only) to the
existing source-role contract. Keep `user_assertion`, `user_endorsement`, and
`assistant_referent`. Update DB check constraints, readback verification, presenters,
API schema and UI role display together; do not relabel old evidence. Assistant
context in a resolution is not licensed to add assistant-origin facts.
Expose the current anchor explicitly in the bound representation. Never recover
authority as "the first non-assistant source" or "any user source". Current roles
are user_assertion/user_endorsement/user_resolution as allowed by mode; antecedents
are support-only regardless of source ordering. Writes and readback must bind the
anchor to the originating run's current user message and check support chronology.
Update diagnostic safety checks too. Operator actions retain separate causation.

### Dispositions And Atomicity

Validate output shape and exact evidence bindings first. Defer/conflict do not
pass through executable-mutation entity/value requirements. Complete writes do.
Do not transform an invalid write into a defer, silently drop sources, or salvage
valid siblings from malformed output.

No-save applies at claim scope and dominates equivalent writes in either order.
A no-save item carries its exact current scope, not an invented target. Adapt
the independent native no-save check to the admitted exchange and explicit anchor,
including inherited restrictions; do not reuse its sentence-only implementation.
A defer declaration
cannot hide a contradictory sibling. Clear removal of an existing fact requires
an authorized forget operation; "do not save this" does not by itself delete it.
Unrelated supported writes survive legitimate deferrals.
Mandatory contrasts include "I prefer coffee in the morning. Don't save that.
I now live in Toronto" and natural Chinese "别保存". Coffee may defer while
Toronto writes; an unauthorized coffee write still rejects the attempt rather
than being silently dropped to rescue its sibling. Restrictions apply to the
identified claim, not indiscriminately to all current facts.

A grounded conflict can exist without a new write. Allow relevant read-only fact
or identity handles from the held lifecycle snapshot, together with current query/
context and a uniquely bound conflicting candidate span. A question need not become
a fabricated user assertion. If F1 names the dog Roxy, "What is my dog's name?" /
"Rocky" can ground a conflict with zero writes. A correct answer followed by an
unrelated question is not conflict. Conflict grounding grants no mutation authority
and adds no retrieval or fourth write-evidence mode. A validated conflict vetoes
the whole attempt. Semantic
contradiction remains reviewer judgment subject to fixtures, not string matching.

After filtering genuine deferrals, derive the effective write set and dependent
new entities/embeddings once. All-deferred/no-change must not create entities,
write embeddings, or advance memory generation. Query embeddings for retrieval,
if already used, are not mutation embeddings and must be reported separately.
Bind once to trusted operation records. Finalization revalidates ownership, source
integrity and original versions transactionally, without rerunning semantic
interpretation, allocating different identities, or rebinding against fresh rows.

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
Use one canonical event producer on successful and failed attempts. Remove
reconstructed request-start/completion events in `worker_events.py` success paths;
keep authoritative domain events for messages, revisions, summaries and tools.
Do not deduplicate by provider response ID: failed requests may have none.

Report attempted, completed, failed, and unresolved counts by kind/model/stage
and run/iteration. These are ADE outbound attempts, not provider billing or a
guarantee of network receipt. Timeouts may have reached the provider; do not
record them as zero. Surface expected versus observed counts as diagnostics,
never a spending veto or a reason to silently omit remaining cases.
Attempted means one retained local dispatch-start ID; completed means transport
returned a supported envelope, even if the product later rejects the proposal.
Failed/cancelled means that invocation ended exceptionally. Unresolved means a
known start lacks a terminal observation. Missing starts make the total incomplete,
not a known exact total with some unresolved calls. Cancellation must be counted
without swallowing cancellation or converting it to success.

For workflow setup outside a run, use the same small event shape in its existing
artifact writer. If process death/capture loss makes coverage incomplete, label
counts incomplete/unknown; never manufacture zero or claim exact billing.
Ordinary telemetry failure must not prevent a product request or alter its result.
An evaluation may remain unscorable because evidence is missing, distinct from
a monetary stop. Do not build durable pre-request reservations again.
Apply non-vetoing observation to trace-start, completion, reviewer callbacks and
capture writes, including writes in finally. Preserve the original result or
exception if observation fails; never trigger retries from capture errors. Use a
small helper, not an observability framework. Required source/revision/run-outcome
persistence is not optional telemetry. Keep optional writes outside or isolated
from the authoritative transaction; do not swallow transaction persistence errors.

Keep existing historical ledgers/frozen files byte-for-byte. Active commands stop
enforcing old monetary schedules; docs mark those schedules historical. Remove
active imports/validation of old caps, while retained fixtures still specify their
semantic cases. Current context/iteration/tool-call bounds remain explicit.
Timeout ownership remains explicit: the attempt controller owns one execution
deadline shared by conversation, continuations and reviewer; the transport receives
the remaining allowance. Preserve the former budget wrapper's applicable
180-second per-request diagnostic ceiling in non-accounting transport construction,
not as a fresh full window at each stage. Explicit retries create distinct attempts
under existing rules. Do not redefine the deadline to span all retries/finalization.
Move timeout tests before deleting budget tests; add no new timeout framework.

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
Include definite versus uncertain/no-save/withdrawn antecedents, following-sentence
restrictions, short affirmative versus bare-name assent, action versus factual
confirmation, conflict grounded in an existing fact, and source-order permutation.
Freeze each case's complete permitted before/after delta: required mutations,
unchanged identities/scopes and forbidden extra changes. Expected-fact presence
alone cannot pass; semantically equivalent values remain subject to explicit review.

### 2. Remove Spending Gates, Retain Observation

Refactor the shared transport factory and active acceptance/development runners
to event-based counts; delete cap-specific settings/readiness/tests. Retain
transport, route validation, exact retries, timeouts and behavioral stops.
Exit: fake transport tests cover failed sends, continuations, retries, setup and
API/worker aggregation with no double counts; exceeding an expected count does
not block a request. Missing telemetry is explicit and does not veto product work.
Inject telemetry failure before/after a successful call and during an original
provider error/cancellation; preserve the result/exception. Required provenance
storage failure must still fail commit. Verify one ID/event source on both success
and failure, with setup and embedding calls included.

### 3. Implement Compact Review And Provenance

Implement discriminated decisions and request-local binding, safe identity views,
three evidence modes, genuine no-write outcomes, strict completion handling and
effective-set preparation. Thread exact output allowance through existing request
construction/preflight without changing other generation behavior. Use cohesive
modules, preferably below 400 lines; split responsibilities before adding to
files over 500 lines. No general policy engine.

The two proposed source roles require a forward constraint migration; update
readers/UI/OpenAPI and diagnostic authority sets in the same checkpoint. Test
fresh and existing disposable DB migrations non-destructively. Existing messages,
facts/revisions and receipts must remain readable unchanged.
Read historical records by their originating policy/lineage without retroactively
certifying them under new endorsement rules, relabeling sources or inventing assent.
Antecedent-only new revisions must fail; source order cannot change authority.

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
source-linked setup, complete allowed mutation deltas and permitted reply claims
before execution. Include the new restriction/action/conflict contrasts in the
frozen diagnostic subset, not only hand-authored unit tests. Optional same-subject
later recall may be added before freezing; without it, label results reconciliation/
write evidence and leave retrieval/continuity claims to the later comparison.

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

No implementation push, merge/deployment/promotion, source-fingerprint rebind, or
production data change is part of writing or reviewing this plan. Documentation-only
review publication is pre-approved under the tracker's standing authorization.
Eventual release still requires fresh evidence, approved
policy/envelope, matched builds and non-destructive migration/recovery checks.

Ask the Pros to scrutinize: whether three evidence modes truly separate authority
from support; whether current/antecedent roles are sufficient without semantic
loopholes; whether write/defer/conflict shapes preserve no-save and contradiction
behavior; whether identity maps leak forgotten facts; whether counter aggregation
is honest without recreating budget infrastructure; and whether the new diagnostic
can falsify the intended improvement without weakening the original product goal.
