# Schema Center

Schema Center manages the JSON output schemas used by Label Lab. It owns
schema validation, workspace persistence, and archive/restore lifecycle; it
does not run model generation.

## Entry Points

- `api.py` owns `/api/v2/schema-center/label-schemas`.
- `contracts.py` defines the public Schema Center request and response models.
- `registry.py` persists schema files under `content/label-schemas/`.
- `presenters.py` owns the API response mapping.

## Boundaries

Label Lab consumes active schemas through the platform option adapter. Schema
Center invalidates that option cache after every mutation, but never selects a
model or invokes a provider.

## Tests

Feature tests live in `services/ade-api/tests/features/schema_center/` and
cover schema contract validation plus API lifecycle behavior.
