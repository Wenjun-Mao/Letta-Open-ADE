# Implementation Plan Pro Review Assessment

Status: recommendations for discussion, not a plan amendment or implementation
authorization. Reviewed packet: `1a3181c133b7404d6159dbb55468c0a53bb857bd`.
Unchanged implementation: `4905ce15dbda6466b12f2d1ed7908eb3d03995a0`.

## Reports And Evidence

- [Plan review A](reports/pro-plan-a.md), attachment
  `dcfe2822-3a4d-47ff-8df1-99066a7b9cba`.
  SHA-256: `db7fdc7e4628b2b44c5680dc14585b29fe2a8745f003affebd1b0d7daee41b46`.
- [Plan review B](reports/pro-plan-b.md), attachment
  `ab8fe58e-eeb1-4ac4-a5ae-466cf7412347`.
  SHA-256: `eca56b459c8b1fd750f00c14a1628175e631001289cdfb58529ac486aa32ad12`.

Originals are preserved byte-for-byte. Both reviewers report static public-GitHub
inspection, not test execution or live validation. This assessment checked the
consequential claims against the local plan and source. No database reproduction,
model calls, or runtime tests were performed. Agreement is not replication.

## Verdict

Keep the design foundation. Both reports recommend bounded implementation after
targeted corrections, not approval of the unchanged plan. The largest remaining
weakness is experimental validity: the plan could confuse better evidence coverage
with a better admission policy, or reward a safe but unhelpful candidate.

The other gaps concern failed-attempt evidence, populated-index compatibility,
dependency-safe cleanup, and UI capabilities. They fit the existing checkpoints;
they do not justify a new memory architecture or another broad research phase.

## Checked Findings

`Use` means recommend an amendment, not silently adopt it. Source paths are under
the runtime roots identified in the [pinned source map](source-map.md).

| Finding | Local check and evidence limit | Disposition |
| --- | --- | --- |
| Removing summaries can change the raw-message pool too | `turn_execution.py` derives recent messages from the summary's `through_sequence`. The plan does not freeze that boundary or freed-budget use for A/A0. This is a possible confound, not an executed experiment failure. | Use: freeze paired input recipes and allocation rules. |
| A0/B changes a package of selection behaviors | Checkpoint 4 gives B a protected local suffix and no older windows; A0 inherits A's admission. Equal total budgets alone do not establish equal eligible evidence. | Use: common preselection pool and explicit treatment differences, not identical final prompts. |
| Positive usefulness is asymmetric | Checkpoint 6 names B for short-exchange answerability, while selection says "if one passes" without defining A0's eligibility. | Use: common positive gates for every selectable configuration; declare A0's role. |
| Failed semantic decisions are not fully inspectable today | `worker_events.py` emits `context.built` and `memory.proposed` through successful finalization. `provider_tracing.py` retains safe response shape, not candidate text or typed review decisions. Failure traces exist, but do not establish false-veto classification. | Use/Test: opt-in synthetic failure evidence, independent of transcript/memory commit. |
| Preserved vectors can become invisible | `persistence/memory.py:search_active_facts` filters by `retrieval_policy_version` as well as embedding fingerprint, subject, status, and current revision. No new migration failure was reproduced. | Use/Test: populated-store coverage for compatible old active indexes and new terminal descriptors. |
| Case-end timing alone cannot make conversation purge safe | `evaluation_sessions.py` removes sources and predecessor links attached to one conversation's messages/run revisions even when another conversation retains the subject. | Use/Test: explicit exclusively owned cleanup scope and surviving-provenance assertions. |
| Conversation execution and direct removal are different capabilities | `use-agent-studio.ts:prepareMemoryAction` requires a nonarchived conversation. `memory-action.ts` recognizes success through run-linked correct/forget revisions. Neither directly represents the proposed operator receipt. | Use/Test: separate capability checks and typed outcomes, not just new labels. |

## Recommended Plan Corrections

### 1. Freeze Fair Comparisons And Symmetric Acceptance

Recommend A and B as the selectable candidates, with A0 diagnostic-only. A0's
success cannot qualify summary-enabled A. Any future decision to select A0 must
name and test that actual configuration, rather than transfer evidence silently.

For A/A0, hold the raw-message boundary, nonsummary evidence, ordering and budgets
constant; leave removed summary space unused for the pure supplied-summary probe.
If freed space is reallocated, label that as a different policy comparison.
For A0/B, use the same eligible local pool, exclude older raw windows from both,
and specify shared selective fallback where applicable. Record the intentionally
different admission and retrieval costs. This compares full-versus-selective,
recent-first admission packages, not the isolated effect of one Boolean rule.

Freeze a common required operating envelope and per-case useful-answer criteria
before execution. Every selectable candidate must satisfy them, including ordinary
short follow-ups under unrelated-memory pressure. Correct abstention on an
unanswerable question is distinct from unnecessary abstention on an answerable one.
Use relevant, source-consistent answers rather than exact response strings.

Report successful useful responses against scheduled required probes, alongside
executed coverage and explicit failed/vetoed/unrun counts. Never hide failed turns
by scoring only delivered replies, or treat unrun cells as observed failures.
Incomplete required coverage cannot produce a winner. Predeclare which ordinary
quality failures disqualify a candidate while comparisons continue, and which
privacy, authorization, infrastructure or budget failures stop the campaign.

Require actual-compaction coverage before accepting summary-producing A; supplied
summaries only test interpretation. Test the actual selectable configuration on
its required cases. Reuse evidence only where identical relevant processing and
serialized inputs are demonstrated, not merely because A and A0 share a rule.
Retain the proposed 96-generation/160-embedding ceiling, still unapproved; freeze
the executable matrix within it or report incomplete coverage, not automatic expansion.

### 2. Make Failed Attempts Observable Without Committing Them

Extend existing diagnostic artifacts for explicitly enabled synthetic evaluations:
selected serialized inputs/bundles, tool evidence, candidate visible reply, typed
review proposals/dispositions, and final commit outcome must survive failure.
Label candidates uncommitted/undelivered. They must never enter the conversational
transcript, memory store, or retrieval indexes merely to support diagnosis.

Keep production events bounded and redacted, with safe structured reason codes.
Do not collect private reasoning, secrets or raw provider exception text, and do
not turn synthetic capture into default production prompt logging. Add a fake
false-veto regression proving inspectable evidence alongside zero assistant/memory
commit and zero generation advance. Distinguish per-claim deferral from terminal
conflict, capacity and provider failures in API/UI outcomes.

### 3. Close Persistence And UI Integration Gaps

Populated migration tests must show compatible legacy active vectors remain
selectable, ended facts use current terminal descriptors, and forgotten chains
remain excluded. Embedding-space identity is not index/read-policy compatibility.
Choose and document a compatible read path or separately budgeted reindex; never
silently relabel incompatible vectors or call providers from a SQL migration.
Use the same coherent populated state for all comparison variants.

For the bounded campaign, prefer an exclusively owned disposable database or
complete evaluation-subject scope over a generic graph-deletion framework.
Refuse individual purges that would damage surviving provenance. Test an
alternating C1/R1 -> C2/R2 -> C1/R3 correction chain, operator-origin revisions,
and active work anywhere in the proposed deletion scope. Successful SQL deletion
without foreign-key errors is not proof that surviving evidence is intact.

Separate continuation, direct removal and reviewed correction capabilities.
An old-policy read-only conversation must not alone disable an authorized direct
removal from its active subject. Corrections still need an eligible conversation.
Update outcome types for operator receipts, deferred claims, terminal failures,
historical replay and newer readback; a later restatement does not invalidate a
successful historical removal receipt or prove current absence.

A new conversation sharing the subject inherits eligible saved facts, not the old
conversation's unsaved raw dialogue, summary, or antecedent for a bare "yes".
Explain and test that boundary rather than silently copying history.

## What Not To Add

Park generic experiment engines, graph cleanup frameworks, new review services,
background memory, stronger erasure, and another context-strategy abstraction.
Keep one lifecycle view, one generation fence, one assembler and one atomic write
boundary. Candidate superiority, semantic matching and false-veto rates remain
empirical unknowns; static agreement does not resolve them.

Accept B's caution against unrelated refactoring, but do not adopt its suggestion
to relax the repository's file-size rule. Split touched oversized responsibilities
cohesively as required by AGENTS.md; do not launch repo-wide cleanup here.

## Next Step And Authority

Recommend updating the existing plan in place with these narrow corrections,
then seeking bounded implementation authority for checkpoints 1-5. Checkpoint 6
still requires a frozen matrix and separate live-call approval. Neither candidate
is selected; product acceptance, deployment and release qualification remain later
decisions. No runtime, design or plan edits, provider calls, commit, push, merge,
or release promotion occurred in this assessment checkpoint. Stage B/C remain blocked.
