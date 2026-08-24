# Model Catalog

Owns ADE's interpretation of model-router source and profile metadata. It resolves
the scenario-specific model and embedding options, validates Comment Lab and Label
Lab selections, exposes `/api/v2/model-catalog/*`, and checks Letta capabilities at
startup.

Other features import its public selection and options functions rather than reading
model-router configuration or internal Model Catalog modules directly. Agent Studio,
Comment Lab, and Label Lab all receive model decisions through this interface.

The model router is authoritative for router-backed Agent Studio availability. ADE
passes an explicit router `llm_config` when it creates an agent, so a stale Letta
catalog list does not hide a healthy compatible model. Catalog diagnostics retain
`letta_catalog_visible` to expose synchronization lag without turning it into a false
availability gate. Letta remains authoritative for embedding handles.

`scenario=label` also includes Label Schema Center metadata because the stable options
response includes it. The dependency is read-only and uses Schema Center's public
registry contract.
