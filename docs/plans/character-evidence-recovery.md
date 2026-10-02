# Character Evidence Recovery Design And Plan

Date: 2026-10-02. Status: **Design prepared for review; implementation unstarted.**
The user requested this follow-on through `relay:brainstorm-and-plan` and selected
keeping four windows while comparing joint source selection methods. This plan
owns that bounded slice under the [story-continuity plan](character-story-continuity.md#model-assisted-evidence-selection).
It replaces the earlier instruction to defer all selector planning, not the frozen
studies or their execution boundaries. [ADR 0060](../adr/0060-joint-history-packet-admission.md)
records the proposed packet contract; [protocol v2](../../workflows/evals/character_memory_dev/story_continuity/evidence_selection/PROTOCOL.md)
owns the exact comparison, prompt, schema and proposed execution envelope.

Relevant product agreements: [PC-01/03/04/05/06/07/08/09/10/11](../product-contract.md).
Product intent is unchanged. Work remains serial on the primary `main` checkout;
planning and normal source publication do not start implementation or provider work.

## Outcome And Evidence

Recover useful original dialogue under the four-window policy, including the
context needed to interpret a correction, without silently giving a referring
passage priority over its missing referent. Preserve unresolved meanings when the
available sources cannot settle them. Natural, useful replies remain the eventual
product outcome; selection coverage alone cannot establish that outcome.

The [D04 readout](../../workflows/evals/character_memory_dev/story_continuity/evidence_selection/behavioral/READOUT.md)
shows the current literal selection supplies the restoration but loses the original
location. Supplying the original produced a supported named answer in one witness;
the incomplete packet produced appropriate uncertainty. All eight sources fit the
measured budgets, so four is a retained policy, not a measured token necessity.
The repaired packet was chosen by the evaluator, not a working recovery method.

The observed gap belongs to selection. Separately, current admission greedily tests
individual exchanges, and pre-exposure source revalidation can remove individual
ones. Those mechanics are compatible with independent ranked candidates but do
not preserve a selection intended to be read jointly. No observed D04 miss is
attributed to those later stages; they are design hazards supported by the code.

## Approaches And Recommendation

| Approach | Value | Limitation | Place in this plan |
| --- | --- | --- | --- |
| Existing literal top four | Reproduces the measured baseline with no new model call. | Scores exchanges individually; a distant referent can lose to repeated retellings. | Fixed control. |
| One anchor with immediate neighbors | Small deterministic implementation; sometimes supplies interpretive context. | Proximity misses distant references and can add unrelated material. | Fixed simpler candidate. |
| One model selecting a joint set of original IDs | Can consider reference meaning, competing accounts and qualifications across the whole pool. | Adds a fallible request and cost; structural validation cannot prove its interpretation. | Candidate worth testing under the retained cap. |

Compare the two candidates against the baseline using one common packet contract.
Prefer the simpler method if it supplies equally useful evidence. A full-pool,
budget-only admission policy would change the chosen count constraint; it remains
an alternative for a later policy decision if necessary evidence cannot fit four.
Neither a persistent graph nor rewritten memory is needed to express this design.

## Proposed Behavior

### 1. Materialize The Eligible Pool

Use complete, committed exchanges with original roles, identity, text hashes,
conversation/version binding, chronology and existing lifecycle annotations.
Preserve workspace/subject/purpose/root scope, archive eligibility and ordinary
persona-version continuity (PC-03/04/10). Messages remain read-only evidence;
history cannot independently recreate a removed fact or authorize a write (PC-05/07).

The first comparison uses the protocol's eight-source synthetic pools. It declares
scope rather than testing the database reader. The existing history reader considers the
newest 128 scoped completed exchanges before content/annotation exclusions; this
slice does not widen that boundary. A source absent from the pool cannot be recovered.

### 2. Select One Proposed Packet

Each method returns zero to four distinct original source IDs. Treat the returned
order as presentation order, not admission priority or truth order. The semantic
method receives the complete allowed pool and current question; evaluator answers,
labels, dependency annotations and previous method outputs remain outside its input.
Its response retains the existing `source_ids` schema and supplies no answer,
summary, canonical episode, dependency graph or proposed memory delta.

Select useful combinations, preserving material contradictions and qualifications.
A self-contained correction may suffice alone; an original-only answer route can
also be sufficient when omitted material does not change the warranted answer.
Only an admitted referential passage creates its conditional antecedent need.
Do not impose origin-plus-correction on every recollection, or use earliest,
latest, repeated wording or a correction keyword as automatic authority.

With a missing or ambiguous referent, preserve useful partial/conflicting sources.
The selection does not certify certainty. The eventual answering model must judge
its supplied evidence and express uncertainty naturally (PC-11); permission to
create new solo fiction remains separate from recall of an established episode.

### 3. Admit The Proposed Packet As A Whole

Validate membership, cardinality, complete exchanges, scope and source integrity.
Build both complete requests from exactly that selection and the same mandatory
local/fact/persona context. Preserve both existing input limits, output reserves,
escaping and lifecycle metadata. A selected packet either fits both consumers
unchanged or yields an explicit `packet_unadmittable` result with no dispatchable
packet. No source is removed merely to rescue the remaining selection.

This common rule applies to all three new comparison arms. Keep the legacy greedy
builder for its frozen studies. New service-test preparation must construct the
whole selection directly with the real binders and serializers; a wrapper that
accepts or retries a greedily trimmed packet does not implement this contract.
On selections that already fit, compare against the legacy builder byte-for-byte.

At a later native integration, source revalidation must preserve the same unit:
loss of a selected source invalidates the whole proposed packet, rather than
rebuilding a subset. Scope/hash/annotation or accepted-generation drift remains
fatal. After exposure, the packet is immutable through generation, review and
commit checks. Before any broader-pool model exposure, authorize the actual pool,
not only the final selected subset. Native failure behavior and integration need
their own reviewed binding before that later work can start.

### 4. Isolate The Consumers And Outcomes

Fresh generation and reviewer requests receive identical admitted H. They receive
neither the selector's broader pool nor its reasoning or invented intermediate
text. Existing H roles and lifecycle authority remain intact. A valid source-bound
reviewer result still requires semantic assessment (PC-05).

Record valid empty selection, invalid output, unavailable/oversized selector input,
unadmittable packet and unrun/uncertain attempts as different outcomes. Invalid or
unadmittable selections have no substitute empty packet. A valid partial selection
may still support appropriate uncertainty. The first campaign constructs requests
only; it does not generate or persist a reply.

## Ordered Deliverables

1. **Freeze semantic expectations and mechanical examples offline.** Retain the
   six exposed D cases unchanged. Author N01 ambiguous reference, N02 corrected
   original and N03 no-history controls plus M01's withheld antecedent exactly as
   specified by the existing ten-case ceiling. Make N01/N02 structurally different
   from the repeated original/restoration pattern. Review source-quoted sufficient
   alternatives, material omissions and deletion challenges before new scoring.
   Add isolated scripted capacity/source-loss examples for packet mechanics;
   they are not extra semantic campaign cases. Confirm reference packets can
   represent the intended meanings within four before building the model runner.
2. **Implement the offline candidate mechanics after approval.** Keep inputs,
   standard-library loaders, prompt/schema and tests with `evidence_selection/`.
   Add a cohesive service-test builder beside `story_packet_builder.py` that
   constructs all chosen sources together through existing binding/request APIs.
   Share only the narrow serialization needed; preserve old builders, hashes and
   artifacts. Verify the fixed neighborhood recipe, output validation, joint
   admission, final H isolation and attempt capture with scripted responses.
   These checks establish mechanics, not semantic recovery quality.
3. **Freeze a concrete selector campaign for a separate live decision.** Publish
   exact inputs, judgments, prompt, route/settings, serialized requests, deadlines,
   stop rules and hashes before outcomes. Use the public Model Router boundary.
   The protocol proposes ten one-attempt selector calls and no other model calls.
   Confirm the real route/configuration and owned environment at launch; do not
   infer readiness from the prior D04 service. Preserve every raw result and
   uncertain attempt; audit remains possible without granting resume authority.
4. **Compare source choices if that campaign is authorized.** Assess each actual
   final packet against full eligible-ledger meaning and source quotes. Separate
   candidate availability, selection, admission, qualifications and uncertainty.
   Count unnecessary admissions and request cost without an aggregate quality
   score. A completed comparison may conclude that neither candidate is useful.
5. **Propose downstream work only from a useful result.** A selected packet gain
   must preserve controls and material qualifications, not merely add an answer
   string. If the simpler candidate matches it, prefer that path. A later bounded
   answer/reviewer comparison must freeze its own requests and measure supported
   naming, uncertainty, ownership and naturalness. Native persistence/continuity
   and runtime adoption require their own evidence; the native turn-7 gate stands.

The requested planning iteration ends with this reviewable design and protocol.
The next implementation slice is deliverables 1-2 only. It ends at offline readiness,
with a complete proposed live packet available for review before any launch.

## Acceptance And Research-Informed Checks

Use [When Knowledge Changes and RAT](../../workflows/evals/character_memory_dev/story_continuity/evidence_selection/RESEARCH_REVIEW.md)
as methodological references. Semantic relations below come from ADE's product
contract and source labels; code tests cannot establish natural-language truth.

| Change or condition | Expected assessment |
| --- | --- |
| Direct correction becomes referential, with its antecedent available | A sufficient named-answer route remains possible; resolving an admitted reference requires its referent. Different source sets may be valid. |
| Genuine correction changes the original account | Selected evidence must preserve the changed meaning; retrieving the original alone cannot earn settled-answer credit. |
| Necessary antecedent is withheld | Name the availability gap; useful partial evidence is allowed. No credit for reconstructing the missing answer. |
| Two plausible referents remain unresolved | Preserve the uncertainty-bearing evidence rather than silently elect one. |
| Irrelevant dialogue is present or wording is paraphrased | Check the source-relative meaning and relevant qualifications before calling it an invariant. Equivalent text is not automatically equivalent evidence. |
| Archive/version changes within the same relationship | Eligibility stays consistent; this campaign's fixture metadata alone does not qualify database behavior. |
| Historical source links to a removed fact | Retained testimony remains attributed history; it does not make the fact active again. Reuse existing lifecycle tests. |
| One selected source exceeds a consumer budget or becomes unavailable | No partial proposed packet is dispatched; record the affected layer. |

Freeze any evaluator reference contrasts before scoring. These relationships do
not enlarge the ten-call ceiling or require identical wording/IDs across answers.
Use source quotes to judge supported naming, qualified evidence and optional detail.
Avoid a binary retrieved/not-retrieved score or fixed uncertainty phrase.

For candidate continuation, require a useful packet gain versus both simpler arms
under the protocol's qualification rules, with no control regression. Report gains
on exposed D cases separately from new N01/N02 controls. A gain confined to the
known restoration pattern warrants limited follow-up, not native integration.
An ambiguous or unassessable control cannot support a positive continuation claim.
N03's empty semantic selection is conformance, not matched superiority over methods
that always fill available slots. A sufficient subset is not partial evidence merely
because optional exchanges are omitted.

Mechanical verification covers exact IDs/text/hash preservation; duplicate/unknown
IDs; zero/four/excess selections; complete U/A windows and annotation retention;
generation versus reviewer overflow; mandatory-context preservation; shared H;
source loss before/after exposure; no label/reasoning leakage; no retry after an
uncertain attempt; and audit of earlier evidence after a later stop. Use existing
`uv run --locked` tests. Broaden only for touched ownership boundaries, and report
database/private-evidence skips. Runtime wiring would also require disposable
PostgreSQL guard/worker tests, which are outside this first workflow slice.

## Files And Boundaries

| Owner | Existing entrypoints and planned responsibility |
| --- | --- |
| Workflow | `workflows/evals/character_memory_dev/story_continuity/evidence_selection/`: new inputs, judgments, prompt/schema, freeze, public-router runner, receipts and readout. Keep completed artifacts immutable. |
| Service-test preparation | `services/ade-api/tests/agent_runtime/story_packet_builder.py` and adjacent story tests: reuse serialization and add a separate whole-selection builder without altering pinned historical construction. |
| Future runtime integration | `history_admission.py`, `history_attempt.py`, `turn_history_setup.py`: explicitly represent joint selection and preserve it through admission and revalidation if later adopted. |
| Source and authority | `persistence/history.py`, `persistence/history_guard.py`, `natural_memory_binding.py`: existing scope, integrity, lifecycle, handles and generation fencing. Broader candidate retrieval stays separate. |

Runtime paths above are relative to
`services/ade-api/src/ade_api/features/agent_runtime/`. No schema migration, memory
service, episode store, graph/proxy model, second reviewer, semantic keyword rules,
rewritten summaries, new fact types, deployment or production-default change is
part of this plan. Atomic selection trades opportunistic salvage for explicit
failure when even one optional selected exchange makes the whole packet unfit;
measure that cost before later adoption.

## Research Revisit Conditions

Keep the [reviewed shortlist](../../workflows/evals/character_memory_dev/story_continuity/evidence_selection/RESEARCH_REVIEW.md)
as a small watchlist. Revisit primary sources when runnable implementations arrive,
methods or results change, a design depends on an unverified claim, or new work
directly tests multi-turn corrections, ambiguous references and missing evidence.
Use each update to ask whether it changes an ADE decision or test; author benchmark
improvements alone do not select a product architecture.

Suggested cadence is a brief monthly scan while recovery is being developed, plus
reviews at consequential design gates. This cadence is a recommendation for later
scheduling. Preserve returned reports unchanged and capture, review and promote
stable findings.
Further consultation is unnecessary for offline preparation; reconsider it if
the concrete design exposes competing source-authority interpretations or a
recovery/scale question the shortlist cannot answer.
