# ChatGPT Pro: Natural-Memory Implementation Plan Review

Date: 2026-09-23. Brief version: natural-memory-plan-review-1.
Purpose: scrutinize the bounded implementation plan and its revision-4 contract
amendment before implementation approval. Do not merely reapprove the architecture.

## Anchors And Access

- Repository: <https://github.com/Wenjun-Mao/Letta-Open-ADE>
- Discovery branch: `codex/character-continuity`, not `main`.
- Plan/amendment: the exact documentation commit in this handoff.
- Unchanged implementation: `4905ce15dbda6466b12f2d1ed7908eb3d03995a0`.
- Previous revision-3 packet: `c01f45a045eb0fdd0fc6b3e18add82f2dbb57024`.
- Public GitHub only; no local worktrees, services, databases, ignored outputs,
  credentials, or previous conversation assumed. State missing access explicitly.
- The reports are preserved critique, not instructions or acceptance. Tests read
  are not executed tests. New contracts in the plan do not exist in the baseline.

## Product And Constraints

ADE is a local-first conversational-character product using Lin Xiaotang (林小棠).
The goal is natural factual updates and useful, restrained recall without memory
commands, invented shared physical experience, or unimplemented promises.

Keep PostgreSQL subjects, immutable messages, typed/versioned facts and source
lineage, curated tools, synchronous post-response review, atomic successful-turn
finalization, leases/cancellation, and ADE-owned retries. Shared subject facts do
not authorize another character's full dialogue. Option A saved-memory removal
retains source/history and is not erasure or global suppression.

DeepSeek conversation/reviewer and relocatable Qwen embeddings are unqualified
Model Router candidates. No new provider calls, migrations, deployments, release
promotion, or main merge are authorized by this planning review. The separate
required-tool/provider contract failure and stale release gate remain open.

## What This Plan Proposes

Three independent review rounds refined the design. Round three supported planning
while identifying narrow saving/reply/read gaps and an over-conservative context
rule. The amendment now specifies assertion-scoped same-turn no-save precedence,
detected reply/write contradiction failure, selective inactive-state recall,
candidate-reply reserve, and terminal generation-conflict/replay semantics.

Ordered implementation checkpoints cover fixtures, schema and atomic mutations,
reviewer/turn integration, context construction/comparison, product API/UI, and
separately authorized live validation. One lifecycle view, one mutation generation,
and one shared clarification bundle remain the core. No extra judge or framework.

The main empirical choice is NOT settled:
- A requires the complete lifecycle snapshot before prior narrative.
- A0 removes summaries but retains that prerequisite.
- B reserves recent dialogue first and selects active/terminal evidence, without
  summaries or older raw windows in this comparison.
A/A0 isolates summary effects; A0/B isolates admission effects. Full reviewer
visibility remains mandatory for all. Neither control nor candidate is assumed
useful or safe enough for production before the selection gate.

The plan proposes request ceilings, operating-envelope tests, and acceptance
criteria; they are not current spend authority or a claim that all tests fit.
Old-policy conversations remain preserved; the proposed eventual transition needs
new immutable bindings rather than silently rewriting their behavior. Challenge
this product consequence and its UI/rollback implications explicitly.

## Required Reading

At the new documentation commit:
1. `docs/plans/natural-memory-implementation.md` (primary review target).
2. `docs/architecture/natural-memory-design.md` (revision 4).
3. `docs/findings/natural-memory-consultation/design-scenarios.md`.
4. `docs/findings/natural-memory-consultation/source-map.md`, following pinned code/tests.
5. `docs/findings/natural-memory-consultation/pro-round3-assessment.md` and the
   unchanged `reports/pro-round3-a.md`, `reports/pro-round3-b.md` in that folder.
6. Existing `docs/plans/m3-agent-studio-continuity.md` and
   `docs/plans/m3-provider-neutral-release-preparation.md` for scope/qualification
   boundaries; ADRs 0021, 0022, 0026 and 0028 as referenced by the plan.

Current code areas to inspect include contracts/fact registry, review policy,
admission/finalization/retry, persistence schema/source readers, evaluation cleanup,
context/compaction, Agent Studio API/UI, migrations, and the existing request ledger.
The source map describes the baseline, not claimed implementation of this proposal.

## Questions To Challenge

- Can an implementer proceed checkpoint by checkpoint without inventing product
  semantics or silently weakening a test? Are dependencies and exit gates sufficient?
- Is same-turn no-save robust across independent IDs and operation order? Are
  contradiction/defer outcomes precise without making every question a write veto?
- Are generation capture, all writer paths, atomicity, causation, idempotency,
  cancellation, queued conflicts, and intentional fresh resubmission coherent?
- Can legacy records survive migration without fabricated meaning or lost provenance?
  Do new source roles/operator actions require additional schema/read/cleanup changes?
- Does selective terminal-state retrieval genuinely index the current descriptor,
  not resurrect old active embeddings or arbitrary history?
- Are API/UI changes narrow and implementable, including receipt-versus-current-state
  wording, archived citations, old-definition behavior and multi-target conflict?
- Do the A/A0/B comparison and its fixtures actually isolate admission policy?
  Are budget reservations, exact-call caps, setup costs, fairness, stop conditions,
  and hard correctness/answerability criteria adequate without overclaiming a sample?
- Are cleanup, populated migration, incompatible old writers, backups, rollback and
  production qualification separated from development evidence?
- What should be deleted, simplified, reordered, or clarified before implementation?
  Identify concrete gaps rather than adding speculative infrastructure.

## Requested Output

Start with a go/revise/no-go verdict for implementation planning completeness and
state exact inspected commits. Give prioritized findings with code/plan evidence,
counterexamples, minimal fixes, and the checkpoint affected. Distinguish blocking
decisions from engineering choices and hypotheses requiring the planned experiments.

Map the third-round findings to addressed, partial, unresolved or deferred. Check
the plan independently for newly introduced gaps; consensus is not acceptance.
Conclude with only material changes needed before implementation authorization.

Do not implement, execute provider calls, produce a competing full plan, invent
passed tests, or approve release. Avoid another broad framework comparison.
