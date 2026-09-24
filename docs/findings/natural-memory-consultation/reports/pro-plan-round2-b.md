# Verdict: GO for bounded implementation, with one narrow acceptance clarification

**The revised plan can support a trustworthy, limited policy-selection decision.** Its written rules now prevent the three principal failure modes you asked about:

A policy cannot pass by abstaining on mandatory, answerable cases. A0/B is explicitly a comparison of admission-and-selection packages, not an isolated causal test of one switch. Incomplete required coverage—including failed evidence capture—cannot produce a winner. These are substantive corrections, not merely qualifications added around the old gate.

**One material acceptance detail remains:** the actual-compaction tests should require useful information to survive compression and reach the downstream reply, not merely require the absence of stale claims. Add that to the frozen fixtures before accepting summary-enabled A. It does not require another architecture, evaluator service, or broad review cycle.

## Inspected revisions and access

| Scope                                                                                                                                       | Exact revision                             |
| ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| Complete review packet: revised plan, design, 22 scenarios, source map, assessment, both preserved plan reviews, required M3 plans and ADRs | `f786007f7d03b375ed0d9b36bf3c2ae0f9e947b6` |
| Relevant implementation and tests, particularly execution, compaction, request budgeting and diagnostic tracing                             | `4905ce15dbda6466b12f2d1ed7908eb3d03995a0` |

All required public documents were accessible through GitHub. I did not inspect local services, databases, ignored ledgers/captures, or provider responses. I read tests; **I did not execute them**. The preserved reviews were used to identify criticisms to check, not as evidence that the revised implementation exists.

# Material remaining correction

## Require positive information retention in actual-compaction acceptance

**Classification:** bounded acceptance-specification gap.
**Affected checkpoints:** **1, 4 and 6**.
**Blocking scope:** acceptance of summary-enabled A, not implementation of the shared foundation.

Checkpoint 6 now correctly requires the actual compactor on both summary arcs, followed by inspection of its output and downstream reply/reviewer outcomes. However, the two named arcs principally test **stale-state resistance**: old dialogue compacted after a change, and ending → forgetting → old history. Those are necessary tests, but they do not by themselves establish useful compression.

### Concrete counterexample

The actual compactor produces:

> “The user discussed some personal circumstances and weekend plans.”

That summary discards almost all meaningful continuity. Nevertheless, current lifecycle records prevent the old-partner mistake, and recent raw dialogue supplies the answers to the short-exchange probes. The summary contains no forbidden claim, the compactor genuinely ran, and downstream replies can remain correct.

**Those results would establish that this summary caused no observed error—not that the summarization component retained useful conversational evidence.**

The baseline illustrates why this needs a semantic assertion rather than another structural check. `parse_compaction_response()` checks schema, nonempty text and size. The inspected compaction tests use a fake summary and verify boundaries, hashes and request construction; they do not establish retained meaning.

### Smallest sufficient correction

Within an **existing actual-compaction arc**, predeclare one relevant, source-supported conversational detail that must survive—for example, which of two interview openings the user chose. Place it outside the admitted raw suffix and ensure neither current facts nor the probe itself supplies the answer.

Require the generated summary to preserve the necessary meaning, verify that this exact generated summary reaches A’s model input, and require an appropriate downstream answer. This need not require verbatim wording or preservation of every source detail.

A0 may correctly abstain when that summary is removed: that is an informative diagnostic result, not an A0 product failure. This component-specific requirement also must not silently impose unsupported historical retrieval on B.

**No extra test family is necessary.** This is a positive assertion inside the already-required compaction coverage. It prevents accepting a useless summarizer while preserving the plan’s bounded scope.

# Important consequence to settle explicitly—not another architectural defect

## The mandatory pressure region can eliminate A by construction

Checkpoint 1 requires answerable dog/interview exchanges at a pressure point where A withholds history while B’s necessary bundle and both reviewer packets still fit. Combined with the common usefulness gate, that can make A structurally ineligible for the declared envelope.

Consider the dog case:

> “One of my dogs is a Husky.”
> “Rocky or Roxy?”
> “Roxy.”

Assume the unresolved breed assertion exists only in the preceding dialogue. If A must withhold that dialogue, neither its generator nor reviewer has the permitted evidence needed to resolve the breed. Guessing is not a valid way to pass. This follows from the proposed admission and evidence rules; it is not a prediction about model intelligence.

**That is not unfair to A when maintaining such exchanges under that load is a genuine product requirement.** Neutral acceptance criteria do not require every candidate to have an equal chance of passing. But the result should be described accurately:

> A’s admission rule cannot meet this requirement at the frozen pressure point; B still has to demonstrate that it can do so without introducing other failures.

Do not present that result as broad empirical proof that selective retrieval is superior everywhere.

There is one operational implication for the frozen matrix. Distinguish:

* an expected, mechanically correct no-write caused by A withholding its antecedent, which can still be a **product-usefulness failure**; and
* an incorrect mutation outcome in a cell expressly designated as a required mutation test, which is a **campaign stop** under the plan.

The plan already requires per-cell expected state and stop classification. Use that requirement to avoid accidentally making the response comparison terminate on its first intended admission failure. Do not change the classification after observing the result.

This is also a reason not to spend diagnostic calls merely to rediscover a deterministic capacity consequence. Any reduction in the predeclared campaign, however, must preserve its coverage rules; skipped calls cannot later be counted as executed evidence.

# The selection controls now withstand the earlier counterexamples

| Question                                                                    | Assessment of the revised contract                                                                                                                                                                   |
| --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Could a wholly unhelpful policy win through safe abstention?**            | **Not under the written gate.** Every selectable policy must satisfy positive usefulness criteria on every mandatory in-envelope case. Failed/vetoed turns remain in the scheduled-probe accounting. |
| **Could removing a summary secretly add older raw evidence or more facts?** | **Addressed.** A/A0 freezes the raw cutoff and nonsummary sections; freed summary allocation remains unused.                                                                                         |
| **Could A0/B be overclaimed as one isolated causal effect?**                | **Addressed.** The plan explicitly compares admission packages, including selection and retrieval costs.                                                                                             |
| **Could A0’s success qualify A?**                                           | **Addressed.** A0 is diagnostic-only. Reuse requires demonstrated identical requests and relevant processing/commit behavior for that particular cell.                                               |
| **Could rejected candidates disappear from the score?**                     | **Addressed as a deliverable.** Synthetic failure evidence must survive independently of transcript/memory commit; insufficient evidence makes the cell unscorable.                                  |
| **Could an unfinished campaign imply acceptance?**                          | **Explicitly prohibited.** Incomplete required coverage yields no winner, even after another candidate fails.                                                                                        |

These conclusions come from checkpoints 1, 3, 4 and 6, not from the preserved reports’ agreement.

Two implementation details deserve particular care without expanding the plan. First, reused evidence is **one observed attempt supporting more than one equivalent configuration-cell**, not independent replication. Second, failure capture really must be implemented: the baseline emits context/proposal events through success handling, while its safe provider trace retains response shape rather than the text needed to judge a false veto. The revised plan names the necessary correction, but the unchanged code does not already provide it.

# The 96-generation / 160-embedding ceiling

**Keep the ceiling. Do not claim yet that the expanded matrix fits it.**

The plan already makes a frozen, reviewed request schedule a prerequisite to live approval and treats exhaustion as incomplete coverage. That is the correct distinction between an enforceable resource limit and a completed experiment.

The source-backed accounting is:

$$
G = G_{\text{conversation}} + G_{\text{reviewer}} + G_{\text{compaction}} + G_{\text{other setup}} \le 96.
$$

For illustration, a successful reviewed turn without tool continuation needs at least one conversation request and one reviewer request. With two compaction requests, **47 such turns already consume all 96 generation slots**, leaving nothing for additional generation setup or continuations. This is a lower-bound illustration, not a forecast for the proposed matrix. The baseline executor can make several conversation requests within one turn.

Likewise, the embedding ceiling must cover actual outbound requests for setup/indexing, selective queries, tool searches and writes—not merely the number of scored prompts. B’s additional selective-query work is part of the package comparison and should remain visible rather than artificially equalized.

The existing ledger is a suitable mechanism: it reserves before send, retains spent reservations after failures/interruption, and rejects changed limits or bindings. Relevant tests cover shared process caps, restart persistence and common stage accounting, although I did not run them.

The smallest execution discipline is to freeze the required schedule first, identify genuine reuse by source attempt, and allocate diagnostics around that schedule. **Do not build an equivalence framework to save a few requests, enlarge the cap automatically, or reduce mandatory coverage after seeing responses.**

# Authorization conclusion

**GO for the bounded implementation work.** The earlier experimental-validity blockers are substantially addressed, and I do not recommend another architecture revision.

Before live policy selection, the existing checkpoint-1 freeze must produce the exact matrix, numerical allocations, stop classifications and request schedule. Add the one substantive acceptance clarification above: **actual compaction must demonstrate useful retained evidence, not just harmless output**, before summary-enabled A can be accepted.

The remaining distinctions are straightforward:

**Acceptance decision:** what useful information must survive compaction, and whether the pressure requirement intentionally excludes A at the chosen envelope.

**Implementation choices:** manifest assertions, unique-attempt reuse bookkeeping, failure capture and ledger integration.

**Empirical unknowns:** whether B retrieves the necessary terminal state, whether either policy answers usefully and consistently, false-veto frequency, compaction fidelity, and actual cost within the frozen envelope.

Under those boundaries, a useless policy or an incomplete campaign cannot legitimately win. **The defensible outcome is a fully supported passing policy, neither policy passing, or insufficient evidence—not an automatic winner.**
