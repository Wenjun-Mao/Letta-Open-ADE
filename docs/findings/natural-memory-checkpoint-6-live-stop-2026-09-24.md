# Natural-memory checkpoint 6: one-attempt live stop

Status: stopped after the first required mutation on 2026-09-24. This is a
partial diagnostic, not an A/B comparison or policy-selection result. The
frozen cases and matrix were unchanged; the exact running source was
`717ee8090a11b56ac3bd683a34ef4a115920d991` with source fingerprint
`6efadd3c4503185346783075befda436c4206b62053e24f2b7251a429306f6af`.

## Measured result

The native `mutation-preference-add::native` cell accepted one user turn,
`我早上喜欢喝咖啡。`, on an isolated synthetic subject. It sent one Qwen query
embedding, one DeepSeek conversation request, and one DeepSeek reviewer
request. All three outbound requests completed; the shared ledger records
embedding 1/160 and generation 2/96. The attempt failed and was atomically
rejected: no assistant message, no fact revision, memory generation unchanged.
The campaign stopped as required, leaving 29 of 30 cells unrun. No retry,
repair, reroll, or further provider request was made.

The reviewer returned an `allow` proposal for `person.preference` with
`qualifier: "drink"`, `value: "咖啡"`, and `entity_ref: <subject UUID>`.
Replaying this captured typed decision offline against the persisted subject
entity reproduced `RuntimeValidationError: Subject facts cannot select an
entity`. This is the immediate rejection cause. Separately, the proposed
value omitted the morning scope in the user's statement. That proposal was
never committed, so the omitted scope is an observed draft-quality issue,
not a saved-memory state. A single attempt does not establish a general model
failure rate.

## Reviewer request and contract diagnosis

The captured reviewer request included the exact current user message and
source span, and its `allowed_fact_contracts` marked `person.preference` as
`entity_kind: "subject"`. It also listed the subject entity ID. The embedded
JSON schema allowed `entity_ref` to be a string or `null`, with `null` as the
default ([proposal model](../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_review.py)); the request's prose did not explicitly say to leave it null for `person.*` facts. The native policy instead requires that condition and resolves subject facts automatically ([entity resolution](../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_policy.py)). The schema could express the invalid combination, while the validator correctly rejected it.

The reviewer prose instructed the model to review supported claims and cite
exact source spans, but did not explicitly require a proposal value to retain
time-of-day scope; `value` was an unconstrained string in the embedded schema
([review request builder](../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_reviewer.py)). The scope was available in the source text.
The smallest follow-up is an offline contract review: make subject entity
selection and scope preservation explicit in the reviewer request or typed
schema, then test those conditions with captured-packet counterexamples before
considering another authorized live campaign. No product or scorer contract
was changed during this campaign.

## Retained evidence

Private artifacts remain under
`data/runtime/natural-c6-01a0d41d-output/` in the retained worktree, with
mode-restricted raw captures and attempt readback. The scoped router container
was stopped after the run. The manifest SHA-256 is
`7190557d61411ac0c75fc040fa0432e138db788c5dddb637ba5ed7dc6dd6b04f`;
the native attempt SHA-256 is
`9d083524748e97ebcf6c2f223c2d1d87229469505eadf02c520df71d65c5c2bc`.
The ledger SHA-256 at stop is
`a7aa18f673a2d0c1b0e832866f09351b90116939b772ffb74d7851c2a43b4268`.
The exact run ID is `35822fab-b987-4947-9e23-4da750f24676`.
