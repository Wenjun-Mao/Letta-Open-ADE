# Natural-memory checkpoint 6: live preflight hold

Status: one campaign authorized on 2026-09-24; zero generation and zero embedding
requests sent. Live execution is held for a product decision on the evaluation
capacity binding. The frozen `cases.json` and `matrix.json` are unchanged.

## Evidence and root cause

- The matrix fixes a 4,096-token generation context with a 512-token output
  reserve, a 3,072-token input limit, and an 8,192-token reviewer context with
  a 6,759-token input limit. Its 48-record pressure cells depend on the full
  generation packet exceeding that 3,072-token limit while the reviewer packet
  still fits. It reserves at most two conversation requests and one reviewer
  request per turn, plus two actual compactions: 92 of 96 generation requests.
- The selected live `deepseek::deepseek-flash` deployment has one pinned
  fingerprint for both conversation and reviewer. Its manifest advertises a
  16,384-token context, 4,096-token output reserve, and six model requests per
  conversation. `context_budget_from_deployment` and `max_model_requests` read
  those values from the stored snapshot. `validate_definition_execution`
  compares the stored fingerprint and payload to the current catalog.
- The offline pressure test substitutes a 4,096-token fake catalog. It proves
  serialized packet behavior under that test budget, not that the live native
  worker will use the same boundary. Running the frozen pressure cells against
  the selected deployment would therefore test a different capacity condition.
  The shared request ledger would still cap total spend, but it would not make
  a six-request native conversation obey the reviewed two-request cell limit.

This is a mismatch between the frozen evaluation contract and the selected
runtime capacity contract. Increasing prompt filler, altering the matrix, or
editing a stored deployment snapshot would change the comparison or bypass the
pinned identity check. None is an authorized repair.

## Verified prerequisites

The approved external config was read narrowly from the project's existing
`.env`; no secret was copied or printed. Catalog discovery reported healthy
`deepseek-flash` and `Qwen/Qwen3-Embedding-0.6B` routes, and the Qwen sidecar
TCP endpoint was reachable. Fresh disposable database
`ade_m2_memory_test_01a0d41d` on loopback port 32768 was created and migrated
to `20260924_0007`; other databases were untouched. The first migration attempt
showed that Alembic's version table needs schema `ade` precreated in a fresh DB.
That schema was created only in this disposable DB, then migration passed.

## Smallest decision and implementation surface

The director recommends an isolated evaluation-only, role-specific capacity
binding on the same actual DeepSeek route. A reviewed implementation would pin
the actual deployment identity while adding immutable generation/reviewer
evaluation limits checked to be within it; apply those limits in context packing,
reviewer preflight, request `max_tokens`, and native continuation count; and
cover exact fingerprint validation and pressure behavior with fake transport and
real-worker tests. The Qwen route, frozen matrix, production manifest, and
normal product binding would remain unchanged. This is a new evaluation runtime
contract, so it awaits explicit user choice before implementation or live calls.

The 512-token conversation reserve and 1,024-token reviewer reserve are both
lower than the selected route's 4,096-token reserve. They can be deliberate
evaluation limits if approved, but may constrain DeepSeek's hidden reasoning
and therefore must be named in the comparison. The separate 4,096/8,192
role-specific contexts cannot be represented by the current single shared
deployment fingerprint without an evaluation-only override contract.

The scoped transport in `natural_live_transport.py` is offline-tested glue: it
requires a named request scope, exact route keys, local call caps, shared SQLite
pre-request reservation, and redacted raw capture. It has not been attached to a
live runner or used for a provider request. The campaign, response scoring,
human comparison, and policy selection are unrun.
