# Upstream References

Use ADE Web and ADE API for project workflows. These upstream sources
are the maintained references for Letta concepts and SDK behavior:

- [Letta documentation](https://docs.letta.com/)
- [Letta Python SDK](https://docs.letta.com/api/python)
- [Agents API](https://docs.letta.com/api/resources/agents)
- [Attaching and detaching memory blocks](https://docs.letta.com/tutorials/attaching-detaching-blocks/)
- [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)
- [Pinned Letta 0.16.8 release](https://github.com/letta-ai/letta/releases/tag/v0.16.8)
- [Letta source repository](https://github.com/letta-ai/letta)
- [Letta Code agent prompt](https://github.com/letta-ai/letta-code/blob/main/src/agent/prompts/letta.md)
- [PydanticAI 2.35.1](https://pypi.org/project/pydantic-ai/2.35.1/)
- [PydanticAI agents](https://pydantic.dev/docs/ai/core-concepts/agents/)
- [PydanticAI message history](https://pydantic.dev/docs/ai/core-concepts/message-history/)
- [PydanticAI OpenAI-compatible providers](https://pydantic.dev/docs/ai/models/openai/)
- [Qwen3-Embedding-0.6B model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- [vLLM pooling models](https://docs.vllm.ai/en/stable/models/pooling_models/)

The current replacement research, source/image provenance, and independently
implemented comparison harness are documented in the
[ADE-Native Agent Runtime Replacement Study](architecture/agent-runtime-replacement-study.md).
Its accompanying [ADR 0009](adr/0009-ade-owned-agent-runtime.md) is accepted for an
opt-in implementation preview. The supported product remains Letta-backed until all
qualification gates pass and a separate production cutover is accepted.

The repository previously carried generated exploratory notebooks and a local
copy of the MemGPT paper under `docs/`. They were removed because they were
unreferenced, bypassed ADE API, and could drift from the pinned
Letta server and SDK. Recreate experiments as self-contained workflows under
`workflows/evals/` when they measure product behavior, or under a documented `examples/`
directory when they demonstrate a maintained integration.
