# D04 Behavioral Comparison — Frozen Prospective Protocol

Date: 2026-10-02. User-approved diagnostic; offline readiness checkpoint only.
Manager review and explicit continuation precede live execution. Commit this
protocol, runtime-built requests and preparation before any provider outcome.
PC-03/04/05/06/09/10/11 and [ADR 0059](../../../../../../docs/adr/0059-bounded-d04-behavioral-comparison.md)
govern scope. No product agreement or runtime admission policy changes.

## Question And Fixed Arms

With D04's unchanged question “你那晚看到木制风铃是在什么地方？”, neutral
persona and empty saved facts, entities and local suffix, does restoring the
missing antecedent change one fresh answer? Does the previously measured whole
pool behave differently?

1. Literal-four: E07, E02, E05, E04.
2. Repaired-four: E07, E02, E05, E01.
3. Whole-pool: E01 through E08, original chronology.

First versus second isolates replacing the last redundant mistaken retelling,
keeping the other sources' count and order fixed. Repaired-four is evaluator
chosen, not a candidate selector. Whole-pool is a complete-packet policy comparison,
not a pure count ablation: content and ordering also differ. Retain every complete
source and original hash. No extra cases, controls, selector reasoning, summaries,
model sweep or reroll. Historical labels/artifacts/builders remain untouched.

## Requests And Source Authority

Runtime-owned service-test mechanics construct generation, reviewer template and
full-reserve reviewer for each arm. Each downstream pair receives identical final
H; prior answers and evaluator topology never enter another arm. Question/persona
and empty context stay fixed. H retains its existing ownership/version/archive
annotations and message hashes; broader eligibility is synthetic, not observed
from a database. No evaluator annotations beyond the established H wire contract.

Route: `deepseek::deepseek-flash`, adapter `deepseek_openai`, public Model Router
`/v1/chat/completions`. Every call pins `thinking={type:enabled}`,
`reasoning_effort=high`, `stream=false`, `max_tokens=4096`; no tools or sampling
overrides. Historical generation omitted thinking fields; router defaults were
enabled/high. The new explicit equivalent fields are measured and tested; the
reviewer already used them and retains `response_format={type:json_object}`.
Effective provider semantics/availability must be verified at launch, never assumed.

Generation input limit 11213; reviewer input limit 11469; both output reserves
4096. Reserve the candidate reply with 16384 ASCII characters before generation.
Substitute only the actual final visible answer, excluding provider reasoning.
Measure the complete UTF-8/JSON serialized reviewer request after substitution;
never truncate. Byte/4 estimates are not provider token counts.

One generation and at most one dependent reviewer per arm, at most six chat
completion requests total. Absolute request deadline 180 seconds, zero automatic
retries or repairs. No embeddings, memory writes or database access. This finite
experimental design adds no runtime spend-policy system.

## Source-Quoted Manual Assessment Rubric Before Outcomes

The unchanged [frozen ledger](../../correction_dependencies/cases.json) supplies:

- E01: “那晚我独自散步，在旧书店门口看见一串木制风铃，风吹起来声音很轻。”
- E07: “我后来把那晚看到木制风铃的地方说错了：不是茶馆里，是最初说的那个地方，最初的说法才对。”

Literal-four has E07 but lacks E01: rejecting the teahouse does not recover the
restored location. It cannot legitimately name that missing location from its
packet. Honest uncertainty can be correct behavior. Repaired/full deliver E01
and E07, supporting the old-bookstore entrance and the correction, without
authorizing invented user participation or previously told details.

Assess each actual final H and visible answer against the full source ledger,
quoting evidence and recording these separate observations:

- Supported named answer: what location is actually available and warranted?
- Honest uncertainty: does qualification accurately reflect missing evidence?
- Unsupported/invented detail: is any missing detail asserted as established?
- Correction handling: is the teahouse mistake/restoration respected, without
  requiring every answer to narrate the correction?
- Ownership: does assistant solo history remain separate from user/shared history?
- Naturalness: is the reply useful and conversational, without a mandated phrase?
- Reviewer interpretation: what did its actual output propose, and do schema and
  source binding hold? A valid citation does not prove interpretation (PC-05).

No phrase requirement, keyword semantic scorer, chronology/repetition truth rule,
aggregate score or second factual judge. Reviewer no-change is not proof of answer
correctness; reviewer conflict requires actual grounding, not absence alone.
Manual source-quoted assessment is exposed/non-blind and must name its assessor
and explicitly identify whether the assessor is human or AI. A Codex manager's
qualitative assessment is AI-authored, not an independent human review; the rubric
does not imply that any human conducted the eventual readout. One result per
arm is a diagnostic witness, not reliability, population causality, production
retrieval quality or persistence qualification.

## Execution, Capture And Stops

Launch only from clean committed source with exact input/request/configuration
hashes. An isolated authenticated loopback router is a fresh process from that
source, using workflow-only DeepSeek configuration, reviewed profiles and
deployment manifest, 180-second upstream timeout and no retries. The operator
attests effective configuration; fresh public catalog verifies canonical model,
provider ID, adapter, profile enabled/high defaults and official endpoint identity.
Catalog and configuration originals remain private. Do not assume retained-service
deployment qualification or inspect credentials at offline readiness.

The single launch directory is ignored `outputs/d04-comparison`. Never replace
or remove it to rerun. Exclusive, fsynced intent precedes each send; exact request
hash, source and route bind the attempt. Capture complete response bytes or error
type afterward, before interpretation. Uncertain timeout, interruption or capture
failure consumes the intent even if no complete outcome exists. Preserve originals.

Transport/auth/routing failure stops all later stages. Source/config/route drift
and any preflight/capacity failure stop before the next send; no fallback model,
route switch or retuning. Complete malformed, empty, tool, refused or truncated
generation is an observed unusable outcome: skip its dependent reviewer explicitly,
then continue the next predeclared arm. Complete malformed reviewer is retained
without repair and the next arm continues. Well-formed reviewer JSON receives a
separate offline audit through existing runtime schema/source-binding contracts;
invalid binding/schema remains an observed invalid output, never repaired.

Bounded resume is permitted only at a fully captured prefix, with identical
committed source/config/requests and fresh matching catalog. No stage is resent.
An infrastructure stop, missing/partial outcome, inconsistent receipt or global
preflight stop refuses continuation. Unexpected process termination leaves later
stages explicitly `unrun` in status inspection; no outcome is inferred. A fresh
catalog attempt is not a chat completion and never resets consumed stage intents.

Receipt validation and execution authorization are separate. Offline audit may
assess earlier complete captured reviewers after a later stopped or uncertain
attempt, and reports each later stage's stopped/uncertain/unrun status. It first
validates the entire observed prefix: tampering, non-prefix or post-stop artifacts
fail, including malformed complete outcomes. A bound intent without an outcome
remains consumed and uncertain; any incomplete raw capture for that attempt stays
uninterpreted. Audit never repairs receipts, permits continuation or resends.

Keep complete raw responses/errors, provider reasoning, secrets and endpoint
details in ignored private evidence. Publish only reviewed synthetic visible
outputs/redacted metadata; manual publication review is required. No services or
providers are touched at this readiness checkpoint. Native turn-7 stop remains.
