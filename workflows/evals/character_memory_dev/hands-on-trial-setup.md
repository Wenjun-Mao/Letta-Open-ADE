# Hands-on trial: operator setup

The [chat playbook](hands-on-trial.md) is for the person trying Lin Xiaotang. This
page describes the isolated development stack. The trial remains an experiment,
not release qualification.

## Start and inspect

From the repository root, with the local development credentials file present:

```sh
ADE_TRIAL_ENV_FILE=/Users/wjmao/projects/HU/Letta-Open-ADE/.env \
  workflows/evals/character_memory_dev/trial-stack.sh start
ADE_TRIAL_ENV_FILE=/Users/wjmao/projects/HU/Letta-Open-ADE/.env \
  workflows/evals/character_memory_dev/trial-stack.sh status
```

Open [the Lin Xiaotang trial](http://127.0.0.1:13001/agent-studio). The web UI
uses loopback port 13001; the API uses 18001. The stack uses Compose project
`ade-history-trial`, its own PostgreSQL database and ignored `.trial/` storage.
It does not share the production app's ports or data. The startup script copies
the required content into trial storage and prepares a trial-only router catalog.
Its source selection checks the existing DeepSeek and pinned Qwen route identities.

Use a new fictional **Memory subject** for each person's trial. Existing
`SMOKE` conversations and subjects were created by the operator and should not
be used as a person's results. Keep the same subject and Lin Xiaotang definition
for chats 1–3; selecting a new conversation does not create a new person.
Archive is available for conversations. The trial UI labels its data experimental.

## Pinned boundary

The trial mounts `/api/v3/history-trial` only when both the development runtime
and `history_trial_enabled` are set. The UI switches its resource endpoints to
that purpose-scoped API only in the trial build. Resource creation binds
`evaluation` purpose, the `chat_v20260926` candidate, the H4 history policy and
capacity, `automatic_history`, the exact Qwen ranking recipe, DeepSeek for
conversation and review, `search_memory`, and zero additional retries before
persisting immutable versions. Worker startup configures the matching probe.
The ordinary Agent Studio API, defaults and production runtime are unchanged.
See [ADR 0045](../../../docs/adr/0045-isolated-history-trial-composition.md).

The development smoke exercised the browser, API, worker and SQL readback. One
archived conversation supplied an admitted historical source for a successful
stool answer in a separate conversation. A different-subject question hit the
existing two-request conversation tool-step ceiling without a reply. Its new
subject had no active facts or eligible prior chat; spoken isolation was not
verified in that smoke. See the [smoke finding](../../../docs/findings/natural-memory-consultation/hands-on-trial-smoke-2026-09-27.md).

## Stop

```sh
ADE_TRIAL_ENV_FILE=/Users/wjmao/projects/HU/Letta-Open-ADE/.env \
  workflows/evals/character_memory_dev/trial-stack.sh stop
```

Stopping retains the ignored trial database and storage so observations can be
reviewed. Start again with the same command above. Do not copy these rows or
the trial route into production.
