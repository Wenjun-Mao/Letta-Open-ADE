# ADR 0050: Consistent Improvised Character History

Status: Accepted product direction, 2026-09-30, recorded as
[PC-11](../product-contract.md#improvised-character-history). No runtime change,
provider experiment, deployment or release qualification is authorized here.

## Problem And Evidence

The [returned-report assessment](../findings/natural-memory-consultation/character-contract-assessment-2026-09-30.md)
left two questions open: may Xiaotang invent solo past experiences, and should
users expect those stories to remain consistent later? The user answered yes to
both. The literature informed the tradeoff but did not determine this choice.
In a subsequent clarification, the user selected per-user relationship scope
with authored biography as the common foundation, rather than universal
cross-user improvised biography.
The user subsequently agreed to stable history with compatible elaboration,
not deliberate rewriting through ordinary chat; genuine mistakes remain correctable.

An earlier listening anecdote was unsupported by supplied history. That alone
does not make a newly created solo episode a product defect under this decision.
Incorrect user attribution and invented shared experiences remain separate
failures. Persistence of assistant dialogue already creates a possible later
recall path, but does not prove reliable continuity or select canon mechanics.

## Decision

Allow Xiaotang to create solo episodes in her fictional past and expect later
conversation to respect those stories. This is permission for character-world
creation, not permission to invent evidence about the user or the relationship.

Scope improvised history to the same user/subject and character root within the
workspace, following PC-03. Preserve continuity across chats and ordinary persona
versions, including archive eligibility under PC-10. Authored biography remains
the shared foundation under PC-04's immutable bindings; one user's conversation
does not modify another user's evolving character history.

Distinguish creating an episode now from claiming that the user previously heard,
endorsed or participated in it. The former is permitted; the latter still needs
actual interaction evidence. Consistency with a previously established story is
part of the product goal, not merely a desirable side effect of retrieval.

Later conversation may reveal compatible new details without pretending those
details were already disclosed. Preserve established episodes rather than
accepting a deliberate rewrite because a user suggests it. This is not a
first-utterance-always-wins rule: genuine errors can be corrected, with the
distinction from optional rewriting made explicit in the probe design.

PC-03/04/05/06/09/10 continue to govern relationship boundaries, immutable
definitions, interpretation/validation ownership, minimum machinery and archive
eligibility. No current schema, prompt, persistence or reviewer contract is
silently broadened. ADR 0047's source-fidelity requirements still apply when
recounting actual dialogue and user/shared history.

## Rationale And Alternatives

The chosen product allows a character to acquire texture beyond a finite authored
biography while treating what she establishes as a continuing commitment. This
is a product judgment, not a claim that anecdotes empirically outperform other
expressive styles or should appear in every reply.

Reject a blanket ban on new solo episodes: it conflicts with the selected creative
freedom. Reject disposable, freely contradictory stories: it conflicts with the
selected continuity expectation. Reject treating all assistant text as universal
truth: fiction about Xiaotang supplies no authority over user facts, real-world
events or shared participation.

Reject automatic global promotion of improvised stories: it would let one user's
conversation establish biography for unrelated users. Relationship-scoped growth
preserves a common authored character without coupling independently developing
conversations or resetting continuity at each new chat.

Reject ordinary-chat co-authoring of replacements for established episodes. The
selected experience is getting to know a continuing character, not silently
editing her past. This does not remove authored-persona editing or its immutable
version behavior; reconciliation after substantive author edits is separate work.

## Consequences And Open Design

Permission, expected continuity, per-user/per-character scope and ordinary-chat
stability are settled; implementation is not. Before changing behavior, specify
what distinguishes an
established episode from a hypothetical, joke or mistaken claim, and how
corrections or conflicts with authored biography are handled. PC-11 does not
authorize global cross-user publication or select a new memory store.

Prefer testing the existing dialogue/history path before introducing machinery.
Future acceptance should include delayed and cross-chat callbacks to an invented
solo episode, stable core details, and negative controls preventing invented user
participation or backdated claims of having told the user. Check that another
user/subject or character cannot inherit the generated story, while a new chat
for the same user and character retains continuity. Include creative expression
controls so continuity does not become blanket refusal. These are verification
needs, not a scheduled or authorized live experiment.

The [bounded continuity-probe plan](../plans/character-story-continuity.md) proposes
the first implementation/evidence steps for review. It does not expand the
existing historical-recall campaign or authorize execution.

The previous assessment and reports remain historical evidence. Its open
permission question is resolved by PC-11, not by retroactively changing the
reports or relabeling earlier tests as continuity acceptance.
