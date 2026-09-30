# ADR 0054: Bounded Native Story Probe

Status: Accepted, 2026-09-30, for the explicitly approved PC-11 diagnostic only.

## Problem

The completed offline harness accepts only in-process test transports. Live
approval does not turn its scripted outputs into evidence, authorize retained
trial access, or justify weakening that boundary. A native run also needs a
clean source binding, immutable receipts and pauses for actual human annotations.

The pinned `dgx-spark` Docker alias does not resolve directly on this Mac, while
the configured `DGX_SPARK_HOST` address serves the expected Qwen catalog. Changing
the baseline URL or fingerprint would test a different configuration.

## Decision

Add a separate workflow-local native entrypoint using public ADE HTTP contracts
and the existing service/worker entrypoints. Leave offline `prepare` and
`OfflineADE` network-free. No runtime memory, prompt, ranking or reviewer changes.

- Freeze a clean commit, source/configuration hashes, existing ten prompts,
  model bindings and request envelope before dispatch. Recheck before every turn.
- Create one owned, loopback-only PostgreSQL container and isolated persona DB.
  Run authenticated loopback ADE/Router processes. Never use the retained trial.
- Preserve the configured endpoint identity. The isolated router process alone
  resolves `dgx-spark` to the explicitly configured IPv4 address, equivalent to
  the existing Docker extra-host mapping. No global resolver or URL changes.
- Validate actual catalog and immutable definitions against the parsed baseline.
  Settings/catalog receipts are not claims of native semantic quality.
- Write dispatch intent before each one-attempt submission. An uncertain outcome
  stops execution; it is not retried. Only terminal-readback polling repeats.
- Keep original capture bytes, independent HTTP readback, full private state
  observations, source ledger and validation outcomes. Missing or invalid evidence
  stops further dispatch; successful HTTP or reviewer output is insufficient.
- Pause after committed turns 1 and 3. Only an identified human's exact-quote
  annotation can open the next frontier. Agents may propose annotations for
  review but cannot label their own judgments as human evaluation.
- Stop owned processes/database at every pause or exit; retain the stopped owned
  database for the remaining sequence. Explicit cleanup verifies ownership and
  removes only this container and its anonymous volumes.

## Alternatives And Consequences

Relaxing the offline harness would hide native/scripted provenance. Reusing the
retained trial would mix state and violate experiment ownership. Changing the
embedding URL to work around DNS would break the exact baseline. Unattended
agent annotations would violate the already-frozen human chronology contract.

The native runner is intentionally a single diagnostic, not a generic campaign
framework or production deployment. Its stopped database must remain until the
sequence is complete or explicitly abandoned. After any uncertain submission,
inspect retained receipts rather than restarting or rerolling that turn.

## Guardrails

Portable tests cover one-attempt transport, uncertain submission, immutable
receipts, clean-source rejection, source drift, annotation chronology, mutable
readback versus immutable identity, version-2 HTTP creation, definition drift,
evidence-failure stops, container ownership and process-local alias scope.
Existing scripted PostgreSQL checks remain the runtime mechanics guardrail.
Native PC-11 feasibility requires actual retained outcomes and human review.

## Annotation-Ownership Amendment (2026-09-30)

After native turn 1, the user explicitly agreed to agent-reviewed annotations
and autonomous continuation, reserving escalation for genuine ambiguity. This
supersedes the human-only evaluator requirement for this sequence, not chronology,
the semantic rubric, or any model/runtime baseline. Agent work must be labeled
`reviewer_kind: agent`; it is not independent human validation.

Preserve the original preparation, approval and turn-1 bytes. A separate immutable
amendment receipt binds the old preparation hash, original outcome hash, explicit
approval and new clean runner commit. Continuation permits only the four named
annotation-runner source files to differ. The governed runtime fingerprint,
prompts, persona, fixture, model configuration, dispatch rules and evidence
validators must remain identical. Subsequent source drift still fails closed.
No turn is rerun. Agent annotations still freeze before turns 2 and 4; the
operator can resume immediately after making the assessment without asking the
user to perform routine semantic classification.
