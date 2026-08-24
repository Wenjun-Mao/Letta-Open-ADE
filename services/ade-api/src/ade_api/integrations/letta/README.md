# Letta Integration

This directory is the ADE API boundary around the Letta SDK.

- `agent_service.py` owns persistent-agent messaging, memory, model, prompt, and attached-tool operations.
- `tool_service.py` owns CRUD and discovery for Letta's global tool catalog.
- `message_parser.py` normalizes Letta message traces into ADE chat responses.

Feature routes depend on the narrow service matching their responsibility. Tool Probe is an Agent Studio runtime operation even though its route lives in Tool Center, so it uses `LettaAgentService`.
