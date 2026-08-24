# Feature README Template

Copy this template into a feature directory as `README.md`. Keep it to
one page. It should help a contributor make a safe change without searching
generic layer directories.

```md
# <Feature Name>

## Purpose

<What user problem does this feature solve? What is explicitly out of scope?>

## Ownership

- ADE Web: `apps/ade-web/src/features/<feature>/`
- ADE API: `services/ade-api/src/ade_api/features/<feature>/`
- Public API: `<the /api/v2/... route family>`
- Feature owner: `<team, role, or maintained-by statement>`

## Request Flow

1. <Browser action and ADE Web state owner.>
2. <ADE API route and application service.>
3. <Storage, content, Letta, or Model Router interaction.>
4. <Response and visible outcome.>

## Dependencies And Boundaries

- Uses: `<platform contracts, integrations, content adapters>`.
- Owns: `<feature-specific business policy and storage adapter>`.
- Must not: `<for example, call providers directly or import another feature's internals>`.

## Data And Content

- Source of truth: `<database, content path, or external runtime>`.
- Runtime/generated data: `<ignored path, retention, or none>`.
- Transition notes: `<only if relevant>`.

## Tests

- Unit: `<command or test location>`.
- API/integration: `<command or test location>`.
- UI: `<command or test location>`.
- Live smoke: `<operator command and expected result>`.

## Common Changes

| Change | Start here |
| --- | --- |
| <Example change> | `<file or module>` |
| <Example change> | `<file or module>` |

## Operational Notes

<Timeouts, retries, model constraints, access rules, or troubleshooting that a
maintainer needs to know. Omit this section if it would be empty.>
```

## Writing Rules

- Describe the feature's current behavior, not an aspirational backlog.
- Link to public contracts and exact code homes; do not list every internal file.
- State why an integration is used and who owns retry, persistence, and content
  policy when those boundaries matter.
- Update this README in the same change as a new endpoint, storage authority,
  external integration, or operational behavior.
- Do not repeat generic architecture guidance. Link to
  [Architecture Overview](architecture/overview.md) or
  [Request Flows](architecture/request-flows.md) instead.
