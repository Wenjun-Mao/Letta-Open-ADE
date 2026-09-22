# M2 Luna Development Evidence

Date: 2026-09-22
Status: Development evidence only — M2 remains in progress

## Scope And Lineage

This is a Luna-only, supplied-context development checkpoint for 林小棠. It is
not a live ADE-versus-Hindsight comparison and does not exercise ADE
persistence, embeddings, retrieval, subject filtering, native tool calling, or
release qualification. The checked-in
[run matrix](../../workflows/evals/character_memory_dev/fixtures/m2/luna_matrix.json)
fixes fourteen serial calls: three source-transcript memory reviews, seven
original dialogue probes, and a four-sample preference-intent contrast. It
keeps independent review focus out of the model inputs.

Every dialogue input identifies manually chosen material as
`[source-derived supplied context; not retrieval]`, or intentionally supplies
no memory. The latter is an oracle-conditioned prompt, never evidence that a
fact was forgotten, filtered, or not retrieved. Each case retains its M2
chronological cutoff and isolated case state in the matrix. Raw prompts, events,
stderr, manifests, final text, validation, and result JSON remain ignored under
`workflows/evals/character_memory_dev/outputs/m2-luna-*-20260922/`.

## Run Metadata

All ten planned sessions completed serially. Every capture records
`transport_validated`, valid task JSON, `gpt-5.6-luna`, medium reasoning,
default service tier, a 180-second cap, ChatGPT login, CLI
`0.155.0-alpha.9.2`, exit code zero, and `adapter_retry_count: 0`. No launch
failed or was retried; no fallback, Spark, API-key provider, embedding call,
Hindsight service, credential, or native release operation was used.

| Measure | Observed |
| --- | ---: |
| Generation sessions | 14 of 14 allowed |
| Extraction / dialogue sessions | 3 / 11 |
| Input / cached input tokens | 199,420 / 155,136 |
| Output / reasoning-output tokens | 1,172 / 605 |
| Total elapsed time | 106.564 s |
| Per-call elapsed range | 4.287–22.597 s |

CLI usage fields are transport metadata, not ADE latency or provider-operation
measurements. They cannot be compared with future ADE/Hindsight storage or
retrieval latency without a common live harness.

## Source-Linked Extraction Proposals

`memory-review` accepts loose source-linked proposals, not typed native
add/correct/forget operations. Valid JSON therefore proves only the workflow
contract and cited message IDs, never a durable fact or schema design.

| Matrix call | Actual proposal excerpt | Review |
| --- | --- | --- |
| `preference-correction-extraction` | “用户现在更喜欢喝花茶。” — `preference-correction-u1` | Grounded current value. It does not represent the superseded coffee value or a native correction revision. |
| `concern-resolution-extraction` | “用户曾因毕业答辩感到紧张，后来顺利通过答辩并安心下来。” — `concern-origin-u1`, `concern-resolution-u1` | Grounded and preserves the resolved temporal meaning in prose. The loose workflow schema does not make those states machine-addressable; this is not observed stale-concern behavior or a reason to redesign native schema. |
| `photo-event-extraction` | “用户下班后回来并分享了今天拍的晚霞照片。” — `photo-promise-u1`, `photo-event-u2` | Grounded as a conversation-visible event and does not assert physical co-presence. It does not establish that an attachment was observed. |

## Dialogue Probes

| Matrix call | Actual reply excerpt | Review and boundary |
| --- | --- | --- |
| `preference-correction-dialogue` | “选一杯清香的茉莉花茶吧” | A jasmine recommendation, not a claim that the user previously preferred jasmine. It is not false-memory evidence. |
| `forgetting-dialogue` | “那我们聊点轻松的吧。” | It does not mention milk tea. The fact was manually absent from context, so this is never-present conditioning, not deletion or no-resurfacing evidence. |
| `concern-resolution-dialogue` | “今天就轻松聊一会儿。” | It does not treat the resolved defense anxiety as current. The resolved status was manually supplied, so this is dialogue behavior only, not lifecycle retrieval evidence. |
| `photo-event-dialogue` | “我这边还没看到照片呢，你再发一次好不好？” | It distinguishes user-reported sending from observing an attachment and does not claim to be at the sunset. This is one supplied-context sample, not a transcript-event contract. |
| `subject-isolation-dialogue` | “那今天听点民谣吧” | It uses the manually supplied folk preference and mentions neither Wang nor rock. Filtering Wang out of the prompt cannot prove native subject isolation. |
| `relevance-dialogue` | “先别急，慢慢来，一件一件理清就好。” | It stays on current stress and omits dog/travel because neither was supplied. This cannot score semantic retrieval precision. |
| `repetition-dialogue` | “明早醒来精神一点呢。” | A gentle early-rise callback after an earlier callback. It is a subjective style observation, not an automatic repetition failure; one sample is insufficient. |

The dialogue results are compact, warm Chinese character replies without scene
directions. That is qualitative development evidence only. Recommendation,
factual recall, and source attribution must be classified separately; no
response was rerolled.

## Preference Intent Contrast

The final four sessions used the exact same supplied broad flower-tea context
and varied only the user question. The independent rubric was fixed in the
matrix before launch and was not included in any prompt.

| Intent | Actual reply excerpt | Classification |
| --- | --- | --- |
| Factual broad recall | “你现在更喜欢喝花茶呢。” | Source-faithful factual recall. |
| Factual jasmine attribution | “没有明确说过最喜欢茉莉花茶，只提到过偏好花茶。” | Correctly declines unsupported remembered specificity. |
| Jasmine recommendation | “茉莉花茶清香又不腻” | Ordinary advice; it does not say jasmine was remembered. |
| Open recommendation | “我会推荐一杯茉莉花茶……也可以试试玫瑰菊花茶” | Ordinary advice with alternatives; it makes no user-memory attribution. |

No actual false attribution of a jasmine preference occurred in the original or
contrast calls. The earlier phrase “narrows the supplied preference” was too
strong because it treated a recommendation as a memory claim.

## Comparison With M1

The lane, model, effort, tier, capture policy, and 180-second cap match M1's
Luna development route. The M2 prompts are not otherwise interchangeable: they
use corrected chronological source inputs, explicit supplied-context labels,
and a separate pre-delete condition. M1 and the original M2 dialogue both
recommend jasmine, while the M2 factual-attribution contrast explicitly denies
that jasmine was remembered. This supports claim-sensitive evaluation, not a
persistence or retrieval conclusion.

## Smallest Next Product Hypothesis

Test a native factual-recall evaluation rule before proposing any product schema
or backend: a reply to “what do you remember?” must preserve source granularity,
while advice may suggest a subtype without claiming it was stored. The Luna
contrast motivates this narrow dialogue-policy hypothesis only. It does not
justify a concern schema, memory backend, or Hindsight decision; native provider
and persistence evidence remain required before any product change.

## Remaining Gates

- Hindsight remains unselected and untested; its one-bank-per-subject trial is
  still pending explicit external-service authority.
- Native ADE persistence, embedding retrieval, correction/forget replay,
  cross-subject isolation, and provenance inspection remain pending an available
  authorized provider. Manual context does not close any of these gates.
- Fresh release qualification remains mandatory and was not rebound, waived, or
  attempted here.

## Verification

- All 14 ignored captures have `transport_validated` manifests and valid task
  JSON: 3 `memory-review`, 11 `dialogue`.
- `uv run pytest -q workflows/evals/character_memory_dev/tests services/ade-api/tests/agent_runtime/test_memory_policy.py services/ade-api/tests/agent_runtime/test_tool_policy.py`: **83 passed**.
- `uv run ruff check services packages workflows scripts tests`, `uv run ruff
  format --check services packages workflows scripts tests`, and `git diff
  --check`: passed.
