# ADE Message Journey: Proposed Interfig Specification

**Review first; no final figure or runtime change yet.** This proposes the
presentation of existing ADE responsibilities and information movement, not a
new pipeline. Reviewed 2026-10-06 against ADE source
`125082447c2c5f5ada7a2c5ed88be41bb8fba4bf`. Source inspection is not a live trace,
behavioral acceptance result, deployment audit or new experiment authorization.

## Read In This Order

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

## Reference And Later Rendering Gate

The exact source figure, [what-hindsight-does.ts](https://github.com/vectorize-io/hindsight/blob/9269b88417ed263e5a8350f2e416ca2b322756b1/hindsight-interfig/figures/what-hindsight-does.ts),
is the presentation reference, not the screenshot. We inspected its layout,
edges and tours together with [model.ts](https://github.com/vectorize-io/hindsight/blob/9269b88417ed263e5a8350f2e416ca2b322756b1/hindsight-interfig/src/model.ts),
[Flow renderer](https://github.com/vectorize-io/hindsight/blob/9269b88417ed263e5a8350f2e416ca2b322756b1/hindsight-interfig/src/index.tsx),
[geometry.ts](https://github.com/vectorize-io/hindsight/blob/9269b88417ed263e5a8350f2e416ca2b322756b1/hindsight-interfig/src/geometry.ts)
and [authoring/export README](https://github.com/vectorize-io/hindsight/blob/9269b88417ed263e5a8350f2e416ca2b322756b1/hindsight-interfig/README.md).
No Hindsight `retain`/`recall`/`reflect` API, background consolidation, mental models,
knowledge pages, graph index or fact taxonomy is imported into ADE.

After review, adapt the presentation renderer locally with MIT attribution and
the approved specification, without changing product runtime. The reference
package is private; do not assume a published npm dependency. Reference export is
`npm run svg -- <spec.json> <output.svg>` within its own package; this repository
does not yet vendor that exporter. Its `around` routing is not a general obstacle
solver, and narrow layouts scale then scroll instead of fully reflowing. Actual
desktop/mobile readability, routing, keyboard use, pause/replay, reduced motion
and static SVG equivalence must be checked during the later rendering iteration.
Schema checks below do not qualify pixels, animation or ADE behavior.

## Offline Checks

From the repository root:

```sh
uv run --locked python docs/architecture/capability-map/message-journey/review.py
uv run --locked python docs/architecture/capability-map/message-journey/review.py --emit
uv run --locked python -m pytest docs/architecture/capability-map/message-journey/test_review.py -q
```

No provider, database, browser or external-account calls are made by these checks.
Review ownership/layout first, then the main spine and branch/status descriptions;
approve rendering separately. No architecture/policy decision is promoted by
publishing this proposed specification.
