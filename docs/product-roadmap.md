# ADE Product Roadmap

This is the current, outcome-oriented direction for Letta Open ADE. It is
deliberately separate from the [historical maintenance record](maintenance-roadmap.md),
which preserves completed cleanup context but does not define current product work.

## Baseline: v0.3.0

`v0.3.0` is the comprehension-first baseline. The repository now has clear
service, feature, content, workflow, and infrastructure ownership. The next
milestone should prove that this structure helps an operator improve real agent
behavior, not add another round of structural work.

The representative live results captured before this milestone are recorded in
the [v0.3.0 live behavior baseline](baselines/v0.3.0-live-baseline.md).

## Current Milestone: Agent Behavior Evaluation Loop

Build one coherent loop across Agent Studio, Test Center, and Prompt Center:

1. Configure an agent with a model, prompt, persona, and embedding.
2. Replay a conversation fixture from the product UI.
3. Inspect each turn's reply, tool activity, persistent-memory layers, and
   before/after memory changes.
4. Score the run for self-disclosure and expected fact capture.
5. Compare runs across model, prompt, and persona choices.
6. Open the relevant prompt or persona in Prompt Center to refine it, then run
   the same fixture again.

The user outcome is simple: an operator can tell whether an agent behaved as
intended, understand why it passed or failed, and make the next prompt or
persona decision without reconstructing the run from raw files or logs.

### Acceptance Criteria

The milestone is complete when a maintainer can use ADE Web to:

- Choose a model, prompt, persona, embedding, fixture, timeout, and retry
  setting for an evaluation run.
- Start the run from Test Center and see a stable run record linked to its
  artifacts.
- Review every replayed turn with the assistant response, visible tool signals,
  memory state before and after the turn, and a readable memory diff when state
  changed.
- See deterministic checks for forbidden self-disclosure, memory mutation, and
  expected user facts, including a clear pass/fail result and failure reasons.
- Compare completed runs using their explicit model, prompt, persona, fixture,
  and scoring metadata.
- Navigate from a run's selected prompt or persona to its editable Prompt
  Center record, then rerun the same configuration after a change.
- Confirm that temporary evaluation agents are safely archived and purged, with
  cleanup failures visible in the run result.

Deterministic checks own the official pass/fail outcome. An optional LLM judge
may add diagnostic commentary or an advisory score, but it must never override
or make the official result non-deterministic.

## Non-Goals

This milestone does not include:

- Broad repository or service restructuring.
- Adding providers merely to increase the catalog.
- A generic evaluation framework beyond the concrete Agent Studio workflow.
- A visual redesign or broad UI overhaul.
- Replacing existing API contracts before the evaluation workflow requires a
  narrowly defined addition.

## Likely Next Milestones

These are candidates for discussion after the current milestone, not committed
delivery promises:

- Curated evaluation suites for Comment Lab and Label Lab, using their own
  task-specific success criteria.
- Repeatable baseline reports for the supported local and cloud models.
- Review and promotion workflow for validated prompts, personas, schemas, and
  tools.
- Focused operational visibility for model availability, latency, and failed
  evaluations.

## Working Rule

Prefer one end-to-end improvement to this loop over a cross-cutting abstraction.
For every change, keep the UI, API contract, deterministic checks, workflow
artifacts, and documentation owned by the relevant feature. Record durable
contract or behavior decisions as ADRs when they are made.
