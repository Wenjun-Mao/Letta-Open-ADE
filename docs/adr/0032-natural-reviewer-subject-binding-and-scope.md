# ADR 0032: Reviewer Subject Binding and Scoped Values

- Status: Historical diagnostic; model-facing interface superseded by
  [ADR 0035](0035-compact-natural-review-and-observational-dispatch.md).

> Scoped factual fidelity remains a product requirement, but this earlier
> model-owned binding interface is not the current implementation contract.
- Scope: natural-memory reviewer request and typed proposal contract

## Problem

A live reviewer proposal for a subject preference selected the subject UUID in
`entity_ref` and omitted “morning” from the saved value. The native policy
correctly rejects a selected entity on subject-kind facts, but the reviewer
request did not state that conditional rule. Its schema allowed string or null
for every add. The request also supplied the full user span without explicitly
asking that meaningful time, place, frequency, and condition survive in value.

## Decision

State the entity and scope rules in the shared natural reviewer instructions.
Subject-kind adds use a null or omitted `entity_ref`; related-entity adds use
the existing/new reference contract. Values retain supported temporal,
spatial, frequency, and conditional scope. Typed `NaturalAdd` validation uses
the fact registry's entity kind to reject a selected subject entity before
native preparation. Native preparation still resolves subject IDs itself and
retains its source, entity-kind, and provenance checks. No invalid proposal is
remapped or repaired, and no deterministic claim is made that parsing can
guarantee every semantic scope.

## Alternatives and guardrails

Silently dropping `entity_ref`, accepting a broad value, or loosening the
mutation scorer would hide the observed failure. The change applies to the
normal natural reviewer path as well as evaluation; it is not a special rule
for one cell or provider. Captured-shaped and counterfactual tests cover
subject rejection, nullable subject binding, related-entity identity, and
the frozen reviewer capacity envelope. Live iterations remain separately
versioned and require committed readback to count as improvement.
