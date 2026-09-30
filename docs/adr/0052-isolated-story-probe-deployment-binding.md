# ADR 0052: Isolated Story Probe Deployment Binding

Status: Accepted for offline preparation, 2026-09-30. No live authorization.

## Problem

The PC-11 workflow's scripted catalog replaced Qwen's computed deployment digest
with the history-trial pin. This concealed an actual configuration difference.
ADR 0027 separated the stable fact-vector-space ID from full deployment identity:
`c549d7dc...` is both the historical deployment digest and the retained opaque
space ID, but the current full deployment digest is `0f16a45a...`. Equal model
names, dimensions or vector-space IDs do not make the configurations identical.

## Decision

Keep the unchanged trial baseline and strict full-deployment checks. Track a
workflow-local isolated manifest using the complete historical Qwen fingerprint
payload from commit `264c57e` and the DeepSeek payload from `90b72b4`, both at
`config/model-router/deployment-manifest.json`. The shared manifest parser must
compute the pinned `c549d7dc...` and `870ff4fb...` digests from these full payloads.
Reset qualification summaries to zero observed rounds and candidate lifecycle;
no historical qualification is claimed for the new experiment.

Track only the two selected source routes alongside the manifest. Fixed endpoint
URLs, adapters, source-file hashes and manifest hash are part of preparation;
omit endpoint environment overrides in this isolated configuration. Credential
environment variable names remain references, never credentials in evidence.
An eventual supplied router catalog must match this expected configuration
exactly, including endpoints and complete deployment metadata. Static expected
metadata is explicitly not a fresh discovery, health, or model-quality receipt.

The same parsed manifest drives the offline fake, eliminating digest rewriting.
Production configuration, retained trial services, immutable definitions, frozen
experiment evidence and runtime fingerprint guards remain untouched. A future
isolated stack must explicitly select these files before separately approved
discovery/provider work; preparation never starts or redeploys a stack.

## Alternatives And Guardrails

Do not compare only vector-space identity, allow either full fingerprint, change
the trial pin to the newer candidate, or reuse private retained configuration as
a portable fixture. Those choices alter the baseline or hide the mismatch rather
than resolve it. A newer deployment can be a separately approved experiment.

Tests recompute both digests, reject changed payloads/digests/endpoints/adapters,
missing or ambiguous routes and file drift, and reject substituting the current
manifest even when its digest is overwritten. Real ADE scripted sequences must
create definitions and execute with this exact configuration. Live environment
attestation and PC-11 semantic quality remain separate approval/evidence gates.
