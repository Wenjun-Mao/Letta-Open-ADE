# Lin Xiaotang isolated browser trial smoke — 2026-09-27

## Scope and binding

The authorized development-only stack ran at
`http://127.0.0.1:13001/agent-studio` with separate Compose project
`ade-history-trial`, loopback API port 18001, isolated PostgreSQL and content
storage. The UI labeled the environment experimental. The options API exposed
the Lin Xiaotang persona, `chat_v20260926`, automatic-history policy, DeepSeek
conversation/reviewer fingerprint `870ff4...`, and pinned Qwen embedding
fingerprint `c549...`. Worker health reported ready with one worker. This smoke
used the browser to create and send all four turns, then read API and SQL state.
It did not alter production bindings or release gates.

## Browser observations

| Turn | Conversation / subject | Browser result | Persisted result |
| --- | --- | --- | --- |
| 1 | `ba86f6bf-c04a-5447-80a5-8e73f94ab208` / `smoke-trial-20260927` | Said a bookshelf attempt became a small stool; Xiaotang acknowledged the stool. The conversation was then archived. | Succeeded, one attempt. |
| 2 | `11672d4e-46a3-5796-b663-2f456885c4f7` / same subject | Asked what the bookshelf became without giving the outcome; Xiaotang answered small stool. | Succeeded, one attempt. `history_probe_status=admitted`; admitted archived-source run `53325ba5-f431-4999-877b-e14ad4d55feb`. |
| 3 | same conversation and subject | Said “我现在住在蒙特利尔。”; Xiaotang responded. | Succeeded, one attempt. Active `person.current_location=蒙特利尔` at generation 2, with the user message as source. |
| 4 | `c3c2c9fd-d8d3-5e46-a0fa-52ce6493576a` / `smoke-isolated-20260927` | Asked which city this different user currently lives in. No assistant reply was delivered. | Failed, one attempt, `conversation_tool_step_budget_exceeded` under the existing two-request ceiling. |

The first two conversations shared an evaluation-purpose subject and Lin
Xiaotang definition `lin_xiaotang_smoke v1`. The archived source remained
archived after the recall answer. SQL readback found one active fact and two
messages in the archived source conversation, one active fact and four messages
in the second conversation, and zero active facts with only its own user
message for the different subject. Four accepted turns yielded three successes
and one bounded failure; all had `retry_count=0` and `attempt_count=1`.

## Interpretation

The second reply and admitted source run verify the automatic-history path
across an archive boundary in this small trial. The fourth turn does not test
spoken subject isolation because the worker returned no answer. The distinct
subject had no fact or eligible prior chat from the first subject, which checks
storage scope only. The tool-step failure is retained as observed; it was not
rerolled or used to justify a ceiling change. This synthetic smoke establishes
readiness for a human development trial, not a semantic score, default policy
selection, or release qualification. The [playbook](../../../workflows/evals/character_memory_dev/hands-on-trial.md)
asks a person to use a fresh fictional subject and record dialogue and saved
memory separately.
