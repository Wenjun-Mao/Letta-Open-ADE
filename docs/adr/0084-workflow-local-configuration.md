# ADR 0084: Workflow-Local Configuration

Status: Accepted, 2026-10-19.

## Root Cause

The full offline sweep's probe Compose failures reached the project-name check.
An ordered two-test reproducer confirmed that chat-eval `load_config` installed
the private root `.env` into `os.environ`; Compose then inherited that unrelated
project name despite its explicit dummy env file. Comment-eval had the same
loader side effect. Removing only the Compose variable in tests would hide the
shared-process configuration error and still leak other defaults/credentials.

## Decision

These loaders read dotenv values into local data, with explicit process values
(including empty values) taking precedence. Config objects carry resolved ADE
and Router credentials directly to their clients; execution must not re-read a
later ambient credential. Hide secrets from config representations and redact
them in exported summaries. No global environment install, caller-specific
Compose workaround or change to live provider/default identities is needed.

Separate comment-eval configuration from its oversized execution module and
use the package-qualified CLI entrypoint. Preserve the documented `run.py`
command. The existing workflow-locality rule remains authoritative, not a new
shared configuration framework or a change to Memory/Character semantics.

## Guardrails

Test local defaults, explicit/empty environment precedence, unchanged caller
environment, bound client authentication and export redaction. Retain the failed
interaction receipt and rerun both workflow tests together with dummy Compose
validation. No inference, historical evidence rebind or CI dispatch is involved.
