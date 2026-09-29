# ADR 0046: Current-Turn-Weighted Trial History Ranking

Status: Accepted for the isolated development trial after manager review,
2026-09-29. Production default, H2 fixtures and prior captures remain unchanged.
Relevant product agreements: PC-01/02/03/05/09/10.

## Problem

The hands-on trial admitted a prior woodworking exchange on one separate-chat
question and missed it on a later question from the same subject and character.
The later accepted snapshot contained the source and prior successful answer.
The local suffix contained two city/music exchanges; the frozen Qwen query
embedded the current question and that longer suffix as one JSON string. An
as-of replay of the pinned recipe placed the two relevant exchanges at ranks 7
and 8, outside the top four. Without that suffix they ranked 1 and 2. The
retained admission IDs match the replay's top four, so the failure belongs to
ranking query composition, before admission or generation. The original
provider scores were not retained; the replay is diagnostic evidence, not an
exact transcript of the original vector response.

## Decision

Add `probe_local_qwen_cosine_v2` for the isolated history-trial worker. It embeds
the unchanged historical documents and, when a local suffix exists, two queries:
the current user message alone and the former current-plus-suffix JSON. Each
exchange receives `0.7 × current-only cosine + 0.3 × contextual cosine`. With
no suffix, it sends the same one query and uses its cosine directly. Both query
inputs travel in one guarded Qwen dispatch, so the source authorization and
two-dispatch attempt boundary remain. The v2 recipe identity includes its query
format and score composition. Its query hash covers both ordered query strings.

The prior `probe_local_qwen_cosine` path, synthetic H2 contract, fixtures,
campaigns and captures retain their original meaning. The new recipe is a
trial-only selection. Its reviewed rebuild at `2026-09-29 20:36:09 UTC` is
recorded in the [finding](../findings/natural-memory-consultation/woodworking-history-ranking-diagnostic-2026-09-29.md#isolated-hands-on-trial-adoption).
Scope, archive eligibility, top-four admission, reviewer, saved-fact search,
timeouts and provider routes are unchanged.

## Tradeoffs and guardrails

A current-only query would lose context needed for genuine anaphora. Enlarging
top four would admit more unrelated history and consume packet capacity while
leaving the query error intact. Topic keywords or a phrase classifier would
create a semantic special case. The fixed blend keeps a contextual channel
without allowing a long unrelated suffix to dictate the whole ranking.

This weight is an empirical trial choice, not a general reliability claim.
The source-bound replay recovers the missed exchange, while a separate small
synthetic anaphoric probe retains both required exchanges; neither establishes
performance across languages, long histories or temporal conflicts. Focused
tests assert v1 preservation, v2 query inputs and weighting, contextual
references, empty suffix, dispatch counts, recipe identity and source guards.
One disposable native turn admitted both woodworking sources, delivered the
supported stool answer and made no memory changes. Its exact scope and limits
are in the [finding](../findings/natural-memory-consultation/woodworking-history-ranking-diagnostic-2026-09-29.md).
Original conversations remain untouched.
