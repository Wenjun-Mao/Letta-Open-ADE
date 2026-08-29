# One-Shot Host Operations

The portable CLI journals intent and reconciliation. It does not invoke private
in-session Codex tools. The coordinator performs one bounded host call around
that journal; no daemon, MCP server, or background secretary is required.

For task creation:

1. Validate the task packet and its absolute launch deadline. For `local`,
   derive the exact worktree root, full `HEAD`, and cleanliness. For
   `host-worktree`, derive the saved repository root, local starting branch,
   exact branch tip, and a distinct unclaimed executor branch from Git.
2. Resolve the coordinator's saved Codex App project and create a project-backed
   visible task in that same project by default. Record its exact project ID in
   the operation before dispatch. A cross-project target needs an exact ID and
   explicit reason.
   Projectless is an explicit exception only for a truly repositoryless task or
   an unsaved disposable fixture, and its reason must be recorded. Hidden
   subagents explicitly inherit their host context.
3. Record a stable, nonsecret host-session marker and capability evidence for
   the requested kind, model, and reasoning. Also record whether filtered
   discovery works or which bounded fallback is available.
4. Run `task operation prepare`, `task operation preflight`, then
   `task operation attempt`. Preparation and attempt fail closed on baseline
   mismatch; unsupported or unverified required selectors stop before dispatch.
5. For `local` or `projectless`, call the host once with the released packet.
   For `host-worktree`, render `task operation bootstrap` and use only that
   no-action prompt in the one creation call.
6. List/read the resulting host object. A task thread must be user-visible and
   its title must be independently reread. If the host used the delegation
   envelope, perform one bounded title update, reread the exact requested title,
   and record `bounded-host-write`. A subagent may have no title field; keep its
   host nickname separate.
7. Reconcile the attempt as `observed` with field-level provenance for title,
   visibility, model, reasoning, project placement, host label, and execution
   path. Exact host-observed placement is complete. Exact host-accepted
   placement is partial when list/read omit the selected project. Any non-null
   mismatch stops before binding. A
   `host-worktree` path must come from host observation.
8. For `host-worktree`, run `git bind`, then `task operation release` and send
   the resulting full packet to the same task. A pristine detached worktree may
   be claimed only as the packet-declared executor branch after an immutable
   claim receipt is persisted; an unreceipted named branch is rejected. An
   interrupted bind may resume only from that exact receipt. Do not release
   unless the final path is distinct from
   the saved checkout, in the same repository, and at the exact starting
   revision.

If the coordinator rejects an observed object before Git binding or objective
release, first archive the task. For `host-worktree`, remove the pristine
unbound path and verify that exact path is absent. Then record the terminal
`rejected-before-release` operation disposition. Conflicting replay, later
retry, binding, or release is forbidden. If binding left an immutable claim
without ownership, rejection may settle it only when the branch is unowned,
unchecked out, free of fetched remote-tracking evidence, and still exactly at
baseline if present. The exact local ref is conditionally removed, and the
terminal receipt retains the claim plus an absent-ref state without attributing
deletion across a crash. Drift requires recovery. Without this explicit
disposition, doctor and cleanup continue to treat the object or claim as
unresolved.

When a host advertises filtered thread listing but rejects the filter at
runtime, make one bounded recent-list call without that filter and match only
the expected operation by exact returned ID, title, kind, and visibility. Record
the rejected query and selected fallback in preflight evidence. Do not search
an unbounded history or infer identity from title alone. If the host does not
expose model or reasoning in list/read results, report those fields as
host-accepted or role-derived, not independently observed. Likewise, an
archive setter response proves the bounded archive operation, but does not
prove archived-list visibility when no such host capability exists.

If any host call times out or returns an indeterminate result, reconcile the
attempt as `ambiguous` and inspect host state before retrying. If the exact
object exists, reconcile it as observed. If inspection proves it was not
created, reconcile `not-created`, then start a new attempt only before the
launch deadline. Never infer failure from a local timeout or create a different
kind as fallback.

For active-turn monitoring, capability-probe `wait_threads`. On the current
Codex App contract it can wait on up to eight task IDs, returns when one task
finishes or needs attention, supports an immediate snapshot with a zero
timeout, and accepts per-task cursors that suppress already-delivered final
text. Batch larger waves within the advertised host limit. New user input may
end a wait early, so every wake or interruption must return to repository
`callback status`; do not busy-poll or treat the wait result as integration
authority. If the capability is absent, use bounded list/read inspection or an
explicit monitor without changing the journal contract.

Urgent direct delivery uses the same one-shot boundary without adding a host
adapter. Persist the logical signal, prepare one attempt, release every journal
lock, and pass the returned `host_prompt` string unchanged to direct Steer once
only when `dispatch_permitted` is true. Reconcile with the operator-observed
`--host-call-result`: `sent`, `rejected-before-send`, or `ambiguous`. A timeout
is ambiguous; it never authorizes replaying that attempt. The recipient observes
the IDs before acting so a host replay or explicit later attempt cannot trigger
duplicate work.

If dispatch fails before creation with a serializer, adapter, backend,
schema-runtime, or host-control error, reconcile `host-session-blocked` with a
specific reason code. Do not retry in that host session. After a reboot or
host-generation change, record a new compatible preflight; only then may a new
attempt start. Permanent selector incompatibility and transient session failure
are different states.

Archive and send operations remain host capabilities. Apply the same
operation-ID, bounded-wait, inspect-before-retry, and duplicate-safe principles,
but the current portable journal directly models creation only. The coordinator
archives a visible task by default only after terminal disposition, preserved
result, consumed callback, and reconciled Git/worktree cleanup. It never archives
a blocked or attention-needed task merely because its current turn ended, and
cleanup never auto-deletes tasks.

There is an unavoidable narrow gap between a successful pre-dispatch check and
the private host call. Keep that call immediate and one-shot; the executor must
still authenticate the baseline it receives before changing repository state.
