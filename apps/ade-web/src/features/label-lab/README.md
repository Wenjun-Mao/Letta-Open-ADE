# Label Lab

Schema-driven extraction workspace for Label Lab requests and provider result presentation.

- Entry route: `/label-lab`
- API client and result contract: `api.ts`
- Catalog dependencies: Prompt Center, Schema Center, and Model Catalog public APIs.
- Page composition: `page.tsx`; feature panels: `panels.tsx`
- Option loading, selection previews, request execution, and result state: `use-label-lab.ts`
- Request validation and payload contract: `generation-request.ts` with `generation-request.test.ts`

Keep UI composition in `page.tsx`; change request validation or payloads through the tested request builder.
