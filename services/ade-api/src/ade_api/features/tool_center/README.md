# Tool Center

Tool Center manages ADE-owned custom tools and exposes the current Letta tool
catalog. It owns tool source persistence and lifecycle state; Agent Studio owns
agent attachment and tool use.

## Entry Points

- `catalog_api.py` lists and reads managed and built-in tools.
- `authoring_api.py` creates and updates managed tools.
- `lifecycle_api.py` archives, restores, and purges managed tools.
- `runtime_api.py` owns runtime discovery and Tool Probe.
- `api.py` composes the feature routes under `/api/v2/tool-center/`.
- `contracts.py` defines Tool Center write and response contracts.
- `registry.py` persists managed sources and their manifest under
  `content/custom-tools/`.
- `presenters.py` maps managed records and Letta runtime records into one API
  response.

## Boundaries

The feature uses the Letta integration to create, update, discover, and delete
runtime tools. Tool Center asks Agent Studio's public interface whether a probe
agent is archived; it does not own agent lifecycle policy.

## Tests

Feature tests live beside the source under `features/tool_center/tests/` and
cover managed-tool lifecycle plus Tool Probe runtime controls.
