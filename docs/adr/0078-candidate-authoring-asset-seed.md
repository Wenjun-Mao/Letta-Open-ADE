# ADR 0078: Candidate Authoring Asset Seed

Status: Accepted for the isolated Stage 1 workflow, 2026-10-19.

## Problem And Evidence

The first actual full-stack startup migrated the new ADE database but the non-root
API exited while creating `/app/content/personas/archive`. Registry initialization
also owns prompt/schema archive directories. Configuring only the persona SQLite
path did not cover those file-backed authoring assets. Image content belongs to
root and is not an appropriate mutable runtime volume.

The failure is candidate filesystem provisioning, not Memory or Character behavior.
No six-slot dialogue began. The activation was closed and retained, both stores
preserved, all owned containers stopped and six baseline identities/health checked
unchanged. Startup native/provider observations remain separate retained evidence.

## Decision

Provision a fresh private `runtime-data/content` copy from the exact staged source's
authored assets. Record each file's SHA-256 and an aggregate hash; exclude generated
Python bytecode and reject symlinks/empty sources. Copying is create-only and does
not alter the source or import incumbent content. API mounts the private content
copy at the existing `/app/content` contract read/write; worker mounts it read-only.
Persona SQLite and other runtime state remain in the same activation-owned private
runtime tree. This supports the existing file-backed authoring lifecycle without
changing global registry paths, requiring root or making image source writable.

Before every guarded product startup step, validate the initial authored assets
against their seed receipt. This frozen demonstration does not edit authored
content; a content-changing authoring workflow would require its own versioned
contract rather than bypass this check. Actual definitions/input hashes still
remain part of capture validation. New files do not silently change the frozen
persona, source manifest or Character acceptance status (PC-04/12/14).

The final Compose startup step waits for configured service startup/health rather
than reporting success merely because containers were created. Native HTTP/model
readiness remains an independent preflight, not implied by Docker running state.
Model-cache preparation explicitly uses root only in its finite one-CPU helper,
with only the new cache writable and any prior public-artifact cache read-only;
the actual pinned weight/metadata verification must pass before inference startup.

## Alternatives And Guardrails

Global chmod/chown, root API execution, writes into the staged source, mounting an
incumbent author's content and adding candidate-specific product-registry logic
were rejected. This configuration-only workflow preserves established APIs and
does not create a second store for Memory or a special semantic path. Tests check
exact copies, post-copy corruption, symlinks, Compose mount access, and actual
application dependency construction using the private content tree. The repaired
stack still requires a fresh source-bound activation and actual M5/M6 evidence.
