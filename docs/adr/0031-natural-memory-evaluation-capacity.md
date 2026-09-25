# ADR 0031: Pinned Evaluation Capacity for Natural-Memory Checkpoint 6

- Status: Historical single-campaign decision on 2026-09-24.

> Frozen capacity settings explain the retained comparison evidence. They are
> not production defaults, a policy selection, or standing authorization to rerun.
- Authority: [implementation plan](../plans/natural-memory-implementation.md)
- Scope: isolated development evaluation sessions only

## Problem

The frozen A/A0/B matrix uses separate 4,096-token conversation and
8,192-token reviewer contexts, with two conversation requests and one reviewer
request per turn. The selected DeepSeek deployment advertises one shared
16,384-token context and six conversation requests. Its actual pinned
fingerprint cannot be edited to reproduce the frozen comparison.

## Decision

Store an additional named checkpoint-6 capacity profile on the immutable
evaluation definition snapshot after resolving the real DeepSeek deployment.
Keep the original route, deployment fingerprint and payload untouched. After
normal fingerprint validation, the native worker verifies the exact profile,
the evaluation purpose and natural policy, the same approved DeepSeek route for
both roles, sufficient underlying provider capacity, and zero reviewer repair.
Only then does it apply the smaller role budgets and two-request conversation
limit. The native natural reviewer remains one request. The shared durable
request ledger still reserves before every outbound generation or embedding
call, including setup and compaction.

The frozen pressure construction also fixes a 640-token shared local suffix.
The normal reviewer's extra 320-token admission reserve would reject its
48-record target set before checking the complete serialized request. Under
this evaluation binding alone, select against the matrix's 640-token suffix
and retain the exact 6,759-token full-request preflight before generation and
the same limit at review. The 48 pressure values use the frozen short-record
construction; the live prompt retains the product prompt and appends the
frozen 5,310-byte synthetic padding, with its modified content hash stored
on the evaluation definition.

## Alternatives and consequences

Changing the production deployment manifest, changing the frozen pressure
matrix, and substituting a fake live catalog were rejected because each would
alter the evidence being measured or bypass pinned identity. The smaller
512/1,024 output reserves may constrain DeepSeek reasoning; comparison results
must describe that tested envelope. This binding confers no release
qualification or normal product policy. A new campaign, wider budget, different
route, or changed profile requires a new decision.
