# Prompt Center

Workspace for system-prompt and persona template CRUD, lifecycle actions, and catalog metadata.

- Entry route: `/prompt-center`
- API client and prompt contracts: `api.ts`
- `page.tsx` composes the workspace without owning lifecycle logic.
- `use-prompt-center.ts` owns template loading, deep-link selection, drafts, and lifecycle actions.
- `panels.tsx` contains the toolbar, list, and editor presentation.
- Keep prompt-key, incoming selection, and workspace-link rules in `helpers.ts` with focused tests.
