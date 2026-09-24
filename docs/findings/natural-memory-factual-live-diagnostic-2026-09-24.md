# Natural factual-continuity diagnostic: bounded live stop

Status: first run stopped before generation on infrastructure; one newly bound
continuation reached five native turns and stopped on a reviewer lifecycle
error. The user authorized this small live
diagnostic after the reviewer/ADE responsibility amendment. Its eleven-turn
schedule and complete-delta expectations were frozen in
`workflows/evals/character_memory_dev/fixtures/natural_memory/factual_live_diagnostic.json`
before dispatch. This is a partial diagnostic, not a policy selection.

The director reviewed the first stopped evidence and independently passed the
alias regression, then directed one fresh disposable run under the user's
existing `go`. That was an operational continuation after a pre-generation
harness failure, not a new explicit user approval for rerolls or a broader
campaign. The original failed attempt remains unchanged and is counted
separately below.

## Exact binding and observed requests

The attempted source was `b22fad9b8a6411f904eb5bc3a8418cf039541647`,
fingerprint `cf64fae94761a403855ed11c41f6f951033852838b3c49ea1e5ef02da9047947`.
The schedule SHA-256 was `db71c625fa9d3ba7047fcb5faf9a3e803df591afa6fe4d405d12b4c900b1ec3a`.
The held context was `natural-user-assertions-v4-b`; reviewer input limit 6,759,
output allowance 4,096, no reviewer repair, turn retry count zero. The DeepSeek
Flash route retained its high-thinking profile and catalog fingerprint
`870ff4fb8a25a9c2016f67dcda05e26e82a6c5dea6ad55781a80be2201161cfe`.
The Spark Qwen embedding fingerprint was
`0f16a45a659a9e5708e1705e750a27ce350c93c8caea1edb01b34d39fff3789f`.
The reviewer instruction/schema hashes in the private manifest identify the
exact wire contract. No release-policy fingerprint was rebound or waived.

The first router preflight output (`natural-factual-live-20260924-01a0d5b7`)
stopped before any model dispatch: an IP-form Spark URL did not match the
pinned catalog URL. A local DNS bridge restored the exact `dgx-spark` URL, and
both pinned deployments appeared in the catalog. The second output
(`natural-factual-live-20260924-01a0d5b7-v2`) began the first native turn.
Observed dispatches: **zero DeepSeek generation**, **one Spark embedding
attempt, zero completed, one failed**. The worker event log separately shows
a completed router catalog observation and the failed `retrieval_query`
embedding request. The native run failed with `http_502` after one attempt.

## Root cause and database delta

The isolated router could discover Spark synchronously, while async HTTPX
could not resolve `dgx-spark`. Its resolver supplied the hostname as bytes;
the diagnostic host's local alias bridge matched only a string. The failed
embedding capture, router `upstream_unreachable` path, and a separate async
catalog GET that reproduced the name-resolution error support this diagnosis.
The bridge now handles both forms; a unit test covers them, and an async GET
to the pinned `/models` route returned HTTP 200. This correction is confined
to the local diagnostic host. It preserves the deployment's pinned URL and
does not alter ADE product semantics or provider selection.

Independent PostgreSQL readback of the retained disposable database
`ade_m2_memory_test_01a0d5b7` found one accepted user message, one failed
run/attempt, **zero assistant messages, facts, revisions or embeddings**, and
subject memory generation **1**. The subject's one implicit entity existed at
session setup; the failed turn added no entity. The native attempt artifact marks generation,
candidate reply and reviewer stages absent, and the candidate undelivered.
Thus no source citation or factual lineage was created. The remaining ten
predeclared turns were unrun. There are no useful reply excerpts to assess;
the browser success check could not apply. No semantic result, recall claim,
habit/preference judgment, or failure-rate estimate follows from this stop.

Private, mode-restricted captures are retained under
`workflows/evals/character_memory_dev/outputs/natural-factual-live-20260924-01a0d5b7-v2/`.
The manifest SHA-256 is
`dc2fba6d0e5c9b66fc194c3d823a40b5fb0a67a60cf77f16e7b15db0f8955ad7`;
attempt SHA-256 is
`36428ae1fe1a2d75b2793873cc8075ba1d8c0955c55006b6fbeb1dddf07730f7`;
failed dispatch capture SHA-256 is
`290fbc242a4002891380b241aadc6f523c52999aad210ccb3e1e53c11357532d`.
The router and worker stopped after capture. The database and ignored evidence
were retained for audit.

## Newly bound continuation: five turns

The fresh database `ade_m2_memory_test_01a0d5b8` was migrated to
`20260924_0008`; the async pinned Spark catalog returned HTTP 200 before the
run. Its output is the separate private directory
`workflows/evals/character_memory_dev/outputs/natural-factual-live-20260924-01a0d5b8/`.
The exact source was `0f919fc11fe43cb67286cc1a56be42b3af483307` with
the same source fingerprint, frozen schedule hash, v4 B policy, 6,759/4,096
reviewer envelope, DeepSeek high-thinking and route fingerprints listed above.
Each of five native runs had one attempt and `retry_count=0`. The observational
counters are complete: **10 DeepSeek generation dispatches, all completed;
8 Spark embedding dispatches, all completed**. These are local dispatch counts,
not a claim about upstream internal retries. Combined with the earlier failed
run, this work observed **10 completed generation dispatches and 9 embedding
attempts (8 completed, 1 failed)**, reported as two separate bindings.

| Frozen turn | Expected complete delta | Observed outcome |
| --- | --- | --- |
| Changed morning preference 1 | Add one morning-coffee preference v1; generation +1 | One active `person.preference` drink fact, `咖啡（早上，尤其是刚起床的时候）`, v1; generation 1→2. Exact current-user citation. Reply engaged the coffee topic. |
| Changed morning preference 2 | Revise that fact to morning tea v2; generation +1; retain v1 | Same fact revised to `茶（早上）`, v2, reason `supersede`; generation 2→3. v1 retained with predecessor link and exact current-user citation. Reply acknowledged the change. |
| Changed morning preference 3, new conversation | No delta; answer morning tea | No fact/revision/entity change; generation stayed 3. Visible reply: `你早上更喜欢喝茶呀。` This is a successful same-subject cross-conversation recall observation. |
| Distinct evening preference 1, independent subject | Add morning-coffee preference v1; generation +1 | One active `person.preference` drink fact, value `早上喝咖啡`, v1; generation 1→2. The source explicitly says `更喜欢`, so the abbreviated value under the preference type is not evidence that the reviewer confused a habit with a preference. |
| Distinct evening preference 2 | Keep morning fact; add evening-tea preference v1; generation +1 | **Rejected atomically.** Generation stayed 2, morning fact stayed v1, and no evening fact, revision, assistant message or write embedding was committed. |

The fifth candidate reply said `早上一杯咖啡，晚上一盏茶` and would have answered
the dialogue, but it was **not delivered**. The reviewer emitted two decisions:
`subject_add` with value `晚上喝茶`, then `reassert` targeting F1 with value
`早上喝咖啡`. F1 was already active, so the existing lifecycle contract
`Reassert requires an inactive target` rejected the entire review with
`natural_review_semantic`. The current user's `早上还是咖啡` required no change
to F1. The reviewer overmutated that stable fact. The source also explicitly
says `晚上我更喜欢喝茶`; its proposed value `晚上喝茶` is abbreviated wording under
`person.preference`, not proof of a habit-to-preference inference. ADE's
atomic rejection worked as designed.

Independent PostgreSQL readback found subject generations **3** and **2**;
five user messages, four assistant messages, two active facts, three revisions
(`add`, `supersede`, `add`), one predecessor link, three exact current-user
source quotes with `user_assertion` role and same-run message linkage, and
three write embeddings. The failed fifth run has one failed attempt,
`runtime_validation_error` / `natural_review_semantic`, no assistant message
and no revision. Four of eleven scheduled turns committed; the fifth was
rejected; **six turns were unrun**, including evening recall, uncertainty,
habit-only behavior and other-subject non-transfer. Thus the diagnostic gives
one positive recall observation and cannot assess those other claims or a
failure rate. It cannot qualify the context policy or release.

The continuation manifest SHA-256 is
`76541546bbe7be10dd23cdab1108429517c0de5ec98a2d320b1ca7d908f9781e`;
the failed fifth attempt SHA-256 is
`436cedeef6fc39aadab54232d2a745998fabcdddc6474911c3cf574c7439180a`.
Raw requests, decisions, replies, events and full readback remain private in
that directory. A representative built-in-browser check was attempted with an
isolated API and web server. Agent Studio's ordinary list omits
evaluation-purpose sessions, so the successful conversation could not be
shown through that UI; direct API/resource and database readback supplied the
evidence above. Those isolated services were stopped, and dev-server-generated
working-tree files were removed.

## Offline root-cause review and contract clarification

The director's follow-up checked the **actual failed reviewer request**, not
only the source prompt. Its user packet offered F1 with `status: active` and
value `早上喝咖啡`. The DeepSeek system text included the full generated JSON
schema, but neither it nor the operation fields said that `reassert` requires
an inactive target. The system text also omitted the rule that an unchanged
active fact receives no decision when another fact changes. The existing ADE
validator did enforce `Reassert requires an inactive target`. Therefore the
precise failure is an **incomplete model-facing lifecycle contract** at this
prompt/schema layer, followed by a reviewer decision that violated ADE's
held target-state rule. The evidence does not show the model ignoring a
clearly communicated lifecycle precondition. It does not justify weakening
the validator, dropping the invalid sibling, or relabeling preference facts.

The offline correction adds general lifecycle descriptions to the existing
reviewer instructions and `kind` schema fields: revise/end require active,
reassert requires inactive, forget allows active/inactive on explicit removal,
and a confirmation of an unchanged active fact emits no mutation. No output
shape, fact ontology, binder, validator or persistence semantics changed.
The historical live request and captures above remain immutable. On the exact
failed case's retained user packet, substituting only the clarified system
text raises the visible serialized request estimate from **3,564 to 3,802**
tokens, below its **6,759** input limit; no provider call was made. Focused
request tests assert the preconditions appear in the real serialized DeepSeek
system/schema. A separate fake-decision PostgreSQL test confirms that an
evening add paired with active F1 reassertion still leaves the baseline fact,
revision count and generation unchanged in both decision orders.

Smallest proposed follow-up, **not run**: use a new source/config binding and
fresh disposable subjects for eight turns covering the seven failed or unrun
checks plus required independent setup—
morning-coffee setup, evening-tea addition and cross-conversation recall;
another setup, uncertain tea, drinking-habit-only statement and recall; then
one other-subject no-transfer query. Use the already frozen texts and complete
delta expectations, one native attempt per turn, and the same early-stop
rule. The four committed turns above need no reroll. A further live diagnostic
requires a new bounded decision. The 30-cell campaign and release gate remain
separate.
