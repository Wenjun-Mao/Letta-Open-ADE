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
This direction does not yet select source-unit size, append/replacement behavior,
ordering/retry mechanics or whether a later recall waits for pending ingestion.
Those choices belong in the integration design, not implicit adapter behavior.

## Integration Decisions Still Needed

The [source-pinned assessment](../findings/hindsight-integration-assessment-2026-10-10.md)
and [consultation synthesis](../findings/hindsight-consultation/assessment.md)
remain inputs, not pre-approved implementation instructions. Resolve:

- Workspace/subject/character scope and profile sharing, including derived
  observations and source context, without transferring participation.
- Source-unit boundaries, ordering, retries, recall freshness during pending
  ingestion and detailed failure behavior for the agreed attributed asynchronous
  delivery. Preserve the boundary between an utterance and an established event.
- Product-data and Hindsight-state authority, replacing the incumbent's reviewer
  and single-transaction Memory assumptions explicitly rather than faking native
  review results or running a duplicate semantic engine.
- Operator removal under later ingestion/reprocessing, retained history,
  fresh-scope cutover and recovery behavior; historical migration is excluded.
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
