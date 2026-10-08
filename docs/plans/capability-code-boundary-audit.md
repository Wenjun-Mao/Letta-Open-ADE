# ADE Capability-To-Code Boundary Audit

Status: Audit completed, 2026-10-08; report awaiting user review. The user invoked
Relay direct and requested implementation of this audit plan. Any subsequent code
reorganization still requires separate approval; no product behavior changes are
proposed here. See the [audit report](../architecture/capability-map/code-boundary-audit.md).

Planning baseline: primary `main` checkout at
`2bfb390a329f2510a141690407829f4c340c2279`, clean before this document.
The executor must record its own baseline and relevant uncommitted changes.

## Problem And Outcome

The capability hierarchy makes ADE easier to discuss, but it does not yet show
how well the existing code supports those responsibilities. We need to determine
whether the difficulty is locating code, unclear interfaces, mixed responsibilities,
or necessary coordination before deciding to move or split anything.

Produce a source-backed **current-state code map and prioritized findings** for
the message journey. Answer: which boundaries already work, which need clearer
documentation, and which would benefit from a narrowly justified refactor?
Keeping the current structure is a valid result.

This is not a benchmark project, semantic behavior evaluation, or a requirement
to arrange every directory as `L1/L2/L3`.

## Authority And Guardrails

- [ADR 0061](../adr/0061-capability-responsibility-map.md): L1/L2/L3 describes
  ownership containment, not execution order, services, folders, or model calls.
- [Product contract](../product-contract.md), PC-02/03/04/10/11: preserve subject
  and character scope, immutable bindings, archive eligibility, and the distinction
  between authored biography and relationship-specific history.
- PC-05/07: distinguish semantic review from structural validation and atomic
  persistence; recording dialogue does not automatically accept a fact.
- PC-08/09: preserve one ADE product API/runtime, PostgreSQL authority, Model Router
  separation, explicit retry ownership, timeouts, and finite tool loops. Do not
  propose services, stores, reviewers, or frameworks just to fill diagram boxes.
- PC-01/06: do not introduce phrase-triggered memory behavior or revive removed
  conversational privacy/no-save policy features.
- PC-12: CHAR-03/04 share generation. Grounding, conversational judgment, and
  character fidelity are assessment lenses, not new internal phases.
- [Development conventions](../development-conventions.md): preserve feature,
  platform, integration, content, and workflow ownership. A feature may not depend
  on another feature's internals.

No agreement is reopened. [ADR 0060](../adr/0060-joint-history-packet-admission.md)
remains proposed. Record a new durable architectural decision only if a later,
approved change actually requires one.

## Scope

Start from the [canonical inventory](../architecture/capability-map/inventory.json)
and [message journey sources](../architecture/capability-map/message-journey/README.md).
Resolve their code/test references rather than treating the chart as runtime proof.

| Area | Audit depth |
| --- | --- |
| Character: Persona Definition and Conversation Behavior | Map CHAR-01 through CHAR-05, including authoring, immutable binding, and the shared generation/tool loop. |
| Memory: Recall & Context, Retention & Updates, Organization & Maintenance | Map MEM-01 through MEM-10; distinguish existing compaction from deferred additional views. |
| Interface | Trace Agent Studio input, run monitoring, reply/state refresh, and directly relevant configuration/inspection interfaces. |
| Supporting responsibilities | Trace runtime coordination, state repositories, model access, schemas/wiring, and observations needed by this journey. Retain supporting identities; do not invent L1 depth. |
| Conditional and experimental paths | Map compaction, discretionary memory search, natural review, bounded history trials, and failure/retry/cancellation where implemented. Record policy/activation conditions. |
| Deferred or proposed work | Account for External Tools and proposed memory work as status-only entries, not executed flows or missing implementation defects. |

Primary source homes are listed in the [codebase map](../codebase-map.md):
`services/ade-api/src/ade_api/features/agent_runtime/` and its tests;
`apps/ade-web/src/features/agent-studio/`; relevant Prompt Center/content sources;
and the directly used platform and Model Router integration contracts.
Inspect other packages and workflows only far enough to establish a direct
dependency, public interface, or existing test/evidence reference.

Exclude unrelated Comment/Label Lab internals, a full Model Router implementation
audit, infrastructure/deployment qualification, historical experiment catalogs,
and generated/vendor trees. Exclude `.venv`, `.git`, dependencies, build outputs,
generated API clients, and ignored private evidence from structural scans.
Handwritten frontend code in scope is not excluded.

## Current Anchors, Not Findings

The planning inspection confirms these starting points; the audit must trace their
callers, conditions, collaborators, and tests before judging their boundaries:

- `RunService.accept_turn` in `run_service.py` captures the original user message
  and creates the run within a transaction. MEM-05 legitimately overlaps runtime
  acceptance; a separate box does not require a separate service or commit.
- `TurnExecution.execute` in `turn_execution.py` coordinates attempt work across
  responsibilities. Numerous imports alone do not establish poor cohesion.
- `RunFinalizer.commit_success` in `worker_finalization.py` commits memory changes
  and the assistant message inside the same transaction. Identify all bundled
  writes and fencing checks; do not recommend independent domain commits.
- The inventory records CHAR-03/04 as responsibilities within shared generation.
  An understanding-to-expression handoff must not be inferred from their names.
- Inventory and journey documents cite earlier source baselines. Revalidate
  implementation/status claims; diagram checks establish consistency, not behavior.

## Ordered Work

### 1. Establish The Audit Baseline

Record commit, working-tree state, source authorities, and exact scope in the audit
report. Read current instructions/contracts and follow inventory source references.
Separate current code, older recorded evidence, product intent, and proposals.
If relevant files change during inspection, refresh affected conclusions or mark
them unresolved; do not mix revisions silently.

Acceptance: the report states what was inspected, what was excluded, and what
revision supports its observations. No deployed-state claim is made.

### 2. Map Responsibilities To Code And Tests

Build a two-way mapping: capability to implementation, and inspected production
files/symbols to responsibilities. Use stable inventory IDs and L1/L2/L3 names.
For each row record source path and symbol/line anchor, primary responsibility,
contributing responsibilities, input/output, applicable policy/status, and tests.
Supporting machinery, persisted records, transient artifacts, and content retain
their actual identities rather than being forced into capability modules.

Allow many-to-many mappings and explain them. Account for every in-scope piece
and inspected production file; an unmapped responsibility is an explicit question,
not a reason to invent a module. Tests are linked evidence: distinguish present,
inspected, executed, skipped, and unavailable checks.

Acceptance: a maintainer can start from either a chart box or a source file and
locate the relevant owner, collaborators, and existing checks.

### 3. Trace Dependencies And The Actual Message Journey

Document three distinct views: ownership containment, code dependencies, and runtime
control/data movement. Use compact tables and a diagram only where it aids reading;
do not build another interactive renderer.

Trace acceptance, worker claim, bound state/context, generation, review, prepared
representations, finalization, and UI readback. Annotate the relevant branches and
their conditions rather than drawing them as mandatory sequential phases.
At each boundary identify the producer, consumer, payload/contract, and owners of
reads, writes, transactions, retries, deadlines, cancellation, and source/version
validation. Show where a candidate becomes persisted and where it is displayed.

Trace typed and natural reviewer inputs separately. Include implemented history
and compaction conditions without promoting them to production defaults.
Separate public activity metadata from private evaluation captures.
Verify suspected cycles and cross-feature imports against actual wiring/calls;
static imports alone do not establish runtime dependencies. Mark unresolved dynamic
dispatch explicitly.

Acceptance: actual information movement is inspectable independently of L1/L2/L3,
including both acceptance and success transaction bundles and their guards.

### 4. Assess Boundaries And Prioritize Findings

For each potential issue, record the observed structure, source evidence, affected
contract, concrete maintenance/testing risk, and alternative explanation. Evaluate
cohesion, change locality, dependency direction, interface clarity, duplicated
authority, and test isolation. File size is a review signal, not proof of a bad
boundary; flag files over 500 lines and inspect their responsibilities.

Use these recommendation categories:

| Category | Meaning |
| --- | --- |
| Keep | Cohesive owner or deliberate collaboration; explain why separation would add cost or risk. |
| Clarify | Improve names, documentation, or interface descriptions without moving behavior. |
| Regroup | Improve navigation/locality for already cohesive pieces; list import/public-surface risks. |
| Split | Separate genuinely mixed responsibilities; state the proposed seam and preserved invariants. |

Rank recommendations by demonstrated consequence and expected benefit, with effort
and confidence labeled where estimates are possible. Include evidence against
unnecessary changes. Do not present an unverified hypothesis as a diagnosed defect.

Acceptance: every recommendation has inspectable evidence and a benefit beyond
matching the chart. No folder tree or runtime change is adopted by the report.

### 5. Review Before Selecting A Refactor

Review the result in this order: L1/L2 ownership, actual message flow and protected
boundaries, then L3/source mappings and prioritized recommendations. Keep the first
readout small enough to discuss one chunk at a time.

Conclude with no-change, clarification-only, or a few bounded refactor candidates.
For each candidate identify affected files/imports, preserved public surfaces and
transaction contracts, existing regression checks, and verification gaps.
Implementation needs a separately approved scope and proportional verification;
this audit does not preapprove code changes or live runs.

## Deliverable And Verification

Maintain one audit report at
`docs/architecture/capability-map/code-boundary-audit.md`, containing the baseline,
responsibility/code/test mapping, dependency/flow views, findings, and review summary.
The canonical inventory remains `inventory.json`; this report adds code-boundary
analysis, not another competing capability registry. Record discovered inventory
or chart drift as proposed corrections rather than silently rewriting authority.

Validate source anchors, linked paths, ID/status coverage, and internal consistency.
Check `git diff --check` and confirm report-only changes. Runtime tests need not run
for a source-reading audit. If a focused offline check would resolve an uncertainty,
inspect it first and use only temporary fixtures and local scratch outputs: no
running services, live database, credentials, or provider access. Report exact
commands/results and what they cannot establish. Do not run broad suites blindly.
Existing chart tests and offline mechanics are not semantic or release qualification.

## Permissions And Review Gates

| Action | Authority |
| --- | --- |
| Save/review this plan; scoped verified documentation commit and normal push | Granted for this planning iteration under current repository conventions. |
| Execute the source-reading audit and create its report | Granted by the user's 2026-10-08 request. Perform covered work on retained `main`; read-only native sidecar inspection follows the explicitly invoked Relay direct skill, with one report writer. |
| Change production files, imports, prompts, schemas, policies, APIs, or persistence semantics | Not authorized; requires review and approval of a specific follow-up scope. |
| New tasks/worktrees, dependency installation, live tests, migrations, service restarts, deployment, or external-account use | Not authorized by this plan. |

Preserve unrelated changes and private evidence. If the audit requires excluded
work or a contract change, explain the dependency and request a scope decision.
No operational rollback is needed for documentation-only work; any later refactor
must define its own verification and rollback before execution. Do not use an old
refactor plan as permission to resume historical work.

## Execution Record

Executed on retained primary `main` at
`0ec2088ece4bc3b7f539bd56e457a5b69ea02245`, clean at entry. One writer integrated
two read-only native inspections into the linked report: ownership, actual flow,
94-file runtime reverse register, import/reference checks, and selective findings.
All 166 inventory code/test references resolved. Seven focused fixture-only test
files yielded 65 passes; database/browser/live qualification was not run.
Only this plan, the report and its README link changed. Production code, canonical
inventory/charts, product contracts and deployment state remain unchanged.
No refactor candidate is adopted; review proceeds L1/L2, protected flow, then findings.
