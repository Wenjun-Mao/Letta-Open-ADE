# ADR 0014: Curated Tool Invocation And External Results Are Explicit Contracts

- Status: Accepted for implementation; deployment exposure requires qualification
- Date: 2026-09-02
- Related: [ADR 0009](0009-ade-owned-agent-runtime.md),
  [ADR 0010](0010-production-path-runtime-qualification.md), and
  [ADR 0013](0013-narrow-native-runtime-product-pilot.md)

## Context

An enabled curated tool was previously always sent with `tool_choice="auto"`. That
was adequate for discretionary agent behavior but did not guarantee an explicit
external action. In live llama-server compatibility evidence, the model plausibly
claimed that a weather lookup failed without calling `get_weather`; therefore no
tool request or failed result existed in the trace. The evaluation fixture also used
one `required_tools` field both to enable a tool and to score its observation, which
blurred product policy with test configuration.

Stronger prompt wording alone cannot establish that an external action occurred.
Retrying an invalid final response would create a second hidden policy owner and
would violate the meaning of an ADE attempt when `retry_count=0`.

## Decision

- A curated tool has one of three effective states for a turn:
  `unavailable`, `available`, or `explicit_action_required`.
- The definition owns availability. ADE may resolve one unambiguous explicit action
  from the current user message through a versioned deterministic policy. A future
  typed UI action may provide the same requirement directly. Model arguments, an
  eval case key, expected observations, and fault-fixture values never select the
  requirement.
- The first policy recognizes narrow English and Chinese requests for subject-bound
  deep-memory search and current-weather lookup. Benign mentions remain
  discretionary. If multiple capabilities match, ADE does not guess an order and
  leaves the turn discretionary until a later multi-action contract exists.
- For `explicit_action_required`, the first provider request uses the exact
  OpenAI-compatible named-function form. A final response, a different tool, or
  malformed arguments before the required call fails the current attempt closed.
  ADE does not issue a repair request. `retry_count` remains the only owner of an
  additional complete attempt.
- A valid required call satisfies the invocation contract even when the curated
  handler returns a typed failure. The returned result is authoritative evidence;
  the following model step may explain success or failure and resumes discretionary
  `tool_choice="auto"` behavior.
- The assistant must never claim that a tool ran or succeeded without a corresponding
  result. Requirement resolution, satisfaction, and failure use correlated events
  containing only mode, curated tool name, capability, source, policy version, and a
  stable failure detail code. They contain no user text or model arguments.
- Evaluation fixtures separately declare `enabled_tools` and
  `expected_tool_observations`. Expected observations only score behavior; they do
  not configure runtime requirements.
- `get_weather` remains a deterministic qualification fixture and is not exposed by
  the memory-focused product pilot. The pilot continues to expose only subject-bound
  `search_memory` under ADR 0013.
- `retry_count` counts additional ADE attempts. Bounded tool-loop continuation and
  the separately recorded reviewer schema-repair step are model steps inside an
  attempt, not hidden SDK/framework retries. Conversation output or tool-protocol
  validation never receives an unrecorded repair step.

## Rejected Alternatives

### Prompt Instructions Only

Prompts can improve model compliance but cannot prove a call occurred. The runtime
must constrain and validate the protocol when the product promises an action.

### Force Every Enabled Tool

Availability does not imply relevance. Always forcing search or weather would make
ordinary dialogue brittle and erase useful agent discretion.

### Infer Requirements From Evaluation Fields Or Failure Values

That would create test-only production behavior and allow `FAIL_CITY`, a case name,
or an expected result to become a hidden runtime control.

### Repair A Missing Call With A Second Model Request

This would conceal a retry when the user requested zero additional attempts and
would make request counts depend on validation luck. The attempt fails closed.

## Consequences And Guardrails

Explicit external actions become model-independent protocol guarantees for phrases
the policy recognizes, while unrecognized free-form wording remains honestly
discretionary. Expanding recognition or adding a curated capability changes the
tool-policy fingerprint and requires deterministic tests, security review, and fresh
qualification.

- Never treat assistant prose as evidence of a tool call.
- Never inspect fault-fixture arguments or evaluation case identity in policy code.
- Never let the model select a memory subject through tool arguments.
- Never broaden multilingual matching without benign-mention and ambiguity tests.
- Never enable an additional product tool merely because it exists in qualification.
