# Feature README Template

Keep a feature README to one page. It should let a contributor find the owner
of a safe change without reading generic layers first.

```md
# <Feature Name>

## Purpose

<User problem and explicit out-of-scope behavior.>

## Ownership

- ADE Web: `apps/ade-web/src/features/<feature>/`
- ADE API: `services/ade-api/src/ade_api/features/<feature>/`
- Public API: `<route family>`

## Request Flow

1. <Browser action and ADE Web state owner.>
2. <ADE API route and application behavior.>
3. <Content, PostgreSQL, or Model Router interaction.>
4. <Visible result.>

## Boundaries

- Owns: <feature-specific policy and storage/content adapter>.
- Uses: <narrow platform contracts or external integration>.
- Must not: <for example call a provider directly or import another feature internals>.

## Tests

- Unit/API/UI: `<command or test location>`
- Live smoke: `<operator command and expected result>`
```

Describe current behavior, not an aspirational backlog. Link to the architecture
guide for shared behavior instead of repeating it. Update this README in the same
change as a feature endpoint, storage authority, integration, or operation.
