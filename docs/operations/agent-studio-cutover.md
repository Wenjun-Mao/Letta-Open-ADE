# Agent Studio Native Cutover Runbook

This runbook closes Milestones 4 and 5 under
[ADR 0016](../adr/0016-ade-native-agent-studio-cutover.md). It activates one
fresh-start ADE-native Agent Studio authority only after qualification, paired
product evidence, deterministic conformance, and rollback rehearsal all bind to
the expected clean source and deployment identities.

## Evidence Model

The release ledger composes three deliberately different kinds of evidence:

- Three canonical native qualification rounds prove native-only guarantees such
  as subject isolation, correction and forgetting, deep retrieval, compaction,
  false-memory prevention, tool behavior, and normalized trace preservation.
- Three Test Center paired rounds compare the common Letta-v2 and native-v3
  product outcome: the same seven-turn fixture, prompt, persona, DGX model,
  timeout, zero-retry policy, replies, durable user facts, and cleanup. The native
  side creates, archives, and restores through `/api/v3/agent-studio/sessions`.
- The deterministic conformance receipt proves exact retry ownership,
  cancellation, idempotency, and event contracts that cannot be inferred from a
  successful conversational sample.

The rollback receipt separately proves that the prior v2 web revision still
builds and serves Agent Studio against the retained v2 API, and that withdrawing
then restoring the native lane leaves definitions, subjects, conversations,
messages, summaries, and typed memory lineage unchanged.

No one artifact substitutes for another. `release-evidence.json` is accepted
only when every capability points to its required signed artifact.

## Preconditions

- Work from one clean source commit. Do not collect release evidence from a dirty
  tree.
- Keep DGX chat and embedding routes reachable from `model-router` and keep the
  llama-server compatibility route reachable.
- Keep Letta, Redis, the v2 ADE API, PostgreSQL, and the native lane running.
- Use `rounds=3`, `timeout_seconds=180`, and `retry_count=0` exactly.
- Do not edit a policy-bound file after qualification. Restart from policy
  rebinding if code, prompt, persona, tool, schema, retrieval, workflow, or gate
  behavior changes.

## 1. Freeze And Bind The Candidate

Run the complete deterministic checks, regenerate committed API artifacts, then
bind the deployment manifest to the final policy inputs:

```text
make check
uv run python scripts/export_openapi.py --check
make agent-studio-policy-rebind
```

Commit the implementation and rebound candidate manifest together. The resulting
clean commit is the qualification source.

## 2. Qualify And Promote The Native Bundle

Start the explicit development lane and run the full canonical matrix:

```text
make agent-studio-qualification
```

The runner must emit a promotion proposal, three distinct passing primary round
digests, and a passing llama-compatibility artifact. Review and apply it while
still on the exact clean qualification commit:

```text
make agent-studio-promotion-apply \
  AGENT_STUDIO_QUALIFICATION_PROPOSAL=<promotion-proposal.json>
```

Commit only the promoted deployment manifest. Rebuild the development lane from
that clean promotion commit before collecting product evidence:

```text
make agent-studio-development-up
```

## 3. Collect Paired Product Evidence

In ADE Test Center, launch `Agent Runtime Parity` with the defaults shown below:

- prompt `chat_v20260516`
- persona `chat_linxiaotang`
- DGX Qwen conversation and reviewer routes
- DGX Qwen embedding route
- three rounds, 180 seconds, zero retries

Require `passed`, `inputs_comparable`, and `cleanup_complete` to all be true.
Inspect all three round summaries and normalized turn evidence in Test Center.
Record the artifact root, normally:

```text
data/runtime/test-runs/<test-center-run-id>/parity-<test-center-run-id>
```

## 4. Record Conformance And Rehearse Rollback

Both commands require the same clean promotion commit that produced the paired
artifacts. Receipts are written under ignored `tests/outputs/` state.

```text
make agent-studio-conformance
make agent-studio-rollback-rehearsal \
  AGENT_STUDIO_LEGACY_REVISION=<last-v2-release-commit>
```

The legacy revision must contain the v2 Agent Studio client. The rehearsal builds
that exact web source in an ephemeral image, smokes `/agent-studio` against the
retained v2 API, removes the image, stops the native API and worker, verifies v2
health, restores the native lane, and compares complete native state snapshots.

## 5. Approve The Single Release Ledger

Create the reviewed ledger only after all four evidence sources pass:

```text
make agent-studio-cutover-review \
  AGENT_STUDIO_QUALIFICATION_PROPOSAL=<promotion-proposal.json> \
  AGENT_STUDIO_PARITY_ROOT=<parity-artifact-root> \
  AGENT_STUDIO_REVIEWER=<reviewer-identity>
```

Review and commit `config/agent-studio/release-evidence.json`. After the evaluated
promotion commit, only that ledger, the deployment manifest, cutover status/ADR
documents, roadmap, and `docs/baselines/agent-studio-cutover/` evidence may change.
Any implementation change invalidates the gate.

## 6. Activate And Verify

```text
make agent-studio-release-gate
make agent-studio-release-up
make status
```

Verify Agent Studio through ADE Web: create or reuse a definition and subject,
start a conversation, send turns, inspect memory revisions and evidence, inspect
run events, reload the page, and archive/restore the conversation. Verify Test
Center still opens the paired summary and normalized turns. The removed
`/native-runtime-preview` route must return 404.

## Release-Level Rollback

Rollback is an operator release decision, never an in-request fallback. Stop the
native API and worker, redeploy the exact prior v2 Agent Studio web artifact against
the still-running v2 ADE API, and verify `/api/v2/health` plus the v2 Agent Studio
page. Do not reset PostgreSQL, import Letta state, dual-write, or delete native
state. Preserve the cutover ledger and failed-run evidence for diagnosis.

Restore native service only through the normal release gate after the incident is
resolved or a newly qualified candidate is approved. Phase 6 may remove the v2
rollback lane only under a separate decision after its observation window closes.
