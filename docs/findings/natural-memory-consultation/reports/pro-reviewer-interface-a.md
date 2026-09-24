# Verdict: redesign the reviewer interface before adding more prompt patches

**Yes—ADE is asking the model to supply several choices that belong to the server.** The smallest durable correction is to separate the **model-facing semantic decision** from the **server-owned mutation record**.

Keep one reviewer call initially, but make its output smaller: which supported assertion changed, which supplied target it concerns, and whether the result is a write, a deferral, or a detected contradiction. The server should supply subject identity, target versions, source roles, message identifiers, offsets, hashes, and database identities wherever those are already determined.

**Do not relax the native validator or silently repair today’s invalid responses.** Introduce a new, explicit interface whose valid responses do not require the model to repeat those server-owned facts.

There is also a substantive validator issue: **the inspected source does not fully enforce the documented requirement that assistant-derived evidence requires current-user endorsement.** That needs correction alongside the interface simplification.

## Inspection and evidence boundary

| Material                                                                                                                                             | Exact commit inspected                     |
| ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| Published consultation brief                                                                                                                         | `aea2719c1e2310d0c5c1a10b9fe75c0d0e3c14e5` |
| Request builder, proposal schema, source binder, native preparation/commit path, capacity binding, diagnostic runner/scorer, relevant tests and ADRs | `92809c4c1cdae7d7aa3dd5f09e42b2b3bf310e75` |

The comparison between these commits shows only the brief’s publication/access amendment. I did not substitute `main`.

The required public sources were accessible. **I did not execute tests or inspect private captures, databases, credentials, or runtime ledgers.** The three diagnostic outcomes are maintainer-reported observations. Their separate source versions, partial coverage, and changed output allowance prevent treating them as a failure-rate estimate or completed A/B comparison.

Runtime paths below are relative to `services/ade-api/src/ade_api/features/agent_runtime/`.

# Root-cause analysis

## 1. The model-facing schema permits choices that the application later forbids

**Source-backed finding.**

`NaturalAdd` exposes `entity_ref: string | null` for every fact type. A Pydantic validator then rejects a nonempty reference for a subject-kind fact. `_resolve_add_entity()` already knows how to resolve a subject fact: it returns the server-bound `subject_id`. The model contributes no useful identity decision in that case. Nevertheless, the request supplies subject entity identifiers and asks the model to remember that this particular identifier must not be returned.

The DeepSeek branch compounds that mismatch: it sends `response_format={"type":"json_object"}` and places the schema in instruction text. **The shown request does not request schema-constrained decoding.** The test suite expressly checks both JSON-object mode and the nullable string field. Stronger wording does not turn that field into a structural subject/related-entity distinction.

**Counterexample:** “我早上喜欢喝咖啡。” becomes a preference proposal containing the correct bound subject’s UUID. The semantic ownership is unsurprising, but the serialization violates the application contract and aborts the turn.

**Minimal correction:** subject-fact additions should have **no model-supplied entity field**. Related-entity additions should have a separate shape containing only a selection from supplied, subject-scoped candidates or an explicit new-entity declaration.

Related-entity selection is not wholly server-owned: deciding whether “Roxy” refers to pet E1 or E2 can require semantic interpretation. Remove the redundant subject choice without pretending that all entity resolution is deterministic.

## 2. Source authority is presented as a citation-choice problem when much of it is predetermined

**Source-backed finding; its causal contribution to the observed errors is an inference.**

The request includes the current message separately and also supplies a heterogeneous `source_messages` list. The response must repeat `message_id`, `quote`, and `role`, plus a separate `evidence_quote`. Yet the binder accepts `user_assertion` and `user_endorsement` only when they identify the already-known current user message.

For the Rocky→Roxy correction, the model needs to identify the existing fact and the new assertion. It does **not** need to choose which user message authorizes the write: that is fixed. ADR 0034 correctly explains why the older Rocky statement was unnecessary authority for that correction, but addresses the problem through another instruction rather than changing the interface.

**Minimal correction:** direct writes should return an exact quote from the current message, not a freely selected authority message and role. The server binds that quote to the current message and derives its identity, offsets, hash, and authority classification. Existing targets should be selected through request-local handles whose versions are retained server-side.

This is **binding a newly defined response format**, not deleting invalid citations from an old response.

### A separate semantic boundary must be reconciled

The design still promises:

> “One of my dogs is a Husky” → “Rocky or Roxy?” → “Roxy”

with both user spans retained. The current binder cannot cite the earlier user span, while the latest answer does not contain “Husky.” The documentation and implemented source contract therefore disagree about this case.

**Current authorization and historical support are different things.** My recommendation is to preserve the current-user anchor while permitting a narrowly identified earlier antecedent as **support**, never as independent authorization or an invitation to extract unrelated old facts. That requires an explicit contract amendment. Until then, mark this form of clarification unsupported rather than inventing provenance.

## 3. The native binder’s endorsement requirement is asymmetric

**Source-backed validation gap; the counterexample below was traced, not executed.**

`bind_natural_sources()` enforces:

> `user_endorsement` requires an `assistant_referent`.

It does **not** enforce the reverse condition:

> using an assistant referent to supply the asserted proposition requires current-user endorsement.

Meanwhile, `_validate_claim()` combines all bound source quotes when checking value support. `_value_supported()` is a substring/token-overlap check, not an entailment or endorsement check.

**Constructed counterexample:** an earlier assistant says “Roxy is a Husky”; the current user merely says “Roxy.” A proposal labels that current span `user_assertion`, cites the assistant statement as `assistant_referent`, and proposes Husky as Roxy’s breed.

With an otherwise valid entity/slot, the shown binding and value-support checks can accept this combination: the current user supplies the required authority-role presence, while the assistant supplies “Husky.” That does not satisfy the documented distinction between a bare name and an affirmative endorsement.

The inspected test named `test_assistant_referent_requires_current_user_endorsement` covers a positive endorsement and an unavailable referent, but does not test this reverse-direction condition.

**Minimal correction:** make direct assertion, reference resolution, and endorsement explicit evidence modes with allowed source combinations. Assistant text must not supply new factual content in direct-assertion mode. Endorsement mode must require a current affirmative anchor tied to the proposition being endorsed.

This strengthens the authority boundary; it does not solve semantic interpretation universally.

## 4. Deferral currently requires too much of a completed mutation

**Source-backed representational problem.**

`NaturalReviewDecision` requires every disposition to correspond to a full proposal. Preparation binds and validates the proposal’s evidence, value, entity, target and collision rules **before** filtering deferred operations.

**Counterexample:** two pets exist, neither has a saved breed, and the user says “One of them is a Husky.” Reporting `unresolved_reference` should not require choosing a pet to manufacture a valid `NaturalAdd`.

Similarly, the uncertainty check can reject a speculative value before its explicit no-write disposition is considered. The existing all-deferred test uses the self-contained assertion “I live in Toronto”; it does not establish that a genuinely unresolved claim can be represented without guessing.

**Minimal correction:** use one per-item result union:

* A **write** contains the complete mutation intent and evidence.
* A **defer/no-save** contains the current claim anchor and reason, without mandatory speculative value or target.
* A **contradiction** identifies the conflicting current interpretation and exact candidate-reply span, without manufacturing an executable mutation.

That also removes the parallel `proposals`/`claim_dispositions` arrays and their model-generated `claim_id` join. Malformed writes still fail; legitimate abstention simply stops requiring fabricated completeness.

## 5. Output exhaustion is a separate failure class—not evidence that the entire architecture needs replacement

**Reported observation plus source-backed handling limitation.**

The published evidence supports a bounded conclusion: one high-thinking response reached 1,024 completion tokens, reported `length`, and supplied no visible JSON; the separately versioned 4,096 diagnostic progressed further. It does not establish a generally sufficient output allowance or prove that high thinking is the wrong setting.

The implementation wraps most parsing and validation failures as `natural_review_validation`. The imported `_response_content()` checks for nonempty content but does not inspect the finish reason. Also, the decision model defaults both arrays to empty, so `{}` can become a structurally accepted no-op.

**Minimal correction:** distinguish output truncation, malformed output, invalid target/source binding, semantic rejection, and explicit no-change. Require the new top-level result shape rather than treating omitted fields as intentional emptiness. A length-terminated response should not qualify as a completed review merely because some JSON parses.

A smaller interface should reduce avoidable output and instruction burden, but **whether it reduces reasoning-token consumption is unmeasured**. Do not assume that simplification automatically makes 1,024 sufficient.

# Recommended design: one compact semantic review, followed by deterministic binding

Keep the present order initially:

**Generate candidate → obtain one semantic review → bind and validate → atomically finalize.**

Change the boundary, not the storage architecture.

| Model should decide                                                                                    | Server should supply or derive                                                                    |
| ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| Whether information is a supported assertion, change, correction, ending, removal, or unresolved claim | Workspace, subject and character/conversation bindings                                            |
| Which supplied related entity or existing assertion is meant                                           | Database IDs behind request-local handles; target versions and accepted generation                |
| The independently editable assertion, preserving morning/evening and other scope                       | Record IDs, revision IDs, normalized keys and derived entity labels                               |
| Which exact current phrase supports the decision; whether assent endorses a supplied proposition       | Message identity, author role, chronology, offsets, hash and permitted evidence-role combinations |
| Whether the candidate explicitly contradicts the interpreted claim                                     | Typed disposition validation and final transaction outcome                                        |

Use short, request-local handles such as an existing-fact reference rather than asking the model to reproduce UUIDs and versions. The map must be bound to the accepted snapshot; it must never resolve against newer state silently.

Separate input sections for **current authority**, **historical context**, **available referents**, and **mutation targets**. Do not expose everything under a generic “sources” label. Preserve complete-message context around selected spans so quotation, negation and scope remain interpretable.

Remove `entity_ref` from subject writes, `new_entity_label` as an independent factual choice, repeated source identity/role fields, duplicate `evidence_quote` representation, and the parallel disposition join. Keep exact-quote matching; do not add fuzzy citation repair.

For example, morning coffee should require the model to express approximately:

> Add a drink preference: “prefers coffee in the morning,” supported by this exact current-user phrase.

It should not require a correct subject UUID convention, message UUID, source-role enum, duplicated quotation and a second object confirming that the first object is allowed.

**Scope remains a semantic responsibility.** The original omission of “morning” is not fixed merely by removing identity fields. The native diagnostic explicitly requires morning scope and separate evening-tea identity; those checks should stay.

# One credible alternative: two bounded reviewer phases

**Rank this second, not as the next default.**

Split memory work into:

**Current-claim extraction and evidence interpretation → reconciliation and candidate-consistency review.**

The server validates the intermediate result; the second phase receives those claims plus current targets and the candidate reply. Neither phase writes memory. Final mutations and reply still commit together after native validation.

| Design                                    | Advantage                                                                      | Cost and failure risk                                                                                          |
| ----------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| **Compact single reviewer — recommended** | Removes clerical work without another model dependency                         | Semantic extraction, reconciliation and reply checking still share one call                                    |
| **Two bounded reviewer phases**           | Separates evidence interpretation from target matching and lifecycle decisions | Adds a call, latency and intermediate failure surface; extraction mistakes can propagate rather than disappear |

Adopt the second only if the compact interface still shows **semantic task interference**—for example, good extraction and good target matching separately but poor combined performance. The reported UUID/citation failures alone do not establish that need.

## Should reply and memory remain coupled?

**For the next diagnostic, yes.** The current coupling makes reviewer failure a chat-availability failure, but it also avoids presenting a candidate whose interpretation has not passed the declared check. The commit code preserves a single mutation generation and transaction-owned write path.

Simply delivering rejected candidates would hide the problem rather than solve it.

An explicit “reply delivered, memory not updated” product mode could eventually be legitimate. It would require new outcome semantics, truthful UI treatment, no silent catch-up, and a policy for candidates whose factual interpretation was not checked. It is not equivalent to current atomic success and should not be introduced as an exception handler during this interface repair.

# Focused verification before restarting comparison

## Offline regressions

| Test group                    | Required result                                                                                                                                                                                                      |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Server-owned binding**      | Subject writes contain no entity choice. Request-local targets resolve to the original subject/version. Unknown, cross-subject and stale handles fail without remapping.                                             |
| **Reported diagnostic cases** | Morning coffee retains scope; evening tea creates an independent assertion; Rocky→Roxy uses current correction authority and the existing target’s lineage.                                                          |
| **Evidence modes**            | Bare “Roxy” cannot endorse assistant-invented Husky. Explicit assent can endorse one proposition. Older user text cannot become current authority. Any approved antecedent-support path preserves its distinct role. |
| **Real deferral**             | An unresolved pet claim needs no guessed pet/value; an unrelated supported update may survive. All-deferred output creates no entities, facts, embeddings or generation advance.                                     |
| **No-save and contradiction** | Same-turn no-save dominates equivalent writes in either order. Genuine contradiction rejects atomically; an unrelated question is not a write veto.                                                                  |
| **Completion and provenance** | Truncation, empty/missing result shape, repeated/ambiguous quotes and invalid source combinations receive distinct failures. No partial JSON salvage or hidden retry.                                                |

Keep the existing successful-outcome, rejection, source-lineage and generation-fence assertions. Do not weaken the mutation scorer to accommodate the new response format. The current scorer checks committed revisions and semantic case requirements, not merely whether a reviewer returned parseable JSON.

## Separately authorized live diagnostic

First test the new interface on the reported three-case sequence plus the endorsement, genuine-deferral and same-turn-no-save controls. Keep the route, thinking setting, and one declared output envelope fixed while assessing the interface change. Then assess a different completion envelope as a separately identified experiment—not a quiet alteration of the frozen comparison.

Record failures by stage, required state outcomes, source correctness, scope preservation, latency, usage, and **useful delivered replies per attempted turn**. Preserve first failures and all spent requests. Repeated tests, if authorized, should be predeclared independent trials, not rerolls until a pass appears.

Only after that diagnostic supports the interface and envelope should ADE publish a new frozen A/B binding and request schedule. The earlier positions are historical diagnostics, not accumulated progress toward the new comparison. That distinction is already explicit in the publication and should remain.

The model-facing format/evidence modes need an explicit amendment to the accepted contracts, particularly ADRs 0029/0034. Changing completion capacity, reviewer-call count, or reply/memory coupling needs its own declared envelope or product-contract amendment.

# Uncertainties and evidence that would change the recommendation

The observed recurrence does not establish that DeepSeek is intrinsically unsuitable, that prompts never help, or that one-call review is fundamentally unreliable. Nor does a successful 4,096-token diagnostic establish that the allowance is sufficient across the workload.

My recommendation would change if the compact interface removed metadata failures but substantial semantic errors persisted; that would strengthen the case for two-phase review or a different qualified model. Conversely, consistently correct semantic decisions with deterministic binding would argue strongly against adding another reviewer.

High, measured reviewer-induced chat failure after interface repair could justify revisiting coupling—but only as an explicit availability/product decision. And source-constrained decoding, if demonstrated through the actual pinned route, could reduce structural errors, though it would not prove correct entity meaning, scope or endorsement.

**Bottom line:** keep ADE’s memory foundation. Stop asking the reviewer to reproduce the persistence contract. Give it a small semantic task, make the server bind what it already knows, and strengthen the endorsement boundary. That is a more durable next step than another paragraph telling the model which UUID or source role not to emit.
