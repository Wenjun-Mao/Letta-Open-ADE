# Packet-Sufficiency Audit

Status (2026-09-30): **Non-blind offline diagnostic complete; candidate unadopted.**
The user approved the [single follow-up plan](../../../../../docs/plans/character-story-continuity.md#packet-sufficiency-audit).
The [returned-report assessment](reports/assessment-2026-09-30.md) preserves both
originals and source checks; each reviewer disclosed inherited ADE context.
The [readout](READOUT.md) covers all ten cases, 38 reference alternatives and 68
exact paired packets. The candidate recovers opposed evidence under varied
retelling but fails antecedent recovery. No blind qualification, measured model
behavior or selector adoption is claimed.
PC-03/04/05/06/09/10/11 remain unchanged; native turns 8-10 remain unrun.

After a further preflight stopped before packet access, the user chose to use
the existing Pro reports and declined API substitution. [ADR 0055](../../../../../docs/adr/0055-nonblind-packet-sufficiency-diagnostic.md)
authorized the remaining offline work as a non-blind diagnostic. `judgments.json`
was committed at `bed18094eaaeabe66c5d754cb098fcccf29ec952` before new-control
selections. A/B conditional alternatives remain distinct.
The original freeze and receipt remain immutable; neither report becomes blind.

## Why This Layer

The earlier coverage metric checked author-designated source groups, not the
claims justified by each question. Its improved cases also fit exactly four
distinct text pairs into four slots. That evidence cannot establish a general
retrieval benefit. This workflow changes measurement preparation, not runtime:
freeze inputs, obtain external query-relative judgments, then inspect actual
packets without tuning. See the [source-verified assessment](../../../../../docs/findings/natural-memory-consultation/character-story-retrieval-review-assessment-2026-09-30.md).

## Input Contract And Ownership

`packet-sufficiency-input-v1` is a bounded audit contract, not a new production API
or a general evaluation framework. `freeze.json` pins the source revision,
historical fixture/outcome/selector bytes, controls, context, rubric, mapping and
runtime owners. `packet.py` pins that manifest and renders an allowlisted view.
Changing an input fails preparation; do not update hashes to accommodate outcomes.
If a real defect is found, preserve this freeze and explicitly amend the audit
before comparison. A later runtime change requires a separately bound audit, not
silent reuse of these results.

- `controls.json` adds exactly two Mandarin controls before scoring. Each has
  seven distinct related exchanges, not four unique pairs padded with copies.
  Neither repeats its target query. The second includes a short overlapping
  correction referring to an earlier day; whether both sources are required for
  this question is recorded separately from correction visibility in the Pro reports.
- `context.json` declares controlled scope, roles, chronology, persona assumptions,
  empty facts/local suffix and H versus U/A authority. Each pair is a distinct
  archived synthetic conversation, matching the old packet mechanics. Synthetic
  timestamps order utterances; they are not event dates. This is not a native
  persona/request replay, and cross-chat antecedent ambiguity must be reported.
- `mapping.json` is operator-only: neutral cases map to old/new IDs; neutral
  `E01`, `E02`, etc. map to source rows in their unchanged chronological order.
- `RUBRIC.md` asks for minimum claims, counterevidence, optional detail, forbidden
  attribution, antecedents, alternative sufficient sets and deletion challenges.
- `REVIEW_PACKET.md` is the generated, complete handoff artifact. It intentionally
  contains all transcripts in one document. Only this file goes to the reviewer;
  do not provide this README, mapping, old reports or the repository tree.

The input author has seen historical results. Neutral IDs and a clean external
session reduce presentation leakage, not all authorship bias or public-repository
exposure. The retained review is exposed-context AI annotation, never human validation. The
operator must record prior exposure and consequential ambiguity rather than
asserting perfect blindness.

## Reproduce Offline

From the repository root, with no database or provider access:

```sh
uv run --locked python -m workflows.evals.character_memory_dev.story_continuity.packet_sufficiency.packet
PYTHONPATH=. uv run --locked python services/ade-api/tests/agent_runtime/story_packet_comparison.py
uv run --locked python -m pytest workflows/evals/character_memory_dev/story_continuity/packet_sufficiency/tests services/ade-api/tests/agent_runtime/test_story_packet_sufficiency.py services/ade-api/tests/agent_runtime/test_story_packet_comparison.py -q
```

The first command prints the packet; tests compare it exactly with the committed
artifact. The loader imports only standard-library code, never selectors or
runtime internals. The frozen historical outcome file is hash-checked but never
decoded into the review packet. The second command is runtime-owned, regenerates
`comparison.json` and `packets.jsonl`, and makes no provider or database calls.
Tests reproduce their exact bytes and all eight old arm selections. Generated
artifacts intentionally retain every inspectable packet rather than abridging
source evidence to meet source-code file-length guidance.

Runtime-owned tests separately call the existing context assembler, admission and
reviewer builders. They bind `history_capacity.py`'s 11,213/11,469 input limits,
4,096 output reserves and 640 shared-suffix ceiling, including full candidate
reply reservation. Toy controls cover empty history, oversized message/annotation
omission with a later fitting window, nonempty annotation links, identical local/H
text with separate authority handles, paired history equality and corrupt hashes.
These five tests do not select from or score the ten semantic cases. Passing is
estimated-capacity/source mechanics, not exact provider-token or model quality proof.

Preparation verification: focused packet/admission/capacity checks passed 34 tests
with one unavailable-historical-evidence skip. The broader command
`uv run --locked python -m pytest services/ade-api/tests/agent_runtime workflows/evals/character_memory_dev/story_continuity -q`
passed 495 tests, with 76 PostgreSQL/private-evidence skips and one existing
Starlette/httpx deprecation warning. Ruff lint/format and scoped whitespace checks
passed. No live service, database or provider verification was performed.

## Historical Handoff And Stop

The following records the superseded clean-session procedure, not a current
request for another review. ADR 0055 replaced its prerequisite for this diagnostic
after the user's final direction. The completed result is in READOUT.md; no
further review dispatch or API substitute is authorized or needed here.

Historical stop (superseded for diagnostic use by ADR 0055): the returned reports are advisory AI evidence, not certified blind
annotations. Do not run the new-control comparison while the clean-session
requirement is unresolved. The user explicitly chose on 2026-09-30 to keep the
gate and obtain one clean-session replacement, not a non-blind diagnostic.
Both original Markdown reports retain their exact bytes, including hard-break
spaces; scoped whitespace checks exclude those imported originals only.

The replacement handoff must require a prior-context preflight before reading the
unchanged packet. If inherited ADE summaries, memories or earlier reviews are
present, stop before annotation. Do not show the replacement reviewer these
reports, their assessment, this README or the mapping. It is a fresh primary
review, not an adjudication between A and B. No automatic account dispatch.

Publish scoped inputs and verify the immutable packet URL without credentials.
Send one fresh external AI reviewer only that URL and a self-contained assignment
requiring the exact commit and the packet's rubric. No external account operation
or automatic chat creation is authorized. Prior unblinded reports cannot fill
this annotation stage.

After the report returns, preserve its bytes here in `reports/`, record reviewer
identity/kind, actual access, packet revision and exposure, and check all ten cases
and source quotes. Keep operator interpretation separate. Freeze the report and
any explicit unresolved/disputed status in a committed receipt **before** computing
new-control arm results. Missing/contaminated labels block affected conclusions;
use a second adjudicator only for consequential disputes.

Only then continue deliverables 3-5: reproduce unchanged selectors and literal
scoring, build evaluator-only reference/empty packets, test each actual supplied
packet at frozen limits, and publish the case-level decision readout. Reference
sets/answers must never enter selectors. Separate answer sufficiency, conflict
visibility, dependencies, optional detail, other-episode and unrelated admissions.
Do not tune inputs or algorithms to manufacture a positive result. No native
call, persistence claim, prompt change, runtime adoption or reopened turn-7 gate
follows from this handoff.
