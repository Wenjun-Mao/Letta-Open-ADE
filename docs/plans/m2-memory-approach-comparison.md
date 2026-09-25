# M2 Memory-Approach Comparison Plan

Status: Deferred external-candidate comparison under
[ADR 0022](../adr/0022-incumbent-memory-first-product-slice.md).

Luna and PostgreSQL development evidence is retained; it does not establish an
ADE/Hindsight comparison winner. The original work specification below is not
active installation or experiment authority.

## Decision Question

For 林小棠's everyday Chinese companionship, does the smallest source-owned ADE
extension meet the M1 continuity cases more safely and simply than Hindsight?
This work compares evidence; it does not adopt either candidate.

## Bounded Work

1. Map the current ADE facts, evidence provenance, correction/forgetting,
   subject boundary, and retrieval contracts against the M1 cases.
2. Add a workflow-local specification with timestamped multi-conversation,
   two-subject inputs, expected state, and negative probes, plus deterministic
   checks for the parts current contracts can actually exercise. This is a test
   specification, not an executed candidate comparison. Report unsupported
   concern, promise, shared-event, and semantic-retrieval requirements rather
   than inventing a production representation. Future runs use fresh isolated
   case state and chronological turns; a forgetting run must prove the prior
   fact was stored and recalled before it is deleted.
   A bounded isolated PostgreSQL test also exercises the existing typed-fact
   add/correct/forget writes as committed transactions with separate
   connection read-backs, source/revision lineage, current-revision embedding
   join, and subject filters with deterministic synthetic vectors. This
   verifies storage/query wiring only; provider-backed semantic retrieval
   remains pending. A separate ADE-only development slice may condition Luna
   dialogue on facts read back from committed PostgreSQL state; it must remain
   distinct from candidate-comparison evidence and use no historical source
   turns or expected answers in its probes.
3. Inspect pinned official Hindsight documentation and source for retain/recall,
   bank isolation, deletion/correction, provenance, dependencies, and provider
   requirements. Record citations and operational implications.
4. Use the common fixtures and a common input/context budget to distinguish
   storage correctness, retrieval quality, extraction quality, dialogue quality,
   and latency. M1 and the bounded M2 Luna records may diagnose source-linked
   extraction, supplied-context dialogue, and factual-recall versus
   recommendation attribution only; they are not candidate comparison or
   native-provider evidence. The PostgreSQL read-back dialogue slice is
   likewise development context-conditioning evidence, not semantic retrieval
   or head-to-head evidence.
5. Publish a concise comparison finding, exact pending live experiments, and a
   confidence-qualified recommendation. Do not select or install Hindsight.

## Non-Goals And Gates

No production API, database migration, memory service, Compose change, Spark
generation, cloud billing, proxy, or release-evidence update belongs to M2
comparison work. Native Qwen/embedding/provider experiments and qualification
remain pending an authorized available provider.
