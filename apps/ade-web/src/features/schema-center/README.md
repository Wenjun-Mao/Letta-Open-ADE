# Schema Center

Workspace for Label Lab JSON schema CRUD and archive lifecycle operations.

- Entry route: `/schema-center`
- API client and schema contract: `api.ts`
- `page.tsx` composes the workspace without owning lifecycle logic.
- `use-schema-center.ts` owns schema loading, drafts, and lifecycle actions.
- `panels.tsx` contains the toolbar, list, and editor presentation.
- Keep JSON formatting and validation rules in `helpers.ts` with focused tests.
