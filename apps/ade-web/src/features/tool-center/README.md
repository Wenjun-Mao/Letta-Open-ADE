# Tool Center

Workspace for managed custom-tool discovery, source editing, and lifecycle operations.

- Entry route: `/tool-center`
- API client and tool contract: `api.ts`
- `page.tsx` composes the workspace without owning lifecycle logic.
- `use-tool-center.ts` owns filters, source loading, drafts, and lifecycle actions.
- `panels.tsx` contains the toolbar, list, and editor presentation.
- Keep identifier, tag parsing, and editability rules in `helpers.ts` with focused tests.
- Agent Studio owns runtime attachment and probing because those are agent actions.
