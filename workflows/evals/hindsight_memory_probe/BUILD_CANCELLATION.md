# P1 owned BuildKit cancellation proof

This is a **future OCI qualification**, unrun at P0. A sleep-process proof does
not qualify Docker daemon cancellation. Use the existing Docker engine's BuildKit
backend without creating another service/builder daemon or pruning any state.

The launcher `--kind build-cancel` accepts no caller command. It registers the
unique token, PID/start identity, epoch and deadline before dispatching exactly:
a pinned ARM Python base, isolated `docker/cancellation/` context, network-none
RUN, no cache, a unique `ade-hindsight-probe-cancel:<token>` tag. No private files,
provider/model inputs or qualified runner tag enter this build. Its dummy Python
RUN has a 300-second finite sleep and unique standalone argv/log sentinel
`ADE_PROBE_BUILDKIT_SENTINEL <token>`. Cancellation job timeout is at most 120s;
launch is refused within 600s of the hard cap. Candidates must be stopped and
prospective memory headroom must satisfy the active epoch allocations.

Run only after the ordinary pinned Python/router image build has finished, while
all candidate services remain stopped. The guard must already be detached and
its dummy disconnect/resume proof recorded. Existing internal candidate keys can
remain generated with a **synthetic provider**; do not activate live credentials.
Use the same current clean release and state variables from the owning README.

```sh
PROBE_BUILD_PID=$(python3 -m workflows.evals.hindsight_memory_probe.launch \
  --state "$PROBE_STATE" --kind build-cancel --timeout 90)
python3 -m workflows.evals.hindsight_memory_probe.build_cancellation \
  --state "$PROBE_STATE" --pid "$PROBE_BUILD_PID"
python3 -m workflows.evals.hindsight_memory_probe.supervisor --state "$PROBE_STATE" inspect
```

The observer requires a positive host `/proc` match of the actual RUN argv,
records its UID/start/cmd identity privately, waits for the guard's registered
job deadline cancellation, and records three consecutive observations with no
sentinel and no token-tagged owned client process. It also verifies the epoch's
stop receipt says `owned_process_deadline_elapsed` at/after that registered job
deadline. An early build failure, hidden/unreadable host process view, never-seen
sentinel, operator stop, or still-running daemon work produces no successful
proof. Only readback occurs: it never signals or prunes daemon workers.

Successful receipt: `build-cancel-<token>.proof.json`, contract
`ade-owned-buildkit-cancellation-v1`, actual observed sentinel identities,
post-deadline samples, unique tag, registered job SHA and outcome
`daemon_cancelled`. Also preserve the seen receipt, exclusive process log, job
registration, epoch stop and baseline/host readback. Inspect the actual log
sentinel and stopped process identities independently; do not manufacture a
qualification boolean from a timed-out Docker client alone.

The job deadline stops the epoch. Write a diagnosis citing this intended probe,
its receipts and safe baseline/headroom, then use the documented `rearm` and
fresh detached `run` commands. The campaign clock stays unchanged. In
`oci-supervisor-proof.json`, put the successful filename in
`build_cancellation_receipt` and include its SHA256 in `evidence_sha256`.
Provider activation validates this typed receipt and its registered job binding,
in addition to the earlier SSH/dummy/resume/baseline proof.

If cancellation fails, keep live activation blocked and preserve failure receipts.
Do not kill a shared daemon, globally stop containers or prune caches. The RUN
has its own finite wall; recheck host resources, diagnose engine cancellation
and requalify an owned candidate after safe stopped readback. No successful
BuildKit cancellation or safety acceptance is claimed by the offline fake tests.
