# ADE Capability And Dataflow Map

Reviewed 2026-10-04 against `f98c0ec6c78f1c6b30697fd49fe81a0b1f4a2189`.
This is a source-backed responsibility inventory, not a deployment audit, new
product contract, implementation authorization or behavioral acceptance result.

## Start Here

- [Static overview](ade-capability-map.svg): all registered pieces and a simplified
  main loop, viewable without executing HTML. Full named edges are in the HTML.
- [Connected map](ade-capability-map.html): choose recall, retention or support;
  select a piece for sources, evidence limits, known gap and next isolated check.
- [Readable inventory](inventory.md): generated reference for all registered pieces.
- [Character assessment guide](character-assessment.md): PC-12's authored-intent
  boundary and character-relative grounding, judgment and fidelity lenses.
- [Moving message journey](message-journey/ade-message-journey.html): playable
  source-backed draft with six paced chapters, fictional worked examples,
  Forward/Back and a detailed ownership/branch view; no runtime change.
- [Journey source and review guide](message-journey/README.md): interfig-compatible
  layout/edges/steps, rendering sources and branch/status evidence limits.
- [Inventory source](inventory.json): the single source for names, ownership,
  implementation scope, evidence limits, records and flow connections.
- [Chart readability](presentation.md): positive support/data identities and
  consistent bypass placement across the moving, connected and static views.
- [ADR 0061](../../adr/0061-capability-responsibility-map.md): vocabulary and the
  distinction between capability ownership and physical deployment.

`Domain -> Subsystem -> Module` means L1/L2/L3 containment, not execution order.
Character and Memory are core capability domains. Interface supports use and
inspection; External Tools reserves a deferred outside-information/action boundary.
The supporting register keeps runtime, storage, provider access, evaluation,
observability, operations, application wiring and schemas with their existing
owners. Comment Lab and Label Lab are adjacent features rather than being forced
into character conversational behavior.

This covers the named moving pieces in the character-memory loop and its current
surroundings. It is not an exhaustive file classification, historical-experiment
catalog or claim that every running service was inspected. Shared source files may
support several logical modules; that is not an instruction to split them.

## Status And Authority

| Status | Meaning |
| --- | --- |
| Implemented | Source-backed machinery exists; does not imply a test rerun, semantic acceptance or current release qualification. |
| Partial | Code covers part of the responsibility, or current and experimental paths differ in scope. |
| Experimental | Implemented/measured only in bounded development or evaluation; no general/default adoption. |
| Proposed | Named design only; no implementation or acceptance claim. |
| Deferred | Optional future capability, not approval to build it. |

Evidence limits are separate. Test links identify checks, not a claim that all
were executed in this documentation iteration. Empty tests remain an explicit gap.

Relevant [product agreements](../../product-contract.md): PC-01/02/03/04 define
natural dialogue, subject/character ownership and persona binding; PC-05/07 define
review versus integrity/persistence authority; PC-06 preserves exclusions;
PC-08/09 preserve the single runtime and minimum-code preference; PC-10/11 define
archive eligibility and consistent, scoped improvised character history.
PC-12 defines authored characterization versus contextual application and the
three overlapping assessment lenses; these are not internal phases or a composite
score. The [assessment guide](character-assessment.md) preserves creative scope,
separate input/sufficiency checks and uncertainty in diagnostic conclusions.
The map clarifies agreed intent; it changes no runtime behavior or qualification.

- Original dialogue records what was said, not automatic fact acceptance.
- CHAR-03/04 share the existing generation call, not two agents or a style rewriter.
- Memory owns recovery/review responsibilities; runtime binds actual consumer
  requests and coordinates the complete turn.
- Input capture precedes generation. Embeddings/compaction are prepared as needed,
  not a new post-reply background loop. Assistant, permitted changes and any summary
  retain existing atomic finalization.
- Fact scope differs from same-user/same-character dialogue scope. Historical
  paths are bounded/experimental; not every branch runs on every turn.
- [ADR 0060](../../adr/0060-joint-history-packet-admission.md) remains proposed.
  This map adopts neither whole-selection admission nor a new window-count policy.
- Existing compaction is MEM-09; only additional derived views are MEM-10.
- Public activity metadata and private captures are not interchangeable. Show
  observable receipts and actual packets, never inferred hidden reasoning.
- Memory search stays internal even when tool-invoked. Synthetic weather/failure
  fixtures are not a production external-tool platform.

## Reproduce And Verify

From the repository root:

```sh
uv run --locked python docs/architecture/capability-map/render.py
uv run --locked python docs/architecture/capability-map/render.py --check
uv run --locked python -m pytest docs/architecture/capability-map/test_render.py -q
node --test docs/architecture/capability-map/test_map.cjs
```

The standard-library renderer checks IDs, domains/subsystems, statuses,
source/test paths and flow endpoints. It generates the readable inventory and
self-contained HTML and static SVG from the same data. `--check` rejects stale
views without writing. Neither view requests network or live data. Node's built-in
tests execute the embedded script against a simulated DOM to check flow controls,
all selections and named connections at desktop/mobile widths; these are not a
substitute for browser pixel-layout or assistive-technology qualification.

The connected map embeds the journey's existing MIT-attributed routing code:
horizontal bypasses prefer one lower side, while direct links and authored return
loops stay distinct. The static overview retains its authored outer lanes.

Open `ade-capability-map.html` locally. At desktop sizes ownership groups and flow
arrows remain visible; at narrow sizes groups stack and named connections preserve
the same relationships. The inspector is documentation about components, not a new
product inspection endpoint. Keep this workflow here rather than in shared scripts.

When ownership, contracts or evidence materially change, update the owning record,
then the inventory and regenerate the views. Routine edits need no file-by-file
reclassification. Never promote status because a diagram/mechanical check passes.

## First Bounded Follow-Up

Trace an existing recorded turn through candidate availability, selection, actual
evidence, response and committed outcome. Then choose one demonstrated module gap.
Map reusable public benchmark tasks before expanding custom cases. Test Character
with fixed sufficient evidence and keep a small end-to-end check. No run is started
or authorized by this document.
