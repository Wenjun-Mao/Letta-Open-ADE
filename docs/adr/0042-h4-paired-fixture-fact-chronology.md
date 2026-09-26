# ADR 0042: Source-Time Fact Order for Paired H4 Fixtures

Status: Accepted for offline H4 evaluation control, 2026-09-26. No live replay authorized.

## Problem

The separately recorded H4 remaining campaign stopped when two equivalent `invalidated_ended` setups assigned opposite `F1`/`F2` reviewer handles. Each arm seeded multiple facts in one PostgreSQL transaction without `created_at`; PostgreSQL gave those rows the same transaction timestamp. The existing repository reads facts by `(created_at, id)`, so random UUID order decided their model-facing sequence. The fixture failed to hold the paired base state constant. Both immutable manifests and the mismatched packets remain evidence.

## Decision

The H4 fact seeder sets each fact's `created_at` from the assistant completion time of its first source-linked transition. A microsecond offset by the fixture's fact-list position resolves a genuine same-source-time tie. This preserves source chronology, yields reproducible order for equivalent independently seeded arms, and leaves fact IDs random and distinct. The timestamp is an evaluation fixture field; revision source times, target status, provenance, and runtime binding rules are unchanged.

The production binding map continues to assign request-local `F/E` handles in the fact order it reads. No reviewed contract requires semantic handles to retain the same number across independent subjects or stores. Two same-label entities or same-type facts may have distinct IDs and versions, so sorting by a guessed semantic identity could change the product contract or conflate records.

## Alternatives, consequences, and guardrails

Changing production target sorting was rejected for this incident because the pairing instability begins in synthetic seed timestamps. Sorting only the comparison artifacts was rejected because it would hide a real model-facing packet difference. Reusing identical fact IDs in both arms was rejected because both subjects coexist in one database and IDs identify distinct records.

A PostgreSQL fake-provider regression replays all 11 paired setups through native generation and reviewer serializers, then compares the existing base packets exactly after only the established `H`, candidate, and fixture-ID exclusions. It runs with deliberately opposite fact UUID orders and with random UUIDs; reads the persisted fact order; and covers inactive, forgotten, related-entity, and source-time tie cases. Fake embedding vectors vary deterministically by input to avoid a test-only all-vector similarity tie. A future real-provider equality gate must still stop on a mismatched packet; this decision does not certify future provider ranking ties or repair the failed live pair.

This full native fake-provider pass can run before any real dispatch and catch a deterministic fixture or serializer mismatch. The current live runner seeds and executes one arm at a time; a setup-only check before its first provider call would require both arms to be staged first. Such a check could compare persisted fact order, but the exact real generation packet also depends on provider embedding/ranking and cannot be certified before those results exist. The existing captured-packet equality gate therefore remains necessary. No live scheduling refactor is included here.
