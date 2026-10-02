# Character Continuity Research Review

Date: 2026-10-02. The supplied shortlist is substantially accurate and useful,
but its immediate next step predates the completed D04 comparison. This note
records source-checked interpretation, not an implementation decision. Relevant
[product agreements](../../../../../docs/product-contract.md): PC-03/04/05/06/07/08/09/10/11.
None changes. No selector, new evaluator, runtime limit, or live run is authorized.

## Evidence Scope

The [original report](reports/research-shortlist-2026-10-02.md) is preserved
byte-for-byte, including its absent final newline. SHA-256:
`5b19b49970fc60644444babb9b91d3a18ee7495734958a8e44610430493f0a8d`.
It reports inspecting ADE at `ffaf24dab13a9b74b78339a600c032bf1adba899`;
that access claim is not independently audited. Its earlier screening briefs were
not supplied, so completeness or optimality of the top-five ranking is unverified.

This assessment is by the Codex manager, an AI, against local source/results at
`6f74f28` and public primary sources checked on the date above. Full texts were
accessible for all five recommended papers, including the two the report checked
only through abstracts. Checks below concern the claims relied upon, not a
reproduction of benchmarks or an audit of every theorem, dataset, or implementation.
The three deferred memory papers received abstract-level checks only.

## What Needs Updating

### D04 Is Now Observed Rather Than Pending

The report accurately labels its inspected revision live-unrun. That recommendation
is now historical: the [reviewed behavioral readout](behavioral/READOUT.md) records
six captured requests. Literal-four expressed warranted uncertainty; repaired-four
and whole-pool named the supported old-bookstore entrance. Their reviewers returned
one source-bound conflict about a tentative aside, then two valid no-change
observations. The first conflict is an unresolved interpretation issue, not proof
of a false recollection or a definitive false positive (PC-05).

Do not summarize this as two successful arms versus one failed answer. Evidence
restoration enabled supported naming in this witness; honest uncertainty remained
correct when the antecedent was absent (PC-11). One sample per arm establishes
neither reliability nor production retrieval or native persistence qualification.
Whole-pool changed content and ordering as well as count.

The report's source claims still match the current
[ranker](../../../../../services/ade-api/src/ade_api/features/agent_runtime/history_ranking.py)
and [admission layer](../../../../../services/ade-api/src/ade_api/features/agent_runtime/history_admission.py):
both retain a four-exchange ceiling. Eight-source capacity and behavioral evidence
were evaluation-only exceptions, not changes to those runtime boundaries.

### Paper Findings And Transfer Limits

**The Recall Trap: Use the task-level comparison principle.** The reported
39.2% to 46.8% result is correct: a fixed 12-slot, single-shot code-repair study
found that removing file deduplication reduced coverage but improved resolution.
The BM25 reversal and unrestricted-reading boundary are also correctly stated.
These are packing-policy findings, not a tested algorithm for conversational
correction dependencies. ADE's inference is to assess meaningful combinations of
original sources against downstream behavior, not optimize coverage alone.
[Full paper, sections 5.1 and 5.4-5.5](https://arxiv.org/pdf/2608.14838).

**When Knowledge Changes: Use the method; Test ADE-specific variants later.**
The two mutation scopes, eleven operators and five datasets are supported.
Distinguishing upstream corpus/retrieval changes from downstream supplied-context
changes is directly useful. Its evaluation is not validation of ADE's archive,
persona-version, fact-removal or fictional-story lifecycle rules. Those oracles
must come from PC-03/04/07/10/11. A paraphrase must preserve speaker, negation,
time and qualification before it can serve as a meaning-preserving control;
the paper itself checks whether mutations preserve meaning rather than assuming
that from the operator's name.
[Full paper, sections 4, 5.2.3 and 8](https://arxiv.org/html/2607.26843v1).

**The RAT: Use the decomposition, not its policy or implementation.** The
retrieval/abstention/task-success separation and noisy-judge treatment are accurate.
The full text adds two material qualifications: Appendix C already studies partial
retrieval, and the principal model uses a fixed abstain-if-retrieval-fails policy
with exact-match abstention detection in constrained, single-turn tasks. It does
not directly model natural partial answers or dialogue history. ADE needs semantic
assessment of uncertainty, not a prescribed phrase or a relevance-document count.
New solo fiction remains allowed under PC-11; missing recollection and creative
invention are different situations.
[Full paper, Limitations and Appendix C](https://arxiv.org/html/2608.24753v1).

**ReCAP: Use the dependency idea; Park the machinery.** Its attention-derived
graph and original-block recovery are described accurately; closed-API experiments
need proxy-model attention extraction. Dependency expansion is only one hop,
skips stale-marked predecessors, and remains budget-constrained. The final serving
cap may drop oldest selected blocks even over protected-record retention.
Consequently, this is not a guarantee of complete dependency recovery. ADE should
inspect its final supplied evidence, not assume a selected dependency survives
packing. This is our design inference, not a result demonstrated for Mandarin
conversation.
[Full paper, sections 5.3 and D.1-D.3](https://arxiv.org/html/2609.40118v1).

**Repair or Resample: Use as experimental discipline.** The report correctly
limits replay to the represented prefix; later model output is not deterministic.
Recorded write responses do not recreate external persisted state. Appendix A.4
also puts variation from unrestored external state outside the replay guarantee.
Frozen ADE packets provide a controlled diagnostic, not SymTrace-equivalent replay
or native-state qualification. Borrow the distinction without installing another
framework (PC-08/09).
[Full paper, Appendix A.3-A.4](https://arxiv.org/html/2608.25920v2).

### Code Availability And Deferred Papers

On 2026-10-02 the author-linked [RAT repository](https://github.com/vodezhaw/rat)
still contains only an under-construction README, and
[ReCAP](https://github.com/UCSB-NLP-Chang/ReCAP) is empty. The report's caution is
confirmed; neither was inspected as runnable code. These are dated observations,
not permanent claims about release availability.

The report omits a separate citation for
[Jev-Mem](https://arxiv.org/abs/2609.23986): its adjacent link identifies
[LycheeMemory V2](https://arxiv.org/abs/2608.12990), not both papers.
Their abstracts support the broad descriptions of relational control and
segment-level memory consolidation. [SANE](https://arxiv.org/abs/2608.00658)
does add model-assisted selection and query-time evidence extraction. Deferring
these implementations is reasonable for the current gap, but is an ADE-specific
judgment, not evidence that their methods are ineffective. No benchmark replication
or complete comparative review of these three papers was performed.

## Integration And Next Step

The report's main contribution is better framing and evaluation, not a demonstrated
replacement retrieval algorithm. For the next design task, prioritize When
Knowledge Changes and RAT for discriminating tests, retain Recall Trap as the
packing-policy warning, and consult ReCAP narrowly for dependency recovery.
Repair or Resample reinforces controls ADE already uses. This ordering reflects
our current decision needs, not a general ranking of research quality.

Recommended next step remains a separately scoped correction-plus-antecedent
recovery design. Specify eligible source scope, alternative sufficient evidence,
competing corrections, final-payload admission, and honest uncertainty when support
cannot be recovered. The existing
[candidate reader](../../../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/history.py)
considers the newest 128 scoped completed exchanges before content and annotation
exclusions; no selector can recover absent candidates. Do not infer unlimited-history
feasibility from the eight-source D04 fixture.

- **Use:** task-level packet assessment, stage-specific diagnosis, controlled
  changes, original-source authority and explicit evidence limits.
- **Test:** ADE-specific semantic invariants in a future authorized fixture slice;
  no new cases or calls were added in this review.
- **Park:** graph/proxy infrastructure, new extraction formats, probabilistic
  scoring and memory-store replacement until a demonstrated need justifies them.
- **Discard:** interpreting correct uncertainty as failure, structural binding as
  semantic correctness, or one favorable response as a durable repair.

No new ADR is needed: this note promotes research interpretation, not a changed
product or runtime contract. Original reports, frozen protocols and observed
results remain unchanged. The optional-aside reviewer question remains open.

**Follow-up recommendation: none now.** Primary-source checks and local outcomes
suffice for the next bounded design discussion. Reopen Pro consultation if a
concrete design has competing authority or correctness interpretations; reopen
Deep Research if it exposes a specific recovery-method or scale question not
answered by these sources. Neither consultation nor implementation is dispatched.

## Verification

The original report's archive hash matches the attachment. Local Markdown links
and authored whitespace are checked separately; original report whitespace is
preserved. Only documentation changes in this iteration. Paper benchmarks, ADE
providers, database/native paths and runtime tests were not rerun.
