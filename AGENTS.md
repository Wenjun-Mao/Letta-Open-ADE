# Product Agreements

For product-affecting work, consult `docs/product-contract.md` before proposing
behavior or reopening a decision. Plans and reviews should cite relevant PC IDs.
Keep current intent separate from implementation and verification status. Update
the contract when the user changes direction; preserve historical ADRs/findings
and explicitly supersede conflicting requirements. Do not treat an old plan as
authority to revive a removed feature. See `docs/development-conventions.md` for
coding and verification conventions. Read only documents relevant to the task.

## Working Branch

Continue development on `main` in the primary checkout. Do not resume the old
character-continuity branch or create a new development worktree unless the user
requests it. Existing trial worktrees may remain as operational dependencies;
merging source does not authorize redeployment. See ADR 0048.

Commits and normal pushes to the configured upstream are pre-approved defaults
after each completed, verified iteration. Commit and push the iteration's scoped
changes without asking again; do not include unrelated work or private evidence.
This does not authorize force-pushes, deployment, live provider experiments or
external-account use. See ADR 0048 for the publication guardrails.
