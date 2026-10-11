# ADR 0063: Feature-Owned Hindsight Character Evaluation Boundary

Status: Accepted for the explicitly assigned P0 offline implementation,
2026-10-11. Evaluation-only; no native runtime or product-contract amendment.

## Problem

The isolated experiment needs Hindsight context compared with deliberate empty
and adequate-memory controls through the existing Character path. Workflow
imports of executor internals would bypass feature ownership. The executor's
request observer swallows capture errors, so merely adding an observer cannot
prove complete experiment receipts. Upstream empty/non-strict tag filters can
also silently broaden scope; HTTP 200 can contain partial reranking. The pinned
cross-encoder timeout path can return HTTP 200 while keeping a raw and normalized
zero-score tail; the engine still reports those candidates as reranked.

The [revision 4 experiment plan](../plans/hindsight-self-hosted-experiment.md)
and [source-checked consultation](../findings/hindsight-consultation/assessment.md)
establish the seam and these limits. PC-02/03/04/10/11 govern scope/attribution,
PC-07 separates workflow-owned curation from recall, PC-12 governs Character
composition and assessment, and PC-13 requires isolated self-hosting. Incumbent
PC-05/08/09 remain unchanged.

## Decision

Expose `python -m ade_api.features.agent_runtime.hindsight_evaluation` with
documented `scope` and `run` subcommands and versioned synthetic JSON inputs.
The feature owns one workspace/subject bank binding, strict nonempty
character-OR-profile recall, returned-scope validation, attributed context
composition, full reranking qualification before generation, and one tool-free
`ConversationExecutor` generation per arm. Qualification binds the reranking
phase metric's candidate count to unique merged/reranked IDs and actual response
IDs; it rejects missing/nonfinite scores and the exact zero/zero timeout
sentinel. Finite nonzero negative logits remain valid even when normalization
underflows to zero. Empty recall requires an explicit zero-candidate trace.
Bank identity is a deterministic hash of workspace/subject; ordinary versions,
chats and archive state do not redefine character continuity. Shared profile
observations and observations mixing character roots fail admission; the
workflow owns character-local consolidation and verifies semantic label quality.

Hold persona/dialogue/model/limits fixed in one input, compare applied router
catalog profiles around dispatch, and require a frozen experiment router release
outside this feature. Use the existing serializer and transport; capture its
actual final payload through the awaited authorization callback. Exclusive fsync
receipts must succeed before dispatch, and result/trace/completion capture failure
invalidates the run. Best-effort observers are insufficient for this evaluation.
Unavailable/malformed/unscoped recall aborts; it never becomes empty memory.
Preserve actual recall trace separately, excluding it from Character context.
Capture successful-HTTP result diagnostics before admission, preserving rejected
type/tag values for causal review without another provider call.
No raw chunk/source supplements or private reasoning enter the captures.
An optional frozen exclusion-term list is checked against both admitted recall
fact text and context before generation; the initial shared-profile case uses it
to reject the cited private origin even if the profile fact otherwise has a
permissive sharing tag.

The workflow owns ingestion, source readback, curation/removal tests, deployment
pins, frozen fixtures and semantic interpretation. This CLI constructs
no native database, reviewer, runtime worker, run service or finalizer. It adds
no generic Memory interface or product HTTP endpoint. Full command/input/receipt
details live in the feature's
[operator documentation](../../services/ade-api/src/ade_api/features/agent_runtime/HINDSIGHT_EVALUATION.md).

## Alternatives And Consequences

- Direct workflow imports: rejected because final composition belongs to the
  feature and needs a stable caller contract.
- New runtime binding/generic provider interface: unnecessary for this isolated
  experiment and would change incumbent ownership before adoption evidence.
- Best-effort request observers or reconstructed prompts: rejected because a
  missing or divergent request capture invalidates comparison evidence.
- Silent clipping, broad tag modes or failure-to-empty fallback: rejected because
  each can hide a different causal failure behind an apparently successful reply.

The optional `ADE_EVAL_PHASE_FILE` protocol publishes atomic recall/Character
phase intents with unique operation and case/arm correlation IDs and captures
the mapping before dispatch. It does not import workflow code. This lets the
workflow-instrumented router distinguish Hindsight recall embedding from the
actual Character generation request.

Offline regression tests cover scope, controls, capture failures, oversized whole
requests, one-generation/tool rejection, trace separation, full-rerank edge cases,
phase transitions and router profile drift.
Capacity uses the executor's estimate, not provider-tokenization proof. Catalog
checks observe drift but cannot prevent concurrent deployment changes; the
workflow must freeze the router. Source-pinned HTTP tests are not pinned-image
serialization or live semantic acceptance. Normal product execution is untouched.
