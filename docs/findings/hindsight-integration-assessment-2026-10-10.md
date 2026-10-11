# Hindsight Integration Assessment

Date: 2026-10-10. Status: source-backed assessment complete; recommendations
await review. Hindsight is the concrete integration target, not an adopted or
qualified runtime. This iteration changes documentation only.

Review follow-up, 2026-10-10: the [returned-report assessment](hindsight-consultation/assessment.md)
revises the recommended sequence below: leave incumbent execution unchanged and
test a disposable Hindsight-to-Character slice before broad isolation. It also
checks native extraction labels omitted from this assessment's scoping discussion.
Sections 4 and 6 retain the original proposal, not the latest recommendation.
No experiment, source isolation or adoption is authorized by either assessment.

## Authority And Baselines

The user requested a Hindsight-first assessment and proposed isolating/freezing
the incumbent Memory domain. Working expectations are to submit user input to
Hindsight for extraction and have an ADE-side adapter construct Character's
final model request. Ingestion timing, assistant-message inclusion, bank layout,
storage consistency and refactoring scope remain design recommendations below.

- ADE: primary `main`, clean at `d94913dd22e4208e0f6092d0144cc5acbcb49606`.
- Hindsight: [v0.10.3][release], released 2026-10-08; annotated tag resolves to
  commit `eb6df499d35300e5b2f3f029b2e6adda04ed90f8`. Public release metadata,
  pinned source, client models and bundled documentation were inspected.
- The earlier [M2 finding](m2-memory-approach-comparison.md) concerns v0.10.1
  and remains historical. Neither it nor this assessment establishes a measured
  quality winner. Moving website documentation is not the version authority.
- Applicable agreements: PC-01/06/12 for natural interaction and Character;
  PC-02/03/04/10/11 for scope and continuity; PC-05/07 for updates and outcomes;
  PC-08/09 for persistence, model access and runtime ownership.
- No Hindsight package installation, server/container startup, database access,
  private-data export, provider call, migration, deployment or live trial occurred.
  Public upstream source was downloaded into temporary storage for inspection.

For Character, use **relevant memories and their context**, not an adjudication
packet. Categories and time help interpretation; they do not make Character a
judge. Source evidence remains useful for ingestion diagnostics and inspection.

## Assessment Summary

**Proceed toward a bounded Hindsight integration, not a new generic Memory SDK.**
Reuse its extraction, categories, temporal retrieval and consolidation. Preserve
ADE's product semantics rather than requiring Hindsight to imitate every native
fact table, reviewer output or index. Its native interfaces remove much of the
design work, but do not automatically determine ADE identity or turn semantics.

| User expectation | Assessment | ADE work that remains |
| --- | --- | --- |
| Multi-user/multi-agent support answers ownership | Supported mechanisms: banks, tenant extensions, strict tag scopes and server-side operation hooks. | Bind existing workspace/subject/character identities to them; preserve shared profile versus private relationship semantics. |
| Each user input goes to Hindsight | Compatible with `retain`; Hindsight performs extraction and storage. | Submit accepted messages with role/time/context, make delivery durable, and distinguish submitted from processed. |
| Adapter constructs the final Character request | Recommended as an ADE-owned composition responsibility. | Combine persona, dialogue, memories and enabled tools, serialize for the selected provider, check the whole request on every loop step. |
| Isolate/freeze existing Memory before replacement | Recommended as a bounded baseline and seam-preparation effort. | Freeze incumbent behavior, not its implementation as a universal contract; avoid a directory-wide rewrite or premature removal. |

## 1. Whose Memory: Use Native Scoping

Hindsight banks are independent recall containers, not separate databases per
agent. Tenant extensions provide another level of isolation/authentication.
The bundled default is single-tenant with no authentication; the built-in
API-key extension authenticates one configured schema. The repository also
ships a static-key multi-tenant extension with a schema per configured user.
These are real capabilities, but they require configuration, not merely a
`user_id` somewhere in a prompt. [Bank docs][banks], [tenant source][tenant],
[static-key extension][static-tenant].

v0.10.3 also exposes `resolve_tag_scope` and `resolve_write_tag_scope` hooks.
They can enforce shared/private visibility on reads, writes and source access;
read permission need not imply write permission. Using these hooks requires an
integration-specific identity mapping. Defaults do not enforce that mapping.
See [extension contract][extensions].

| ADE identity/behavior | Mapping constraint |
| --- | --- |
| Workspace and subject | Different subjects must remain isolated (PC-02). The model must not select arbitrary bank IDs. |
| Definition root | Distinguishes characters and their relationship histories (PC-03/11). A persona version is not a new character. |
| Conversation and persona version | Source metadata, not new continuity banks on every chat/edit (PC-04/10). |
| Shared profile facts | Remain usable by other characters for that subject, without transferring participation in private exchanges (PC-02/03). |
| Archive | Changes UI visibility, not eligibility or bank identity (PC-10). |

Two layouts are viable; neither is silently selected by the API:

1. **Separate relationship banks plus a shared profile bank.** Relationship bank
   identity is workspace + subject + character root. Strong default separation;
   ADE recalls from the permitted relationship and profile banks and merges their
   results. The shared-profile extraction route needs a narrow Hindsight mission
   and testing; do not dump every private dialogue into globally shared context.
   This can add extraction calls and duplicate some information across banks.
2. **One bank per workspace/subject with character/shared scopes.** Reuses strict
   tag filters and, if needed, server-side scope hooks. Fewer banks and easier
   within-bank sharing, but ingestion tags, derived observations, source chunks
   and background consolidation all need consistent scope. Tags alone are not
   automatically an authorization policy.

Recommendation: start the isolation design from option 1; assess option 2 if its
native scoping materially simplifies shared-profile handling. Do not introduce
a second ADE semantic reviewer just to divide records between banks. If native
configuration cannot preserve PC-02/03, surface that gap instead of hiding it.
`world` versus `experience` is a perspective category, not ADE's authorization
or profile-sharing rule. [Retain categorization][retain-model].

Important native behavior: non-strict tag matching includes untagged results;
an empty filter normally removes filtering even with a strict mode. Observation
scopes also affect what is consolidated together. Do not use a global/shared
observation scope over character-private content and assume later filtering
will undo the mixture. [Recall contract][recall], [retain contract][retain].

## 2. When And What To Retain

**Submit every accepted user input; let Hindsight decide what is worth retaining.**
Submission is not a promise that every input becomes a memory. Preserve the
user's original text rather than pre-extracting native ADE facts for Hindsight.
Hindsight documents conversation ingestion with speakers and timestamps, plus
document replacement and append modes. [Retain contract][retain].

Bare messages are insufficient for referential replies such as "yes, that one".
Proposed source unit: an ordered, attributed conversation document, updated as
messages commit. The current user input enters it at acceptance; only committed
Character replies enter it later. Include stable source IDs and sequence, role,
time, subject, character root and definition version. Exclude uncommitted reply
candidates and retries that merely reproduce an already accepted message.

**User-only ingestion does not cover the agreed product.** PC-03 shared exchanges
and PC-11 improvised character history also depend on what Character actually
said. Recommend retaining committed replies with explicit speaker attribution.
That preserves the record of an utterance; it does not automatically establish
that a joke, hypothetical, or unsupported claim is a true shared experience.
PC-11 story-admission behavior still needs a focused semantic check, not a new
hand-written episode schema in advance.

Proposed delivery model, not implemented:

```text
ADE commits accepted user message + durable ingestion event
  -> Hindsight retain -> processed / failed status tracked by ADE
ADE commits final Character reply + next ingestion event
  -> ordered conversation update -> Hindsight retain
```

An ADE outbox/ingestion worker is a justified delivery mechanism here, not a
second memory engine: it delivers source text and tracks progress, without
interpreting facts. It is not yet authorized or present. Recommendations:

- Do not put the Hindsight network call inside ADE's SQL transaction. Retain has
  its own persistence authority; even shared PostgreSQL hosting does not make
  the two operations one transaction.
- Keep every accepted user message eligible even if reply generation later
  fails. There is then no assistant source for that failed run. This changes
  today's success-only derived-memory timing and needs explicit adoption.
- Decouple initial reply generation from retain completion: Character already
  receives the current input. Track ingestion lag and define next-chat/read-
  after-write behavior before claiming immediate cross-chat recall.
- Use stable document identity and ordered revisions; choose append versus
  replacement in the pilot. Prevent delayed retries from overwriting newer
  content. Do not assume append plus an application retry is exactly-once.
- For async retain, bind an immutable payload hash to the caller-generated
  `operation_id` and reuse that pair after a lost acknowledgement. Upstream
  replay checks bank/type, not equality of the new content with the original
  payload. A genuinely new revision needs a new operation ID. [Engine source][engine].
- A queued receipt is not extraction completion, and completion is not semantic
  correctness. Inspect extraction error metadata; consider
  `HINDSIGHT_API_FAIL_ON_EXTRACTION_ERRORS=true` for the trial. It exposes partial
  extraction failures, not a guarantee that failed work rolled back. [Configuration][config].

## 3. What Reaches Character

The ADE-side **Character request adapter/composer** should own the final model
request. Its Hindsight connector supplies memories; it does not own persona
authoring, model selection or the conversation loop. These can be small cohesive
modules, not a plug-in framework or a separate service per responsibility.

```text
Bound persona + ADE requirements + current/local dialogue
                         + Hindsight recall results
                         + permitted tool definitions/results
  -> ADE Character request composer -> Model Router -> Character step
  -> reply candidate OR recall request -> ADE-controlled continuation
```

Use recall result text, category, people and relevant dates as conversational
context. Keep IDs, source references and diagnostics available where needed;
do not dump all scores and tracing fields into every Character prompt.
Treat retrieved text as past information, not new system instructions. An
unavailable call must remain distinguishable from no relevant memory.

Hindsight's `max_tokens` is not a complete request-capacity guarantee: metadata
and optional source material have separate costs, and an oversized first fact
can be returned whole. The composer must bound the actual serialized request,
including persona, dialogue, tools and follow-ups. `query_timestamp` anchors
relative time; `temporal_window` influences ranking rather than excluding every
out-of-window result. Neither creates an ADE accepted-generation snapshot.
[Recall contract][recall], [client result model][recall-model].

Begin the proposed integration with retain/recall. Evaluate reflect only for a
demonstrated memory-synthesis need; do not add it as a mandatory Character phase.
Character still chooses and expresses the reply (PC-12).

## 4. Incumbent Boundary And Freeze Preparation

Root cause of replacement friction: the current native Memory implementation
crosses context construction, model dispatch and the success transaction. It is
not a standalone component that can be replaced by swapping a search callback.
The completed [boundary cleanup](../plans/capability-boundary-cleanup.md) improved
ownership; it explicitly did not create a replacement protocol.

Paths below are under `services/ade-api/src/ade_api/features/agent_runtime/`.

| Existing seam | Source-verified coupling | Proposed treatment |
| --- | --- | --- |
| Accepted input | `run_service.py:134` commits exact user text and captures native memory generation. | Preserve ADE source capture/idempotency; add delivery only in the adoption implementation. |
| Snapshot and recall | `turn_memory_snapshot.py`, `turn_retrieval.py`, `turn_memory_views.py` expose native facts/generation/embedding identity. | Keep behind an explicitly native owner; Hindsight must not impersonate its fact rows. |
| Context selection | `turn_context_selection.py:56` couples Character context to natural-review capacity and lifecycle snapshots. | Separate native-review policy from reusable Character request composition. |
| Optional search | `executor.py:16,318` describes user facts only and wraps results as `facts` with `memory_subject_role=current_user`. | Preserve the incumbent contract until a new binding is adopted; do not mislabel Hindsight character memories as user facts. |
| Final request | `executor.py:142` serializes each request and checks capacity when a limit is supplied. | Keep one final composer/serializer path for initial and tool-follow-up requests; preserve provider continuation fields. |
| Review/index preparation | `turn_execution.py:372` and review/embedding collaborators prepare native operations. | Freeze native policy behavior; the Hindsight path must not run a duplicate reviewer or native embedding pipeline. |
| Finalization | `turn_result.py` requires native review/embedding results; `worker_finalization.py:51` commits memory, reply, summary and success together. | Preserve incumbent atomicity during isolation. Redesign Hindsight delivery separately, not with dummy reviewer results or independent commits hidden in native helpers. |
| Local dialogue compaction | `turn_compaction.py`, `compaction_executor.py`, `compaction.py`. | Keep necessary conversation-window management; Hindsight consolidation is not a replacement for fitting local dialogue. |
| Inspection/removal | `memory_contracts.py`, `memory_removals.py`, presenters and Agent Studio consume native fact/lineage contracts. | Freeze existing views for native data; design truthful Hindsight readback/removal separately rather than fabricating native versions. |

**Freeze recommendation:** name the pinned commit above as the incumbent
behavior baseline; stop new native memory features while preparing the seam.
Allow necessary correctness/security fixes with explicit baseline updates.
Preserve original records, prompts, policy hashes, tests and historical findings.
Use Git history for preservation, not a copied source tree or a new development
worktree. Do not disable current memory or change the running trial.

**Isolation is not yet implemented.** Before source edits, approve one bounded
preparation plan: pull native-specific collaboration behind cohesive owners,
keep the incumbent success transaction intact, and retain exact Character
requests and committed outcomes under fixed fixtures. Reuse current seams;
do not reorganize every file into the capability-map hierarchy. Avoid a generic
`MemoryBackend` registry, remote-transaction abstraction, or permanent dual-write
fallback. Each eventual turn must have one explicit memory implementation.

## 5. Adoption Decisions And Gaps

| Area | Required decision or proof before adoption |
| --- | --- |
| PC-05/08/09 | Explicitly replace the native reviewer/atomic-memory-write assumption for the Hindsight binding. Keep ADE's conversation/run authority, one product API and finite loop; define Hindsight's internal service/storage ownership. |
| PC-02/03/04/10 | Select bank/scope mapping and prove shared profile, private relationship, cross-version and archived-chat behavior. No per-chat reset disguised as isolation. |
| PC-07 removal | Hindsight supports individual edit/invalidate, but reprocessing the source document resets curation. Define operator-removal behavior under subsequent conversation updates; do not silently resurrect removed derived facts or erase ADE history. [Curation docs][memories]. |
| PC-11 stories | Test committed assistant stories, later correction, jokes and incomplete recall with attributed source input. Do not imply that extraction alone solves this policy. |
| Model Router | Hindsight supports custom LLM/embedding base URLs, but wire compatibility is unverified. ADE's DeepSeek adapter rejects `json_schema`; its router has no rerank endpoint. Select provider configuration through fake-contract tests before real calls. |
| Operations | Prefer an isolated self-hosted candidate with its own database/schema/role, pinned image digest and explicit auth. Verify models, reranking, worker recovery, backups and restore. No live ADE database or credentials borrowed implicitly. |
| Existing data | Decide fresh pilot versus a separately authorized backfill from ADE originals. Existing extracted facts alone omit relationship history. No migration or deletion is authorized by this assessment. |
| Failure visibility | Keep conversation success separate from retention progress/failure. Monitor queued, completed, partial and failed ingestion truthfully; never report that Hindsight remembered something from enqueue alone. |

Hosting support is documented for Apple Silicon and PostgreSQL, including slim
and embedded options; it is not local deployment evidence. The HTTP client is
the recommended first boundary rather than importing the engine into ADE's
process. Installation/model choices remain pending. [Installation][installation],
[configuration][config], [ADE router](../../services/model-router/src/model_router/app.py).

## 6. Recommended Next Iteration

1. Review the freeze scope and choose the scope/ingestion policy above. Write
   the concise adoption ADR and bounded preparation plan; explicitly amend
   affected PC requirements instead of overriding them in adapter code.
2. Implement behavior-preserving native isolation and the ADE request-composer
   seam with fixed-input tests. No Hindsight calls or hidden policy change.
3. Add a pinned-client, fake-transport integration slice covering bank binding,
   source delivery, progress readback and initial/follow-up request composition.
4. With separate installation/provider authorization, run a disposable Hindsight
   pilot using synthetic, chronological cases. No existing chat export by default.
5. Review product results and operational recovery before authorizing backfill,
   runtime selection or cutover. Retire replaced code only with a recovery plan;
   no automatic native fallback on a Hindsight failure.

Minimum pilot cases: two simultaneous subjects; two characters sharing only
profile information; same character across chats/version/archive; "yes, that
one" extraction; committed assistant story versus failed candidate; temporal
correction; operator removal followed by re-retain; duplicate/lost-ack and
out-of-order ingestion; extraction/provider failure; oversized recall and tool
continuation. Keep current dialogue available even when memory is delayed.

## Verification And Limits

The following offline incumbent checks ran without Hindsight or providers:

```sh
/opt/homebrew/bin/uv run --locked python -m pytest \
  services/ade-api/tests/agent_runtime/test_executor.py \
  services/ade-api/tests/agent_runtime/test_run_service.py \
  services/ade-api/tests/agent_runtime/test_worker_finalization.py \
  services/ade-api/tests/agent_runtime/test_natural_context.py -q
```

Result: **45 passed in 30.53s**. This establishes only the inspected incumbent's
offline checkpoint, not a Hindsight integration test or fresh SQL/deployment
proof. Hindsight quality, latency, Chinese conversational extraction, actual
scope enforcement, restore behavior and Model Router compatibility are untested.
Eight added local links and twelve pinned upstream paths passed existence
checks; source anchors and `git diff --check` also passed. Runtime, app, content,
configuration and workflow paths have no diff from the incumbent baseline.

## Pinned Upstream References

[release]: https://github.com/vectorize-io/hindsight/releases/tag/v0.10.3
[banks]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/memory-banks.md
[tenant]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/extensions/builtin/tenant.py
[static-tenant]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-extensions/static-keys-tenant/README.md
[extensions]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/extensions.md
[retain-model]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/retain.md
[retain]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/retain.md
[recall]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/recall.md
[recall-model]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-clients/python/hindsight_client_api/models/recall_result.py
[engine]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/engine/memory_engine.py#L22245
[memories]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/memories.md
[installation]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/installation.md
[config]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/configuration.md
