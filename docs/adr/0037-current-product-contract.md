# ADR 0037: One Current Product Contract

Status: Accepted 2026-09-25 for documentation governance only.

## Context

A settled character-continuity boundary was asked again because it lived in an
older design while ADRs and plans described narrower implementation slices.
Append-only status amendments also made historical constraints look current.

## Decision

[The product contract](../product-contract.md) owns current product intent using
stable PC identifiers, source links, separate implementation status and explicit
open questions. Plans and product reviews cite relevant agreements. Record an
approved direction change there in the same checkpoint and explicitly supersede
conflicting instructions; preserve historical evidence.

ADRs retain technical rationale, the roadmap retains sequencing, and the tracker
retains current work and evidence. None is a second copy of the product contract.
README, the reading guide and repository instructions link the contract.

## Alternatives And Consequences

Rejected another index of every historical document: it still makes readers
reconstruct current intent. Rejected replacing ADR history or treating every
proposal as accepted. This small maintained summary reduces repeated decisions,
but requires updates when the user changes direction. It grants no runtime,
live-call, release, merge or deployment authority.
