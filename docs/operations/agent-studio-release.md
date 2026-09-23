# Agent Studio Release Evidence

Agent Studio releases are evidence-gated. A promoted ledger must bind a clean
source revision, exact ADE API and worker build identities, governed policy
hashes, active conversation/reviewer/embedding route aliases, the approved agent
bundle, three native qualification rounds, selected compatibility checks,
deterministic conformance, and reviewer approval.

The current release candidate selects `deepseek::deepseek-flash` for
conversation and reviewer, and
`dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B` for retriever. These are
unqualified candidate entries, not release authorization. The latter alias is
legacy naming; its endpoint is configured with `QWEN_EMBEDDING_API_BASE` and
defaults to the current Spark service. The effective endpoint must match the
manifest's `route_base_url` before Agent Runtime can bind it. A move requires
an updated endpoint/deployment fingerprint, healthy route, fresh full
qualification, and vector-space compatibility review. Different dimensions,
artifact revision, query/document format, or output semantics require a new
space; stored vectors are not automatically re-embedded.

New promotion emits schema-v4 evidence. Its `compatibility_checks` list is
empty unless a supported compatibility target was explicitly selected in the
qualification configuration. The existing schema-v3 ledger remains historical
and continues to require its llama-server receipt; it is never interpreted as
evidence for the new routes. On endpoint or runtime relocation, promotion also
requires `--embedding-compatibility-receipt`: a content-addressed synthetic
receipt bound to the clean source, retriever route, new deployment fingerprint,
and origin/candidate URLs. It contains query and document inputs' SHA-256s,
both provider request IDs and full paired 1024-dimensional vectors. The
validator requires finite, nonzero vectors with cosine distance at most
0.001; a human reviewer must independently verify the request provenance,
input formatting, model artifact and serving configuration. Numerical
closeness alone does not establish provenance or general model equivalence.

Run the release and qualification targets listed by `make help`. The promotion
command validates proposal, conformance, reviewer approval, manifest update, and
ledger promotion as one operation. A failure requires new evidence; development
mode is not a way to bypass release policy.

The ordinary recovery contract is deployment rollback and PostgreSQL
backup/restore. Do not introduce a second runtime, a data importer, or an
application-level fallback as a recovery mechanism. See
[ADR 0019](../adr/0019-ade-steady-state-runtime.md) for the durable policy.
