# Label Lab

Label Lab extracts schema-validated entity groups from a text input using a
selected prompt, label schema, and Model Catalog entry.

## Entry Points

- `api.py` owns `POST /api/v2/label-lab/generations` and request validation.
- `contracts.py` defines the public Pydantic request, response, and runtime-default
  contracts.
- `service.py` coordinates generation, validation, and bounded repair attempts.

## Provider Boundary

`request_builder.py`, `response_mapper.py`, and `helpers.py` define Label Lab's
structured-output contract. Schema Center reuses the helpers to validate editable
schemas, and provider probes reuse the stable probe helpers.

## Tests

Feature tests live in `services/ade-api/tests/features/label_lab/`. They cover
the API contract, output mapping, generation service, and repair behavior.
