# Hindsight Integration Assessment Kit

Status, 2026-10-13: implemented **offline assessment kit**, the first authorized
implementation deliverable. Twelve frozen Mandarin cases cover Q01-Q05; fifteen
authored examples propose reference judgments. These are not observed model
outputs or human-calibrated consensus. No live adapter, runtime change, provider
call, installation, OCI activation or quality baseline is included.

Authority: [PC-02/03/11/12/14](../../../docs/product-contract.md), the
[review method](../../../docs/architecture/capability-map/character-assessment.md#repeatable-review-method),
[starter meanings](../../../docs/architecture/capability-map/character-assessment-cases.md)
and [ADR 0069](../../../docs/adr/0069-offline-character-assessment-kit.md).
This workflow owns evidence artifacts, not product APIs or semantic policy.

## Integration Work In Progress

2026-10-18: the user approved M0-M6 and A1-A6 in the implementation plan.
The concrete Hindsight HTTP client and immutable per-message source contract
have offline coverage; the normal product runtime and live collector are still
being implemented. [ADR 0070](../../../docs/adr/0070-hindsight-message-delivery.md)
records the source/replay decision and its pending native feasibility gate.

The pre-change current-source baseline reports 1,568 passed, 81 skipped, 54 failed
and 61 errors. The failure/error totals match the October 13 checkpoint; the
new CI guardrail adds one pass. The ignored baseline log is under
`outputs/implementation-20261018/`.
Generated upstream/source-copy tests are excluded from normal discovery by the
repository's pytest configuration. Existing historical replay failures remain
visible; their evidence has not been rebound or weakened.

## Run The Offline Rehearsal

From the repository root, choose a new output directory each time:

```sh
uv run --locked python -m workflows.evals.hindsight_integration validate-cases
uv run --locked pytest workflows/evals/hindsight_integration -q
uv run --locked python -m workflows.evals.hindsight_integration dry-run \
  --out workflows/evals/hindsight_integration/outputs/rehearsal-01
```

Read `outputs/rehearsal-01/report/report.md` and its sealed JSON companion.
The rehearsal plans 12 cases twice, then deliberately leaves 18 attempts unrun,
one interrupted, one captured/unreviewed, and four reviewed. One reviewed capture
has an execution failure and cannot be semantically assessed. The other three
use authored examples, including a repeated case with differing judgments.
This tests accounting, not model reliability. The workflow uses no network
client, credentials or running service. Outputs are ignored by Git.

## Frozen Cases

| Promise | Exact cases | Setup and distinction |
| --- | --- | --- |
| Q01: useful continuity | `q01-relevant`, `q01-unrelated` | User-only seeds; relevant preference helps a choice, unrelated preference need not be recited. |
| Q02: factual meaning | `q02-correction`, `q02-change`, `q02-one-order` | User-only seeds distinguish a misspeak, genuine change and temporary choice. |
| Q03: relationship continuity | `q03-shared-joke`, `q03-other-character`, `q03-other-subject` | Controlled attributed dialogue distinguishes a shared joke from physical participation and prevents transfer to another relationship. |
| Q04: invention and recollection | `q04-known-detail`, `q04-missing-detail`, `q04-creation` | Controlled committed story with known/missing details; separate open-ended, no-history creation probe. |
| Q05: contextual response | `q05-listen` | User-only seed and explicit request to listen rather than advise. |

The fixture persona snapshots the existing Xiaotang seed, with content hash;
it does not edit the product persona. `fixtures/catalog.json` fixes suite revision
and files; `lock.json` binds their exact bytes. Each case has evaluator-only
success meanings, failure modes, acceptable alternatives, unknowns and limits.
`actor-input` exports only scope, history and current utterance, never the rubric
or calibration replies. Neither keyword matching nor a mandatory gold reply
grades meaning. The mechanical quote check only verifies review attribution.

Changing a fixture requires a reviewed new case/suite revision and new lock,
before observing that revision's answers. `freeze-cases --out /new/lock.json`
generates a candidate lock without replacing the old one. Review the diff and
promote the new lock with the fixture change. Old runs embed their frozen cases;
do not alter or silently rebind their evidence. These exposed starter cases are
not held-out coverage. Add unseen variants under a reviewed suite revision.

## Capture And Review Procedure

The CLI can receive local artifacts now. `live_capture` means an explicitly
labeled import, **not** live execution or authorization. Stage 1 must implement
and verify the actual product adapter before any live baseline. Its collector
must use public product/observation boundaries, not native fact APIs or a second
reviewer. Export schemas with `schema runtime`, `schema observation`, or
`schema review`; there is intentionally no live-run command.

1. Freeze cases, repeats and runtime bindings before execution. Bind product
   revision, exact persona/system prompt and versions, Character route/served
   identity/settings, Memory configuration and embedding identity. Use a clean,
   committed evaluator for a live baseline; its HEAD and file hash are recorded.
2. Start each declared attempt **before** setup or external actions. It gets one
   create-only slot. A rerun is another predeclared repeat or a new run, not an
   overwritten failed reply. Plan repeats rather than selecting the best answer.
3. Allocate fresh disposable source/target relationships per attempt. Map the
   fixture's logical scopes to real identities, preserving which fields match
   or differ. Capture empty-state readbacks before setup. No relationship may
   be reused by another attempt, including another branch of the same scenario.
4. For user-dialogue cases, send exact seed user messages through the product
   and capture **all** resulting accepted users and committed assistant replies,
   not just the scripted user lines. For controlled histories, preserve the exact
   authored turns and explicitly mark their diagnostic provenance. Never present
   supplied history as evidence the product generated/established it.
5. Preserve original message IDs, speakers, scopes, conversation IDs and times.
   Await and observe retention/consolidation for history-dependent probes;
   capture delivery receipts, memory readback and raw recall separately. Start
   a fresh probe conversation; old source dialogue must not be local history.
6. Preserve the complete provider-facing request body for **every** generation
   request, served identity and timestamp, plus final reply/commit ID. Capture
   memories actually delivered, not an ideal reconstructed prompt. Exclude auth
   headers, credentials and private model reasoning at collection; do not redact
   conversational input to hide a failed observation. Explain absent evidence.
7. Import the observation even when execution failed. Structurally representable
   failures are saved with issue codes; `capture` exits 1 for mechanical issues.
   Malformed or forbidden-field inputs exit 2, leaving the started slot incomplete.
   A failure must include its stage/reason; never replace it with a synthetic pass.
8. Generate a blank review, inspect the frozen rubric/persona and actual source,
   memory, input and reply. A human fills all three lenses with a result, exact
   quote and contextual reason. Missing replies use empty quotes and
   `cannot_assess`. Mechanically invalid captures cannot receive positive semantic
   qualification. AI advice is not submitted as an authoritative human judgment.
9. Generate the report in a new directory. It includes every planned slot,
   failure, limitation, reviewer/revision and per-lens denominator. To correct a
   judgment, generate the next template and supply a change reason; its predecessor
   hash is required and both judgments remain visible. Regenerate the report.

The following commands are local artifact operations; `runtime.json` and
`observation.json` must come from the future verified collector, not guesses:

```sh
uv run --locked python -m workflows.evals.hindsight_integration prepare \
  --out /private/assessment/run-01 --run-id run-01 --mode live_capture \
  --runtime /private/assessment/runtime.json --repeats 2
uv run --locked python -m workflows.evals.hindsight_integration start \
  --run /private/assessment/run-01 --case q01-relevant --repeat 1
uv run --locked python -m workflows.evals.hindsight_integration actor-input \
  --run /private/assessment/run-01 --case q01-relevant \
  --out /private/assessment/actor.json
uv run --locked python -m workflows.evals.hindsight_integration capture \
  --attempt /private/assessment/run-01/attempts/q01-relevant-r001 \
  --input /private/assessment/observation.json
uv run --locked python -m workflows.evals.hindsight_integration review-template \
  --attempt /private/assessment/run-01/attempts/q01-relevant-r001 \
  --out /private/assessment/review-draft.json
uv run --locked python -m workflows.evals.hindsight_integration review \
  --attempt /private/assessment/run-01/attempts/q01-relevant-r001 \
  --input /private/assessment/review-completed.json
uv run --locked python -m workflows.evals.hindsight_integration report \
  --run /private/assessment/run-01 --out /private/assessment/report-01
```

## Interpretation And Limits

`meets`, `partly_meets`, `fails` and `cannot_assess` remain separate for grounding,
conversational judgment and character fidelity. There is no average or release
threshold. Family counts use reviewed, mechanically eligible attempts; missing,
invalid and unreviewed attempts are also reported against the planned total.
Semantic ambiguity can still produce `cannot_assess` with valid capture. Distinct
case counts and repeat labels are shown separately; neither establishes statistical
independence or generalization. Structural checks do not judge semantic sufficiency.

Human review of the fifteen authored examples is still needed to calibrate the
proposed judgments. Preserve disagreements rather than treating these labels as
empirical truth. Controlled-history successes do not qualify product ingestion;
Q04 creation alone does not qualify subsequent continuity. To extend it, capture
the actual committed story, annotate its established/unknown details, then freeze
a linked follow-up case before asking its questions. Do not substitute a fixed
gold anecdote or infer an unmentioned detail. That dependent follow-up runner is
not part of this minimal kit; the known/missing-detail probes remain controlled.

Seals and create-only writes detect accidental drift, stale joins and overwrites;
they are not signatures, authentication or proof of actual provider execution.
The collector must verify declarations/readbacks and input completeness. The
current mechanical request checks target text chat-completions bodies; a different
wire shape needs an explicit reviewed evidence-contract change, not silent coercion.
Private evidence stays outside source control. Field rejection is defense in depth,
not a comprehensive secret scanner; operator review remains required before sharing.

The live adapter, human calibration, unseen variants, baseline, and broader
isolation/lifecycle/fault/recovery checks remain in the
[integration plan](../../../docs/plans/hindsight-integration.md). No runtime,
deployment or release status follows from this offline rehearsal.

## Verification Checkpoint

2026-10-13: the 54 kit tests and 27 adjacent evaluation-contract/chat-eval tests
pass; repository Ruff lint, changed-file formatting and the 24-slot rehearsal
pass. No provider or product-runtime experiment was run.

The broader Python suite is **not green**. Excluding generated `*/outputs/*`
test copies, it reports 1,567 passed, 81 skipped, 54 failed and 61 errors.
Excluding this kit as well gives the identical failure/error list and 1,513
passes. Historical correction-dependency checks reject an already-changed
`executor.py` fingerprint; one existing Compose-name check fails in the broad
run but passes in its isolated 17-test module. These remain separate verification
follow-ups, not repaired or waived by this kit. Historical fingerprints and
private evidence were not rebound to make the suite pass.
