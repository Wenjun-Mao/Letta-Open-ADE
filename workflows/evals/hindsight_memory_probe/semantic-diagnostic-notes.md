# Revision 5 Semantic Diagnostic Checkpoint

This is a bounded evidence note for the approved revision-5 follow-up, not a
product decision or a claim that Hindsight is ready for adoption. The archived
revision-4 evidence remains sealed at
`outputs/campaign-closeout/final-a3e78c5-1791733755949290911/`; archive SHA-256
`ac09bb1ce1450b4841c1b872ffccffc1f777aa3d0d474b5bf5edd1b8c5bf3464`, index
SHA-256 `26e6685880f4021371323f8f6663403957ab638838618623b6d0abc8361d72fc`.
The descriptions below point to safe synthetic source and evaluation receipts;
no private wire bodies, credentials, dumps, or model reasoning are copied here.

## Causal diagnosis

| Failure or distinction | Supplied information and observed path | Established cause | Unknown or confound | Owning layer and next discriminating probe |
|---|---|---|---|---|
| q01: source origin and participation crossed a character-root boundary | s01 source/readback contains the portable drink preference together with source interaction details. The candidate05 profile readbacks for s01-s03 and `initial-compare-a/character/q01-initial-1791713842204252902/` show recall returned 8 items. Before the projection retest, the admitted memories retained source context; the actual Character request and completed reply used that context and answered “Oct 1 morning” as origin. The query scope is `subject_a` / `root_other`; the source is `subject_a` / `root_xiaotang`. | Retrieval included root-local source context and Character used it to answer a cross-root origin question. This violates PC-02/03 separation: portable preference does not carry the private origin or participation. The initial source profile was also fragmented across s01-s03 rather than only current-state facts. | The sealed readbacks establish what source/facts were retained and tags, not which extractor decision caused each recalled fact. Exact model attention/cause cannot be inferred from its output. | Extraction/classification and Character-facing projection. Review fresh s01-s03 source/document/memory readbacks and recall/context receipts; ensure origin/time/participation are not presented to the cross-root request. q01 adequate control should supply only current profile and omit all origin/time/participation. Never substitute Sep 30 or Oct 1 as the desired source answer. (PC-02/03/06) |
| q01: empty Character output after the structural projection retest | `context-projection-retest/character/q01-structural-projection/` has recall and projected-context receipts, then `failure.json` code `conversation_output_empty`; `hindsight.request.json` records a final request with `max_tokens: 2048`. All eight attached contexts are absent in the projection, but factual text and source metadata remain. No assistant result receipt exists. | The attempted answer is incomplete. Empty output provides no semantic result and cannot be counted as a projection success. The request used the 2048 ceiling, but the failure receipt does not show that the model exhausted it. | Output-capacity pressure is plausible but not proven; provider-side empty generation or run variability also remain possible. The projection removed context but still passed facts. | Character generation/output capacity. Run the same q01 input and all three arms on the same bank with identical settings except `max_output_tokens=4096`; compare actual request `max_tokens`, finish/error receipt, usage, and observable reply. Preserve both captures. (PC-09/12) |
| q06: unsupported detail in a partially grounded answer | s09 is subject_b/root_xiaotang and says lemon water plus the shared plant name “绿邮差”. Candidate05 recall returned three s09-derived items before consolidation and six afterward; Character context retained them. The initial completed answer added “iced”; the post-consolidation answer also embellished the naming event with a windowsill/post-office detail. No subject_b source supports ice or that embellishment. s05 bag-repair story belongs to subject_a, not subject_b; no subject_b source establishes that it was told to this user. | Retrieval supplied the correct subject facts. The unsupported additions first appear in the observable Character reply, so the established defect is answer grounding/over-elaboration for this case, not a missing s09 fact. | The campaign changed bank profile between candidates and consolidation changed recall composition. Those factors may change answer likelihood, but do not support the added details. Absence of s05 under subject_b does not prove nobody ever told the story. | Answer generation/judgment, with scope as an input invariant. Compare Hindsight, empty and adequate arms; the adequate memory states only the supported lemon-water and naming facts. Assess unsupported elaboration separately from cautious uncertainty about s05. (PC-02/03/06/12) |
| q07: bicycle omitted after consolidation; other distinctions remain | The s08 readback is subject_a/root_other. Its standalone bicycle commute fact is profile-portable; “青石” was named only in that other-root chat. s06/root_xiaotang describes a yellow scarf only as a hypothetical future beach trip. Initial candidate05 recall returned 17 items including s08; the completed answer recalled bicycle, declined to invent a prior nickname, correctly kept the trip hypothetical, and offered to name the bicycle now. Post-consolidation recall returned 33 items including s08; projected context still included s08, and the actual serialized request had a 14,336-character system message. The completed answer missed the bicycle but preserved uncertainty about the name and the hypothetical trip. | The initial answer demonstrates that a new naming offer can be allowed as present invention under PC-11 while not being a remembered joint event. The post-consolidation miss is not a retrieval omission: an s08 candidate remained in both recall and projected context. | More recalled material and a longer request coincide with the miss, but consolidation, ranking/order, changed projection behavior, and generation attention are confounded. This small sample cannot establish which made the bicycle fact lose salience. | Retrieval ranking/context selection versus answer generation. Compare safe recall projections, actual projected contexts, and actual Character requests for q07 across both checkpoints. The adequate control supplies bicycle profile and s06 hypothetical separately, while audit metadata keeps 青石 out of current-root context. (PC-02/03/06/11/12) |

The finding at `docs/findings/hindsight-oci-campaign-2026-10-11.md` remains the
summary authority for revision-4 observations. Candidate04/05 records and their
result receipts are unchanged. The local sealed archive index binds individual
receipt paths; use it to verify archive members rather than copying receipts
into tracked files.

## Additive adequate controls

`fixtures/semantic-diagnostic-controls-v1.json` adds versioned q01/q06/q07
controls without editing `fixtures/campaign.json`, its source corpus, questions,
persona, or old expected fields. Existing q02/q04 adequate controls remain in
place. The freezer hashes and embeds the new file in each candidate manifest;
the replay driver supplies Hindsight, empty, and adequate arms in one feature CLI
input. Each stage-completion summary repeats the predeclared semantic
distinctions and source/scope audit beside the input fingerprint. Controls are
mechanics and semantic sufficiency probes, not hand labels of runtime output.

q01's supplied memory contains only the current profile. Its audit receipt binds
the source to subject_a/root_xiaotang while the active scope is
subject_a/root_other; source time, origin, and participation are intentionally
absent from Character input. q06 controls bind s09 to subject_b/root_xiaotang
and exclude unrelated s05. q07 supplies the bicycle as profile and the s06
hypothesis as a separate character-local memory. The audit records that “青石”
belongs only to root_other, without supplying that root-specific name to the
current Character. Expected distinctions cover PC-02/03/06/11/12.

## Reproducible manager-run inputs

Run from a clean checkout at the exact committed revision used for the
candidate. The manager provides Hindsight URL/key through the existing operator
environment. `OUT` must be a new private directory. Commands below do not start
services; they freeze inputs or call the already-authorized operator replay.

```sh
OUT=/tmp/ade-hindsight-semantic-v1
WORKSPACE=hs_semantic_followup_v1
mkdir -m 700 -p "$OUT"

uv run --locked python -m workflows.evals.hindsight_memory_probe.freeze \
  --workspace-id "$WORKSPACE" \
  --output-directory "$OUT/freeze"

uv run --locked python -m workflows.evals.hindsight_memory_probe.replay \
  --manifest "$OUT/freeze/campaign-manifest.json" \
  --output-directory "$OUT/retain-a" --stage initial-retain-a
uv run --locked python -m workflows.evals.hindsight_memory_probe.replay \
  --manifest "$OUT/freeze/campaign-manifest.json" \
  --output-directory "$OUT/retain-b" --stage initial-retain-b

# Baseline: q01, q06 and q07 each run Hindsight, empty, and adequate arms.
uv run --locked python -m workflows.evals.hindsight_memory_probe.replay \
  --manifest "$OUT/freeze/campaign-manifest.json" \
  --output-directory "$OUT/compare-a-2048" --stage initial-compare-a
uv run --locked python -m workflows.evals.hindsight_memory_probe.replay \
  --manifest "$OUT/freeze/campaign-manifest.json" \
  --output-directory "$OUT/compare-b-2048" --stage initial-compare-b

# Capacity ablation on the same retained banks and the same arm inputs.
# The only changed setting is 2048 -> 4096 output tokens for every arm.
uv run --locked python -m workflows.evals.hindsight_memory_probe.replay \
  --manifest "$OUT/freeze/campaign-manifest.json" \
  --output-directory "$OUT/compare-a-4096" --stage initial-compare-a \
  --max-output-tokens 4096
uv run --locked python -m workflows.evals.hindsight_memory_probe.replay \
  --manifest "$OUT/freeze/campaign-manifest.json" \
  --output-directory "$OUT/compare-b-4096" --stage initial-compare-b \
  --max-output-tokens 4096
```

The baseline comparison stages include the original q02/q04 adequate controls;
the added q01/q06/q07 controls are additive. `stage-completion.json` identifies
the control version, expected distinctions, source/scope audit, output-token
ceiling and immutable input hash. Preserve candidate04/05 and all revision-4
receipts. For post-consolidation diagnostics, use a separate fresh candidate
workspace and `--stage consolidate`; that stage runs all three arms at the
default 2048 ceiling. Do not change questions, source fixture, persona, route,
or limits when interpreting the 4096-token capacity ablation.

The new `--max-output-tokens` flag only prepares an input to the existing
feature CLI and is limited to the predeclared 2048/4096 diagnostic ceilings. No
Character implementation, model default, deployment, or product contract was
changed; an ADR is not warranted for this offline experiment control.
