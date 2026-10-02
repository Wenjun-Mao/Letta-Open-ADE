# ADR 0060: Joint History Packet Admission

Status: **Proposed implementation contract, 2026-10-02.** The user authorized
planning the correction-plus-antecedent recovery follow-on and chose to keep four
windows while comparing joint selection methods. Atomic admission below is a
proposal for review, not adopted runtime behavior or execution authorization.
The [bounded plan](../plans/character-evidence-recovery.md) owns delivery scope.

## Problem And Evidence

The [D04 comparison](../../workflows/evals/character_memory_dev/story_continuity/evidence_selection/behavioral/READOUT.md)
supplied a referential correction without its original named location. Literal
generation remained appropriately uncertain; an evaluator-restored four-source
packet supplied the location. This identifies an observed source-selection gap,
not a proven generation failure or general reliability result.

The existing ranker chooses individual windows, and `admit_history` greedily admits
them if each fits both requests. `HistoryAttempt.omit_before_exposure` can also
remove individual sources after revalidation. A new selector that deliberately
chooses sources to be read together cannot rely on those later operations to
preserve its meaning. These are code-backed hazards, not observed causes of D04.

## Proposed Decision

Represent a selector's zero-to-four original source IDs as one proposed packet,
distinct from an independent ranked candidate list. The IDs retain presentation
order but express no truth priority. The selector chooses sources; it supplies no
canonical facts, answers, dependency graph or persistence authority.

Construct the entire proposed packet using existing immutable source binding and
generation/reviewer serializers. Validate source membership, scope, integrity,
complete exchanges and lifecycle annotations, then preflight both full requests
with mandatory context and output reserves intact. Either the exact selection
fits both consumers or it produces an explicit unadmittable result. Never remove
one exchange to salvage the rest or disguise that failure as a valid empty selection.

Apply the same contract to every arm of the new comparison. Preserve the legacy
greedy builder for frozen historical studies. The initial implementation would be
workflow preparation in a service-owned test helper; the owning runtime would
adopt a named joint-selection contract only after a separate integration decision.
This evaluation-versus-runtime distinction is deliberate and must be mechanically tested,
not an implicit semantic-model exception in production admission.

If integrated later, selected-source loss before exposure invalidates the whole
proposal. Integrity/scope/annotation or accepted-generation drift remains fatal;
exposed history remains fixed through generation, review and commit checks.
Authorize all candidate sources before a model sees the broader pool and revalidate
the selected packet at each existing exposure/commit boundary. A newly smaller
pool does not silently authorize a new semantic call or a partially reused output.

Final generation and reviewer H are identical. Evaluator annotations, the broader
selector pool, model reasoning and synthetic summaries cannot enter either request.
Structural checks establish valid sources and packet preservation, not semantic
dependency completeness. Missing or ambiguous evidence remains a model
interpretation question under PC-05/11. All applicable PC-01/03/04/05/06/07/08/09/10/11
agreements remain unchanged.

## Alternatives And Consequences

- Retain greedy salvage for a joint packet: rejected because a valid selection can
  become a different, semantically incomplete packet after selection.
- Add model-produced dependency edges or a persistent graph: defer; one small joint
  selection already expresses the required admission unit, and edges add another
  interpretation contract without demonstrated need.
- Admit the whole eligible pool based only on budgets: a viable later policy
  alternative, but changes the user's retained four-window constraint.
- Give originals, latest messages or correction phrases automatic priority:
  rejected; meaningful correction and uncertainty belong to semantic interpretation.

Atomic admission may reject an otherwise useful subset because an optional
selected exchange overflows a request. Record that tradeoff explicitly. Selecting
fewer useful sources can help; automatic reselection, output repair and caller-
specific fallbacks are not part of this proposed experiment.

## Guardrails And Follow-Up

The [protocol proposal](../../workflows/evals/character_memory_dev/story_continuity/evidence_selection/PROTOCOL.md)
retains ten cases, three methods and the original source-only response schema.
Its v2 change is proposed joint admission and clearer semantic assessment, not
permission to run a campaign. Existing D04 count exceptions stay bounded to their
completed diagnostics. ADR 0057's investigation direction and the native turn-7
stop remain intact; this ADR would refine admission only if accepted.

Tests must exercise whole-packet fit against each consumer separately, source loss,
full metadata retention, identical H, and byte-equality with the historical builder
when the same selection fits. Preserve historical source/artifact hashes rather
than rebinding them after a refactor. Source-quoted semantic review still needs to
check omitted corrections, alternatives and warranted uncertainty.

No runtime, prompt, schema, provider binding or persistence code changes with this
record. Implementation approval would first cover offline preparation; live
selection, downstream answer comparison and native adoption remain separate work.
