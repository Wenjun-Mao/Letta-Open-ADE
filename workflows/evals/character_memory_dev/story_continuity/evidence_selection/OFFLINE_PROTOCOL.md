# Offline Whole-Pool Capacity And Packet Qualifications

Version 1, 2026-10-02. **Approved offline slice; specified before the new D04
whole-pool measurement.** [ADR 0058](../../../../../docs/adr/0058-offline-packet-capacity-and-qualifications.md)
owns the experiment-only count exception. The original
[selector proposal](PROTOCOL.md) is not approved for implementation or execution.
PC-03/04/05/06/09/10/11 and the native turn-7 stop remain unchanged.

## Question And Fixed Scope

Does D04's already eligible eight-exchange pool fit both complete downstream
requests under their existing token budgets, without first compressing it to
four? Separately, which distinctions must a future packet assessment retain so
that answer availability is not mistaken for a settled, interpretable answer?

Reuse the original hash-validated correction-study inputs and labels unchanged.
No new dialogue, N01-N03 controls, selector, semantic scorer, model judge, provider
runner, database, external account or native turn is part of this slice. D02's
counterexamples and neighborhood IDs are already exposed in the reviews/local
checks. The rubric below is non-blind author interpretation, not new independent
labels. Commit this protocol before constructing the new eight-source request;
bind its bytes and that commit in the result receipt.

Construct exactly these eight packet pairs. A pair means fresh generation and
reviewer payloads, not executed requests or another model-selection case:

| Key | Case | Complete source IDs in priority order | Purpose |
| --- | --- | --- | --- |
| D04/empty | D04 | None | Unchanged base overhead. |
| D04/literal-four | D04 | E07, E02, E05, E04 | Existing failing baseline; verify the unchanged ranker still returns it. |
| D04/whole-pool | D04 | E01, E02, E03, E04, E05, E06, E07, E08 | Sole eight-window exception, in original chronology. |
| D02/empty | D02 | None | No named answer can be supplied from H. |
| D02/original | D02 | E01 | Preserve a legitimate original-only answer alternative. |
| D02/competing | D02 | E01, E02 | Named answer present alongside an unresolved competing account. |
| D02/restored | D02 | E01, E07 | Named answer and supplied restoration. |
| D02/neighborhood | D02 | E02, E01, E03, E04 | Previously derived four-window conflict witness, not a newly tuned selector. |

No additional case, variant, neighbor recipe or changed source text may be used
to improve the result. Synthetic negative tests exercise mechanics only and do
not enter the measurement table.

## Capacity And Integrity Contract

Use the existing runtime request serializers, source binder, token estimator and
reviewer preflight. The diagnostic may call the history-rendering helper directly
instead of four-window admission, with the exception explicit in the receipt.
Do not monkeypatch global limits, route around identity/hash validation, enlarge
budgets or fabricate an admission receipt. Output `included` sources and a
counterfactual capacity status, not a claim of runtime admission.

Keep `deepseek::deepseek-flash` / `deepseek_openai` as the existing serializer
configuration, not a provider-verified deployment. Generation input limit is
11,213; reviewer input limit is 11,469; both output reserves are 4,096; the local
suffix ceiling remains 640. Use the same neutral persona/system text and empty
facts, entities, saved/local context as the old packets. Both final histories
must be byte-equivalent after JSON decoding and contain complete source exchanges.

Measure the complete serialized generation request. For reviewer capacity use
the runtime preflight's full candidate-reply placeholder of 16,384 ASCII `x`
characters, reserving 4,096 estimated tokens for the future answer, in addition
to the reviewer's own output budget. Also retain the ordinary explicit synthetic
reviewer-reply payload used by the historical builder. Preserve both payload
hashes and the full-reserve request for inspection; no answer was generated.

Record each request estimate, limit, remaining headroom, overflow and fit flag.
If either consumer overflows, preserve all included sources and report that
failure; never omit an exchange, shorten a message or increase a limit. A source,
scope, freeze or serialization error stops the diagnostic, not an empty fallback.
Provider usage/latency and live model quality remain unmeasured, not zero-valued
successful outcomes.

Verify original run/conversation/version/archive bindings, U/A roles, message
identity/hash/timestamp and source-order receipts. H message handles do not expose
original IDs or sequence; judge delivered meaning from H, not richer receipts.
Retain that existing wire contract. Check no evaluator commentary or source
topology leaks into the model payloads and no input is mutated.

## Prospective Whole-Packet Rubric

Do not replace the historical `named_answer_supported` or `unresolved` fields.
The former is answer-route inclusion; the latter is a full-ledger annotation,
not an adjudication of a new subset. Neither alone establishes settled recall.

For a future comparison, record these judgments separately, with source quotes:

1. **Available answer:** which query-relevant claims can actually be recovered
   from the final payload, including alternative sufficient routes?
2. **Visible competition:** does the packet contain incompatible accounts or
   multiple materially plausible antecedents? Chronology/repetition cannot pick
   an authority by themselves.
3. **Necessary qualification:** does the eligible ledger contain a correction,
   scope restriction or alternative antecedent whose omission makes a selected
   claim misleading? Inspect both that ledger and the actual delivered payload;
   do not give consumers credit for evaluator-only knowledge.
4. **Permissible answer status:** settled answer supported, qualified/uncertain
   answer only, historical answer unavailable, or interpretation unassessable.
   An empty packet is not equivalent to preserving known competing evidence.
5. **Additional observations:** correction explanation, conditional referent
   dependencies, irrelevant admissions and capacity remain separate dimensions.

There is no aggregate quality score or automated truth rule. Future investment
cannot rely on a named-answer gain that creates false clarity or conceals a
material qualification. An original-only packet can still suffice when omitted
material does not change the warranted answer; provenance completeness is not a
universal answer requirement. If meaning is disputed, record it as unassessable
rather than resolving it through a preferred source ID.

### D02 Source-Grounded Witnesses

The exact question asks which weekday the silver bookmark was found at the bus
stop. These complete assistant quotes come from the frozen D02 sources:

- E01: "那是周一下班后，我独自在公交站等车时捡到一枚银色书签。"
- E02: "公交站捡到银色书签是在周三，下班等车时看见的。"
- E07: "我后来把公交站捡到银色书签的日期说错了：不是周三，是最初说的那天，最初的说法才对。"

| Packet | Prospective interpretation, not observed model behavior |
| --- | --- |
| Empty | Historical weekday unavailable; no support for a named answer. |
| E01 alone | Monday is a valid bare-answer route in this ledger. No correction explanation is required merely for provenance completeness. |
| E01 + E02 | Monday and Wednesday compete without a resolving passage. Only a qualified/uncertain weekday answer is warranted. The old named-answer field remains true. |
| E01 + E07 | Monday plus the statement rejecting Wednesday and restoring the original supports a settled Monday answer and the correction explanation. |
| Neighborhood | Monday competes with three Wednesday accounts without E07. Repetition does not settle the conflict. It is not equivalent to E01 + E07. |

This does not make earliest statements universally authoritative. A genuinely
corrected-original control must reject stale certainty; an ambiguous-reference
control must retain material alternatives. If the selector study proceeds, use
the already planned N01/N02 to break the E01/E07 restoration pattern without
scrambling meaningful chronology. No new controls or B's stricter new-case-gain
gate are adopted or authored in this slice. N03 remains asymmetric policy
conformance, not matched abstention superiority.

## Completion And Decision

Publish reproducible mechanical receipts and complete paired requests for all
eight rows, or a clear failure with remaining rows unmeasured. Verify normal
in-budget rows reproduce the historical builder exactly; negative tests must
cover full-source overflow, scope/count/input drift and integrity rejection.
Re-run both historical packet-comparison suites without rehashing their evidence.

If the whole pool fits, report that four-window compression is not required by
these budgets for this fixture. Prefer deferring the selector runner absent a
separate need for compactness; do not adopt larger runtime packets. If it does
not fit, identify the binding consumer/representation without inferring a model
selector is best. Either result is a completed diagnostic, not continuity proof.

End with a next-step and consultation recommendation. Further consultation needs
a concrete additional contribution; local capacity uncertainty alone does not
justify it. Any behavioral test, candidate-retrieval expansion, model-selection
campaign or runtime change requires a separate decision and authorization.
