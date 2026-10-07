# ADE Message Journey: Interactive Draft

**Playable documentation preview; no ADE runtime change.** The user requested
the moving chart on 2026-10-06 after the specification was produced. The
architecture/status mapping remains a draft for review, not a newly adopted
pipeline. Reviewed 2026-10-06 against ADE source
`125082447c2c5f5ada7a2c5ed88be41bb8fba4bf`. Source inspection is not a live trace,
behavioral acceptance result, deployment audit or new experiment authorization.

## Read In This Order

Open [the moving chart](ade-message-journey.html), not `player-template.html`
(the unbuilt source template). The default is a paused **six-chapter guided
journey** with three to six relevant pieces visible. **Forward/Back** moves one
chapter at a time and stays paused. **Play chapter** animates only the selected
chapter and stops at its end; it never automatically advances to the next chapter.
The chapter buttons jump directly to a chapter, paused.

The guide carries one explicitly **fictional worked example** through all six
chapters. Literal values replace generic payload descriptions; **Input / Output
preview** lets you inspect a chapter without playing it. The output preview is
the chapter's possible result, not the current animated state. The diagram's
values change at their original source beats. See the worked-example revision
below for the illustration's scope and verification limits.

**Show detailed map** opens the existing full map at the current source beat.
Here Forward/Back moves one detailed beat; **Follow this step** shows only its
endpoints. **Guided journey** returns to the corresponding chapter of the main
tour, or the remembered chapter when returning from another path. Both view
changes pause playback. Expand **Explore other paths** for the seven original
flows, including accurately labeled experiments and unimplemented work.

In the full-page player,
**Full screen** expands the chart when the browser supports native fullscreen;
Escape exits without resetting the flow. The seven flow buttons sit under the
canvas in that expandable section. Chapter selection has an active progress
underline, narration and manual navigation below the canvas. Tour selection
resets to paused; Replay plays only the selected chapter/flow and stops at its
end. With reduced motion, use manual stepping instead.

1. [Layout](layout.json): nested ownership frames and processing/artifact boxes.
2. [Edges](edges.json): named information/control connections, independent of depth.
3. [Steps](steps.json): seven selectable narrated tours, with ordered animation beats.
4. [Evidence](evidence.json): inventory bindings, conditions, status and source anchors.

The files use the JSON-compatible subset of Hindsight's `FigGroup`, `FigEdge[]`
and `FigStep[]` types. `review.py --emit` assembles a complete `Figure` JSON on
stdout without writing or rendering an artifact. Status/provenance live in the
sidecar, not invented fields in the renderer schema. Visible labels/captions
also retain status so an exported figure cannot lose the experimental/deferred
distinction. Review metadata is not a second capability inventory.

## The Main Journey

```text
Existing authored persona and immutable conversation binding
  |
User sends ordinary text
  -> Acceptance gates and one user/run transaction
  -> Accepted run receipt; UI monitors, worker claims
  -> Coherent bound state and attempt preflight
  -> Consider compaction BEFORE generation, only when eligible
  -> Subject-scoped fact search and local context construction
  -> Actual serialized conversation request
  -> Shared interpretation / choice / character expression
       optional: tool request -> Memory search -> actual result -> next request
  -> Candidate reply, not persisted or delivered
  -> ONE reviewer under the bound policy
  -> Prepare representations for value-bearing factual operations
  -> Revalidate and atomically commit the success bundle
  -> UI reloads persisted reply / facts / retained activity
```

This main tour picks a **typed-policy successful new run**, with automatic fact
search, value-bearing review operations, no new compaction and no tool call. It
does not claim every turn takes these branches. Cards are illustrative payload
descriptions, not recorded evidence or gold-standard character responses.

The chronological journey crosses ownership boundaries repeatedly. L1/L2/L3
frames remain a responsibility hierarchy, not numbered execution layers. The
supporting runtime owns sequencing and finalization; boxes do not imply services,
agents, separate files or extra model phases (PC-08/09/12).

Inside an L2 frame, L3 tags identify inventory responsibilities, not model calls.
The shared generation box explicitly carries both CHAR-03 and CHAR-04. Records
and supporting runtime boxes are not assigned fictional L3 capability depth.

## Ownership And Representation

| Frame | Included responsibility |
| --- | --- |
| L1 Character / L2 Persona Definition | CHAR-01 authored intent and CHAR-02 existing immutable binding; authoring is a pre-turn prerequisite. |
| L1 Character / L2 Conversation Behavior | One shared CHAR-03/04 generation box plus CHAR-05 finite curated-tool mechanics; no interpretation-to-expression handoff. |
| L1 Memory / L2 Recall & Context | MEM-01/02 scope/search, experimental MEM-03 historical selection, MEM-04 consumer context. The typed path does not traverse MEM-03. |
| L1 Memory / L2 Retention & Updates | MEM-05 user capture, MEM-06 one policy-bound reviewer, MEM-07 structural integrity/atomic commit. |
| L1 Memory / L2 Organization & Maintenance | Implemented MEM-08 fact representations and MEM-09 compaction; deferred MEM-10 additional views has no flow edges. |
| L1 Interface | Conversation, lineage and public activity, plus accurately labeled private evaluation artifacts rather than a new public inspection UI. |
| L1 External Tools | Deferred EXT-01, isolated from all executed paths. Internal `search_memory` is not an outside tool platform. |
| Supporting register | SUP-01 orchestration, SUP-03 Model Router, and PostgreSQL records under SUP-02; not another L1 domain. |

Cylinders are the inventory's six persisted record families. Candidate text is
a plain artifact box, not a new database. Original dialogue records what was
said, not automatically accepted facts (PC-05). Definition snapshots include
runtime bindings but do not make deployment policy part of persona content.
Character-specific history does not rewrite global persona or transfer another
character's participation (PC-02/03/04/11).

This focused journey omits unrelated UI configuration, independent Comment/Label
labs and operational/evaluation subsystems not on the shown route. The full
[inventory](../inventory.json) remains their register. Logical arrows can collapse
internal work but may not invent it: for example, the fact search arrow includes
the revision/space-bound fact join, not an independent vector truth store.

## Conditional And Experimental Tours

| Tour | Meaning and placement |
| --- | --- |
| 1 Current message | The concrete typed-policy spine above. Machinery is source-backed; Character/Memory behavioral responsibilities retain their inventory statuses. |
| 2 Compaction | Implemented conditional local-summary preparation before generation; persist only with successful finalization. |
| 3 Memory tool | Enabled, discretionary `search_memory` inside generation's finite request loop. Not an always-on phase or phrase-triggered rule (PC-01/06/09). |
| 4 Natural review | Development-only variants: original source/lifecycle bundle plus candidate reply as reference. Replaces typed review for that policy, never a second reviewer. |
| 5 History | Development/evaluation `automatic_history` trial: bounded same-subject/same-character completed originals, archived/versioned eligibility, ranking/admission, guarded H reuse (PC-03/10). |
| 6 Failure / retry | Explicitly separate alternative cases. Retried attempts reuse the accepted run; failed/cancelled success bundles do not persist. Lease loss prohibits this worker's terminal commit. |
| 7 Not implemented | Static pauses only: proposed joint/neighborhood selection and ADR 0060 admission, deferred views/tools, open semantic/story questions. No invented packets. |

**Reviewer input is a real current boundary difference.** The capability
inventory lists the aggregate responsibility; it is not an exact per-policy call
trace. Current typed review receives current user, up to eight prior user messages,
active facts and entities, **not** the candidate reply. Natural variants receive
their supplied originals/lifecycle state and reference-only candidate. History H
is shared only in the bound experimental historical path. Source IDs and valid
citations prove neither sufficiency nor correct semantic interpretation (PC-05/12).

Natural variants also differ in full-snapshot/selective context and compaction
eligibility. Per-request serialized overflow checking is conditional on supplying
`input_token_limit`, currently for natural variants; do not imply that the typed
tool loop performs that same check on every follow-up request. Historical ranking
recipes can involve additional guarded embedding
work; tour 5 collapses those recipe-specific internals rather than implying zero
provider requests. The trial reader, greedy admission and revalidation exist;
general historical recall and joint/neighborhood selection do not. The precise
whole-selection contract in [ADR 0060](../../../adr/0060-joint-history-packet-admission.md)
remains proposed. This figure adopts none of those future mechanisms.

PC-11's permitted solo fiction is not an instruction to accept every assistant
story as a fact or invent user/shared history. Story admission/correction remains
open. PC-12's grounding, judgment and fidelity are response assessment lenses,
not nodes/calls or a generic agreeable-character standard.

## Animation Contract For Review

- Beats are narrative moments, not literal function calls or wall-clock timing.
  Edges show information, control or persisted visibility as labeled.
- Explicit return edges preserve arrow direction; do not use reversed packets to
  leave a misleading forward arrow visible.
- An edge array animates simultaneously in interfig. The only arrays here group
  an atomic transaction's conceptual writes, explicitly not concurrent SQL.
- `show` accumulates within a tour and resets between tours. Packet descriptions
  are illustrative and never expose private captured conversation data.
- `quiet` hides a connection until a tour uses it; it does not mean experimental,
  deferred or asynchronous. Status is expressed separately in text and metadata.
- Start paused (`autoplay: false`). Each tour is an illustration of an attempt or
  branch; renderer replay/looping must not imply repeated runtime acceptance.
- Public activity is retained metadata. Restricted full captures are a separate
  optional observation side channel, not hidden reasoning or a new runtime phase.
- Failure/cancellation beats illustrate separate cases, not a run that fails and
  then cancels after already terminating. A cancellation request can lose to commit.

## Reference And Presentation Implementation

The exact source figure, [what-hindsight-does.ts](https://github.com/vectorize-io/hindsight/blob/9269b88417ed263e5a8350f2e416ca2b322756b1/hindsight-interfig/figures/what-hindsight-does.ts),
is the presentation reference, not the screenshot. We inspected its layout,
edges and tours together with [model.ts](https://github.com/vectorize-io/hindsight/blob/9269b88417ed263e5a8350f2e416ca2b322756b1/hindsight-interfig/src/model.ts),
[Flow renderer](https://github.com/vectorize-io/hindsight/blob/9269b88417ed263e5a8350f2e416ca2b322756b1/hindsight-interfig/src/index.tsx),
[geometry.ts](https://github.com/vectorize-io/hindsight/blob/9269b88417ed263e5a8350f2e416ca2b322756b1/hindsight-interfig/src/geometry.ts)
and [authoring/export README](https://github.com/vectorize-io/hindsight/blob/9269b88417ed263e5a8350f2e416ca2b322756b1/hindsight-interfig/README.md).
No Hindsight `retain`/`recall`/`reflect` API, background consolidation, mental models,
knowledge pages, graph index or fact taxonomy is imported into ADE.

The local player adapts interfig's presentation contract to standalone SVG/DOM,
using its MIT edge-routing algorithm and no new product dependency. The reference
package is private; no published npm package is assumed. Reference export is
`npm run svg -- <spec.json> <output.svg>` within its own package; this repository
does not vendor that exporter. The editable presentation sources are
`flow-model.js` (routing), `flow-layout.js` (fixed content sizing),
`flow-view.js` (drawing), `player.js` (finite
playback), `guide.js` (source-backed reading projections), `examples.js` and
`example.json` (fictional teaching values), `player.css` and
`player-template.html`. `build.py` embeds the validated
specification and sources into one offline HTML file and optionally an inline
conversation fragment. [Third-party notices](THIRD_PARTY_NOTICES.md) are embedded.

### Reference-Style Revision, 2026-10-06

The first player's focused default, upper toolbar and unfilled process cards
made it a step inspector rather than the requested Hindsight-style moving map.
That revision followed the inspected `src/index.tsx` more closely: dotted
canvas, softly filled nested frames, centered process/store labels, fixed inset
data cards with dashed borders, initially blue cumulative trails, glowing packets,
traveling data chips, arrow labels, and a quiet bottom control track. This is
still an SVG/DOM adaptation, **not** a claim that we use the original React
component unchanged or achieved browser pixel parity. No `layout` ownership,
edge identity or narrated runtime beat was changed by this styling revision.

Visible subtitles retain capability/record IDs and every status qualifier. Full
source descriptions and flow conditions remain in the expandable **Flow
conditions and module details** section and accessible SVG titles. Payload
metadata is rendered too, including qualifications such as "Summary if present."
Card sizes account for the largest content and metadata across every tour;
showing a payload does not move its endpoints. Old saved preview state is ignored
on this presentation revision so it cannot restore the previous focused default.

The root cause of packet/text overlap was upstream routing without obstacle
avoidance, not ADE dataflow. Obstructed edges now use a tested, rounded
card-and-heading-aware visibility-grid route; clear curves retain the upstream mechanism.
Routing includes quiet edges when assigning ports, so labels/payloads and beat
changes cannot move a connection. Arrow labels appear only where they fit clear
of cards and canvas edges; the full connection remains in the details readout.
Traveling data chips hide when they would cover a card. Endpoints are returned
exactly, avoiding floating-point arrival drift after arc-length interpolation.

The standalone player keeps the wide reference-style topology, scales to fit
down to 75%, and scrolls horizontally below that. It no longer uses a short
vertically clipped viewport or automatic panning. The inline preview instead
reflows groups to its measured width, with no internal scroll pane or font
scaling; it cannot reproduce the same desktop proportions at chat width. Both
are driven by the same reviewed ADE specification. Fullscreen is a full-page
presentation feature, not a host-required dependency.

Offline DOM tests cover desktop/mobile standalone and 736/320px inline widths,
all tours/views, moving packet
positions, pause/replay, end-of-tour stopping, reduced motion, fixed geometry,
status/metadata preservation, bottom controls, mock native fullscreen, and
obstacle routing.
Native SVG raster snapshots were visually inspected for the send and atomic-write
scenes plus the complete map. These are **not real browser-engine screenshots**:
browser pixel layout, host integration and assistive-technology behavior remain
unqualified.
Drawing/interaction checks do not qualify ADE's product behavior.

### Guided Reading Revision, 2026-10-06

The complete map put ownership, provider mechanics, stored records and 42 main
tour beats on the same initial surface. That presentation-level information
overload, not an ADE runtime defect, made the journey hard to comprehend. The
user approved trying progressive reading and requested their own pace.

The guide partitions those existing beats into six reading chapters: accept
message (0-7), assemble context (8-23), generate candidate (24-27), review updates
(28-35), validate/commit (36-38), display reply (39-41). These are zero-based
source beat ranges, **not new L2/L3 modules, agents or model calls** (PC-08/09/12).
`guide.js` selects real endpoint nodes and exact original edges within each
range, preserves their order and records each displayed beat's source identity.
Visible data cards carry the source's accumulated state at that exact beat,
including responses from omitted provider mechanics; hiding a transfer does not
erase its returned data or advance a result before it exists in the source tour.
The worked-example revision below decorates only the guide's illustrative values
at these same source beats.
It never invents a shortcut arrow for omitted provider work. The original
layout/edges/steps/evidence and all 31 details remain available unchanged.

The guided canvas uses one combined L1/L2 ownership header per group instead
of nested frames. Runtime support, records and candidate artifacts stay distinct;
layout placement does not establish execution order. Endpoint geometry is stable
within a chapter, but intentionally changes between chapters. Only the current
transfer is blue; completed transfers are subdued, including in the detailed map.
Atomic grouped transfers still highlight together, not as parallel SQL calls.

Provider/catalog mechanics, detailed snapshot reads and some atomic transaction
members are omitted from the guided drawing, explicitly labeled as selected
transfers. Narration retains the existing typed-policy branch, pre-turn persona
binding, no historical retrieval/new summary, shared character generation, typed
reviewer's exclusion of the candidate, vector preparation condition, atomic
success and persisted UI refresh. Partial capability status remains visible;
deferred/experimental/proposed work stays qualified in the footer and full map.
This is a reading projection, not a simplified runtime specification or a new
behavioral qualification (PC-02/04/05/09/12).

Rejected alternatives were deleting low-level source information, redrawing a
fictional linear pipeline, and merely slowing the same crowded full map. Manual
chapter navigation remains paused, including after interrupting playback. Play
and Replay stop at chapter boundaries; detailed controls still navigate all
original beats. Saved state is presentation-versioned and restores paused, so
old full-map state cannot defeat the new default. Offline guardrails verify
source identity, range coverage, boundary stopping, view round trips, reduced
motion, unobstructed routing and width-fitting without text scaling. Native SVG
snapshots cover every chapter and a narrow projection; real-browser pixels and
assistive-technology behavior remain unverified.

### Worked Example Revision, 2026-10-07

The guide reduced structural overload but still showed labels such as "original
text + attribution" and "proposed operations." Those descriptions did not show
what a message becomes. This is a presentation-data problem, not missing ADE
processing. `example.json` and `examples.js` supply a single authored teaching
fixture without modifying the layout/edge/step/evidence source specification or
runtime. The generic detailed/conditional/experimental maps remain reference
views rather than inheriting this fictional success case.

Fictional user Alex says, "I've moved to Toronto. My slides are finished, but I
haven't rehearsed." The existing local chat says the presentation is tomorrow;
the stored location is Ottawa v1. Fictional Rowan v3 is warm and direct and
prefers concrete help. This is **not Xiaotang's actual persona**, a new saved
definition or a measured character response (PC-04/12). The illustration shows
an accepted user/run, selected context, one possible candidate reply, a typed
location correction with the exact current-user quote, a prepared representation,
atomic success and the same reply reloaded by the UI (PC-01/02/05/08/09).

Only `show` values in a derived guided view are decorated. Node membership,
ownership/status labels, edge identities/direction, source beat identities,
ordering and timing remain source-backed. The source projection itself remains
unchanged. The timeline's identities are tested against the original transfers.
Candidate text appears after generation; the typed reviewer receives user/fact
input, never the candidate. The proposal appears on review return, a vector only
after representation preparation, and reply/fact/success state changes at the
atomic commit beat. UI reply text changes at the persisted refresh beat, not at
candidate generation. No new summary, history recovery, hidden reasoning, numeric
embedding, privacy policy or additional module/call is illustrated.

The Input / Output preview is a teaching view of the **whole chapter**, available
while paused, not early runtime visibility. It is explicitly fictional; proposal
and success previews are neither provider observations nor model-quality gold
standards. Success assumes guards pass. Structural schema/source checks establish
fixture compatibility, not reliable interpretation (PC-05/12). The proposal uses
the current registry's `person.current_location` and existing `correct` schema;
synthetic IDs and readable payloads are not public API JSON. No actual records,
provider requests or persona updates are created.

Adding more panels or a second pipeline was rejected: examples reuse existing
inset cards plus one compact, width-reflowing input/output pair. Guided cards now
reserve the largest content **within that chapter**, avoiding empty space for
later chapters' longer values while preserving geometry throughout playback.
The complete reference map still sizes across all its tours. Back/Forward,
chapter end-stops, reduced motion and paused view/state restoration are unchanged.

Guardrails verify immutable source structure, every chapter's paused preview,
phase visibility, consistent candidate/committed/displayed wording, exact quote
binding, typed proposal schema, inset sizing, obstacle routing, inert data and
absence of fictional overlays on experimental paths. Native SVG snapshots cover
chapter starts/results and narrow layouts. These are not browser screenshots;
real-browser page layout, host integration and assistive technology remain
unqualified. The user's supplied Safari screenshot confirms the prior guided
view displayed, not acceptance of this updated version.

## Offline Checks

Acceptance routing refinement, 2026-10-07: independent shortest detours put
`accepted-source` and `save-accepted-run` on opposite sides of the worker card,
visually bracketing it. Both now use interfig's existing `around: "below"` hint
in `edges.json`. This is presentation geometry only: endpoints, ownership,
transaction grouping and source beat order are unchanged. Switching the hint to
`"above"` is a small authoring edit; obstacle avoidance still protects cards and
headings at wrapped/narrow widths. A wide-layout guard checks both paths below
the worker, canvas containment and stable geometry throughout playback;
`acceptance-wide` adds a native SVG snapshot, not browser qualification.

From the repository root:

```sh
uv run --locked python docs/architecture/capability-map/message-journey/review.py
uv run --locked python docs/architecture/capability-map/message-journey/review.py --emit
uv run --locked python -m pytest docs/architecture/capability-map/message-journey/test_review.py -q
uv run --locked python docs/architecture/capability-map/message-journey/build.py
uv run --locked python docs/architecture/capability-map/message-journey/build.py --check
uv run --locked python -m pytest docs/architecture/capability-map/message-journey/test_build.py -q
node --test docs/architecture/capability-map/message-journey/test_player.cjs
node --test docs/architecture/capability-map/message-journey/test_guide.cjs
node --test docs/architecture/capability-map/message-journey/test_examples.cjs
uv run --locked python -m pytest docs/architecture/capability-map/message-journey/test_example.py -q
node docs/architecture/capability-map/message-journey/snapshot.cjs
```

Node checks use the existing `apps/ade-web/node_modules` packages (`jsdom`, plus
`sharp` for optional snapshots), not a new dependency installation. Snapshot
outputs remain under ignored `.preview/`. Build output is deterministic and
`--check` rejects a stale tracked view. `--inline-dir <task-owned-directory>` also
generates a fragment without changing the tracked presentation.

No provider, database, real-browser or external-account calls are made by these
checks. Review the main journey and ownership/branch descriptions through the
playable draft. Publishing it promotes no architecture/policy decision.
