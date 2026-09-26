# H4/H5 independent Pro review packet

This is a synthetic, deidentified evidence packet for one independent ChatGPT Pro consultation. It is a documentation-only extraction from three local H4 capture batches. The raw manifests, provider captures, answer keys, and human score fields remain outside this packet. The packet does not constitute human acceptance or production qualification.

## Reading order

1. `01-answer-trajectories.json`: source exchanges, pending user turns, and exact candidate and delivered answers under anonymous labels. Assess answers before looking at mutations or contract notes.
2. `02-scope-lifecycle.json`: arm-neutral source scope and saved-fact lifecycle, including what source dialogue is eligible by scope. This is the existing companion copied without alteration.
3. `03-expected-observed-deltas.json`: frozen fixture expectations beside deidentified committed mutation readback and stage source IDs. Its comparator flags check literal operation, value, source quote, and counts; they are not semantic verdicts.
4. `04-contract-notes.md`: bounded implementation contract excerpts for a second-pass assessment.
5. `pro-prompt.md`: one paste-ready consultation request, with publication placeholders.

## Comparability and limits

The nine matched target pairs are `archived_version_recall`, `correction_return`, `extraction_repair`, `removed_acknowledgment`, `h_only_referent`, `habit_not_preference`, `resolved_concern`, `ambiguity_and_unrelated`, and `isolation`. Three of these also have paired follow-up turns: `removed_acknowledgment`, `h_only_referent`, and `ambiguity_and_unrelated`. A follow-up depends on its own preceding target turn, so do not treat its outcome as an independent sample.

`invalidated_ended` has two delivered answers, but the base packets differed because fixture fact ordering differed. It is a confounded comparison. `user_retraction` has one delivered answer only: the other label's first attempt was boundedly rejected and has no answer to score. Neither belongs in a nine-pair aggregate.

The packet describes observed turns, not a representative population. All characters and exchanges are synthetic. A source marked eligible by scope was not necessarily retrieved or admitted; the per-label stage arrays in file 03 state what actually entered each captured turn. `target_turn` there means the preceding captured turn in the same trajectory. Anonymous labels are preserved, but outcome details may make the intervention guessable. No arm key is included.

## Provenance

`source-hashes.json` records SHA-256 hashes of the three ignored blind packets, their ignored manifests, the fixture, and the untouched scope/lifecycle companion. The three capture batches contain 32 planned turns: 31 committed and one bounded rejection. The answer packet contains 11 cases and 14 case-turn trajectories, with 27 delivered answers. The final batch's 18 committed turns had complete, hash-matched capture and independent readback in the private H5 stage audit; earlier batch audits also exist. These audit files remain private. Source code excerpts in file 04 were checked against retained implementation revision `8505fc656ec0a5c2a6c02dd0c074a59a3c72708d`; that revision is not part of this documentation-only branch.

For publication, use the exact immutable commit of this documentation-only branch. Do not substitute the unreviewed implementation branch or a changing branch URL. No consultation has been dispatched from this packet.
