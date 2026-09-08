# References

ADE's current product contracts are defined in this repository, especially the
feature READMEs, generated OpenAPI artifacts, and [ADR 0019](adr/0019-ade-steady-state-runtime.md).

## Runtime Research Provenance

The following sources informed the historical runtime study and its design
principles. They are research provenance, not current ADE runtime dependencies
or operating instructions.

- [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)
- [Letta repository](https://github.com/letta-ai/letta)
- [Letta 0.16.8 release](https://github.com/letta-ai/letta/releases/tag/v0.16.8)
- [Letta Code agent prompt](https://github.com/letta-ai/letta-code/blob/main/src/agent/prompts/letta.md)
- [PydanticAI agents](https://ai.pydantic.dev/agents/)

The detailed source and experiment record remains in the
[ADE-native agent runtime replacement study](architecture/agent-runtime-replacement-study.md).

## Active Provider References

- [Qwen3-Embedding-0.6B model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- [vLLM pooling models](https://docs.vllm.ai/en/stable/models/pooling_models/)

Use Model Router configuration and its catalog for active source/model behavior;
do not copy provider endpoints into product features.
