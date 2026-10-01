# Correction-Dependency Measurement

Status: **Inputs and non-blind author judgments prepared before selection.**
The user approved the [bounded plan](../../../../../docs/plans/character-story-continuity.md#correction-dependency-measurement).
This is an offline evidence-availability experiment, not a retrieval fix,
independent review, native model evaluation or runtime adoption. PC-01/03/04/05/06/09/10/11
remain unchanged. The baseline is retained and the novelty candidate is unadopted.

## Frozen Inputs And Ownership

`cases.json` contains three fresh Mandarin episode families, each expanded into
two cases. The only paired text difference is the correction's assistant reply:
name the restored value versus refer to the original account. Eight complete
windows comprise an origin, four nonidentical mistaken retellings, a compatible
detail, the correction and one unrelated exchange. Seven plausible episode
windows compete for four slots; there is no exact-copy padding or new benchmark.

`context.json` declares the prior audit's persona/system assumptions but a new
single-archived-dialogue topology, with sixteen ordered source messages and a
fresh current chat. Each selected exchange remains a separate window. Synthetic
source order is not fictional event dating, and selected order is not adjacency.
Eligibility and ordinary-version lineage are controlled assumptions, not reader
or database evidence. No saved facts, local suffix or persona fact gives the answer.

`judgments.json` records the author agent's prior exposure, exact role-attributed
quotes, minimum answer alternatives, restoration and mistake visibility, optional
detail, forbidden attribution, source-relative deletion challenges and ambiguity.
The existing Pro reports did not annotate these new cases. There is no blind,
external, independent or human-validation claim and no new reviewer dispatch.

`freeze.json` binds these inputs, unchanged selector/runtime owners and all prior
packet-audit artifacts. `inputs.py` pins the manifest and separates transcript
expansion from label loading. Runtime-owned comparison code belongs in the
service-test layer; this workflow imports only the standard library. Reference
sets are evaluator-only and cannot influence source selection. ADR
[0056](../../../../../docs/adr/0056-matched-correction-dependency-measurement.md)
records this bounded evidence contract, not a production API.

## Ordered Execution

The input/label freeze must be committed and pushed before any new-case scoring
or selection. No variant search, scorer tuning, slot increase, prompt change,
episode store, semantic keyword rule or native continuation is authorized.

Stage-one verification from the repository root, without selectors or providers:

```sh
uv run --locked python -m pytest workflows/evals/character_memory_dev/story_continuity/correction_dependencies/tests/test_inputs.py -q
```

After that committed freeze, use the unchanged current-only literal recipe and
both existing selectors once, then build twelve selected-arm packets, six empty
packets and all 45 distinct-per-case labeled reference packets. Real runtime
builders must bind the unchanged 11,213/11,469 input limits, 4,096 reply reserve
and 640 suffix ceiling. Record exact paired requests, H handles/hashes/roles,
source ordering, selected versus admitted sources and all omission causes.

Named-answer support is separate from correction admission, missing antecedents,
correction explanation and visibility of mistaken retellings. Original-only may
answer either case; self-contained correction alone may answer its case. Missing
correction is not a dangling or resolved dependency. Preserve conditional or
unassessable readings rather than forcing consensus; do not aggregate quality.

The predeclared investment trigger is the same selector showing the matched
dependency-specific gap in at least two episode pairs, with fitting reference
packets resolving it. It can justify proposing one bounded design, never adopting
or implementing it within this study. Negative, unassessable or generic selection
failures also complete the study; do not add cases until it wins.

All historical evidence remains byte-preserved. No database/trial access, provider
or API calls, external account/review operation, native turns 8-10 or deployment.
The user's Relay request permits internal read-only technical review; that does
not create independent semantic annotations. Keep the study explicitly non-blind
and synthetic, with generation, naturalness, reviewer interpretation, persistence
and production retrieval unmeasured. Final results will be recorded in `READOUT.md`.
