#!/usr/bin/env node

import { existsSync, readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { parseArgs } from "node:util";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  CliError,
  PACKAGE_VERSION,
  readJson,
  readJsonInput,
  requireEnum,
  requireInteger,
  stableStringify,
} from "../lib/core.mjs";
import {
  callbackStatus,
  consumeCallback,
  deliverCallback,
  expireCallback,
  expireCallbacks,
  observeCallback,
} from "../lib/callbacks.mjs";
import { cleanupAudit } from "../lib/cleanup.mjs";
import {
  projectConfigPath,
  REASONING_EFFORTS,
  validateProjectConfig,
  writeProjectConfig,
} from "../lib/config.mjs";
import { runDoctor } from "../lib/doctor.mjs";
import { discoverGit, gitSnapshot } from "../lib/git.mjs";
import {
  applyGitCleanupPlan,
  authorizeGitBoundTaskRelease,
  bindGitOwnership,
  createGitCleanupPlan,
  GitCleanupApplyError,
  gitLifecycleAudit,
  gitLifecycleReadiness,
  recordGitIntegration,
} from "../lib/git-lifecycle.mjs";
import {
  applyInstallationPlan,
  checkRepositoryInstallation,
  createInstallationPlan,
} from "../lib/installation.mjs";
import { acquireLease, leaseStatus, releaseLease } from "../lib/leases.mjs";
import {
  synchronizeRepository,
  withRepositoryManagementLock,
} from "../lib/managed.mjs";
import { validatePlan } from "../lib/plan.mjs";
import {
  bindRecipient,
  rebindRecipient,
  recipientStatus,
  recipientStatuses,
  resolveRecipient,
} from "../lib/recipients.mjs";
import {
  applyTaskDefaults,
  renderHostWorktreeBootstrap,
  renderReleasedTaskPacket,
  renderTaskPacket,
  validateTaskPacket,
} from "../lib/task-packet.mjs";
import {
  authorizeHostWorktreeBootstrap,
  beginTaskOperationAttempt,
  prepareTaskOperation,
  recordTaskOperationHostPreflight,
  rejectTaskOperationBeforeRelease,
  reconcileTaskOperation,
  taskOperationStatus,
} from "../lib/task-operations.mjs";
import {
  consumeUrgentSignal,
  expireUrgentSignal,
  expireUrgentSignals,
  observeUrgentSignal,
  persistUrgentSignal,
  prepareUrgentAttempt,
  reconcileUrgentAttempt,
  urgentSignalStatus,
} from "../lib/urgent-signals.mjs";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const HELP = `codex-flow ${PACKAGE_VERSION}

Usage:
  codex-flow init --plan [--json] [initialization options]
  codex-flow init --apply-plan PLAN_ID [initialization options]
  codex-flow init --check
  initialization options:
                  [--force] [--project-id ID] [--max-concurrency N]
                  [--model MODEL] [--reasoning-effort EFFORT]
                  [--setup-mode new|existing]
                  [--agents-mode managed|external]
                  [--external-agents-path PATH] [--attest-external-agents]
  codex-flow sync [--check] [--force]
  codex-flow config show [--json]
  codex-flow config set [--model MODEL|host-default]
                        [--reasoning-effort EFFORT|host-default]
                        [--max-concurrency N] [--json]
  codex-flow doctor [--json]
  codex-flow task start --role coordinator|executor
  codex-flow task packet validate|render <packet.json> [--model MODEL]
                  [--reasoning-effort EFFORT] [--json]
  codex-flow task operation prepare --file <packet.json> [--json]
  codex-flow task operation preflight --operation-id ID --file <host-capabilities.json> [--json]
  codex-flow task operation attempt --operation-id ID [--timeout-seconds N] [--json]
  codex-flow task operation bootstrap --operation-id ID --file <packet.json> [--json]
  codex-flow task operation reconcile --operation-id ID --attempt-id ID
                  --outcome observed|not-created|ambiguous|failed|host-session-blocked
                  [--object-id ID --actual-kind KIND --evidence <observation.json>]
                  [--reason-code CODE] [--json]
  codex-flow task operation reject --operation-id ID --reason-code CODE
                  --host-object-state archived [--json]
  codex-flow task operation release --operation-id ID --file <packet.json> [--json]
  codex-flow task operation status [--operation-id ID] [--json]
  codex-flow plan validate <plan.json> [--json]
  codex-flow recipient bind --lineage-id ID --thread-id ID [--fence-token TOKEN] [--json]
  codex-flow recipient rebind --lineage-id ID --thread-id ID --generation N
                  --fence-token TOKEN [--next-fence-token TOKEN] [--json]
  codex-flow recipient status [--lineage-id ID] [--json]
  codex-flow recipient resolve --lineage-id ID --thread-id ID --generation N [--json]
  codex-flow callback deliver [--file receipt.json] [--json]
  codex-flow callback observe --callback-id ID --lineage-id ID --thread-id ID --generation N
                  [--json]
  codex-flow callback consume --callback-id ID --lineage-id ID --thread-id ID
                  --generation N --executor-id ID [--json]
  codex-flow callback expire [--callback-id ID] [--at TIMESTAMP] [--json]
  codex-flow callback status [--json]
  codex-flow urgent persist [--file signal.json] [--json]
  codex-flow urgent attempt prepare --urgent-id ID --attempt-sequence N
                  [--retry-reason host-ambiguous|recipient-rebound|operator-approved-retry]
                  [--json]
  codex-flow urgent attempt reconcile --urgent-id ID --delivery-attempt-id ID
                  --host-call-result sent|rejected-before-send|ambiguous [--json]
  codex-flow urgent observe --urgent-id ID --delivery-attempt-id ID
                  --lineage-id ID --thread-id ID --generation N [--json]
  codex-flow urgent consume --urgent-id ID --lineage-id ID --thread-id ID
                  --generation N --sender-executor-id ID [--json]
  codex-flow urgent expire [--urgent-id ID] [--at TIMESTAMP] [--json]
  codex-flow urgent status [--json]
  codex-flow git bind --operation-id ID [--json]
  codex-flow git integrate --operation-id ID --main-branch BRANCH
                  [--superseded-by REF] [--json]
  codex-flow git status [--json]
  codex-flow lease acquire --resource ID --owner ID [--ttl-seconds N] [--break-expired] [--json]
  codex-flow lease release --resource ID --owner ID --token TOKEN [--json]
  codex-flow lease status [--resource ID] [--json]
  codex-flow cleanup audit [--json]
  codex-flow cleanup plan --operation-id ID... --main-branch BRANCH
                  [--include-remote] [--json]
  codex-flow cleanup apply --plan-id ID --operation-id ID... --main-branch BRANCH
                  [--include-remote] [--json]
`;

function parse(options, args = process.argv.slice(2), allowPositionals = true) {
  return parseArgs({ args, options, allowPositionals, strict: true });
}

function boolAndJsonOptions(extra = {}) {
  return { json: { type: "boolean", default: false }, ...extra };
}

function output(value, { json = false, human } = {}) {
  if (json || !human) console.log(stableStringify(value, 2));
  else console.log(human(value));
}

function requireCanonicalSource() {
  const packagePath = resolve(packageRoot, "package.json");
  const pluginPath = resolve(packageRoot, ".codex-plugin", "plugin.json");
  const agentsTemplate = resolve(packageRoot, "templates", "agents-block.md");
  if (![packagePath, pluginPath, agentsTemplate].every((path) => existsSync(path))) {
    throw new CliError(
      "Run init/sync from the installed codex-orchestration plugin package, not a repository-pinned snapshot",
    );
  }

  let packageMetadata;
  let pluginMetadata;
  try {
    packageMetadata = JSON.parse(readFileSync(packagePath, "utf8"));
    pluginMetadata = JSON.parse(readFileSync(pluginPath, "utf8"));
  } catch {
    throw new CliError("Installed codex-orchestration package metadata is not valid JSON");
  }
  if (
    packageMetadata.name !== "@wjmao/codex-flow"
    || packageMetadata.private !== true
    || packageMetadata.version !== PACKAGE_VERSION
    || !Array.isArray(packageMetadata.files)
    || !packageMetadata.files.includes("skills/")
    || pluginMetadata.name !== "codex-orchestration"
    || pluginMetadata.version !== PACKAGE_VERSION
    || pluginMetadata.skills !== "./skills/"
  ) {
    throw new CliError(
      `Installed codex-orchestration package metadata must exactly match version ${PACKAGE_VERSION}`,
    );
  }
}

async function loadConfig(gitRoot) {
  const manifestPath = resolve(gitRoot, ".codex", "orchestration", "version.json");
  const manifest = await readJson(manifestPath, { allowMissing: true, guardRoot: gitRoot });
  if (!manifest) {
    throw new CliError("Pinned Codex Flow runtime is missing; run the setup skill from the accepted plugin");
  }
  if (manifest.package_version !== PACKAGE_VERSION) {
    throw new CliError(
      `Installed Codex Flow ${manifest.package_version ?? "unknown"} requires explicit retirement before fresh ${PACKAGE_VERSION} installation`,
    );
  }
  const raw = await readJson(projectConfigPath(gitRoot), { allowMissing: true, guardRoot: gitRoot });
  if (!raw) throw new CliError("Project is not initialized; run codex-flow init from the canonical package");
  return validateProjectConfig(raw);
}

function withTaskOverrides(packet, values) {
  const result = structuredClone(packet);
  if (values.model !== undefined) result.model = values.model === "host-default" ? null : values.model;
  if (values["reasoning-effort"] !== undefined) {
    const effort = values["reasoning-effort"] === "host-default" ? null : values["reasoning-effort"];
    requireEnum(effort, REASONING_EFFORTS, "reasoning_effort");
    result.reasoning_effort = effort;
  }
  return result;
}

function repositoryOptions(git) {
  return {
    gitRoot: git.root,
    stateRoot: git.stateRoot,
    stateGuardRoot: git.commonDir,
  };
}

function recipientFromValues(values) {
  return {
    lineage_id: values["lineage-id"],
    thread_id: values["thread-id"],
    generation: requireInteger(Number(values.generation), "generation", { min: 1 }),
  };
}

async function commandInit(args) {
  requireCanonicalSource();
  const { values } = parse({
    plan: { type: "boolean", default: false },
    "apply-plan": { type: "string" },
    check: { type: "boolean", default: false },
    force: { type: "boolean", default: false },
    "project-id": { type: "string" },
    "max-concurrency": { type: "string" },
    model: { type: "string" },
    "reasoning-effort": { type: "string" },
    "setup-mode": { type: "string" },
    "agents-mode": { type: "string" },
    "external-agents-path": { type: "string" },
    "attest-external-agents": { type: "boolean", default: false },
    json: { type: "boolean", default: false },
  }, args);
  const selectedModes = [values.plan, Boolean(values["apply-plan"]), values.check].filter(Boolean).length;
  if (selectedModes !== 1) {
    throw new CliError("init requires exactly one of --plan, --apply-plan PLAN_ID, or --check");
  }
  if (values.check && (
    values.force
    || values["project-id"] !== undefined
    || values["max-concurrency"] !== undefined
    || values.model !== undefined
    || values["reasoning-effort"] !== undefined
    || values["setup-mode"] !== undefined
    || values["agents-mode"] !== undefined
    || values["external-agents-path"] !== undefined
    || values["attest-external-agents"]
  )) throw new CliError("init --check does not accept initialization changes");
  if (values["agents-mode"] !== undefined) {
    requireEnum(values["agents-mode"], ["managed", "external"], "agents_mode");
  }
  if (values["setup-mode"] !== undefined) {
    requireEnum(values["setup-mode"], ["new", "existing"], "setup_mode");
  }
  const git = gitSnapshot();
  const max = values["max-concurrency"] === undefined
    ? undefined
    : requireInteger(Number(values["max-concurrency"]), "max_concurrency", { min: 1, max: 32 });
  if (values["reasoning-effort"] !== undefined) {
    const effort = values["reasoning-effort"] === "host-default" ? null : values["reasoning-effort"];
    requireEnum(effort, REASONING_EFFORTS, "reasoning_effort");
  }
  const options = {
    ...repositoryOptions(git),
    packageRoot,
    repository: {
      branch: git.branch,
      revision: git.revision,
      cleanliness: git.cleanliness,
    },
    force: values.force,
    projectId: values["project-id"],
    maxParallelExecutors: max,
    defaultModel: values.model === "host-default" ? null : values.model,
    defaultReasoningEffort: values["reasoning-effort"] === "host-default" ? null : values["reasoning-effort"],
    setupMode: values["setup-mode"],
    agentsMode: values["agents-mode"],
    externalAgentsPath: values["external-agents-path"],
    attestExternalAgents: values["attest-external-agents"],
  };
  if (values.plan) {
    const result = await createInstallationPlan(options);
    output(result, {
      json: values.json,
      human: (item) => [
        `codex-flow installation plan: ${item.plan_id}`,
        `project: ${item.project_id}`,
        `AGENTS: ${item.agents.mode} ${item.agents.path ?? "unresolved"}`,
        `AGENTS lines: ${item.agents.before_lines ?? "missing"} -> ${item.agents.after_lines ?? "unresolved"}`,
        `planned changes: ${item.operations.length}`,
        `compatibility conflicts: ${item.conflicts.length}`,
        ...item.conflicts.map((entry) => `conflict: ${entry.message}`),
      ].join("\n"),
    });
    if (!result.applicable) process.exitCode = 1;
    return;
  }
  if (values.check) {
    const result = await checkRepositoryInstallation(options);
    output(result, {
      json: values.json,
      human: (item) => `codex-flow check passed for ${item.project_id} (unchanged)`,
    });
    return;
  }
  const result = await applyInstallationPlan(options, values["apply-plan"]);
  output(result, {
    json: values.json,
    human: (item) => `codex-flow initialization passed for ${item.project_id}${item.changed ? " (updated)" : " (unchanged)"}`,
  });
}

async function commandSync(args) {
  requireCanonicalSource();
  const { values } = parse({
    check: { type: "boolean", default: false },
    force: { type: "boolean", default: false },
  }, args);
  const git = discoverGit();
  const result = await synchronizeRepository({
    ...repositoryOptions(git),
    packageRoot,
    check: values.check,
    force: values.force,
  });
  output(result, {
    human: (item) => `codex-flow sync ${values.check ? "check passed" : item.changed ? "updated managed files" : "was already current"}`,
  });
}

async function commandConfig(args) {
  const [subcommand, ...rest] = args;
  const git = discoverGit();
  const config = await loadConfig(git.root);
  if (subcommand === "show") {
    const { values } = parse(boolAndJsonOptions(), rest);
    output(config, {
      json: values.json,
      human: (item) => [
        `Project: ${item.project_id}`,
        `Default model: ${item.default_model ?? "host default"}`,
        `Default reasoning effort: ${item.default_reasoning_effort ?? "host default"}`,
        `Maximum parallel executors: ${item.max_parallel_executors}`,
      ].join("\n"),
    });
    return;
  }
  if (subcommand === "set") {
    const { values } = parse(boolAndJsonOptions({
      model: { type: "string" },
      "reasoning-effort": { type: "string" },
      "max-concurrency": { type: "string" },
    }), rest);
    if (
      values.model === undefined
      && values["reasoning-effort"] === undefined
      && values["max-concurrency"] === undefined
    ) throw new CliError("config set requires at least one setting");
    const written = await withRepositoryManagementLock(repositoryOptions(git), async () => {
      const next = { ...await loadConfig(git.root) };
      if (values.model !== undefined) next.default_model = values.model === "host-default" ? null : values.model;
      if (values["reasoning-effort"] !== undefined) {
        const effort = values["reasoning-effort"] === "host-default" ? null : values["reasoning-effort"];
        requireEnum(effort, REASONING_EFFORTS, "default_reasoning_effort");
        next.default_reasoning_effort = effort;
      }
      if (values["max-concurrency"] !== undefined) {
        next.max_parallel_executors = requireInteger(Number(values["max-concurrency"]), "max_parallel_executors", {
          min: 1,
          max: 32,
        });
      }
      return writeProjectConfig(git.root, next);
    });
    output(written, {
      json: values.json,
      human: (item) => `Project defaults updated: ${item.default_model ?? "host default"} / ${item.default_reasoning_effort ?? "host default"}; max ${item.max_parallel_executors}`,
    });
    return;
  }
  throw new CliError("config requires show or set");
}

async function commandDoctor(args) {
  const { values } = parse(boolAndJsonOptions(), args);
  const result = await runDoctor(gitSnapshot());
  output(result, {
    json: values.json,
    human: (item) => [
      `codex-flow doctor: ${item.ok ? "PASS" : "FAIL"}`,
      `project: ${item.project?.project_id ?? "unconfigured"}`,
      `git: ${item.git.branch} ${item.git.revision.slice(0, 12)} (${item.git.cleanliness})`,
      `runtime: ${item.runtime?.package_version ?? "missing"}${item.runtime?.drift?.length ? `, ${item.runtime.drift.length} drift item(s)` : ""}`,
      `AGENTS integration: ${item.agents_contract?.mode ?? item.agents_block}`,
      `task-thread creation: ${item.thread_creation}`,
      `callbacks: ${item.callbacks.pending_count} pending, ${item.callbacks.consumed_count} consumed`,
      `urgent signals: ${item.urgent_signals.pending_count} pending, ${item.urgent_signals.consumed_count} consumed, ${item.urgent_signals.host_replay_count} host replay(s)`,
      `task operations: ${item.task_operations.total_count} total, ${item.task_operations.ambiguous_count} ambiguous, ${item.task_operations.host_session_blocked_count} session-blocked, ${item.task_operations.partial_evidence_count} partial-evidence, ${item.task_operations.rejected_before_release_count} rejected-before-release`,
      `recipient lineages: ${item.recipients.lineage_count}`,
      ...item.warnings.map((warning) => `warning: ${warning}`),
      ...item.errors.map((error) => `error: ${error}`),
    ].join("\n"),
  });
  if (!result.ok) process.exitCode = 1;
}

async function commandTask(args) {
  const [subcommand, ...rest] = args;
  const git = discoverGit();
  const config = await loadConfig(git.root);
  if (subcommand === "start") {
    const { values } = parse({ role: { type: "string" } }, rest);
    requireEnum(values.role, ["coordinator", "executor"], "role");
    const rolePath = resolve(git.root, ".codex", "orchestration", "roles", `${values.role}.md`);
    const role = await readFile(rolePath, "utf8").catch(() => {
      throw new CliError(`Pinned role entrypoint is missing: ${rolePath}`);
    });
    console.log([
      `Project: ${config.project_id}`,
      `Default task model: ${config.default_model ?? "host default"}`,
      `Default reasoning effort: ${config.default_reasoning_effort ?? "host default"}`,
      `Maximum parallel executors: ${config.max_parallel_executors}`,
      "Task creation capability: record a current host-session preflight; this CLI cannot infer it.",
      "",
      role.trim(),
      "",
    ].join("\n"));
    return;
  }
  if (subcommand === "packet") {
    const [action, ...packetArgs] = rest;
    if (!["validate", "render"].includes(action)) throw new CliError("task packet requires validate or render");
    const { values, positionals } = parse(boolAndJsonOptions({
      model: { type: "string" },
      "reasoning-effort": { type: "string" },
    }), packetArgs);
    if (positionals.length !== 1) throw new CliError("task packet requires exactly one JSON file");
    const raw = await readJson(resolve(positionals[0]));
    const packet = validateTaskPacket(withTaskOverrides(applyTaskDefaults(raw, config), values));
    if (action === "render") {
      if (values.json) output(packet, { json: true });
      else console.log(renderTaskPacket(packet));
    }
    else output(packet, {
      json: values.json,
      human: (item) => `Task packet ${item.task_id} is valid: ${item.model ?? "host default"} / ${item.reasoning_effort ?? "host default"}`,
    });
    return;
  }
  if (subcommand === "operation") {
    const [action, ...operationArgs] = rest;
    if (action === "prepare") {
      const { values } = parse(boolAndJsonOptions({ file: { type: "string" } }), operationArgs);
      const readiness = await gitLifecycleReadiness({ git, config });
      if (readiness.blocked) throw new CliError(`${readiness.message}; reconcile cleanup before launching another task wave`, 74);
      if (readiness.warning) console.error(`codex-flow: warning: ${readiness.message}`);
      const raw = await readJsonInput(values.file ? resolve(values.file) : null);
      const result = await prepareTaskOperation({
        stateRoot: git.stateRoot,
        projectId: config.project_id,
        packet: applyTaskDefaults(raw, config),
      });
      output(result, {
        json: values.json,
        human: (item) => `Task operation ${item.status}: ${item.operation_id}`,
      });
      if (result.status === "expired") process.exitCode = 74;
      return;
    }
    if (action === "attempt") {
      const { values } = parse(boolAndJsonOptions({
        "operation-id": { type: "string" },
        "timeout-seconds": { type: "string", default: "60" },
      }), operationArgs);
      const result = await beginTaskOperationAttempt({
        stateRoot: git.stateRoot,
        operationId: values["operation-id"],
        timeoutSeconds: Number(values["timeout-seconds"]),
      });
      output(result, {
        json: values.json,
        human: (item) => [
          `Task operation ${item.status}: ${item.operation_id ?? item.operation?.operation_id}`,
          `Attempt: ${item.attempt?.attempt_id ?? "already observed"}`,
          item.request ? `Create ${item.request.execution_kind} titled: ${item.request.title}` : null,
          item.request ? `Model/reasoning: ${item.request.model ?? "host default"} / ${item.request.reasoning_effort ?? "host default"}` : null,
        ].filter(Boolean).join("\n"),
      });
      return;
    }
    if (action === "bootstrap") {
      const { values } = parse(boolAndJsonOptions({
        "operation-id": { type: "string" },
        file: { type: "string" },
      }), operationArgs);
      const raw = await readJsonInput(values.file ? resolve(values.file) : null);
      const authorized = await authorizeHostWorktreeBootstrap({
        stateRoot: git.stateRoot,
        operationId: values["operation-id"],
        packet: applyTaskDefaults(raw, config),
      });
      const prompt = renderHostWorktreeBootstrap(authorized.packet, authorized.operation_id);
      if (values.json) output({
        operation_id: authorized.operation_id,
        attempt_id: authorized.attempt_id,
        prompt,
      }, { json: true });
      else console.log(prompt);
      return;
    }
    if (action === "preflight") {
      const { values } = parse(boolAndJsonOptions({
        "operation-id": { type: "string" },
        file: { type: "string" },
      }), operationArgs);
      const evidence = await readJsonInput(values.file ? resolve(values.file) : null);
      const result = await recordTaskOperationHostPreflight({
        stateRoot: git.stateRoot,
        operationId: values["operation-id"],
        evidence,
      });
      output(result, {
        json: values.json,
        human: (item) => {
          const active = item.host_preflights.find(
            (entry) => entry.preflight_id === item.active_host_preflight_id,
          );
          return [
            `Task operation ${item.status}: ${item.operation_id}`,
            `Host preflight: ${item.active_host_preflight_id}`,
            `Host session: ${active?.host_session_id ?? "none"}`,
          ].join("\n");
        },
      });
      if (result.status === "host-incompatible") process.exitCode = 74;
      return;
    }
    if (action === "reconcile") {
      const { values } = parse(boolAndJsonOptions({
        "operation-id": { type: "string" },
        "attempt-id": { type: "string" },
        outcome: { type: "string" },
        "object-id": { type: "string" },
        "actual-kind": { type: "string" },
        evidence: { type: "string" },
        "reason-code": { type: "string" },
      }), operationArgs);
      const evidence = values.evidence ? await readJson(resolve(values.evidence)) : null;
      const result = await reconcileTaskOperation({
        stateRoot: git.stateRoot,
        operationId: values["operation-id"],
        attemptId: values["attempt-id"],
        outcome: values.outcome,
        objectId: values["object-id"] ?? null,
        actualKind: values["actual-kind"] ?? null,
        evidence,
        reasonCode: values["reason-code"] ?? null,
      });
      output(result, {
        json: values.json,
        human: (item) => [
          `Task operation ${item.status}: ${item.operation_id}`,
          item.observation_policy?.state === "rejected"
            ? `Host observation policy rejected: ${item.observation_policy.reason_code}`
            : null,
        ].filter(Boolean).join("\n"),
      });
      if (result.observation_policy?.state === "rejected") process.exitCode = 74;
      return;
    }
    if (action === "reject") {
      const { values } = parse(boolAndJsonOptions({
        "operation-id": { type: "string" },
        "reason-code": { type: "string" },
        "host-object-state": { type: "string" },
      }), operationArgs);
      const result = await rejectTaskOperationBeforeRelease({
        stateRoot: git.stateRoot,
        operationId: values["operation-id"],
        reasonCode: values["reason-code"],
        hostObjectState: values["host-object-state"],
      });
      output(result, {
        json: values.json,
        human: (item) => `Task operation ${item.status}: ${item.operation_id}`,
      });
      return;
    }
    if (action === "release") {
      const { values } = parse(boolAndJsonOptions({
        "operation-id": { type: "string" },
        file: { type: "string" },
      }), operationArgs);
      const raw = await readJsonInput(values.file ? resolve(values.file) : null);
      const packet = applyTaskDefaults(raw, config);
      const authorization = await authorizeGitBoundTaskRelease({
        git,
        operationId: values["operation-id"],
        packet,
      });
      const prompt = renderReleasedTaskPacket(packet);
      if (values.json) output({ ...authorization, prompt }, { json: true });
      else console.log(prompt);
      return;
    }
    if (action === "status") {
      const { values } = parse(boolAndJsonOptions({ "operation-id": { type: "string" } }), operationArgs);
      const result = await taskOperationStatus({
        stateRoot: git.stateRoot,
        operationId: values["operation-id"] ?? null,
      });
      output(result, {
        json: values.json,
        human: (items) => items.length
          ? items.map((item) => [
            `${item.operation_id}: ${item.effective_status} (${item.request.execution_kind})`,
            `placement ${item.request.host_placement.mode}${item.request.host_placement.target_project_id ? ` -> ${item.request.host_placement.target_project_id}` : ""}`,
            item.observation_policy ? `observation policy ${item.observation_policy.state}${item.observation_policy.reason_code ? `: ${item.observation_policy.reason_code}` : ""}` : null,
            item.resolution ? `resolution ${item.resolution.disposition}` : null,
          ].filter(Boolean).join("; ")).join("\n")
          : "No task operations.",
      });
      return;
    }
    throw new CliError("task operation requires prepare, preflight, attempt, bootstrap, reconcile, reject, release, or status");
  }
  throw new CliError("task requires start or packet");
}

async function commandPlan(args) {
  const [subcommand, ...rest] = args;
  if (subcommand !== "validate") throw new CliError("plan requires validate");
  const { values, positionals } = parse(boolAndJsonOptions(), rest);
  if (positionals.length !== 1) throw new CliError("plan validate requires exactly one JSON file");
  const git = discoverGit();
  const config = await loadConfig(git.root);
  const result = validatePlan(await readJson(resolve(positionals[0])), {
    projectMaxConcurrency: config.max_parallel_executors,
  });
  output(result, {
    json: values.json,
    human: (item) => [
      `Plan ${item.plan_id} is valid with ${item.tasks.length} task(s).`,
      ...item.waves.map((wave, index) => `wave ${index + 1}: ${wave.join(", ")}`),
    ].join("\n"),
  });
}

async function commandRecipient(args) {
  const [subcommand, ...rest] = args;
  const git = discoverGit();
  await loadConfig(git.root);
  if (subcommand === "bind") {
    const { values } = parse(boolAndJsonOptions({
      "lineage-id": { type: "string" },
      "thread-id": { type: "string" },
      "fence-token": { type: "string" },
    }), rest);
    const result = await bindRecipient({
      stateRoot: git.stateRoot,
      recipient: {
        lineage_id: values["lineage-id"],
        thread_id: values["thread-id"],
        generation: 1,
      },
      fenceToken: values["fence-token"],
    });
    output(result, {
      json: values.json,
      human: (item) => [
        `Recipient ${item.status}: ${item.recipient.lineage_id} generation ${item.recipient.generation} -> ${item.recipient.thread_id}`,
        item.recipient.fence_token
          ? `Rebind fence token (store privately): ${item.recipient.fence_token}`
          : "Rebind fence token is redacted; retain the token returned by the original bind.",
      ].join("\n"),
    });
    return;
  }
  if (subcommand === "rebind") {
    const { values } = parse(boolAndJsonOptions({
      "lineage-id": { type: "string" },
      "thread-id": { type: "string" },
      generation: { type: "string" },
      "fence-token": { type: "string" },
      "next-fence-token": { type: "string" },
    }), rest);
    const result = await rebindRecipient({
      stateRoot: git.stateRoot,
      recipient: recipientFromValues(values),
      fenceToken: values["fence-token"],
      nextFenceToken: values["next-fence-token"],
    });
    output(result, {
      json: values.json,
      human: (item) => [
        `Recipient ${item.status}: ${item.recipient.lineage_id} generation ${item.recipient.generation} -> ${item.recipient.thread_id}`,
        `New rebind fence token (store privately): ${item.recipient.fence_token}`,
      ].join("\n"),
    });
    return;
  }
  if (subcommand === "status") {
    const { values } = parse(boolAndJsonOptions({ "lineage-id": { type: "string" } }), rest);
    const result = values["lineage-id"]
      ? await recipientStatus({ stateRoot: git.stateRoot, lineageId: values["lineage-id"] })
      : await recipientStatuses({ stateRoot: git.stateRoot });
    output(result, {
      json: values.json,
      human: (item) => {
        const entries = Array.isArray(item) ? item : item ? [item] : [];
        return entries.length
          ? entries.map((entry) => `${entry.lineage_id}: generation ${entry.current.generation} -> ${entry.current.thread_id} (${entry.binding_count} binding(s))`).join("\n")
          : "No recipient bindings.";
      },
    });
    return;
  }
  if (subcommand === "resolve") {
    const { values } = parse(boolAndJsonOptions({
      "lineage-id": { type: "string" },
      "thread-id": { type: "string" },
      generation: { type: "string" },
    }), rest);
    const result = await resolveRecipient({
      stateRoot: git.stateRoot,
      recipient: recipientFromValues(values),
    });
    output(result, {
      json: values.json,
      human: (item) => `Recipient resolves to generation ${item.recipient.generation} -> ${item.recipient.thread_id}${item.stale ? " (input was stale)" : ""}`,
    });
    return;
  }
  throw new CliError("recipient requires bind, rebind, status, or resolve");
}

async function commandCallback(args) {
  const [subcommand, ...rest] = args;
  const git = discoverGit();
  await loadConfig(git.root);
  if (subcommand === "deliver") {
    const { values } = parse(boolAndJsonOptions({ file: { type: "string" } }), rest);
    const receipt = await readJsonInput(values.file ? resolve(values.file) : null);
    const result = await deliverCallback({
      stateRoot: git.stateRoot,
      receipt,
    });
    output(result, { json: values.json, human: (item) => `Terminal callback ${item.status}: ${item.callback_id}` });
    return;
  }
  if (subcommand === "observe") {
    const { values } = parse(boolAndJsonOptions({
      "callback-id": { type: "string" },
      "lineage-id": { type: "string" },
      "thread-id": { type: "string" },
      generation: { type: "string" },
    }), rest);
    const result = await observeCallback({
      stateRoot: git.stateRoot,
      callbackId: values["callback-id"],
      recipient: recipientFromValues(values),
    });
    output(result, { json: values.json, human: (item) => `Terminal callback ${item.status}: ${item.callback_id}` });
    return;
  }
  if (subcommand === "consume") {
    const { values } = parse(boolAndJsonOptions({
      "callback-id": { type: "string" },
      "lineage-id": { type: "string" },
      "thread-id": { type: "string" },
      generation: { type: "string" },
      "executor-id": { type: "string" },
    }), rest);
    const result = await consumeCallback({
      stateRoot: git.stateRoot,
      callbackId: values["callback-id"],
      recipient: recipientFromValues(values),
      executorId: values["executor-id"],
    });
    output(result, { json: values.json, human: (item) => `Terminal callback ${item.status}: ${item.callback_id}` });
    return;
  }
  if (subcommand === "expire") {
    const { values } = parse(boolAndJsonOptions({
      "callback-id": { type: "string" },
      at: { type: "string" },
    }), rest);
    const now = values.at ?? Date.now();
    const result = values["callback-id"]
      ? await expireCallback({ stateRoot: git.stateRoot, callbackId: values["callback-id"], now })
      : await expireCallbacks({ stateRoot: git.stateRoot, now });
    output(result, {
      json: values.json,
      human: (item) => Array.isArray(item)
        ? item.map((entry) => `Terminal callback ${entry.status}: ${entry.callback_id}`).join("\n") || "No terminal callbacks."
        : `Terminal callback ${item.status}: ${item.callback_id}`,
    });
    return;
  }
  if (subcommand === "status") {
    const { values } = parse(boolAndJsonOptions(), rest);
    const result = await callbackStatus(git.stateRoot);
    output(result, {
      json: values.json,
      human: (item) => [
        `${item.pending.length} pending callback(s); ${item.consumed_count} consumed, ${item.superseded_count} superseded, ${item.expired_count} expired journal record(s).`,
        ...item.pending.map((entry) => `${entry.callback_id} ${entry.effective_integration} ${entry.classification} (${entry.executor_id})`),
      ].join("\n"),
    });
    return;
  }
  throw new CliError("callback requires deliver, observe, consume, expire, or status");
}

async function commandUrgent(args) {
  const [subcommand, ...rest] = args;
  const git = discoverGit();
  await loadConfig(git.root);
  if (subcommand === "persist") {
    const { values } = parse(boolAndJsonOptions({ file: { type: "string" } }), rest);
    const signal = await readJsonInput(values.file ? resolve(values.file) : null);
    const result = await persistUrgentSignal({ stateRoot: git.stateRoot, signal });
    output(result, {
      json: values.json,
      human: (item) => `Urgent signal ${item.status}: ${item.urgent_id}`,
    });
    return;
  }
  if (subcommand === "attempt") {
    const [action, ...actionArgs] = rest;
    if (action === "prepare") {
      const { values } = parse(boolAndJsonOptions({
        "urgent-id": { type: "string" },
        "attempt-sequence": { type: "string" },
        "retry-reason": { type: "string" },
      }), actionArgs);
      const result = await prepareUrgentAttempt({
        stateRoot: git.stateRoot,
        urgentId: values["urgent-id"],
        attemptSequence: Number(values["attempt-sequence"]),
        retryReason: values["retry-reason"] ?? null,
      });
      output(result, {
        json: values.json,
        human: (item) => [
          `Urgent delivery attempt ${item.status}: ${item.delivery_attempt_id}`,
          `Dispatch permitted: ${item.dispatch_permitted ? "yes" : "no"}`,
          `Host prompt: ${item.host_prompt}`,
        ].join("\n"),
      });
      return;
    }
    if (action === "reconcile") {
      const { values } = parse(boolAndJsonOptions({
        "urgent-id": { type: "string" },
        "delivery-attempt-id": { type: "string" },
        "host-call-result": { type: "string" },
      }), actionArgs);
      const result = await reconcileUrgentAttempt({
        stateRoot: git.stateRoot,
        urgentId: values["urgent-id"],
        deliveryAttemptId: values["delivery-attempt-id"],
        hostCallResult: values["host-call-result"],
      });
      output(result, {
        json: values.json,
        human: (item) => `Urgent delivery attempt ${item.status}: ${item.delivery_attempt_id}`,
      });
      return;
    }
    throw new CliError("urgent attempt requires prepare or reconcile");
  }
  if (subcommand === "observe") {
    const { values } = parse(boolAndJsonOptions({
      "urgent-id": { type: "string" },
      "delivery-attempt-id": { type: "string" },
      "lineage-id": { type: "string" },
      "thread-id": { type: "string" },
      generation: { type: "string" },
    }), rest);
    const result = await observeUrgentSignal({
      stateRoot: git.stateRoot,
      urgentId: values["urgent-id"],
      deliveryAttemptId: values["delivery-attempt-id"],
      recipient: recipientFromValues(values),
    });
    output(result, {
      json: values.json,
      human: (item) => [
        `Urgent signal ${item.status}: ${item.urgent_id} (${item.disposition})`,
        ...(item.consume_arguments ? [
          `Next: codex-flow urgent consume --urgent-id ${item.consume_arguments.urgent_id} --lineage-id ${item.consume_arguments.lineage_id} --thread-id ${item.consume_arguments.thread_id} --generation ${item.consume_arguments.generation} --sender-executor-id ${item.consume_arguments.sender_executor_id}`,
        ] : []),
      ].join("\n"),
    });
    return;
  }
  if (subcommand === "consume") {
    const { values } = parse(boolAndJsonOptions({
      "urgent-id": { type: "string" },
      "lineage-id": { type: "string" },
      "thread-id": { type: "string" },
      generation: { type: "string" },
      "sender-executor-id": { type: "string" },
    }), rest);
    const result = await consumeUrgentSignal({
      stateRoot: git.stateRoot,
      urgentId: values["urgent-id"],
      recipient: recipientFromValues(values),
      senderExecutorId: values["sender-executor-id"],
    });
    output(result, {
      json: values.json,
      human: (item) => `Urgent signal ${item.status}: ${item.urgent_id}`,
    });
    return;
  }
  if (subcommand === "expire") {
    const { values } = parse(boolAndJsonOptions({
      "urgent-id": { type: "string" },
      at: { type: "string" },
    }), rest);
    const now = values.at ?? Date.now();
    const result = values["urgent-id"]
      ? await expireUrgentSignal({ stateRoot: git.stateRoot, urgentId: values["urgent-id"], now })
      : await expireUrgentSignals({ stateRoot: git.stateRoot, now });
    output(result, {
      json: values.json,
      human: (item) => Array.isArray(item)
        ? item.map((entry) => `Urgent signal ${entry.status}: ${entry.urgent_id}`).join("\n") || "No urgent signals."
        : `Urgent signal ${item.status}: ${item.urgent_id}`,
    });
    return;
  }
  if (subcommand === "status") {
    const { values } = parse(boolAndJsonOptions(), rest);
    const result = await urgentSignalStatus(git.stateRoot);
    output(result, {
      json: values.json,
      human: (item) => [
        `${item.pending.length} pending urgent signal(s); ${item.consumed_count} consumed, ${item.superseded_count} superseded, ${item.expired_count} expired.`,
        `Observed duplicates: ${item.host_replay_count} host replay(s), ${item.sender_attempt_duplicate_count} additional sender attempt(s).`,
        ...item.pending.map((entry) => `${entry.urgent_id} ${entry.effective_state} ${entry.classification} (${entry.executor_id})`),
      ].join("\n"),
    });
    return;
  }
  throw new CliError("urgent requires persist, attempt, observe, consume, expire, or status");
}

async function commandLease(args) {
  const [subcommand, ...rest] = args;
  const git = discoverGit();
  await loadConfig(git.root);
  if (subcommand === "acquire") {
    const { values } = parse(boolAndJsonOptions({
      resource: { type: "string" },
      owner: { type: "string" },
      "ttl-seconds": { type: "string", default: "7200" },
      "break-expired": { type: "boolean", default: false },
    }), rest);
    const result = await acquireLease({
      stateRoot: git.stateRoot,
      resource: values.resource,
      owner: values.owner,
      ttlSeconds: Number(values["ttl-seconds"]),
      breakExpired: values["break-expired"],
    });
    output(result, {
      json: values.json,
      human: (item) => [
        `Lease ${item.status}: ${item.lease.resource} owned by ${item.lease.owner} until ${item.lease.expires_at}`,
        `Release token: ${item.lease.token}`,
      ].join("\n"),
    });
    return;
  }
  if (subcommand === "release") {
    const { values } = parse(boolAndJsonOptions({
      resource: { type: "string" },
      owner: { type: "string" },
      token: { type: "string" },
    }), rest);
    const result = await releaseLease({ stateRoot: git.stateRoot, resource: values.resource, owner: values.owner, token: values.token ?? null });
    output(result, { json: values.json, human: (item) => `Lease ${item.status}: ${item.resource}` });
    return;
  }
  if (subcommand === "status") {
    const { values } = parse(boolAndJsonOptions({ resource: { type: "string" } }), rest);
    const result = await leaseStatus({ stateRoot: git.stateRoot, resource: values.resource ?? null });
    output(result, {
      json: values.json,
      human: (items) => items.length ? items.map((item) => `${item.resource}: ${item.state}, owner ${item.owner}, expires ${item.expires_at}`).join("\n") : "No leases.",
    });
    return;
  }
  throw new CliError("lease requires acquire, release, or status");
}

async function commandGit(args) {
  const [subcommand, ...rest] = args;
  const git = discoverGit();
  const config = await loadConfig(git.root);
  if (subcommand === "bind") {
    const { values } = parse(boolAndJsonOptions({
      "operation-id": { type: "string" },
    }), rest);
    const result = await bindGitOwnership({
      git,
      operationId: values["operation-id"],
    });
    output(result, { json: values.json, human: (item) => `Git ownership bound: ${item.branch} -> ${item.operation_id}` });
    return;
  }
  if (subcommand === "integrate") {
    const { values } = parse(boolAndJsonOptions({
      "operation-id": { type: "string" },
      "main-branch": { type: "string" },
      "superseded-by": { type: "string" },
    }), rest);
    const result = await recordGitIntegration({
      git,
      operationId: values["operation-id"],
      mainBranch: values["main-branch"],
      supersededBy: values["superseded-by"] ?? null,
    });
    output(result, { json: values.json, human: (item) => `Git integration ${item.disposition}: ${item.operation_id}` });
    return;
  }
  if (subcommand === "status") {
    const { values } = parse(boolAndJsonOptions(), rest);
    const result = await gitLifecycleAudit({ git, config });
    output(result, {
      json: values.json,
      human: (item) => [
        `${item.items.length} owned Git task(s); ${item.eligible_count} cleanup-eligible; ${item.backlog_count} require reconciliation.`,
        ...item.items.map((entry) => `${entry.operation_id} ${entry.classification} ${entry.branch}`),
      ].join("\n"),
    });
    return;
  }
  throw new CliError("git requires bind, integrate, or status");
}

async function commandCleanup(args) {
  const [subcommand, ...rest] = args;
  const git = discoverGit();
  const config = await loadConfig(git.root);
  if (subcommand === "audit") {
    const { values } = parse(boolAndJsonOptions(), rest);
    const result = await cleanupAudit(git);
    output(result, {
      json: values.json,
      human: (item) => [
        `Cleanup audit only; no mutation performed. State size: ${item.state_size}.`,
        `Callbacks: ${item.callbacks.pending.length} pending, ${item.callbacks.consumed_count} consumed, ${item.callbacks.superseded_count} superseded, ${item.callbacks.expired_count} expired.`,
        `Task operations: ${item.task_operations.length}; recipient lineages: ${item.recipients.length}.`,
        `Git tasks: ${item.git_lifecycle.items.length}; ${item.git_lifecycle.eligible_count} cleanup-eligible; ${item.git_lifecycle.backlog_count} require reconciliation.`,
        `Leases: ${item.leases.filter((lease) => lease.state === "active").length} active, ${item.leases.filter((lease) => lease.state === "expired").length} expired.`,
        ...item.recommendations.map((recommendation) => `review: ${recommendation}`),
      ].join("\n"),
    });
    return;
  }
  if (["plan", "apply"].includes(subcommand)) {
    const { values } = parse(boolAndJsonOptions({
      "operation-id": { type: "string", multiple: true },
      "main-branch": { type: "string" },
      "include-remote": { type: "boolean", default: false },
      "plan-id": { type: "string" },
    }), rest);
    const common = {
      git,
      config,
      operationIds: values["operation-id"] ?? [],
      mainBranch: values["main-branch"],
      includeRemote: values["include-remote"],
    };
    let result;
    try {
      result = subcommand === "plan"
        ? await createGitCleanupPlan(common)
        : await applyGitCleanupPlan({ ...common, expectedPlanId: values["plan-id"] });
    } catch (error) {
      if (!(error instanceof GitCleanupApplyError)) throw error;
      output(error.result, {
        json: values.json,
        human: (item) => [
          `Git cleanup ${item.status}: ${item.plan_id}`,
          ...item.completed_actions.map((action) => `  completed: ${action}`),
          `  stopped at: ${item.failed_action}`,
          `  error: ${item.error}`,
          "Run cleanup audit and create a fresh plan; do not retry this plan.",
        ].join("\n"),
      });
      process.exitCode = error.exitCode;
      return;
    }
    output(result, {
      json: values.json,
      human: (item) => subcommand === "plan"
        ? [
          `Git cleanup plan ${item.plan_id}: ${item.candidates.length} task(s)`,
          ...item.candidates.flatMap((candidate) => [
            `${candidate.operation_id} ${candidate.disposition}`,
            ...(candidate.remove_worktree ? [`  remove worktree: ${candidate.worktree_path}`] : []),
            ...(candidate.delete_local ? [`  delete local branch: ${candidate.branch}`] : []),
            ...(candidate.remote ? [`  delete remote branch: ${candidate.remote.remote}/${candidate.remote.ref}`] : []),
          ]),
        ].join("\n")
        : [
          `Git cleanup ${item.status}: ${item.plan.plan_id}`,
          ...item.completed_actions.map((action) => `  completed: ${action}`),
        ].join("\n"),
    });
    return;
  }
  throw new CliError("cleanup requires audit, plan, or apply");
}

async function main() {
  const [command, ...args] = process.argv.slice(2);
  if (!command || command === "help" || command === "--help" || command === "-h") {
    console.log(HELP);
    return;
  }
  if (command === "--version" || command === "version") {
    console.log(PACKAGE_VERSION);
    return;
  }
  if (command === "init") return commandInit(args);
  if (command === "sync") return commandSync(args);
  if (command === "config") return commandConfig(args);
  if (command === "doctor") return commandDoctor(args);
  if (command === "task") return commandTask(args);
  if (command === "plan") return commandPlan(args);
  if (command === "recipient") return commandRecipient(args);
  if (command === "callback") return commandCallback(args);
  if (command === "urgent") return commandUrgent(args);
  if (command === "git") return commandGit(args);
  if (command === "lease") return commandLease(args);
  if (command === "cleanup") return commandCleanup(args);
  throw new CliError(`Unknown command: ${command}\n\n${HELP}`);
}

try {
  await main();
} catch (error) {
  if (error instanceof CliError) {
    console.error(`codex-flow: ${error.message}`);
    process.exitCode = error.exitCode;
  } else {
    console.error(error?.stack ?? String(error));
    process.exitCode = 1;
  }
}
