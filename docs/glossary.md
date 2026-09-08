# ADE Glossary

| Term | Meaning |
| --- | --- |
| ADE Web | The Next.js browser application in `apps/ade-web`. |
| ADE API | The single FastAPI product backend in `services/ade-api`. |
| Model Router | The OpenAI-compatible provider boundary that owns source discovery, model identity, profiles, and forwarding. |
| Agent Studio | The `/api/v3` product feature for persistent agent conversations and inspectable runs. |
| Agent definition | An immutable prompt, persona, deployment, tool, and policy snapshot reusable across subjects. |
| Memory subject | The explicit owner of typed durable facts. Model arguments cannot choose a subject. |
| Conversation | A binding of one definition to one subject with immutable messages and versioned summaries. |
| Memory fact | A typed, versioned durable fact with source-message provenance. |
| Memory revision | An auditable add, correct, merge, or forget operation on a fact. |
| Run | One asynchronous conversation turn, its attempts, cancellation state, and normalized events. |
| Evaluation session | An isolated `purpose=evaluation` resource bundle with safe, idempotent cleanup. |
| Model key | The canonical Model Router identifier selected by ADE features. |
| Model profile | Reviewed capability and sampling defaults for a model key. |
| Release ledger | Reviewed evidence binding runtime identity, policies, aliases, bundle, qualification, and approval. |
| Content | Reviewed product material under `content/`: prompts, personas, schemas, and reports. |
| Workflow | A self-contained eval, qualification, probe, or smoke check with inputs, config, artifacts, docs, and tests. |
| Artifact | A generated CSV, JSONL, summary, log, or other run-owned workflow output. |
