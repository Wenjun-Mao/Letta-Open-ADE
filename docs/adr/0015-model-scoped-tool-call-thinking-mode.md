# ADR 0015: Tool-Call Thinking Defaults Are Model-Scoped Router Policy

- Status: Accepted for implementation; deployment exposure requires qualification
- Date: 2026-09-02
- Related: [ADR 0007](0007-router-authority-for-router-backed-models.md),
  [ADR 0010](0010-production-path-runtime-qualification.md), and
  [ADR 0014](0014-curated-tool-invocation-and-external-source-authority.md)

## Context

The DGX Qwen deployment intermittently returned a Qwen XML-style tool block inside
the OpenAI `function.arguments` string when thinking was enabled. ADE correctly
failed the attempt with `conversation_tool_arguments_invalid_json`; parsing that
provider-specific text in the runtime would weaken the OpenAI tool contract.

An exact-context live diagnostic reproduced the behavior. The existing profile
produced valid JSON in 4 of 6 calls, while greedy sampling made all 6 calls invalid.
With thinking disabled and the normal sampling profile, 10 of 10 weather calls and
6 of 6 deep-memory calls produced valid JSON. The same runtime schema already worked
with llama-server. Qwen's official
[function-calling guide](https://qwen.readthedocs.io/en/stable/framework/function_call.html)
recommends Hermes-style tool use and documents `enable_thinking` as a tool-call
generation control. Its
[vLLM guide](https://qwen.readthedocs.io/en/stable/deployment/vllm.html)
also treats thinking mode and tool parsing as explicit serving concerns.

## Decision

- Model profiles may define nullable `tool_call_thinking_default_enabled` metadata.
- For a vLLM request with a non-empty `tools` list, Model Router uses this value when
  `chat_template_kwargs.enable_thinking` is omitted. Requests without tools continue
  to use `thinking_default_enabled`.
- An explicit caller value always wins. The router never overwrites explicit
  thinking mode, sampling, tools, or named tool choice.
- The DGX Qwen profile keeps ordinary thinking enabled and defaults tool-bearing
  requests to non-thinking mode.
- The tool-call mode is part of the deployment fingerprint. Changing it invalidates
  prior qualification evidence.
- ADE continues to require strict JSON object arguments. It does not parse Qwen XML,
  issue a hidden repair call, or retry a failed attempt unless `retry_count` permits
  another complete ADE attempt.

## Rejected Alternatives

### Parse Provider-Specific XML In The Runtime

This would duplicate the provider adapter, accept ambiguous malformed output, and
make the ADE runtime depend on one model family's private wire format.

### Retry Or Repair Malformed Arguments

This would make `retry_count=0` misleading and hide protocol instability. The
original attempt must remain failed and observable.

### Disable Thinking For Every Qwen Request

Normal dialogue and reviewer behavior can benefit from thinking. The observed
incompatibility is limited to tool-bearing generation, so the default is scoped to
that protocol mode.

### Use Greedy Decoding For Required Tools

The live diagnostic made the malformed format deterministic, and Qwen's guidance
also warns against greedy decoding in thinking mode.

## Consequences And Guardrails

Model Router remains the only owner of provider-specific request normalization.
Future local models can opt into a different tool-call default without runtime
branches, and explicit experiments remain possible through caller overrides.

- Add profile, catalog, router-normalization, and explicit-override tests for every
  model that declares this field.
- Record the field in deployment sampling settings and require fresh qualification.
- Keep raw malformed arguments out of runtime events and persisted artifacts.
- Re-run both required curated tools against every candidate conversation model.
