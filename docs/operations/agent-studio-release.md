# Agent Studio Release Evidence

Agent Studio releases are evidence-gated. A promoted ledger must bind a clean
source revision, exact ADE API and worker build identities, governed policy
hashes, active conversation/reviewer/embedding route aliases, the approved agent
bundle, three native qualification rounds, llama-server compatibility,
deterministic conformance, and reviewer approval.

Run the release and qualification targets listed by `make help`. The promotion
command validates proposal, conformance, reviewer approval, manifest update, and
ledger promotion as one operation. A failure requires new evidence; development
mode is not a way to bypass release policy.

The ordinary recovery contract is deployment rollback and PostgreSQL
backup/restore. Do not introduce a second runtime, a data importer, or an
application-level fallback as a recovery mechanism. See
[ADR 0019](../adr/0019-ade-steady-state-runtime.md) for the durable policy.
