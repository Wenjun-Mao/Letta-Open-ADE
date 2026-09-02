# ADE Glossary

## Product And Services

| Term | Meaning |
| --- | --- |
| ADE | Letta Open ADE, the local-first environment for building and evaluating agent experiences. |
| ADE Web | The Next.js browser application at `apps/ade-web`; the only user-facing web service. |
| ADE API | The FastAPI product API at `services/ade-api`; it owns feature workflows and orchestration. |
| Model Router | The OpenAI-compatible service at `services/model-router`; it owns provider access, model discovery, and profiles. |
| Letta | The retained v2 runtime used only by Phase 5 product areas and the Agent Studio release-level rollback lane after native cutover. |
| Memory subject | The explicit owner of ADE-native durable user facts; subjects can be shared deliberately across conversations but never selected by model arguments. |
| Native agent runtime v3 | The ADE-owned Agent Studio API/worker runtime with PostgreSQL state, typed memory, curated tools, and evidence-gated release activation. |
| Feature | A product capability with one owner, such as Agent Studio or Comment Lab. |
| Platform | ADE API composition concerns: application setup, settings, auth, lifecycle, and dependency injection. It is not a feature. |
| Integration | An adapter for an external protocol or service, such as Letta or Model Router. |

## Model Terms

| Term | Meaning |
| --- | --- |
| Model source | A configured provider endpoint known to Model Router, for example a local server or cloud provider. |
| Model handle | The stable ADE selection identifier for a discovered model, including its source when necessary. |
| Model profile | Reviewed model behavior metadata, such as supported sampling parameters or thinking defaults. |
| Model catalog | The normalized model-and-capability view Model Router exposes and ADE API presents to features. |
| Provider request | The one upstream request Model Router sends to a selected provider. |
| Retry owner | The feature request policy that decides whether an end-user operation retries. Model Router does not hide feature retries. |

## Product Content

| Term | Meaning |
| --- | --- |
| System prompt | Scenario-specific instructions supplied to an LLM or agent. |
| Persona | Reusable behavioral and voice instructions selected with a prompt. |
| Label schema | A JSON schema defining structured extraction output for Label Lab. |
| Custom tool | Reviewed tool source that an agent can invoke. |
| Content | Versioned, human-edited product assets under `content/`; it contains no application code. |
| Runtime projection | Generated local state derived from content, such as a SQLite persona store. It is not the source of truth. |

## Agent And Workflow Terms

| Term | Meaning |
| --- | --- |
| Agent Studio | The ADE feature for operating reusable agent definitions, explicit memory subjects, persistent conversations, and inspectable native runs. |
| Persistent state | Immutable conversation history plus versioned summaries and typed subject memory retained in ADE PostgreSQL. |
| Agent definition | An immutable v3 prompt, persona, tools, and exact deployment snapshot reusable across memory subjects. |
| Memory subject | The explicit v3 identity whose typed durable facts are isolated from other subjects and agents. |
| Conversation | A v3 binding between one agent-definition version and one memory subject, with immutable messages. |
| Run | One asynchronous v3 turn execution with attempts, cancellation state, qualification state, and normalized events. |
| Tool Probe | An Agent Studio operation that invokes or validates a configured tool through the runtime path. |
| Test Center | The ADE feature for launching maintained checks and viewing their artifacts. |
| Workflow | A self-contained eval, probe, or smoke check with runner, config, inputs, outputs, docs, and tests. |
| Artifact | A generated workflow result such as CSV, JSONL, summary JSON, or logs. |

## Contract And Operations Terms

| Term | Meaning |
| --- | --- |
| Same-origin proxy | ADE Web server route that forwards browser requests to ADE API and keeps the API credential server-side. |
| Public contract | A documented HTTP or package interface another component may use. |
| Internal module | A feature implementation detail that other features must not import directly. |
| Vertical slice | One complete feature change including UI, API, tests, docs, and removal of its replaced implementation. |
| No compatibility alias | The architecture rule that replaced names, paths, environment variables, and API routes are removed rather than maintained in parallel. |
