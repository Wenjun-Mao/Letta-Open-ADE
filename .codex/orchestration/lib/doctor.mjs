import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { callbackStatus, findCodexBinary } from "./callbacks.mjs";
import { PACKAGE_VERSION, readJson } from "./core.mjs";
import { projectConfigPath, validateProjectConfig } from "./config.mjs";
import { gitLifecycleAudit } from "./git-lifecycle.mjs";
import { inspectExternalAgents, inspectInstalledRuntime } from "./managed.mjs";
import { recipientStatuses } from "./recipients.mjs";
import { taskOperationStatus } from "./task-operations.mjs";
import { urgentSignalStatus } from "./urgent-signals.mjs";

export async function runDoctor(git) {
  const errors = [];
  const warnings = [];
  let config = null;
  try {
    const raw = await readJson(projectConfigPath(git.root), { allowMissing: true });
    if (!raw) errors.push("Project configuration is missing");
    else config = validateProjectConfig(raw);
  } catch (error) {
    errors.push(error.message);
  }

  let runtime = null;
  try {
    runtime = await inspectInstalledRuntime(git.root);
    if (!runtime.installed) errors.push("Pinned codex-flow runtime is not installed");
    else if (runtime.manifest.package_version !== PACKAGE_VERSION) {
      errors.push(
        `Installed Codex Flow ${runtime.manifest.package_version} requires explicit retirement before fresh ${PACKAGE_VERSION} installation`,
      );
    } else if (runtime.drift.length > 0) errors.push("Pinned codex-flow runtime has managed-file drift");
    if (runtime?.unexpected?.length > 0) errors.push("Pinned codex-flow runtime contains unowned files");
  } catch (error) {
    errors.push(error.message);
  }

  const agentsPath = resolve(git.root, "AGENTS.md");
  let agentsBlock = "missing";
  let agentsContract = { mode: config?.agents_integration.mode ?? "unconfigured", status: "unknown" };
  if (config?.agents_integration.mode === "external") {
    try {
      await inspectExternalAgents({ gitRoot: git.root, integration: config.agents_integration });
      agentsContract = {
        mode: "external",
        status: "verified",
        path: config.agents_integration.path,
        contract_version: config.agents_integration.contract_version,
      };
      agentsBlock = "external";
    } catch (error) {
      agentsContract = {
        mode: "external",
        status: "drifted",
        path: config.agents_integration.path,
        contract_version: config.agents_integration.contract_version,
      };
      agentsBlock = "external-drifted";
      errors.push(error.message);
    }
  } else {
    try {
      const agents = await readFile(agentsPath, "utf8");
      const starts = (agents.match(/<!-- codex-flow:start v[^\s]+ -->/g) ?? []).length;
      const ends = (agents.match(/<!-- codex-flow:end -->/g) ?? []).length;
      if (starts === 1 && ends === 1) {
        agentsBlock = "present";
        agentsContract = { mode: "managed", status: "verified", path: "AGENTS.md" };
      } else if (starts !== 0 || ends !== 0) {
        agentsBlock = "malformed";
        agentsContract = { mode: "managed", status: "malformed", path: "AGENTS.md" };
        errors.push("AGENTS.md codex-flow managed block is malformed");
      } else {
        agentsContract = { mode: "managed", status: "missing", path: "AGENTS.md" };
        warnings.push("AGENTS.md codex-flow managed block is absent");
      }
    } catch (error) {
      if (error?.code === "ENOENT") warnings.push("AGENTS.md is absent");
      else errors.push(error.message);
    }
  }

  const [nodeMajor, nodeMinor] = process.versions.node.split(".").map(Number);
  if (nodeMajor < 20 || (nodeMajor === 20 && nodeMinor < 11)) {
    errors.push(`Node ${process.versions.node} is unsupported; require >=20.11`);
  }
  const codex = findCodexBinary();
  if (!codex) warnings.push("Codex CLI was not found; optional host operations may be unavailable");
  else if (codex.error) warnings.push(`Codex CLI probe failed: ${codex.error}`);

  let callbacks = { pending: [], consumed_count: 0 };
  try {
    callbacks = await callbackStatus(git.stateRoot);
  } catch (error) {
    errors.push(`Callback state is invalid: ${error.message}`);
  }

  let urgentSignals = {
    pending: [],
    consumed_count: 0,
    superseded_count: 0,
    expired_count: 0,
    host_replay_count: 0,
    sender_attempt_duplicate_count: 0,
  };
  try {
    urgentSignals = await urgentSignalStatus(git.stateRoot);
    if (urgentSignals.pending.length > 0) {
      errors.push(`${urgentSignals.pending.length} urgent signal(s) require coordinator disposition`);
    }
    if (urgentSignals.host_replay_count > 0) {
      warnings.push(`${urgentSignals.host_replay_count} urgent host replay(s) were durably suppressed`);
    }
    if (urgentSignals.sender_attempt_duplicate_count > 0) {
      warnings.push(`${urgentSignals.sender_attempt_duplicate_count} additional urgent sender attempt(s) were durably suppressed`);
    }
  } catch (error) {
    errors.push(`Urgent-signal state is invalid: ${error.message}`);
  }

  let recipients = [];
  try {
    recipients = await recipientStatuses({ stateRoot: git.stateRoot });
  } catch (error) {
    errors.push(`Recipient state is invalid: ${error.message}`);
  }

  let taskOperations = [];
  try {
    taskOperations = await taskOperationStatus({ stateRoot: git.stateRoot });
    const incompatible = taskOperations.filter((operation) => operation.status === "host-incompatible");
    const sessionBlocked = taskOperations.filter((operation) => operation.status === "host-session-blocked");
    const partialEvidence = taskOperations.filter(
      (operation) => operation.status === "observed" && operation.observation_evidence?.quality === "partial",
    );
    const rejectedObservationPolicies = taskOperations.filter(
      (operation) => operation.status === "observed" && operation.observation_policy?.state === "rejected",
    );
    if (incompatible.length > 0) {
      warnings.push(`${incompatible.length} task operation(s) are incompatible with their recorded host selector`);
    }
    if (sessionBlocked.length > 0) {
      warnings.push(`${sessionBlocked.length} task operation(s) are blocked for their recorded host session`);
    }
    if (partialEvidence.length > 0) {
      warnings.push(`${partialEvidence.length} observed task operation(s) have partial host evidence`);
    }
    if (rejectedObservationPolicies.length > 0) {
      warnings.push(`${rejectedObservationPolicies.length} observed task operation(s) violate requested host observation policy`);
    }
  } catch (error) {
    errors.push(`Task-operation state is invalid: ${error.message}`);
  }

  let gitLifecycle = { items: [], eligible_count: 0, backlog_count: 0, warning: false, blocked: false };
  if (config) {
    try {
      gitLifecycle = await gitLifecycleAudit({ git, config, inspectRemotes: false });
      if (gitLifecycle.incomplete_claim_count > 0) {
        warnings.push(`${gitLifecycle.incomplete_claim_count} executor branch claim(s) require Git binding recovery`);
      }
      const ownedOperationIds = new Set(gitLifecycle.items.map((item) => item.operation_id));
      const unboundHostWorktrees = taskOperations.filter((operation) => (
        operation.status === "observed"
        && operation.request.environment.type === "host-worktree"
        && !ownedOperationIds.has(operation.operation_id)
      ));
      if (unboundHostWorktrees.length) {
        warnings.push(`${unboundHostWorktrees.length} observed host worktree(s) lack Git ownership binding`);
      }
      if (gitLifecycle.warning) {
        warnings.push(`${gitLifecycle.backlog_count} task Git record(s) require cleanup reconciliation`);
      }
      if (gitLifecycle.blocked) {
        errors.push(gitLifecycle.incomplete_claim_count > 0
          ? "Executor branch claim recovery is required before another task wave"
          : "Task Git cleanup reached the configured block threshold");
      }
    } catch (error) {
      errors.push(`Git lifecycle state is invalid: ${error.message}`);
    }
  }

  return {
    ok: errors.length === 0,
    project: config,
    git: {
      root: git.root,
      common_dir: git.commonDir,
      branch: git.branch,
      revision: git.revision,
      upstream: git.upstream,
      cleanliness: git.cleanliness,
    },
    runtime: runtime ? {
      installed: runtime.installed,
      package_version: runtime.manifest?.package_version ?? null,
      drift: runtime.drift,
      unexpected: runtime.unexpected ?? [],
    } : null,
    agents_block: agentsBlock,
    agents_contract: agentsContract,
    node_version: process.versions.node,
    codex_cli: codex,
    thread_creation: "runtime-probe-required",
    callbacks: {
      pending_count: callbacks.pending.length,
      consumed_count: callbacks.consumed_count,
      superseded_count: callbacks.superseded_count ?? 0,
      expired_count: callbacks.expired_count ?? 0,
    },
    urgent_signals: {
      pending_count: urgentSignals.pending.length,
      consumed_count: urgentSignals.consumed_count,
      superseded_count: urgentSignals.superseded_count,
      expired_count: urgentSignals.expired_count,
      host_replay_count: urgentSignals.host_replay_count,
      sender_attempt_duplicate_count: urgentSignals.sender_attempt_duplicate_count,
    },
    recipients: {
      lineage_count: recipients.length,
    },
    task_operations: {
      total_count: taskOperations.length,
      ambiguous_count: taskOperations.filter((operation) => ["ambiguous", "ambiguous-due"].includes(operation.effective_status)).length,
      host_incompatible_count: taskOperations.filter((operation) => operation.status === "host-incompatible").length,
      host_session_blocked_count: taskOperations.filter((operation) => operation.status === "host-session-blocked").length,
      complete_evidence_count: taskOperations.filter(
        (operation) => operation.status === "observed" && operation.observation_evidence?.quality === "complete",
      ).length,
      partial_evidence_count: taskOperations.filter(
        (operation) => operation.status === "observed" && operation.observation_evidence?.quality === "partial",
      ).length,
      observation_policy_rejected_count: taskOperations.filter(
        (operation) => operation.status === "observed" && operation.observation_policy?.state === "rejected",
      ).length,
      rejected_before_release_count: taskOperations.filter(
        (operation) => operation.status === "rejected-before-release",
      ).length,
    },
    git_lifecycle: {
      total_count: gitLifecycle.items.length,
      eligible_count: gitLifecycle.eligible_count,
      backlog_count: gitLifecycle.backlog_count,
      warning: gitLifecycle.warning,
      blocked: gitLifecycle.blocked,
    },
    errors,
    warnings,
  };
}
