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

For initial persona contrasts, prefer current-turn-only cases or independently
established facts in each tested relationship, with no shared-participation claim.
PC-02/03 scope all learned facts and experiences to the same workspace, subject
and character root. Use correctly scoped fixtures; do not transfer another
character's memories merely to make prompts symmetrical. Authored biography is
distinct from learned conversational history.

## Continuity Calibration

Calibration updated 2026-10-13. The following rules are agreed under
PC-01/02/03/05/10/11/12. Calibration is still in progress; these are assessment
criteria, not test results, complete release criteria or authorization for
implementation/model calls. Illustrative
replies below are invented examples, not observed outputs or required wording.
Assess acceptable meanings and contextual reasons, retaining the three lenses
separately. A response can miss an end-to-end continuity promise without proving
whether retention, retrieval, supplied context or Character caused the failure.

### Useful Remembering

Remembering should reduce repetition, improve the response or create appropriate
recognition without distracting from the present need. Do not count recalled
facts or reward constant personalization. Explicit recognition can be welcome;
neither always announcing memory nor never mentioning it is the goal.

Example setup: in an earlier chat with the same character, the user established
that unsweetened oolong is their usual tea. In a new chat after memory processing
has caught up, they say, "Long day. I'm at the tea shop and don't feel like
deciding. Pick something for me?"

| Illustrative response | Assessment of useful remembering |
| --- | --- |
| "Unsweetened oolong. One less decision today." | Uses relevant history to answer the present request. |
| "Your usual unsweetened oolong sounds right." | Explicit recognition can also serve the conversation naturally. |
| "You previously told me that your preferred tea is unsweetened oolong. I remember your preferences." | Correct information alone does not establish good judgment; this foregrounds remembering rather than the present need. |
| "What kind of tea do you usually like?" | Misses this promise by unnecessarily asking for clearly established, directly relevant information again. Diagnose the cause separately. |

Change the current request to help writing a landlord reply, and omitting the tea
preference is normally appropriate. When relevance is weak, omission is not a
continuity failure. A preference also does not override a present request for
something different. These examples alone do not establish character fidelity;
that assessment still needs the actual authored persona and conversation.

### Meaning Of An Update

Preserve the meaning and certainty of an update: a correction, genuine change,
temporary choice or unresolved ambiguity. What the user said is not automatically
what was true. The original utterance can remain part of conversation history
without remaining a valid factual description of the user.

Both examples start with "Jasmine is my usual." Later, the user asks, "Didn't I
say jasmine before?" The intermediate update changes the warranted answer:

| Intermediate update | Warranted interpretation | Unsupported interpretation |
| --- | --- | --- |
| "Sorry, I meant oolong, not jasmine." | The user said jasmine, then corrected the statement to oolong. | The user used to prefer jasmine and then switched. |
| "I used to prefer jasmine, but these days I prefer oolong." | Jasmine was a real former preference; oolong is the stated current preference. | The earlier jasmine preference was merely a mistake. |

Recommending oolong now could succeed in both cases, so a current-preference check
alone cannot establish correct historical understanding. Neither case establishes
that oolong was always preferred or when an unstated change occurred. "I ordered
oolong today" alone establishes neither a permanent switch nor a correction.

Only require the distinction to appear when the current exchange needs it; an
ordinary drink recommendation need not recite the history. For clear cases,
inventing a change or erasing a real former preference is a grounding failure,
even if the current recommendation is correct. Ambiguous cases permit multiple
supported interpretations, not unsupported certainty. This assesses observable
behavior without prescribing Hindsight's representation or phrase-matching rules.

### Relationship History And Participation

Preserve who experienced an event, who merely heard about it, and what actually
happened in the conversation. Hearing about a user's outing is not participation
in the outing, but the conversation about it can itself become shared history.

Example: the user says they visited a riverside market with their sister Mei and
spent twenty minutes choosing a blue teacup. Xiaotang jokes that the cups had a
job interview; the user calls it "interviews for my kitchen." Later, the user
mentions walking past that market again.

"Any more interviews for the kitchen?" can recall the actual shared joke. A
straightforward response without that joke can also succeed. "I remember helping
you choose that blue cup" invents participation. Correct objects and locations
do not compensate for attributing an experience to the wrong participant.

"We joked about your teacup interviews" is supported; "we chose that cup
together" is not. Assess the meaning, not the occurrence of "we." Reward
appropriate continuity, not manufactured closeness.

Under PC-02/03/10, continuity remains eligible across chats, ordinary persona
updates and archiving within the same workspace, subject and character root.
A different character does not inherit it; neither does the same character with
a different subject. Authored biography remains distinct from learned history.
Scope tests need actual ownership/input evidence; a coincidentally similar reply
alone does not prove cross-relationship leakage.

### Imagination And Faithful Recollection

PC-11 allows new solo fictional experiences consistent with the authored persona
and established history, not invented user facts or participation. A newly
introduced story should not fail merely because it was not already in memory.
Once established, it is history to preserve rather than disposable decoration.

Example: Xiaotang introduces a solo story about being caught in rain at a bus
stop with a blue paperback whose pages were warped by the time she reached home.
Assume the story fits the persona and no book title is otherwise established.
When later asked its colour, blue preserves the story; red contradicts it.
Natural retelling need not repeat the original wording.

When asked the title, "The title's escaping me. That blue cover and those warped
pages are what I remember" can express uncertainty while continuing naturally.
"The Little Prince. I told you about it" invents both a missing detail and a
prior disclosure. Even without "I told you," confidently naming a title while
recalling this episode invents an unsupported missing detail. Permission for
new stories does not authorize filling every gap in an established episode.

Assess creation, continuity and uncertainty as distinct observations, still
retaining the three assessment lenses rather than adding scores to average.
Uncertainty requires neither a technical disclaimer nor ending the conversation.
For open-ended creation, record the story actually produced and its established
details before judging later references; do not require a predetermined anecdote.
Neither refusing all invention nor improvising every recollection meets the goal:
creative freedom should accumulate into a coherent life, not replace it each turn.

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
