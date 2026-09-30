# Character Voice And Memory: Returned-Report Assessment

Date: 2026-09-30. Status: reviewed findings and proposed next decision, not an
adopted fiction policy, implementation plan or acceptance result.

Subsequent user decision, 2026-09-30: [PC-11](../../product-contract.md#improvised-character-history)
permits solo invented past experiences and expects their later consistency within
each user-character relationship, with authored biography as the common foundation.
[ADR 0050](../../adr/0050-consistent-improvised-character-history.md) records that
direction. The assessment below preserves the pre-decision analysis; its open
permission and cross-user scope questions are resolved; implementation remains open.

## What Changes Our Next Decision

**Keep the architecture. Separate creative freedom from evidential authority.**
The reports sharpen the question from "warmth versus grounding" to whether
Xiaotang may establish new solo autobiographical episodes, and what authority
those episodes have when encountered again. They do not settle that choice.

The most consequential verified finding is that **zero saved-fact changes does
not mean zero future memory effect**. Accepted assistant replies are persisted
as dialogue and can become eligible historical evidence. A transcript proves
that Xiaotang said something; it does not by itself prove authored biography,
user endorsement, current truth or user participation. Actual downstream
misuse of a generated anecdote remains a hypothesis, not an observed result.

Two concrete source-channel limits also deserve attention before more prompting:
recent dialogue cannot directly ground a reviewer conflict, whereas retrieved
history can; current endorsement may cite a recent assistant proposition, but
not one supplied only as retrieved history. These are representation/authority
questions, separate from the permission to improvise character stories.

Relevant agreements: PC-01/03/04/05/06/09/10 in the
[product contract](../../product-contract.md). Preserve natural conversation,
same-character continuity, immutable definitions, model-owned interpretation,
structural enforcement, archive eligibility and minimum direct ownership.
This assessment changes none of them and adds no ADR: no new contract is adopted.

## Reports And Evidence Boundary

All four reports were read in full. A/B labels distinguish supplied reports,
not known model versions or demonstrably independent research processes.

| Report | Main contribution | SHA-256 of unchanged original |
| --- | --- | --- |
| [Pro A](reports/character-contract-pro-a-2026-09-30.md) | Transcript propagation; recent/H conflict asymmetry; evidence-authority tests. | `7880900c12e6bac5ba0ad3e20c01450cc9cb25d764931f37442ea888170582d4` |
| [Pro B](reports/character-contract-pro-b-2026-09-30.md) | Habit versus preference; elliptical endorsement; longitudinal propagation probe. | `42888c08565c7d0f75571bb778183b8b55a5cb213072446cf78f0c215d19f3ed` |
| [Research A](reports/character-contract-research-a-2026-09-30.md) | Separate claim provenance and referent; measure warmth and source comprehension; keep fiction choice open. | `6b749f6e7053095ff4af94b60749e027d0cb928aa413e234be2382ed5f4c9a5b` |
| [Research B](reports/character-contract-research-b-2026-09-30.md) | Prior assistant speech is not automatically canon; warmth can affect accuracy; explicitly framed collaborative fiction differs from claimed shared past. | `e24b4c99e5b8b2df545b379c084508c6b8b336d97467d347f646eb48b30d86fb` |

Original citation tokens, formatting, trailing-space hard breaks and long files
are preserved as evidence, not normalized. Embedded research citation tokens
are not independently resolvable; use the checked public sources below.
Pro A contains a malformed source URL followed by its own corrected URL. Its
substantive findings were checked against local source rather than that bad link.

Both Pro reports identify source anchor
`2e3322db32946df947f002143a964ec440628715`. This assessment checked the primary
checkout on `main` at `90b72b435f2d54af00c3c44d413518a628ee94aa`; the difference
from that anchor is confined to two consultation documents, not runtime code.
The research reports are literature syntheses, not ADE source audits. Agreement
among reports is not replication, and their recommendations are not authorization.

The earlier live summaries concern `5af403b53fbf40c2be4bfc9250d70973c77783b5`;
the trial subsequently adopted `9cb6aa047ddb30f216aa097cd0f21dd90b0a81e8`.
No old observation is relabeled as evidence from today's mainline or a new trial.
See the [handoff packet](character-contract-review-brief-2026-09-30.md).

## Verified Source Findings

### Dialogue Persistence Is Separate From Fact Mutation

[`commit_natural_memory_review`](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_commit.py)
returns an empty result when no operations exist.
[`RunFinalizer.commit_success`](../../../services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py)
still appends the accepted assistant message and completes the run in the same
transaction. [`read_history_corpus`](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/history.py)
reads succeeded user/assistant exchanges within workspace, subject, purpose and
definition-root boundaries, including archived conversations, subject to its
capacity, content, integrity and annotation checks. Eligibility is not guaranteed
retrieval, admission or later model use.

**Implication:** record complete fact deltas and accepted dialogue separately.
Do not describe a no-op fact review as proving no memory-trust consequence. If a
continuation promotes generated speech into canon or shared experience, diagnose
authority interpretation before blaming ranking or adding storage.

### Reviewer Acceptance Is A Narrower Claim Than Reply Faithfulness

[`natural_review_request`](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_reviewer.py)
and [`NaturalBindingMap.packet`](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_binding.py)
supply current/recent dialogue, held facts/entities, the candidate reply, allowed
fact contracts and optional H history. They do not supply the bound persona or
base generation template. Therefore absence from that packet cannot distinguish
an authored Xiaotang childhood detail from a newly invented solo episode.

The H instructions explicitly distinguish unsupported details from positive
contradictions. This is intentional under
[ADR 0047](../../adr/0047-recalled-dialogue-attribution.md), not proof that every
accepted sentence is supported. `_validate_conflict` checks exact source binding;
it does not independently establish semantic contradiction. A bound conflict
rejects the entire attempt before sibling writes are prepared.

**Implication:** do not introduce a generic unsupported-claim veto or silently
repurpose the reviewer as a persona/canon judge. Such changes would need an
explicit mandate, sufficient evidence inputs and measurement of false rejection
and lost otherwise-valid updates. This assessment does not recommend them now.

### Source-Channel Representation Limits Are Real

[`NaturalConflict`, `EndorseAssistantEvidence`, `ResolveUserEvidence`](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_review.py)
and [`_bind_evidence` / `_validate_conflict`](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_policy.py)
confirm these boundaries. Read-only model-schema checks produced:

| Representation | Result |
| --- | --- |
| Conflict with an H quote | Schema accepts |
| Conflict with only a recent A reference | Schema rejects |
| Conflict with only a recent U reference | Schema rejects |
| Current endorsement with recent A support | Schema accepts |
| Current endorsement with H support | Schema rejects |
| Current resolution with H support | Schema rejects |

For a speaker mismatch supported only by recent dialogue, with no corresponding
F/E or H grounding, the reviewer has no valid direct conflict representation.
This is a schema coverage limit, not evidence that the model necessarily makes
or overlooks that error. Passing a schema check also does not establish binding
or semantic validity.

The endorsement distinction matters for Mandarin such as "对，就是那股劲儿，
太对我胃口了" when only H supplies the thing being endorsed. The existing
[fixture/test](../../../workflows/evals/character_memory_dev/tests/test_attribution_contract.py)
instead repeats the preference in the current message and uses `direct` evidence.
It proves full current assertion support, not H-backed elliptical endorsement.
Allowing H to supply a referent for a current assertion is conceptually different
from allowing H to authorize a write alone, but both are currently excluded from
write support. The commit revalidation also requires write sources to remain in
the originating conversation; broadening a regex alone would not suffice.

**Root cause and owning layer:** channel-specific wire contracts and binding/
commit authority, not missing prompt encouragement. If these capabilities are
selected, amend that contract end-to-end with regression tests. Do not fabricate
citations, disguise H reliance as `direct`, or add keyword rules (PC-05/06/09).

### Prompt Incentives And Preference Meaning Remain Test Questions

The [base template](../../../content/prompts/system/chat/chat_v20260926.py)
uses literal-real-person wording; the
[persona](../../../content/personas/personas.jsonl) promises to remember
preferences, emotions and recurring details; the
[runtime instructions](../../../services/ade-api/src/ade_api/features/agent_runtime/context.py)
constrain recall and capability claims. This is a plausible competing-incentive
hypothesis, not a demonstrated cause of the listening anecdote. If tested, separate
identity wording from episode permission while keeping admitted evidence fixed.

The [hands-on memo](../../../workflows/evals/character_memory_dev/hands-on-feedback.md)
also reports frequent listening becoming a preference. That is a distinct
meaning-preservation concern, not resolved by better speaker attribution. Test
task-driven listening against genuine implicit liking; do not require a literal
"喜欢" token or generalize all frequent behavior into a preference. No new
model output or private receipt was independently reproduced for this assessment.

## Research Checks And Corrections

Verification was limited to claims useful for the next decision, not the entire
bibliography. The following primary publication/author-institution pages were
checked on 2026-09-30; abstract-only checks are identified explicitly.

| Checked source | Usable conclusion | Important limit |
| --- | --- | --- |
| [LongMemEval, ICLR 2025](https://arxiv.org/abs/2410.10813), abstract | Separates extraction, multi-session/temporal reasoning, updates and abstention; decomposes indexing, retrieval and reading. | Factual memory evaluation does not settle character warmth or fiction permission. No benchmark effect size transfers to ADE. |
| [Dialogue NLI, ACL 2019](https://aclanthology.org/P19-1363/), abstract | Dialogue consistency can be evaluated separately through NLI. | Consistency is not proof of recollection provenance; no claim here to have audited its full dataset or methods. |
| [Saffarizadeh et al., JAIS 2024](https://aisel.aisnet.org/jais/vol25/iss3/9/), abstract | Two randomized text/voice-agent experiments report an indirect self-disclosure effect on trustworthiness through anthropomorphism. | Not a comparison of newly invented versus authored character biography. |
| [Chung and Kang, 2023](https://pure.ewha.ac.kr/en/publications/im-hurt-too-the-effect-of-a-chatbots-reciprocal-self-disclosures-/), author-institution abstract | Twenty-one Korean-speaking participants, one conversation each; self-disclosure affected perceived support, with intimacy limitations. | Small, short, topic-specific study; cannot qualify sustained Mandarin fictional memory. |
| [Ibrahim et al., Nature 2026](https://www.nature.com/articles/s41586-026-10410-0), article | Warmth fine-tuning increased errors in studied tasks; prompting effects were weaker and less consistent. Supports testing the actual character configuration. | Does not show that ADE's identity sentence caused its anecdote, or that warmth inevitably sacrifices accuracy. |
| [Ding et al., AAAI 2025](https://ojs.aaai.org/index.php/AAAI/article/view/34550), publication abstract | Citation presence, even random citations, increased reported trust; checking citations was associated with lower trust. | Not a causal experiment on Mandarin recollection phrases or proof that memory badges should be banned. |

The reports do not supply a direct study of unmarked solo improvisation versus
authored-only biography in sustained Mandarin character chat. This review also
does not establish that no such study exists anywhere. General self-disclosure
evidence motivates comparison, not automatic approval or prohibition.

Research B provisionally favors asymmetric self-fiction; Pro A favors a narrower
initial default; Research A keeps the final choice open. That disagreement is
useful product judgment, not an empirical tie broken by counting reports.

Two qualifications to proposed examples matter before turning them into tests:
"要按我的习惯，我大概会..." still presupposes a habit; "大概" does not remove
every unsupported commitment. Prefer a clean hypothetical such as "要是换成我，
我会..." for that control. Likewise, an explicitly fictional shared scene is
not actual shared history, but a mutually understood frame must be established;
the model cannot relabel an ordinary false recollection as roleplay after the fact.

The memory-poisoning, witness-memory, dependence, legal, repair and remaining
quantitative claims were not independently audited. They are not needed for this
decision and are not promoted into ADE requirements or causal safety claims.

## Insight Disposition

| Disposition | Insight | Integration or next action |
| --- | --- | --- |
| Use | Retrieved speech has transcript authority, not automatic truth or canon authority. | Interpret future observations using this distinction; preserve speaker/time/source evidence. |
| Use | Zero fact delta is not zero dialogue persistence. | Report both outcomes, plus full entity/revision/generation deltas when testing. |
| Use | Separate style, reply fidelity, reviewer interpretation and persistence. | Keep independent labels, including supported recall and legitimate creativity as positive controls. |
| Use | Current reviewer coverage has specific channel/input limits. | Record verified limits above; do not claim general fact-checking or persona approval. |
| Test | Self-only anecdotes, expressed stance and explicit imagination have different user meaning. | Matched Mandarin examples first; ask about warmth, provenance and expected future consistency. |
| Test | Recent/H asymmetry and elliptical agreement affect ordinary conversation. | Schema mechanics checked here; choose desired behavior before a bounded native/reviewer probe. |
| Test | Habit is being widened into preference. | Contrast obligation/contextual behavior with implicit and explicit liking, without phrase gates. |
| Test | Earlier generated episodes acquire inappropriate authority later. | One bounded continuation arc; distinguish recalling a statement from inventing canon or user participation. |
| Park | Literal identity wording caused the problem. | Hypothesis only; use a separate causal ablation if the selected contract still produces failures. |
| Park | Dynamic canon, new episode storage, broader reviewer mandate, elaborate trust UI. | Require a selected product need and demonstrated residual failure first. |
| Discard | Consultant agreement or research results qualify ADE behavior. | Neither replaces direct native evidence or release gates. |
| Discard | Universal grounding, keyword bans or mandatory uncertainty markers solve memory trust. | They conflate expression with history and may still preserve false provenance claims. |

## Smallest Recommended Next Step

First resolve one human product question with matched examples, without model
calls: **may Xiaotang invent unmarked solo past episodes, and if so should the
user expect those episodes to remain consistent later?** Keep authored biography,
spontaneous opinions/metaphors and faithfully grounded user/shared recollection
available in every option. Compare expressive stance, explicit imagination and
an unmarked solo anecdote, matched for length, vividness and emotional content.
Do not choose a winner by contrasting a rich anecdote with a robotic refusal.

Then select one small natural-Mandarin probe, not the union of all suggested
experiments: source attribution, habit/preference, full/elliptical endorsement,
and a short continuation after a self-story. Keep its purpose diagnostic. Separate
the fiction-policy choice from any change to H write support or recent conflict
grounding. Retain first attempts and failed outputs; verify actual immutable
definition bindings and admitted packets, not merely intended settings.

Evaluate reply fidelity, naturalness, reviewer decisions and full persisted
outcomes separately. Include both faithful recollection and creative-expression
positive controls. Additional provider requests need explicit authorization;
target turns are not the same as provider calls. A larger user study, causal
prompt matrix or schema extension is conditional follow-up, not today's task.

## Verification And Unchanged State

- All four imported files match the supplied SHA-256 hashes byte-for-byte.
- `uv run --locked python -m pytest workflows/evals/character_memory_dev/tests/test_attribution_contract.py -q`: **18 passed**. These are offline packet/binding tests, not model-quality evidence.
- Six read-only schema cases produced the results shown above. No provider or database experiment was run.
- Authored Markdown whitespace and local links were checked separately from deliberately unchanged report formatting.
- Runtime, persona, base template, product contract, schemas and release bindings remain unchanged. No deployment, provider use, commit or push accompanied this assessment.
