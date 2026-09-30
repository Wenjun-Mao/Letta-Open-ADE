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

## Alternatives And Guardrails

Keeping a separate review branch would publish evidence without integration,
but the user chose a single development baseline instead. `main` is not thereby
a promise of release qualification. Existing experimental labels, source-bound
evidence requirements, tests and explicit deployment decisions remain in force.
Do not rebuild services, alter running trial bindings, publish private captures,
or delete old worktrees as an implicit part of source integration.
