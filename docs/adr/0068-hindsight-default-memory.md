# ADR 0068: Hindsight As Default Memory

Status: Accepted product direction, 2026-10-12, by explicit user decision.
Implementation and deployment remain pending integration planning; historical
data migration is excluded from the fresh-workspace/subject scope.

## Context

After reviewing the closed Hindsight campaigns, the user selected Hindsight as
the default Memory implementation and requested discussion of next steps.
Earlier assessments treated adoption as open. Continuing to require another
vendor-selection experiment would now conflict with that decision.

The experiments provide bounded evidence of useful retention and recall and
identify a consolidation meaning defect. Several other reported failures arose
in Character replies despite relevant distinctions being present in supplied
memories. Neither successful replies nor those failures alone qualify or
disqualify the Memory implementation. Historical findings retain their original
scope and limits; adoption is a product decision, not a revised experiment score.

## Decision

Use self-hosted Hindsight as ADE's default Memory implementation, under
[PC-14](../product-contract.md#default-memory-implementation) and PC-13.
Move from candidate selection to integration planning against its concrete
capabilities rather than designing a generic replacement protocol.

Preserve the responsibility map in [ADR 0061](0061-capability-responsibility-map.md):
Memory owns retention, organization, recall and context delivery. Character
owns authored characterization and conversational interpretation/expression.
Interface owns user-facing use, configuration and inspection. Service placement,
model access and operational recovery remain supporting responsibilities.

The decision supersedes the assessment-only/adoption-deferred direction in
[ADR 0062](0062-self-hosted-hindsight.md) and the product contract's former
open Hindsight-adoption item. It does not supersede the self-hosting choice,
subject/character boundaries, archive eligibility, operator removal, or PC-11/12
Character agreements. Existing findings and completed experiment plans remain
historical, including their failures and qualification gaps.

### Character-Local Learned Memory

On 2026-10-12 the user rejected another character receiving a preference told
to Xiaotang. All learned conversational memories, including ordinary facts and
preferences about the user, belong to `(workspace, subject, character root)`.
There is no shared-profile exception and no automatic cross-character propagation.
If the user independently tells another character the same fact, that is a
separate source in that relationship, not inherited memory.

The same character retains continuity across chats, ordinary persona versions
and archived conversations. Different subjects remain isolated. This governs
learned conversational memory, not common authored persona definitions or the
model's general knowledge. PC-06 still excludes conversational consent/no-save
policy features; structural ownership does not introduce a sharing mechanism.

This explicitly amends PC-02/03 and supersedes the subject-wide profile-sharing
direction in [ADR 0022](0022-incumbent-memory-first-product-slice.md), the relevant
part of the [historical natural-memory design](../architecture/natural-memory-design.md),
and the cross-root profile exception used by
[ADR 0063's experiment](0063-hindsight-character-evaluation-boundary.md).
Historical fixtures and captures remain unchanged. Their sharing successes are
not acceptance evidence for this corrected boundary. Bank layout remains an
integration design choice and must isolate learned memories by character; do
not copy the experiment's character-OR-profile recall policy into the new path.

### Fresh Start Without Backward Compatibility

The user selected a fresh workspace/subject and explicitly rejected backward
compatibility as a design constraint. Existing data remains untouched; it is not
an input to migration, backfill or automatic ingestion in this scope. This is not
a commitment to a later legacy migration or to opening old conversations in the
new runtime.

Implement a direct Hindsight path and replace obsolete incumbent contracts where
needed. Do not add compatibility adapters, dual writes, automatic native fallback
or a generic backend framework to keep the old Memory implementation executable.
Preserve historical evidence and stored data without carrying old behavior into
the new design. Breaking source/API changes may be part of the implementation
plan; deletion, data rewriting and live cutover are not authorized by this
planning decision. PC-02/03/04/10/11 still govern continuity in the new scope.

### Attributed Asynchronous Source Delivery

The user approved retaining accepted user messages and committed Character
replies with explicit speaker, time and conversation attribution. Uncommitted
reply candidates are excluded; accepted user input remains eligible even when
Character generation fails. Submission records what was said without declaring
all utterances established events or removing their uncertainty (PC-03/11).

Delivery is durable and asynchronous, with visible progress and failure status.
Do not couple a successful conversation outcome to a claim that Hindsight has
finished retention. Distinguish queued/accepted delivery from completed
processing; processing completion is not a semantic-quality certificate.
This direction does not yet select source-unit size, append/replacement behavior
or ordering/retry mechanics. Those choices belong in the integration design,
not implicit adapter behavior.

### No Retention Wait Before Replies

The user selected replies without waiting for pending retention. Current input
and bounded recent dialogue are supplied independently of the Memory ingestion
pipeline; normal scoped recall uses the memories available at that time. Do not
add a retention catch-up barrier before generation.

The rationale applies to recent turns actually included in the current
conversation context, not to every recent chat or all older history. Cross-chat
and out-of-window recall can lag while earlier source messages are still being
processed. Interface exposes retention progress/failures; no forced Character
disclaimer is introduced. This accepts eventual recall availability, not skipped
recall, hidden delivery failure or a promise of immediate cross-chat freshness.

### Pause On Failed Recall

The user selected pausing the affected reply and offering Retry when a Hindsight
lookup fails. Keep the accepted message saved; do not continue generation using
an empty-memory substitute, switch to native Memory or report that no relevant
history exists. Interface presents the failure and retry action rather than
having Character generate an in-character error response.

Retry starts another reply attempt for the same saved user message, with a fresh
scoped recall. It must not append a duplicate user message. Exact attempt and
delivery-idempotency mechanics belong in the integration design. Successful
empty recall remains a usable result, and pending background retention alone
does not trigger this failure behavior. The distinction preserves the earlier
no-retention-wait agreement without hiding inability to read existing Memory.

### Remove Saved Memory Without Erasing Chat

The user approved using Hindsight's native invalidation for selected saved
memories. The original chat remains unchanged, and recent dialogue can still
contain the statement. New statements remain eligible for retention; there is
no permanent topic ban or promise that Character can never mention the fact.
This preserves PC-07's distinction between memory removal and historical erasure.

Ordinary delivery/retries must not recreate a removed memory. Do not repeatedly
reprocess an entire conversation as new messages arrive. Hindsight's source
reprocessing resets fact curation, so a deliberate rebuild is a separate
operation outside the first integration scope, not an automatic maintenance
step or a promised removal-preserving replay. The integration must verify
invalidation and affected derived memories before reporting completion; exact
delivery/source-unit mechanics remain to be designed. Historical chat contents
and experiment captures are not rewritten by this decision.

### Separate Product Records And Learned Memory

The user approved ADE as the authority for original conversation messages,
character definitions/bindings, run state and durable delivery status. Hindsight
owns extracted memories, organization, recall and curation. Source copies kept
by Hindsight for processing do not replace ADE's original conversation record.
ADE delivery bookkeeping is operational state, not a parallel fact store or
semantic reviewer. The new path must not maintain either alongside Hindsight.

The incumbent couples native fact changes and reply success in one transaction.
That cannot be treated as a transaction across ADE and Hindsight: the approved
asynchronous delivery can complete after the product commit. Preserve durable
source capture and truthful status instead of fabricating native review results
or making Hindsight imitate native fact versions. The integration plan must
define crash/retry behavior at this boundary, including removal preservation.

Back up both authorities. ADE conversations alone cannot restore Hindsight's
curated state, including removals; do not treat Hindsight as a disposable cache
or automatic chat replay as recovery. Coordinated backup/restore procedures
remain to be designed and verified. This selects data responsibility, not a
physical database topology or authorization to operate existing services.

For the Hindsight path this supersedes the single Agent Studio persistence
authority in [ADR 0019](0019-ade-steady-state-runtime.md) and the native reviewer /
atomic-Memory requirements in [ADR 0035](0035-compact-natural-review-and-observational-dispatch.md).
It preserves one ADE product API/runtime, Model Router's identity responsibility,
source integrity, character-local isolation and PC-07's retained chat history.
The unchanged incumbent and historical evidence retain their original contracts.

## Integration Decisions Still Needed

The user requested the [three-stage integration plan](../plans/hindsight-integration.md)
and selected a new isolated OCI stack for its live checks. Current ADE/trial
services and closed experiment data remain unchanged; full-stack capacity must
be rechecked before activation. Plan approval alone does not authorize execution.

The [source-pinned assessment](../findings/hindsight-integration-assessment-2026-10-10.md)
and [consultation synthesis](../findings/hindsight-consultation/assessment.md)
remain inputs, not pre-approved implementation instructions. Resolve:

- Bank mapping and enforcement of the agreed workspace/subject/character
  ownership, including derived observations and source-context access. There
  is no cross-character profile sharing to design.
- Source-unit boundaries, ordering, retries and detailed failure behavior for
  the agreed attributed asynchronous delivery. Preserve the boundary between an
  utterance and an established event.
- Product-commit/delivery mechanics and backup/restore across the agreed ADE and
  Hindsight authorities; remove native reviewer/transaction dependencies without
  dummy review results or a duplicate semantic engine.
- Native invalidation and removal verification under ordinary delivery/retries,
  fresh-scope cutover and recovery behavior. Historical migration and deliberate
  old-source rebuild/reprocessing are excluded from the first integration.
- Truthful Interface inspection and status, plus integration and operational
  verification separate from Character behavioral evaluation.

## Alternatives And Consequences

- Further vendor-selection evaluation before accepting direction: superseded by
  the user's adoption decision. Targeted defect and integration checks remain
  useful; they are not a reason to silently reopen the selected default.
- Immediate deployment or automatic historical backfill: not authorized by a
  request to adopt the direction and discuss next steps; backfill is explicitly
  outside the selected fresh-start scope.
- Compatibility-preserving replacement: rejected by the user. Keeping stored
  data untouched does not require retaining old code contracts or runtime paths.
- A new generic Memory framework or second semantic reviewer: not implied by
  adoption and inconsistent with PC-09 without a separate demonstrated need.

The running incumbent, existing data and closed experiment resources remain
unchanged. Implementation must follow a bounded integration plan and its actual
execution permissions. This documentation checkpoint authorizes no installation,
provider call, live service operation, migration or cutover. Tests and rollout
criteria must distinguish Memory behavior, Character behavior and Interface
behavior rather than using one domain's result as another's acceptance gate.
