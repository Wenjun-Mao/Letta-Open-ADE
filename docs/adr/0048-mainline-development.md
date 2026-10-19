# ADR 0048: Mainline Development

Status: Accepted, 2026-09-30, by explicit user direction.

## Problem

Character-continuity development had accumulated outside `main`, making the
primary checkout and GitHub baseline lag the work under discussion. Preparing
an independent consultation exposed that publication/integration gap.

## Decision

Integrate the retained character-continuity branch into `main` and continue
development in the primary checkout on `main`. A separate consultation branch
is not required. Pin consultation evidence to immutable commits, independently
of the branch used for discovery.

Create or resume a separate development branch/worktree only when the user
requests it. Preserve existing trial checkouts, private evidence and operational
mounts until their dependencies are explicitly retired. Their retention is not
permission to continue a parallel development line.

The user's subsequent 2026-09-30 direction pre-approves local commits and makes
them the default after every completed, proportionally verified iteration.
Do not repeatedly ask permission to record a local checkpoint. Scope each commit
to the iteration, preserve unrelated work, and report material verification gaps.
That initial direction replaced approval-per-commit, not the then-separate push
or deployment boundary. The publication amendment below supersedes only that
push boundary; earlier findings retain their historical authorization statements.

### Publication Amendment (2026-09-30)

The user subsequently directed: "Take commit and push as default and pre-approved."
After each completed, proportionally verified iteration, commit the scoped work
and normally push to the configured upstream without another permission request.
This prevents local-only evidence from blocking GitHub-only consultation and
keeps the shared development baseline current. Retaining push-by-push approval
was rejected by the user's explicit workflow choice.

Inspect the outgoing scope and preserve unrelated work. Do not publish secrets,
private captures or account-bound data as an incidental part of a source push.
Check remote state and verify publication; report failures or divergence rather
than force-pushing or silently rewriting history. For consultation, independently
verify the exact anchor and required files at the reviewer's access level.
This is source-publication authority, not deployment, release qualification,
live provider experimentation, external-account operation or reviewer dispatch.

### Manual-Only CI Amendment (2026-10-18)

The user explicitly requires GitHub Actions CI only on request and directed
removal of automatic workflow triggers. Keep `workflow_dispatch` only; normal
pushes and pull requests must not trigger CI. Do not dispatch or rerun a workflow
without a new explicit user request. Retaining automatic CI or repeatedly
withholding ordinary source publication was rejected in favor of manual CI.

Local verification and scoped commits/pushes remain the default. This changes
when hosted verification runs, not the requirement to verify source changes or
report gaps. A repository guardrail checks every workflow's manual-only trigger
block. Future workflows must follow the same rule; restoring automatic triggers
requires a changed user decision. Existing workflow jobs remain available for
explicit manual execution. No CI run is authorized by this amendment itself.

## Alternatives And Guardrails

Keeping a separate review branch would publish evidence without integration,
but the user chose a single development baseline instead. `main` is not thereby
a promise of release qualification. Existing experimental labels, source-bound
evidence requirements, tests and explicit deployment decisions remain in force.
Do not rebuild services, alter running trial bindings, publish private captures,
or delete old worktrees as an implicit part of source integration.
