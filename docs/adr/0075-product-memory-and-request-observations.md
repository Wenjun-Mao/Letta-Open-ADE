# ADR 0075: Product Memory And Request Observations

Status: Accepted for the approved isolated Stage 1 implementation, 2026-10-19.
The live six-slot demonstration and M6 closeout remain separate, pending gates.

## Problem

Router's final-wire capture did not identify normal ADE attempts. ADE's safe
activity retained Memory IDs, not the recall response that informed a particular
request. Consequently a collector could not distinguish actual context from a
later reconstruction. The governed source/policy sets also omitted the concrete
Hindsight client, bank missions and message-source contract. Captured commit IDs
were still exact, but the earlier governed fingerprint did not cover those files.

These are observation and source-governance defects, not evidence of Memory
semantic quality or Character failure. PC-02/05/08/12/14 remain unchanged.

## Decision

Normal worker attempts bind their real saved run/attempt/conversation/workspace
IDs. After SQL ownership checks, execution adds subject/character identity.
Task-local correlation sends those identifiers, stage, a generated ADE request ID
and the runtime phase `reply` to Router without adding fields to model input.
Transport consumes Router's response-header identity even on failed HTTP outcomes.
Safe activity may include that ID, never raw prompts or provider error bodies.

`ADE_API_AGENT_RUNTIME_OBSERVATION_ROOT` explicitly opts a non-default development
workspace with configured operator/admin authentication into private, create-only snapshots.
Its directory must be private and
operator-owned; runtime never chmods an unrelated existing directory. Capture
records actual lookup queries/responses, selected IDs, composer spans and source
IDs, compaction provenance, every pre-Router request, Router correlation and the
attempt's execution outcome. Native recall enables its diagnostic rerank trace
only while this capture is enabled; retrieval policy/budget are unchanged.

Composer spans identify instructions, persona, Memory policy, current input,
local dialogue, summary and automatic recall. The collector verifies those spans
against the actual final-wire messages and labels executor-added policy and tool
continuations separately. It does not construct a substitute model request.

`GET /api/v3/private-observations/runs/{id}` is operator-only, versioned and
workspace-scoped. Reader activity and saved chat do not depend on this export.
The export joins saved attempts and committed reply IDs, detects invalid files
and retains explicit incomplete attempts. Observation failures cannot rewrite or
veto product replies; missing records/incomplete flags fail assessment validation.
Execution producing a candidate is not evidence that its reply committed.

The workflow freezes `setup`/`probe` run groups outside model input and preserves
public API/Router read receipts before validation. It checks all persisted attempts,
public lifecycle request IDs/counts, exact wire bytes/hash/body, scope/source/lease,
continuation chains, component coverage and actual final-response/committed-reply
equality. A fresh probe additionally requires no source dialogue or summary in
non-Hindsight context. No missing capture is repaired by another recall or an
ideal-prompt builder. Failed transport outcomes remain explicit, not billed calls.

Credential/private-reasoning fields are excluded at collection. A request containing
them remains explicitly incomplete, with no raw body stored. In particular these
mechanics do not establish complete capture of a provider continuation that requires
private reasoning in its input. Preserve such a failure, rather than strip provider
protocol fields or silently weaken the complete-input gate.

Add the three concrete Hindsight integration files to current governed hashes and
the relevant current policy bundles. Regenerate only the new unqualified candidate
manifest; never rebind historical fingerprints or promote the old release ledger.
Router's embedding observer recognizes base64 float32 dimensions without retaining
vectors. This does not retroactively supply dimensions missing from old captures.

## Alternatives And Guardrails

Reconstruction in the evaluation runner was rejected: it cannot prove actual
recall, omitted context or Router normalization. Global prompt logging and reader
exports were rejected for privacy. Adding evidence fields to the model payload
would change the experiment. A parallel fact/reviewer store remains excluded.

Portable and application-role SQL tests cover private permissions, corruption,
failed recall/Retry, real normal-worker -> Router -> recording-provider -> public
collector joins, tools and rejected missing/misbound continuations. Controlled
provider/native substitutes prove these mechanics only. Actual native product
probes, source-bound live findings and M6 recovery/closeout are still required;
human Character reviews may remain unreviewed, never synthesized from AI advice.
