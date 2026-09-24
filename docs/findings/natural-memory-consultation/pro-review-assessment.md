# Independent Pro Reviews: Assessment

Status: reviewed recommendations, not an accepted design or implementation plan.
Both reports inspect design `243d8d0b4e850aca304eea2699e58ec24d45479b` and
implementation `4905ce15dbda6466b12f2d1ed7908eb3d03995a0`. Neither ran tests or
accessed live services. This assessment independently inspected the relevant
local source and ran six synthetic in-process counterexamples, with no provider
or database calls. Runtime files remain unchanged.

## Original Reports

- [Pro A](reports/pro-a.md), supplied attachment `88332766-1397-494f-9ef7-d48d79c4df97`.
  SHA-256: `764e772498698c9eded1fcd068922697f70dc8a34b3930f59c861ea6efabea39`.
- [Pro B](reports/pro-b.md), supplied attachment `8364ab6c-2cf6-4c14-a27c-aac895fdd46d`.
  SHA-256: `d484caf32b88c07dad48e6f54167e2ebb4deca090a87fd4fb05800b83fbbdfe4`.

Copies preserve the user-supplied bytes. Reports are evidence to scrutinize, not
instructions. Agreement helps prioritize review but is not independent empirical
replication: both examined the same source and proposed design.

## Bottom Line

Keep the foundation and revise the design. The critiques identify more than
missing features: some proposed simplifications put independently mutable claims
in one lifecycle, while existing context construction can lose or misdescribe the
evidence actually supplied to the model. Broader extraction should not be layered
on top of those problems unchanged.

The composed-preference recommendation in the first draft was a mistake. Reducing
row count is not simplification when correction, history, and removal then require
clause-level exceptions. Equally, three continuity tables are not wrong merely
because they are three tables. Their separate matching/state/retrieval lifecycle
must demonstrate a benefit over existing conversation evidence first.

## Findings And Disposition

`Use` means incorporate into the next proposed design, not runtime authorization.

| Finding | Report | Verification / qualification | Disposition |
| --- | --- | --- | --- |
| Composite preferences cannot independently forget/correct clauses | A1, B1 | Structural counterexample confirmed by category-level key and record-level revisions. No model test needed to expose the representational gap. | Use: multiple independently addressable preferences, existing tables; no universal graph or inferred legacy split. |
| Known current state need not establish whether the old state was true | A2 | Proposed supersede/correct reasons force historical meaning not always supplied by the user. | Use: preserve unknown historical relationship instead of inventing it. |
| Error without replacement and end-then-forget are missing | A4, B2 | Current target validation requires active records; proposed inactive state/removal target discovery is incomplete. | Use: complete the transition table and eligibility rules. |
| Correcting an older revision must not overwrite the present | A2 | Present-only targeting cannot express retrospective error cleanly. | Use in specification; bounded historical targeting versus explicit abstention remains a design choice. |
| Clarification needs bounded multi-message evidence | B3 | Synthetic current-only breed proposal is rejected; reviewer input contains recent users but not intervening assistant questions. | Use: current-user resolution anchor plus eligible prior user spans; assistant questions are context, not fact authority. |
| Policy truncation, omitted-fact dedup, overstated retrieval IDs, stale revision dedup | A3, B4 | Four in-process counterexamples reproduced below. | Use: protect instructions, pack whole records, resolve versions, trace actual supplied evidence before ranking experiments. |
| Entity labels can bypass fact evidence/lifecycle | A5, B6 | Unevidenced label accepted in-process. Source trace confirms labels sent to reviewer and not updated by fact revision. No live entity-confusion claim. | Use: derive eligible current identity or opaque fallback; old aliases need explicit lifecycle. |
| Ending/retracting a fact does not neutralize old summaries | A4, B5 | Source loads summary independently; inactive records would vanish from active selection. Bad reply is a hypothesis, not reproduced provider behavior. | Use: relevant current lifecycle information, not a second truth summary. Test cross-conversation stale narrative. |
| Shared profile knowledge is not shared conversational experience | A7, B6 | `_context_fact` lacks source/character provenance; current source reader is an operator facility, not authorization for broader model access. | Use: compact attribution envelope and scope-aware source access. |
| Private continuity cannot imply universally current world state | A7 | Product tradeoff: a second character may hear an update unavailable to the first root. | Use: dated reported-context semantics; avoid claiming private notes are shared current truth. |
| Source-history baseline should precede continuity schema | A8, B7 | Plausible smaller alternative, not a demonstrated retrieval win. | Test before adopting tables. Freeze eligibility, update coverage, and token budget. |
| No-op staleness and semantic duplicate entities remain possible concurrently | A9, B8 | Target/version validation does not validate all read dependencies or absence assumptions. No concurrent database reproduction in this review. | Test; retain explicit weak snapshot guarantee unless product need justifies stronger ordering. |
| Reviewer capacity must not prevent targeted removal | A10, B8 | Proposed capacity failure plus existing reviewer-mediated actions creates a credible recovery trap. | Use: specify a bounded target-specific escape path; do not add it as an ad hoc bypass. |
| Existing tests/fixtures protect some superseded assumptions | A6, B9 | Separate synthetic mechanics from semantic quality; older fixtures cannot silently become current response exemplars. | Use: update named contracts and score missed writes as well as false writes. |
| Name/location pinning and entity expansion | B6 and recommendation | Current location meaning and cross-entity recall need definition; ranking advantage unmeasured. | Test after packing; do not freeze arbitrary pins yet. |

Park continuity tables, background extraction, graph/temporal engines, broad
transcript access, global suppression/erasure, and stronger subject-wide ordering.
Discard treating two agreeing reviews as proof, weakening Option A silently, or
adding a second model judge as a substitute for evidence validity.

## Important Refinements Before Adoption

- Independently editable preferences need application-owned stable identity,
  entity/category/scope semantics, matching and duplicate rules, and migration
  tests. This is not just dropping a SQL uniqueness constraint. Preserve legacy
  composites without fabricating clause-level historical evidence.
- Current-user anchoring is about a new turn resolving a specific prior user
  claim. It is not blanket authority to extract old conversations. Define bounded
  same-conversation sources, exact spans, negation, quoted speech, and assistant
  suggestions that were never asserted by the user.
- Fixing active entity-label exposure is distinct from erasing old transcripts.
  Option A intentionally retains history, but it does not require presenting a
  stale derivative as a canonical current identity.
- Status guards must distinguish "relationship with X ended" from "has no
  partner." A summary timestamp alone does not provide the missing semantic fact.
  A subject-generation marker is one candidate, not an accepted new requirement.
- Root isolation applies to private dialogue evidence, not intentionally shared
  subject facts. A source citation for a shared fact must not reveal unrelated
  private text in the same message. Character creation/versioning needs a clear
  workflow, not a model guessing whether a persona edit is a new person.
- A stale in-flight no-op reply is permitted by the draft's snapshot contract.
  Do not mislabel it as proven lost-write corruption or promise linearizability.
  Duplicate-entity races need targeted tests before selecting a wider lock/check.
- Full request accounting includes executor-added policy, tool definitions, and
  continuation results. Repairing the initial context alone does not close that
  boundary. Delimiting untrusted data reduces risk; it is not an injection proof.

## Reproduced Counterexamples

Executed with `uv run --no-sync python` in the feature worktree. All six assertions
confirmed the failure/limitation described, not successful product behavior. These
are small synthetic characterization probes, not the full unit suite or a deployed
test. The following condensed reproduction uses only current in-process functions:

```python
from dataclasses import replace
from ade_api.features.agent_runtime.context import ContextBudget, build_context
from ade_api.features.agent_runtime.memory_policy import prepare_memory_review
from ade_api.features.agent_runtime.memory_review import ReviewDecision
from ade_api.features.agent_runtime.errors import RuntimeValidationError

base = ContextBudget(32768, 4096, 256)

def fact(key, value, version=1):
    return {"id": key, "key": key, "value": value, "version": version}

def build(facts=(), retrieved=(), persona="", budget=base):
    return build_context(
        system_prompt="Policy", persona=persona,
        active_facts=list(facts), retrieved_facts=list(retrieved),
        recent_messages=[], current_user_content="Hello", budget=budget,
    )

context = build(persona="P" * 20000)
assert "A separate ADE reviewer" not in context.messages[0]["content"]

location = fact("location", "Toronto")
context = build([fact("long", "X" * 2000), location], [location],
                budget=replace(base, profile_tokens=100))
assert "Toronto" not in context.messages[0]["content"]

context = build(retrieved=[fact("long", "X" * 2000), fact("second", "Ottawa")],
                budget=replace(base, retrieval_tokens=100))
assert "second" in context.retrieved_fact_ids
assert "Ottawa" not in context.messages[0]["content"]

context = build([fact("city", "Toronto", 1)], [fact("city", "Montreal", 2)])
assert "Toronto" in context.messages[0]["content"]
assert "Montreal" not in context.messages[0]["content"]

entities = [
    {"id": "subject", "subject_id": "subject", "kind": "subject", "label": ""},
    {"id": "pet", "subject_id": "subject", "kind": "pet", "label": "Roxy"},
]
decision = ReviewDecision.model_validate({"proposals": [{
    "operation": "add", "fact_type": "pet.breed", "value": "Husky",
    "evidence_quote": "Roxy", "entity_ref": "existing:pet",
}]})
try:
    prepare_memory_review(
        decision=decision, subject_id="subject", active_facts=[], entities=entities,
        current_user_message={"id": "message", "content": "Roxy"},
    )
except RuntimeValidationError as error:
    assert "not supported" in str(error)
else:
    raise AssertionError("expected current-only evidence rejection")

decision = ReviewDecision.model_validate({"proposals": [{
    "operation": "add", "fact_type": "pet.name", "value": "Rocky",
    "evidence_quote": "Rocky", "entity_ref": "new:rocky",
    "new_entity_label": "UnsupportedLabel",
}]})
prepared = prepare_memory_review(
    decision=decision, subject_id="subject", active_facts=[], entities=entities[:1],
    current_user_message={"id": "message", "content": "My dog is called Rocky."},
)
assert prepared.new_entities[0].label == "UnsupportedLabel"
```

The clarification probe tests rejection of a hand-authored breed proposal under
current evidence rules; it does not simulate a model resolving a real dialogue.
The entity probe proves label acceptance in preparation, not database persistence
or downstream model confusion. Policy loss uses the normal prompt budget; the
packing probes use smaller explicit budgets to isolate the same code paths.

## Recommended Next Step

Revise the proposed design before a coding plan. Replace composed preference
mutation with independently addressable records. Write a complete lifecycle and
bounded multi-source evidence contract, including historical uncertainty,
invalidation without replacement, inactive removal, and reassertion. Put context
integrity and lifecycle-safe identity/provenance ahead of retrieval ranking.
Move the same-root source-window comparison before continuity-table adoption.

Expand the twelve arcs with the reviewers' counterexamples and review their
expected states first. Then plan deterministic infrastructure tests, shadow
reconciliation, equal-budget retrieval tests, fixed-evidence dialogue comparisons,
and a bounded integrated replay in that order. Live steps need fresh call budgets.

The original design stays identifiable at its published revision; this assessment
does not silently replace it or accept the recommendations. No runtime changes,
provider calls, new services, release rebind, main merge, commit, or push were
performed during this review. Existing Stage A failure and release blockers remain.
