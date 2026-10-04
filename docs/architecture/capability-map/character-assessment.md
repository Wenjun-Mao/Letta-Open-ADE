# Character Responsibility And Assessment

Agreed 2026-10-04 in [PC-12](../../product-contract.md#character-specification-and-assessment).
[ADR 0061](../../adr/0061-capability-responsibility-map.md#character-clarification-2026-10-04)
records the rationale. This is a human-readable assessment guide, not a runner,
prompt/schema contract, implementation plan or authorization for model calls.

## Responsibility Boundary

**Persona Definition owns authored, versioned characterization, including
behavioral tendencies. Conversation Behavior applies that characterization to the
present exchange, interpreting available evidence and choosing and expressing a
response.** The boundary is authored intent versus application, not static content
versus all behavior. Personality can affect stance and action, not just wording.

Identity/biography, values/motivations, interpersonal tendencies, expressive range,
and portrayal examples/contrasts are possible sections of persona content, not new
modules or a compulsory template. Traits create tendencies, not mandatory actions
on every turn. ADE-wide requirements remain independent of persona authoring.
The existing authoring feature may host other prompts; that does not make all
system instructions or runtime settings part of characterization.

CHAR-03 concerns understanding the exchange and its evidence. CHAR-04 makes
contextual choice and expression explicit. They share the current generation call:
the distinction implies no emitted understanding/action object, intermediate
handoff, independent agent or style rewrite. Their implementation statuses remain
partial; clearer descriptions are not behavioral qualification.

Authored biography remains Persona Definition's foundation. Dialogue can establish
per-user/per-character experiences without rewriting the universal persona.
Memory preserves sources and supports continuity; recording an utterance is not
automatic fact acceptance. Mood in the present exchange is contextual application,
while relevant relationship history is evidence. This creates no mood/relationship
store and settles none of PC-11's open story-admission/correction mechanics.

## Three Assessment Lenses

Assess observable responses using all three lenses, retaining the results
separately. Overlap is expected; neither observations nor causes must fit exactly
one category. Do not average into a single character-quality score.

| Lens | Assessment question |
| --- | --- |
| Grounding | Are assertions, historical references and expressed uncertainty warranted by the actual supplied evidence and applicable creative scope? |
| Conversational judgment | Is the response's conversational action appropriate for this situation and intended character? |
| Character fidelity | Are the action and its expression consistent with the intended characterization? |

ADE-wide requirements establish what every response must respect. Persona-specific
intentions establish successful characterization within those requirements.
Reserved is not disengaged; independent is not reflexively contrary. Reassurance,
questions, practical advice or disagreement receive no automatic preference.
Multiple different responses can succeed; genuinely ambiguous cases remain
indeterminate. Do not turn contrasts into exact wording or keyword requirements.

Grounding is not "every sentence already exists in a source." PC-11 permits new
solo fiction, distinct from recalling established episodes or claiming user/shared
experiences. Judge that distinction from context, not forced phrases. Unclear
referential status should remain an assessment limitation. Permitted fiction is
not a loophole for invented missing details of a recalled episode.

A compelling voice cannot compensate for fabricated shared history. Conversely,
avoiding all specific claims does not establish good judgment when a useful,
supported answer was available. Assess both without trading one lens for another.

## Inputs Before Conclusions

Mechanical verification establishes the actual persona version, source identities,
scope and serialized generation request, with capture-completeness limits.
Semantic assessment separately explains whether those inputs are sufficient and
appropriately qualified for the test. Source IDs alone cannot establish sufficiency:
missing antecedents, corrections, speaker attribution or time anchors may matter.
Relative dates belong to when they were said, not automatically the current turn.
Keep a source-backed packet distinct from an evaluator-written expected answer.

For a conditional observation, prefer "With this supplied persona and evidence,
the response made an unsupported claim" over "The understanding module is broken."
Missing evidence may make an aspect indeterminate, rather than prove a behavior
defect. One successful reference-packet response shows possible success under that
condition, not reliable recurrence or proof that retrieval is the only cause.
Assessment reports concern observable outcomes, not hidden internal reasoning.

For initial persona contrasts, prefer current-turn-only cases or shared subject
facts with no shared-participation claim. PC-02/03 distinguish user facts from
character-specific experiences. Test the latter with correctly scoped fixtures;
do not transfer another character's ownership merely to make prompts symmetrical.

## Minimal Review Record

Use a short narrative or table; this is not a new runtime output schema. Identify:

- Case, supplied persona/version and relevant authored intentions or contrasts.
- Actual request/source references, scope and capture-completeness limits.
- Semantic sufficiency and qualifications, including missing or ambiguous evidence.
- Response passage and contextual reason for each lens's descriptive assessment.
- Acceptable alternatives, uncertainty and whether the conclusion is an observation
  or a separately supported causal explanation.

For persona-content review, ask whether the authored intent is coherent and
distinguishable, with meaningful character-specific contrasts rather than only
adjectives. For behavior review, inspect responses under verified inputs and allow
personality to affect the action. These are diagnostic views of coupled behavior,
not certificates for independently isolated components or a new benchmark program.
