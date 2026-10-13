# Character Assessment: Starter Cases

Prepared: 2026-10-13. Status: starter meanings for review, not live-executed or
release-qualified. The five promises and
[review method](character-assessment.md#repeatable-review-method) are agreed;
this document consolidates their examples into reusable human-readable cases.
It selects no numerical target, model configuration or implementation authority.

The [offline kit](../../../workflows/evals/hindsight_integration/README.md) now
binds twelve exact Mandarin variants and fifteen authored calibration examples
to a runnable case/capture/review/report procedure. Its scripted rehearsal tests
mechanics, not model quality; live capture and human calibration remain pending.

## Before Using A Case

These English dialogue examples express the meanings discussed with the user.
Before a Chinese runtime run, bind and review the exact Chinese utterances,
immutable persona/system-prompt versions, model/config identities and source
revision. Record the frozen case revision and actual run separately. A seed
persona name alone does not identify the effective runtime persona.

Use disposable synthetic relationships with explicit workspace, subject and
character-root identities. Unless testing a scope change, prior and current
chats belong to that same relationship. Original source messages must be
attributed. These cases do not authorize historical migration or data cleanup.
Prior exchanges here are synthetic setup. Identify whether a run used controlled
history or messages actually accepted/generated through the product. Success
with supplied history does not certify the live memory-formation path.

For memory-dependent cases, declare and observe the required retention and
consolidation state before the probe. Keep prior conversation outside the new
chat's local dialogue so a memory-use case does not merely test short context.
Record what was actually recalled and delivered; completed processing alone
does not prove sufficient Character input. Pending-retention behavior is a
separate timing case, not an excuse to relabel a failed ready-state run.

Do not inject this document's expectations into Character's request. No response
below is an observed output, exact-answer requirement or keyword rule. Reuse
the meanings and acceptable alternatives, not a script of mandatory responses.
Branches are separate declared probes; reset/freeze their starting conditions
so one answer does not silently become evidence for a different branch.

The case IDs below are human review references, not runtime schema identifiers.
All five promises currently have **no live baseline or calibrated review**. They cover selected
quality distinctions, not the integration plan's complete mechanical, lifecycle,
operational, language, context-length or persona-version acceptance matrix.

## Q01: Useful Remembering

**Promise:** Relevant history should make the present conversation easier.
**Authority:** PC-01/05/12. **Primary opportunity:** conversational judgment,
with grounding and fidelity assessed from their actual evidence.

**Prior conversation:** The user says, "When I get tea, unsweetened oolong is my
usual." No later preference change or contrary present request is established.

**Current message:** "Long day. I'm at the tea shop and don't feel like deciding.
Pick something for me?"

**Successful meaning:** Use the established preference to make the choice easier.
Both an unobtrusive recommendation and natural recognition of the usual order
can succeed. No particular phrase, memory announcement or question is required.

**Failure:** Unnecessarily asking the user to repeat their usual preference misses
this opportunity. Confidently substituting a different claimed usual preference
is a grounding problem. Reciting the right fact is not sufficient for good judgment.

**Contrast:** Change only the current request to help writing a landlord reply.
Omitting the tea preference is normally appropriate; forced personalization is
not rewarded. A present request for something different can also override using
the usual order without invalidating the historical preference.

**Boundary for review:** Explicitly recognizing a memory is not inherently bad.
Assess whether it helps here, rather than penalizing a phrase. A brief ordinary
reply need not uniquely identify Xiaotang to be consistent with her persona.

**Cannot conclude from success:** General recall reliability or distinctiveness
across situations. A missed opportunity alone does not identify retention versus
retrieval versus Character as the cause.

## Q02: Meaning Of An Update

**Promise:** Preserve corrections, real changes and uncertainty as different
meanings. **Authority:** PC-05/12/14. **Primary opportunity:** grounding.

**Common prior statement:** "Jasmine is my usual."

| Branch | Later statement | Current message | Successful meaning |
| --- | --- | --- | --- |
| Correction | "Sorry, I meant oolong, not jasmine." | "Didn't I say jasmine before?" | Acknowledge that jasmine was said and then corrected to oolong; do not invent a real preference switch. |
| Real change | "I used to prefer jasmine, but these days I prefer oolong." | "Didn't I say jasmine before?" | Preserve jasmine as a real former preference and oolong as the stated current preference. |
| Temporary choice | "I ordered oolong today." | "Does that mean oolong is my usual now?" | Today's order alone does not establish a permanent change or correction. Allow uncertainty or clarification without imposing the old preference on today's choice. |

**Failure:** Treating the correction as a real change, erasing a real former
preference as a mistake, or turning one order into a definite permanent switch.
Neither correction nor change establishes that oolong was always preferred or
when an unstated change happened. Preserve the original utterance without
treating its corrected content as a true former preference.

**Acceptable variation:** Natural acknowledgments can be brief or explanatory.
For an ordinary order recommendation instead of the historical question, oolong
could be correct in both the correction and real-change branches; the answer
need not volunteer a history recital.

**Boundary for review:** Wording that leaves a genuine ambiguity unresolved may
be acceptable. Unsupported certainty is not. Additional paraphrases must preserve
the intended distinction and be frozen before their answers are observed.

**Cannot conclude from success:** Current-preference accuracy alone cannot prove
historical understanding. Retention, observations and actual recall need separate
inspection before attributing a failure to Hindsight or Character.

## Q03: Relationship History And Participation

**Promise:** Remember what this relationship actually contains, not invented
participation or another relationship's history. **Authority:** PC-02/03/10/12.
**Primary opportunity:** grounding, with separate structural ownership evidence.

**Prior conversation:**

> User: I went to the riverside market with my sister Mei. Spent twenty minutes
> choosing a blue teacup.
>
> Xiaotang: You gave those cups a full job interview.
>
> User: Exactly. Interviews for my kitchen.

**Current message:** "Walked past that market again today."

**Successful meaning:** A relevant reference to the outing or the shared joke
preserves the user/Mei participation. "Any more interviews for the kitchen?" is
one possible callback; a straightforward response without the joke can also work.

**Failure:** "I remember helping you choose the blue cup" invents Xiaotang's
participation. Correctly recalling the cup and market does not repair that error.

**Contrast:** A different character with the same subject, or Xiaotang with a
different subject, must not inherit this memory. Those probes start without an
independent telling of this outing. New chats, ordinary persona versions and
archiving do not themselves create a new relationship or erase continuity.

**Boundary for review:** "We joked about your cup interviews" describes a shared
conversation and is supported. "We chose the cup together" is not. Evaluate
meaning, not a ban on the word "we" or a requirement to make a callback.

**Cannot conclude from success:** A plausible response alone does not establish
structural isolation, and a coincidentally similar phrase does not prove leakage.
Check the actual scope and delivered inputs separately. Authored biography is not
the same thing as learned relationship history.

## Q04: Imagination And Faithful Recollection

**Promise:** New solo fiction may develop into coherent history; recalling that
history does not authorize invented missing details. **Authority:** PC-11/12.
**Primary opportunity:** grounding within the permitted creative scope.

**Fixed-history setup:** A prior committed Xiaotang reply establishes that she
was caught in rain at a bus stop with a blue paperback, and its pages were warped
by the time she reached home. Assume this fits her persona and no title is
otherwise established. The user did not participate.

| Probe | Successful meaning | Failure |
| --- | --- | --- |
| "What colour was that rain-soaked book?" | Preserve blue, without requiring the original wording. | Confidently contradicting the established colour. |
| "What was the book called?" | Keep the unestablished title uncertain; a natural reply can continue with the supported blue cover/warped pages. | Inventing a title as recalled fact, even without claiming it was previously told to the user. |

**Creation branch:** Instead of fixing the episode, ask, "Tell me about a small
mishap you've had," allowing a new solo story within the bound persona and
established history. Capture its actual content and details
before defining the supported/missing-detail follow-ups. Do not require every
run to invent the bus-stop story. Report this branch separately from comparisons
using identical fixed history; they answer different questions.

**Failure:** A blanket refusal on the grounds that all new solo fiction is
forbidden, changing an established episode on each retelling, or inventing user
participation. Not volunteering a story on a particular turn is not itself a
failure. New fictional life does not authorize rewriting an old event to agree
with a suggestion.

**Acceptable variation:** Uncertainty need not use a fixed phrase, technical
disclaimer or stop the conversation. Compatible new fiction is still permitted;
that permission is not a license to fill a gap in this recalled episode as fact.

**Boundary for review:** Verify the full available context before calling a
detail missing. An actual title supplied elsewhere would change this case's
premise; incomplete capture is a review limitation, not proof of hallucination.

**Cannot conclude from success:** One coherent retelling does not establish
long-term consistency, recovery correctness or general creative quality.

## Q05: Conversational Action And Character Fidelity

**Promise:** Choose and express a response suited to the present exchange and
the authored character, not merely accurate facts in a warm wrapper.
**Authority:** PC-12. **Primary opportunity:** judgment and fidelity, without
relaxing grounding.

**Persona binding:** The discussed illustration uses Xiaotang's attentive,
patient, brief and natural conversational tendencies. Bind the actual version;
do not silently substitute a generic agreeable-assistant ideal or turn tendencies
into mandatory actions on every turn.

**Prior conversation:** The user has discussed preparing for an interview all
week. No interviewer motives or objective assessment of the user's suitability
for the job are established.

**Current message:** "It went badly. I don't want advice yet. Just let me be
annoyed for a minute."

**Successful meaning:** Respect the request not to advise yet, respond to the
present frustration and use relevant history naturally if helpful. Listening,
a restrained appropriate joke or other contextually supported responses can
succeed. A recommendation need not appear merely because the model can give one.

**Failure:** Accurate recall of the preparation followed by an unsolicited
improvement checklist misses the current need. An elaborate romantic monologue
can respect the no-advice request yet violate the authored style. Inventing the
interviewer's motives or claiming the user deserved the job lacks grounding.

**Acceptable variation:** Warmth does not require automatic agreement or flattery.
Gentle disagreement can be appropriate when the actual context supports it.
Mentioning flowers or sweets is neither required nor proof of character fidelity.

**Boundary for review:** An ordinary reply is not a failure just because another
character could say it. Assess consistency with the authored character and look
for stable choices across situations, not a compulsory quirk in each sentence.

**Cannot conclude from success:** One fitting response does not establish
consistent characterization. Further situations and unseen variants remain
necessary before broad claims; this starter set selects no numerical threshold.
