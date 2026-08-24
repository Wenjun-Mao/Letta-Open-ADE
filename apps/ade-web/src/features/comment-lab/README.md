# Comment Lab

Stateless comment-generation workspace with independent model, prompt, persona, sampling, timeout, and retry controls.

- Entry route: `/comment-lab`
- API client and response contract: `api.ts`
- Page composition: `page.tsx`
- Option loading, request execution, and result state: `use-comment-lab.ts`
- Request validation and payload contract: `generation-request.ts` with `generation-request.test.ts`
- Feature-local view panels: `panels.tsx`

Keep UI composition in `page.tsx`; change request validation or payloads through the tested request builder.
