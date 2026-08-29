import { callbackStatus } from "./callbacks.mjs";
import { projectConfigPath, validateProjectConfig } from "./config.mjs";
import { directorySize, formatBytes, readJson } from "./core.mjs";
import { gitLifecycleAudit } from "./git-lifecycle.mjs";
import { leaseStatus } from "./leases.mjs";
import { inspectInstalledRuntime } from "./managed.mjs";
import { recipientStatuses } from "./recipients.mjs";
import { taskOperationStatus } from "./task-operations.mjs";
import { urgentSignalStatus } from "./urgent-signals.mjs";

export async function cleanupAudit(git) {
  const config = validateProjectConfig(await readJson(projectConfigPath(git.root)));
  const callbacks = await callbackStatus(git.stateRoot);
  const urgentSignals = await urgentSignalStatus(git.stateRoot);
  const leases = await leaseStatus({ stateRoot: git.stateRoot });
  const operations = await taskOperationStatus({ stateRoot: git.stateRoot });
  const recipients = await recipientStatuses({ stateRoot: git.stateRoot });
  const runtime = await inspectInstalledRuntime(git.root);
  const gitLifecycle = await gitLifecycleAudit({ git, config });
  const bytes = await directorySize(git.stateRoot);
  const recommendations = [];
  if (gitLifecycle.incomplete_claim_count > 0) {
    recommendations.push(`${gitLifecycle.incomplete_claim_count} executor branch claim(s) require Git binding recovery before cleanup`);
  }
  const oldPending = callbacks.pending.filter((item) => item.age_seconds > 24 * 60 * 60);
  if (oldPending.length) recommendations.push(`${oldPending.length} callback record(s) have been pending for more than 24 hours`);
  const callbacksDueForExpiry = callbacks.pending.filter((item) => item.effective_integration === "expired-due");
  if (callbacksDueForExpiry.length) recommendations.push(`${callbacksDueForExpiry.length} callback record(s) have reached their explicit expiry and may be marked expired`);
  const oldUrgentSignals = urgentSignals.pending.filter((item) => item.age_seconds > 24 * 60 * 60);
  if (oldUrgentSignals.length) recommendations.push(`${oldUrgentSignals.length} urgent signal(s) have been pending for more than 24 hours`);
  const urgentSignalsDueForExpiry = urgentSignals.pending.filter((item) => item.effective_state === "expired-due");
  if (urgentSignalsDueForExpiry.length) recommendations.push(`${urgentSignalsDueForExpiry.length} urgent signal(s) have reached their explicit expiry and may be marked expired`);
  if (urgentSignals.host_replay_count > 0) recommendations.push(`${urgentSignals.host_replay_count} urgent host replay(s) were suppressed and remain in audit evidence`);
  if (urgentSignals.sender_attempt_duplicate_count > 0) recommendations.push(`${urgentSignals.sender_attempt_duplicate_count} additional urgent sender attempt(s) were suppressed and remain in audit evidence`);
  const ambiguousOperations = operations.filter((operation) => ["ambiguous", "ambiguous-due", "dispatching"].includes(operation.effective_status));
  if (ambiguousOperations.length) recommendations.push(`${ambiguousOperations.length} task creation operation(s) require host inspection or bounded-wait review`);
  const blockedHostSessions = operations.filter((operation) => operation.status === "host-session-blocked");
  if (blockedHostSessions.length) {
    recommendations.push(`${blockedHostSessions.length} task creation operation(s) require a new host-session preflight before retry`);
  }
  const incompatibleHosts = operations.filter((operation) => operation.status === "host-incompatible");
  if (incompatibleHosts.length) {
    recommendations.push(`${incompatibleHosts.length} task creation operation(s) require compatible selector evidence before dispatch`);
  }
  const partialObservations = operations.filter(
    (operation) => operation.status === "observed" && operation.observation_evidence?.quality === "partial",
  );
  const rejectedObservationPolicies = operations.filter(
    (operation) => operation.status === "observed" && operation.observation_policy?.state === "rejected",
  );
  const rejectedBeforeRelease = operations.filter(
    (operation) => operation.status === "rejected-before-release",
  );
  if (partialObservations.length) {
    recommendations.push(`${partialObservations.length} observed task operation(s) retain explicitly partial host evidence`);
  }
  if (rejectedObservationPolicies.length) {
    recommendations.push(`${rejectedObservationPolicies.length} observed task operation(s) require archive or policy reconciliation before release`);
  }
  const ownedOperationIds = new Set(gitLifecycle.items.map((item) => item.operation_id));
  const unboundHostWorktrees = operations.filter((operation) => (
    operation.status === "observed"
    && operation.request.environment.type === "host-worktree"
    && !ownedOperationIds.has(operation.operation_id)
  ));
  if (unboundHostWorktrees.length) {
    recommendations.push(`${unboundHostWorktrees.length} observed host worktree(s) require Git ownership binding or manual archive review`);
  }
  const expired = leases.filter((lease) => lease.state === "expired");
  if (expired.length) recommendations.push(`${expired.length} exclusive-resource lease(s) are expired and require owner review`);
  if (runtime.drift.length) recommendations.push("Pinned runtime has managed-file drift; review before sync");
  if (runtime.unexpected?.length) recommendations.push("Pinned runtime contains files not owned by codex-flow; review before sync");
  if (callbacks.superseded_count || callbacks.expired_count) {
    recommendations.push("Terminal callback journal contains superseded or expired records; cleanup remains audit-only");
  }
  if (gitLifecycle.eligible_count) {
    recommendations.push(`${gitLifecycle.eligible_count} task Git record(s) are eligible for an explicit cleanup plan`);
  }
  if (gitLifecycle.blocked && gitLifecycle.incomplete_claim_count === 0) {
    recommendations.push("Git cleanup reconciliation has reached the configured task-wave block threshold");
  }
  return {
    mutation_performed: false,
    state_root: git.stateRoot,
    state_bytes: bytes,
    state_size: formatBytes(bytes),
    callbacks,
    urgent_signals: urgentSignals,
    task_operations: operations,
    observation_policy_rejected_count: rejectedObservationPolicies.length,
    rejected_before_release_count: rejectedBeforeRelease.length,
    recipients,
    leases,
    runtime: {
      installed: runtime.installed,
      package_version: runtime.manifest?.package_version ?? null,
      drift: runtime.drift,
      unexpected: runtime.unexpected ?? [],
    },
    git_lifecycle: gitLifecycle,
    unbound_host_worktrees: unboundHostWorktrees.map((operation) => ({
      operation_id: operation.operation_id,
      object_id: operation.observed.object_id,
      execution_path: operation.observed.evidence.execution_path.value,
    })),
    recommendations,
  };
}
