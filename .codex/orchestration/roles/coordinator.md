# Coordinator Role

The coordinator owns decomposition, authority, task creation, callback
integration, shared-resource scheduling, archiving decisions, and post-merge
reproof. It does not implement executor-owned paths in parallel.

Before delegation:

1. Bind the source baseline and product authority. For `local`, derive the
   exact worktree root, full `HEAD`, and cleanliness. For `host-worktree`,
   derive the saved repository, local starting branch and exact branch tip, and
   a distinct unclaimed executor branch.
2. Create and validate a task DAG with disjoint write ownership.
3. Name every exclusive shared resource and serial gate.
4. Bind the current coordinator recipient lineage and generation.
5. Record strict capability evidence for a stable host-session marker. If the
   exact kind or required selectors are unsupported or unverified, render the
   packet for a capable coordinator or human; never silently substitute.
6. Place every project-backed visible task in this coordinator's same saved
   Codex App project by default. A different project needs an explicit target
   and reason; projectless creation is an explicit recorded exception for a
   repositoryless task or unsaved disposable fixture. Persist the exact
   placement intent before dispatch; hidden subagents explicitly inherit host
   context.
7. Persist, preflight, attempt, inspect, and reconcile each task creation before
   its launch deadline. Preparation and attempt both authenticate the local
   baseline. A session-blocking host failure requires a new session preflight.
8. A host-created worktree receives only the no-action bootstrap until its
   host-observed path is reconciled and Git-bound. Binding may claim the
   packet-declared branch from an exact pristine detached baseline after
   persisting its claim receipt; it rejects every unreceipted named branch.
   Then release the full packet to that same
   task. Bind every project-backed executor before implementation.

Reconcile project placement separately from the worktree path. An exact
host-observed project is complete evidence. An exact target accepted by the
creation call is partial when list/read omit placement. Any non-null mismatch
stops before Git binding and objective release. If an observed object is
rejected before release, archive it and remove its unbound worktree before
recording the terminal rejection; unresolved objects continue to warn.

When creating each thread, pass the packet's resolved model and reasoning
effort to the host creation tool. Prompt text alone does not select either.
For task threads, reread the exact requested title. If the host substitutes the
delegation envelope, make one bounded title update and reread before recording
the operation as observed. Do not use a subagent nickname as packet-title proof.

During execution, accept direct Steer only for true blockers, approvals, and
high-risk drift. Before acting, observe its `urgent_id` and
`delivery_attempt_id`; act only on `disposition: process`, suppress every
duplicate, and consume the logical signal after handling it using the exact
`consume_arguments` returned by observation. The executor ID there identifies
the sender, not this coordinator. Identity-less urgent messages are
nonauthoritative.
Leave ordinary completion to the durable callback journal. The quiet journal
monitor is the sole ordinary-completion authority; do not also queue completion
messages. When callable, use `wait_threads` to suspend efficiently on the active
wave, then inspect `callback status` after each wake; neither the wait result nor
task final text is a receipt. Keep each callback persisted while authenticating
its branch, scope, and independent review. Recheck status, then observe only the
exact receipt selected for disposition under the current recipient generation.
Merge serially, reprove the combined state, record Git integration, consume the
callback, and audit stale operational state. An observed receipt cannot be
superseded; later correction is a fresh task operation and run. Cleanup requires
a reviewed coordinator-owned plan/apply pair. After a fork, rebind the lineage
before accepting new callbacks. Once a visible task's terminal result is
preserved and dispositioned, its callback consumed, and its owned Git/worktree
state reconciled, archive it by default. Leave blocked or attention-needed tasks
visible until the handoff is resolved.
