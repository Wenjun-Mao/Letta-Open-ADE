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
| q01: source origin was exposed alongside a correctly resolved current preference | s01/s03 readbacks contain the portable drink preference and source interaction details. Candidate05 profile readbacks for s01-s03 and `initial-compare-a/character/q01-initial-1791713842204252902/` show recall returned 8 items. The Character request included source context and the completed answer named “Oct 1 morning” as origin. The query scope is `subject_a` / `root_other`; the source is `subject_a` / `root_xiaotang`. | The output is evidence that the origin answer matched material exposed in the request; it does not establish which recalled item caused the answer. The current-value resolution itself was correct: the final hot, unsweetened oolong preference is supported by the explicit correction and later preference change. Those time-bounded former values and corrections remain portable profile facts under the current contract. The cross-root exposure of source origin and participation is the boundary concern (PC-02/03), not a defect in resolving the preference. | The sealed readbacks establish retained facts, tags, and request exposure, not the model's attention or which fact caused its answer. | Extraction/classification and Character-facing projection. Review source/document/memory readbacks and recall/context receipts; ensure source origin and participation are not exposed to the cross-root request while preserving useful current, former, and corrected profile values. The q01 adequate control supplies only the current profile and omits origin/time/participation. (PC-02/03/06) |
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
absent from Character input. q06 binds s09 to subject_b/root_xiaotang and
excludes unrelated s05. Its adequate arm separates the lemon-water preference
as an unowned profile memory from the mint-naming experience tagged to
root_xiaotang. The experience retains the source wording “昨天” and records the
2026-10-01 message timestamp separately, without treating that message date as
the naming-event date. q07 supplies the bicycle as profile and the s06
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
receipts. For post-consolidation diagnostics, run `--stage consolidate`
against the same retained candidate workspace/bank used for the preceding
retain and comparison stages, with a new output directory for the stage
receipts. Do not initialize a fresh empty workspace: it would not measure
consolidation of the retained candidate. The consolidation stage runs all three
arms at the default 2048 ceiling. Do not change questions, source fixture,
persona, route, or limits when interpreting the 4096-token capacity ablation.

The new `--max-output-tokens` flag only prepares an input to the existing
feature CLI and is limited to the predeclared 2048/4096 diagnostic ceilings.
At that control-preparation checkpoint, no Character implementation, model
default, deployment, or product contract had changed. This statement describes
that earlier checkpoint only. The approved activation-clock contract is
recorded in
[ADR 0067](../../../docs/adr/0067-hindsight-revision-five-activation-clock.md).

## Revision-5 Exact-Source Retest And Regression Outcome (2026-10-11)

The focused retests and original-case regression ran the repaired Character
runtime at source SHA
`d2a27c338d71d90ef2fa8ad7a7085682a7aa4e06`. The capture-shape documentation
commit `d9f67986cdaee8c1f7ff6d0134e72b0f20b76d5a` was documentation-only and is
not the runtime identity; this note update is also documentation-only. Persona,
model, questions and Character defaults were unchanged, and no native default
or deployment change is implied.

### Mechanically verified composition

The feature captured the two Character context groups and actual request; the
groups matched their context receipts. Same-bank before/after ordered raw recall
was identical for q01 (14), q06 (4) and q07 (35), and retained-bank inventory
hashes match. This isolates response changes from raw-recall changes in that
pair, but not model attention or semantic cause. Fresh initial and
post-consolidation stages completed nine arms each at 2048 tokens under this
runtime SHA, the latter on a newly retained bank. The original q02/q03/q04/q05/
q08 cases ran once as a 12-arm regression, not as focused-case rerolls. Receipts:
[same-bank comparison](outputs/revision5/d2a27c3/manager-same-bank-raw-recall-comparison.json),
[fresh initial](outputs/revision5/d2a27c3/fresh-d2a27c3/initial-focused-2048/stage-completion.json),
[fresh post-consolidation](outputs/revision5/d2a27c3/fresh-d2a27c3/post-consolidation-2048/stage-completion.json),
[original-case regression](outputs/revision5/d2a27c3/fresh-d2a27c3/remaining-original-cases-2048/stage-completion.json).

The 46599c6 baseline also has 2048-token comparison and a 4096-token
max-output ablation. All recorded Character responses in those capacity checks
were nonempty and ended with `stop`; they neither reproduced nor identify the
cause of the earlier empty q01 output. Capacity observations are bounded to
those requests and do not prove provider-side capacity generally.

### Focused semantic results

- **q01:** The current hot, unsweetened oolong order is correct. The cross-root
  answer now leaves the originating conversation and this character's hearing
  unestablished. In the fresh post-consolidation answer, however, it calls
  2026-10-01 09:00 the “earliest record” when asked for the origin. That
  timestamp may describe a profile record, but does not establish the first
  source conversation. Preserve useful preference-change/correction dates;
  this is a remaining source-time inference, not evidence that all profile
  dates should be erased. The misleading consolidated jasmine-as-original
  summary is memory `61c86409-af11-4977-bc03-1ed355eac314` in q07's context,
  not q01's. The immutable
  [`manager-capture-location-correction.json`](outputs/revision5/d2a27c3/manager-capture-location-correction.json)
  corrects the earlier capture-location record; the raw s03 source says jasmine
  was a misspeak and oolong was intended. q02 regression Hindsight still
  presents jasmine as a real earlier preference/change, while its adequate
  control correctly distinguishes the misspeak from later temperature and
  sugar changes. See [q01 post result](outputs/revision5/d2a27c3/fresh-d2a27c3/post-consolidation-2048/character/q01-post-consolidation-1791760733178036716/hindsight.result.json)
  and [s03 source](fixtures/campaign.json#L12).
- **q06:** The same-bank Hindsight result still contains the unsupported prior
  shared naming utterance (“那天我还笑说…”), absent from its supplied facts.
  Neither of the two fresh Hindsight answers repeats it. This mixed sample is
  not proof of a deterministic repair. The same-bank optional solo bag story
  was introduced as something the character could tell now, not as a prior
  shared event; it is compatible with PC-11's permission for new solo history.
  See [same-bank result](outputs/revision5/d2a27c3/same-bank-repair-2048-d2a27c3/character/q06-same-bank-repair-1791759809734043506/hindsight.result.json),
  [fresh initial](outputs/revision5/d2a27c3/fresh-d2a27c3/initial-focused-2048/character/q06-fresh-initial-1791760513993038797/hindsight.result.json)
  and [fresh post](outputs/revision5/d2a27c3/fresh-d2a27c3/post-consolidation-2048/character/q06-post-consolidation-1791760817785599081/hindsight.result.json).
- **q07:** The repaired same-bank and both fresh Hindsight answers state the
  bicycle profile, keep the yellow-scarf trip hypothetical and do not expose
  `青石` from the other character root. Judgment remains mixed: the same-bank
  answer turns an unconfirmed red-kite guess into a categorical denial; fresh
  initial also ends with an unsupported “we have not gone together” statement,
  while fresh post-consolidation preserves uncertainty. Speculation that the
  user confused another chat remains weakly supported. These samples show
  restored bicycle use without qualifying reliable recall or judgment. See
  [fresh initial](outputs/revision5/d2a27c3/fresh-d2a27c3/initial-focused-2048/character/q07-fresh-initial-1791760550854681316/hindsight.result.json)
  and [fresh post](outputs/revision5/d2a27c3/fresh-d2a27c3/post-consolidation-2048/character/q07-post-consolidation-1791760856386776014/hindsight.result.json).

### Original-case regression and scoped usage

- **q02:** Hindsight resolves the current order but treats the corrected
  misspeak as a real earlier jasmine preference; adequate distinguishes it.
- **q03 and q05:** Hindsight recalls the rainy-alley shared event and the
  imaginary bookstore `慢灯`, including its exact tagline, and keeps the shop
  imaginary.
- **q04:** Hindsight correctly recalls the blue cotton thread and the
  character's solo repair, but invents a beige bag color absent from s05 and
  the supplied context. The thread detail is source-supported. Adequate leaves
  the bag color unknown.
- **q08:** Hindsight returns the red notebook cover. This single run is not a
  new curation qualification.

[`manager-character-usage-summary.json`](outputs/revision5/d2a27c3/manager-character-usage-summary.json)
counts 39 baseline and 39 repaired
Character responses (78 total), all nonempty with `stop`. Its reported
161,442 prompt and 35,357 completion tokens are API-reported Character-result
usage only; the summary excludes retain, consolidation and embedding-model
usage and is neither a complete model-usage total, invoice, nor spend estimate.
No native default changed. These exact-source observations establish a
mechanical projection/request change with mixed semantic outcomes; they do not
establish Hindsight adoption or general behavioral qualification.
