# Comment Lab

Comment Lab produces one stateless comment from a selected system prompt,
persona, and model catalog entry.

## Entry Points

- `api.py` owns `POST /api/v2/comment-lab/generations` and request validation.
- `contracts.py` defines the public Pydantic request, response, and runtime-default
  contracts.
- `service.py` applies Comment Lab runtime defaults and coordinates provider calls.

## Provider Boundary

`request_builder.py`, `response_mapper.py`, and `helpers.py` own Comment Lab's
provider payload and response rules. The service receives the selected provider
connection from the Model Catalog feature; it does not choose models itself.

## Tests

Feature tests live in `services/ade-api/tests/features/comment_lab/`. They cover
the API contract, provider payload and response mapping, and request-scoped retry
behavior.
