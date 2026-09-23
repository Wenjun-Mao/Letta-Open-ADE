# ADR 0027: Selected-Route Release and Stable Embedding Space

- Status: Accepted for static implementation; live qualification and promotion pending
- Date: 2026-09-23

## Problem

The release reviewer already binds configured conversation, reviewer, and
retriever aliases to exact manifest deployments, but schema-v3 Agent Studio
promotion unconditionally requires a llama-server compatibility receipt.
That historical gate blocks a selected DeepSeek release candidate even when
llama-server is not a supported release route. The embedding store also tags
vectors with the entire retriever deployment fingerprint, mixing vector
semantics with endpoint/runtime identity. Moving a compatible Qwen embedding
endpoint would hide old vectors even though deployment evidence correctly
becomes stale.

## Decision

Use a new release-evidence schema version for the selected-route contract;
keep schema-v3 evidence historically strict and do not reinterpret its llama
receipt. The current candidate uses `deepseek::deepseek-flash` for conversation
and reviewer and the existing Qwen embedding route for retriever. Every role
must still pass three full canonical native rounds, exact manifest/fingerprint
binding, policy/source/build identity, deterministic conformance, and explicit
reviewer approval. Compatibility checks block promotion only when the
qualification configuration explicitly selects them as part of the supported
deployment contract. No current DeepSeek candidate requires llama-server.
Selection and fingerprint rebinding invalidate old qualification; they do not
inherit a passing state.

Keep the Qwen semantic-facts vector space distinct from its deployment. Its
identity pins model artifact/revision, dimensions, query and fact-document
format, pooling/output and normalization/cosine semantics, and retrieval
policy. The existing Qwen deployment fingerprint is retained as the opaque
legacy space ID so already-stored vectors remain addressable without rewriting
them. New definitions use that stable ID; old immutable definition snapshots
without the new metadata retain their historical full-fingerprint behavior.
The router endpoint remains configurable by environment. Endpoint/runtime
changes alter deployment fingerprint and require fresh route health,
qualification, and vector-compatibility review before promotion, but neither
runtime code edits nor automatic re-embedding. Different model/semantic space
must use a new ID; old vectors stay intact and are not searched as if
compatible. Matching dimensions by itself is never proof of compatibility.
The origin-runtime image digest uses the manifest parser's normalized value
(without the optional `sha256:` prefix) so an unchanged runtime is not
misclassified as relocation.

## Rejected Alternatives and consequences

- Do not promote the development DeepSeek entry by changing only hashes or
  relabel old DGX/llama evidence.
- Do not make every optional compatibility target a universal release gate.
- Do not assume relocated embedding endpoints produce numerically identical
  vectors from matching model names or dimensions; the reviewer needs a
  comparison/attestation for the new endpoint before approving reuse.
- Do not rewrite existing vectors or immutable conversation definitions in
  this preparation slice. No private histories enter qualification inputs.

The provider-neutral contract makes future chat APIs selectable through the
existing Model Router, but each selected deployment remains unqualified until
fresh evidence is reviewed. The current Qwen semantic format is deliberately
not generalized to arbitrary embedding models by this decision.
