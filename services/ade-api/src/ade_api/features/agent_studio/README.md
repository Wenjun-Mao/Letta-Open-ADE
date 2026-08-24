# Agent Studio

## Purpose

Agent Studio creates and operates persistent Letta agents. It owns chat, runtime
overrides, memory and system updates, state inspection, archive lifecycle, and
agent-tool attachment. Stateless generation belongs to Comment Lab and Label Lab.

## Request Flow

1. ADE Web calls `/api/v2/agent-studio/agents/...`.
2. Feature route modules validate Agent Studio policy and lifecycle state.
3. `integrations/letta/service.py` performs Letta SDK operations with request-scoped
   timeout and retry settings.
4. State and memory changes are returned to the inspector; durable state remains in
   Letta and archive metadata in `data/runtime/agent-lifecycle/`.

## Key Files

| Change | Start here |
| --- | --- |
| Agent creation/listing | `agents_api.py` |
| Chat behavior | `messages_api.py` and `context.py` |
| Inspector state | `state_api.py` |
| Memory/model/tool updates | `runtime_api.py` |
| Archive/purge | `lifecycle_api.py` and `lifecycle_registry.py` |
| Public contracts | `contracts.py` |

## Tests

```bash
uv run python -m pytest services/ade-api/src/ade_api/features/agent_studio/tests -q
```
