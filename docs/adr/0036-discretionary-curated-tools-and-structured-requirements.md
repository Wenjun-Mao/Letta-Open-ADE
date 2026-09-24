# ADR 0036: Discretionary Curated Tools And Structured Requirements

- Status: Accepted for offline implementation; live qualification remains pending
- Date: 2026-09-24
- Supersedes: The free-form requirement inference in [ADR 0014](0014-curated-tool-invocation-and-external-source-authority.md) and [ADR 0021](0021-evidence-scoped-memory-and-affirmative-tools.md)

## Context

The turn dispatcher inferred mandatory `get_weather` and `search_memory` calls
from English and Chinese action and negation patterns. Natural paraphrases,
compound requests and context-dependent meanings made that rule table a second
semantic interpreter. It could force a call the user did not want or fail to
recognize a request. The failure came from deciding conversational intent in a
lexical policy before model execution, not from tool execution or result handling.

## Decision

An enabled curated tool is available to the conversation model with automatic
tool choice. The turn dispatcher does not derive a `ToolRequirement` from user
text. Tool descriptions explain purpose, argument boundaries and evidence use,
without wording-dependent mandatory calls. The executor retains the
`ToolRequirement` contract for callers that supply an explicit structured
requirement directly. It enforces the named call and records resolution,
satisfaction or failure. The ordinary turn request API has no structured
required-action field; this decision does not add one or imply that free-form
requests carry such a guarantee.

ADE still limits tools to the definition's allowlist, validates arguments and
subject binding, and treats returned results as the evidence of a call. Automatic
context retrieval remains in place. Model prose cannot prove a tool ran or
succeeded. The tool policy version advances to `curated_tool_invocation_v2`,
which changes the deployment policy fingerprint; old release evidence is not
rebound to it.

Evaluation `expected_tool_observations` are observations to score, not runtime
forcing inputs. A case requiring weather or deep memory search fails if a
discretionary call is absent, even when the answer sounds plausible. Frozen
historical fixtures and results retain their original meaning and provenance.

The natural-context selector may expand up to two retrieved candidates when one
non-subject entity label occurs in the current content or recent suffix. That
bounded lexical match is a relevance heuristic for context admission. It does
not prove the meaning of the mention, authorize a memory write, or assert that
the selected fact is true of the utterance.

## Rejected Alternatives

- Expanding multilingual action and negation patterns retains the same semantic
  failure mode and grows an unbounded phrase catalogue.
- Forcing every enabled tool would conflate availability with necessity.
- Passing evaluation expectations into runtime would let a fixture determine
  product behavior.
- Removing explicit structured requirements would discard an existing protocol
  guarantee used by direct executor and probe callers.

## Consequences And Guardrails

Free-form tool requests are model-discretionary and may miss a call. Qualification
must measure that behavior instead of treating a plausible answer as compliance.
A future required-action product UI needs its own explicit request contract and
review; it cannot resurrect text inference. Tests cover discretionary auto
choice, structured call enforcement, result truthfulness, argument validation,
and failed expected observations. No live provider call or release promotion is
part of this decision.
