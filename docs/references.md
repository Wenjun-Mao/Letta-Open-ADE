# Upstream References

Use ADE and the Agent Platform API for project workflows. These upstream sources
are the maintained references for Letta concepts and SDK behavior:

- [Letta documentation](https://docs.letta.com/)
- [Letta Python SDK](https://docs.letta.com/api/python)
- [Agents API](https://docs.letta.com/api/resources/agents)
- [Attaching and detaching memory blocks](https://docs.letta.com/tutorials/attaching-detaching-blocks/)
- [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)

The repository previously carried generated exploratory notebooks and a local
copy of the MemGPT paper under `docs/`. They were removed because they were
unreferenced, bypassed the Agent Platform API, and could drift from the pinned
Letta server and SDK. Recreate experiments as self-contained workflows under
`evals/` when they measure product behavior, or under a documented `examples/`
directory when they demonstrate a maintained integration.
