# ADR 0061: Capability Responsibility Map

Status: Accepted for documentation/development vocabulary, 2026-10-04,
by explicit user direction. Not a runtime change or run authorization.

## Problem

Continuity discussions mixed memory formation, retrieval, evidence delivery,
interpretation, personality and persistence into one problem. A sequential pipeline
helped locate failures but did not separate containment, execution and stored records.
An independent discussion proposed a Domain/Subsystem/Module hierarchy. The user
agreed to inventory and categorize the moving pieces, then draw their connections.
Much supporting machinery exists; the map must not imply rebuilding or qualifying it.

## Decision

Use **Domain -> Subsystem -> Module**, with **L1/L2/L3** denoting containment depth.
Stages/calls describe execution; ownership describes responsibility. Neither
levels nor modules imply separate services, directories, agents or model calls.

Character and Memory are core capability domains. Character contains Persona
Definition and Conversation Behavior. Memory contains Retention & Updates,
Organization & Maintenance, and Recall & Context. Interface contains user-facing
use/configuration/inspection responsibilities. External Tools is a deferred outside
information/action capability, distinct from internal memory tools.

Keep runtime, state, model access, evaluation, observations, operations, application
wiring and schemas in a supporting register with their existing owners. Register
Comment/Label labs as adjacent features, without redefining ownership. Show stored
records distinctly from processing.

Maintain one [source-backed inventory](../architecture/capability-map/README.md).
Each piece has a stable ID, source/test homes, implementation scope, separate
evidence limits, input/output, gap and next isolated check. Generate both map and
readable inventory from the same data; reject stale views. This is a work/evidence
locator, not competing product authority.

## Alternatives

- One undifferentiated continuity problem: rejected; it confounds availability,
  selection, delivery, interpretation and expression failures.
- L1/L2/L3 as execution layers: rejected; collaborating domains are not a strict stack.
- New services/files for every box: rejected; responsibilities may share code/calls.
- Platform/labs forced into Character/Memory: rejected; explicit registers preserve
  their established ownership.

## Consequences And Guardrails

No new store, reflection agent, provider request, tool framework or public inspection
endpoint is adopted. PC-01 through PC-11 remain unchanged. PC-08/09 and existing
retry, source-binding and atomic-finalization contracts still govern.
[ADR 0060](0060-joint-history-packet-admission.md) remains proposed.

Existing code, bounded semantic evidence and released behavior have separate
statuses. Optional new views must not erase existing compaction. Private artifacts
do not become public UI data through documentation.

Use subsystem measures first; isolate a module when evidence identifies its gap.
Test Memory with controlled consumers and Character with fixed sufficient evidence,
then their interaction. Reuse benchmarks where suitable; this creates no new
benchmark program or implementation priority by itself.

## Character Clarification, 2026-10-04

The user explicitly adopted authored intent versus contextual application and
three response-assessment lenses. [PC-12](../product-contract.md#character-specification-and-assessment)
owns that agreement; the [assessment guide](../architecture/capability-map/character-assessment.md)
describes its use without starting an experiment.

Persona Definition owns authored, versioned characterization, including behavioral
tendencies. Conversation Behavior interprets the exchange and evidence, then
chooses and expresses a response in context. Personality can affect the action,
not just wording. Refine existing CHAR-03/04 descriptions without introducing a
materialized handoff; they still share generation. Retain all module IDs, names,
statuses and topology. The inventory's previous allocation of "conversational
choices" to interpretation and "grounded meaning" as expression's input is
clarified here; it is not a new runtime interface.

Grounding, conversational judgment and character fidelity are overlapping
assessment lenses, not three pipeline boxes or independent diagnoses. Reject a
generic agreeable-assistant ideal, mandatory trait enactment, a composite score
that trades factual integrity for voice, and demands for internal planning objects.
Assess observable behavior against the intended persona and ADE-wide constraints.
PC-11's creative scope and open story-admission mechanics remain unchanged.

Separate mechanical input verification from semantic evidence sufficiency.
Source IDs cannot prove that missing antecedents or qualifications were supplied.
Report conditional observations before causal explanations; one successful
reference-packet response proves neither a sole retrieval cause nor reliability.
No runtime change, additional model call or behavioral acceptance follows.
