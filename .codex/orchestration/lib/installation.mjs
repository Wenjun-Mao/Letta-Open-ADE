import { randomUUID } from "node:crypto";
import { readFile, rename, rm } from "node:fs/promises";
import { dirname, relative, resolve, sep } from "node:path";
import { TextDecoder } from "node:util";
import {
  assertNoSymlinkComponents,
  atomicWrite,
  atomicWriteJson,
  CliError,
  ensureDirectory,
  PACKAGE_VERSION,
  pathExists,
  readJson,
  sha256,
  stableStringify,
} from "./core.mjs";
import {
  defaultProjectConfig,
  EXTERNAL_AGENTS_CONTRACT_VERSION,
  orchestrationRoot,
  projectConfigPath,
  validateProjectConfig,
  validateRepositoryRelativePath,
} from "./config.mjs";
import {
  inspectAgentsBlock,
  inspectManaged,
  removeManagedAgentsBlock,
  targetSnapshot,
  withRepositoryManagementLock,
} from "./managed.mjs";

const PLAN_SCHEMA_VERSION = 1;
const utf8Decoder = new TextDecoder("utf-8", { fatal: true });

function encodeJson(value) {
  return Buffer.from(`${stableStringify(value, 2)}\n`);
}

function lineCount(value) {
  if (value === null || value.length === 0) return 0;
  const text = Buffer.isBuffer(value) ? value.toString("utf8") : String(value);
  return text.endsWith("\n")
    ? text.slice(0, -1).split(/\r?\n/).length
    : text.split(/\r?\n/).length;
}

function repositoryRelativePath(gitRoot, path) {
  return relative(gitRoot, path).split(sep).join("/");
}

async function readOptionalBytes(gitRoot, path, label) {
  await assertNoSymlinkComponents(gitRoot, path, label);
  try {
    return await readFile(path);
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw error;
  }
}

function sameBytes(left, right) {
  if (left === null || right === null) return left === right;
  return Buffer.from(left).equals(Buffer.from(right));
}

function changeRecord(gitRoot, path, before, after, owner) {
  if (sameBytes(before, after)) return null;
  return {
    path: repositoryRelativePath(gitRoot, path),
    action: before === null ? "create" : after === null ? "delete" : "update",
    owner,
    before_sha256: before === null ? null : sha256(before),
    after_sha256: after === null ? null : sha256(after),
    before_lines: before === null ? null : lineCount(before),
    after_lines: after === null ? null : lineCount(after),
  };
}

function conflict(code, message, path = null) {
  return { code, message, path };
}

async function buildAgentsState({ gitRoot, packageRoot, existingConfig, options, conflicts }) {
  const existingMode = existingConfig?.agents_integration.mode ?? null;
  const mode = options.agentsMode ?? existingMode ?? "managed";
  if (!["managed", "external"].includes(mode)) {
    throw new CliError("agents_mode must be one of: managed, external");
  }

  if (mode === "managed") {
    if (options.externalAgentsPath !== undefined || options.attestExternalAgents) {
      conflicts.push(conflict(
        "agents-mode-options",
        "External AGENTS options are not allowed with managed mode",
        "AGENTS.md",
      ));
    }
    try {
      const inspected = await inspectAgentsBlock({ gitRoot, packageRoot });
      const existing = await readOptionalBytes(gitRoot, inspected.agentsPath, "AGENTS.md path");
      return {
        mode,
        path: inspected.agentsPath,
        existing,
        desired: Buffer.from(inspected.desired),
        integration: { mode: "managed" },
        attestation_reused: false,
      };
    } catch (error) {
      conflicts.push(conflict("agents-markers", error.message, "AGENTS.md"));
      return {
        mode,
        path: resolve(gitRoot, "AGENTS.md"),
        existing: null,
        desired: null,
        integration: { mode: "managed" },
        attestation_reused: false,
      };
    }
  }

  const configuredExternal = existingMode === "external"
    ? existingConfig.agents_integration
    : null;
  const relativePath = options.externalAgentsPath ?? configuredExternal?.path;
  if (!relativePath) {
    conflicts.push(conflict(
      "external-agents-path",
      "External AGENTS mode requires --external-agents-path",
    ));
    return {
      mode,
      path: null,
      existing: null,
      desired: null,
      integration: null,
      attestation_reused: false,
    };
  }
  validateRepositoryRelativePath(relativePath, "external_agents_path");
  if (relativePath === ".git" || relativePath.startsWith(".git/")) {
    throw new CliError("external_agents_path cannot be inside Git metadata");
  }
  if (relativePath === ".codex/orchestration" || relativePath.startsWith(".codex/orchestration/")) {
    throw new CliError("external_agents_path cannot be inside the managed codex-flow runtime");
  }
  const path = resolve(gitRoot, relativePath);
  const existing = await readOptionalBytes(gitRoot, path, "External AGENTS instruction path");
  if (existing === null) {
    conflicts.push(conflict(
      "external-agents-missing",
      `External AGENTS instruction file is missing: ${relativePath}`,
      relativePath,
    ));
    return {
      mode,
      path,
      existing,
      desired: null,
      integration: null,
      attestation_reused: false,
    };
  }

  let desired;
  try {
    desired = Buffer.from(removeManagedAgentsBlock(utf8Decoder.decode(existing)));
  } catch (error) {
    conflicts.push(conflict("external-agents-content", error.message, relativePath));
    desired = existing;
  }
  if (desired.toString("utf8").trim() === "") {
    conflicts.push(conflict(
      "external-agents-empty",
      "External AGENTS instruction file would be empty after removing the managed block",
      relativePath,
    ));
  }

  const desiredHash = sha256(desired);
  const canReuse = configuredExternal
    && configuredExternal.path === relativePath
    && configuredExternal.sha256 === desiredHash;
  if (!options.attestExternalAgents && !canReuse) {
    conflicts.push(conflict(
      "external-agents-attestation",
      "External AGENTS mode requires --attest-external-agents for this exact file state",
      relativePath,
    ));
  }
  return {
    mode,
    path,
    existing,
    desired,
    integration: {
      mode: "external",
      path: relativePath,
      sha256: desiredHash,
      contract_version: EXTERNAL_AGENTS_CONTRACT_VERSION,
      attested: true,
    },
    attestation_reused: !options.attestExternalAgents && canReuse,
  };
}

function desiredProjectConfig(gitRoot, existingConfig, agentsIntegration, options, conflicts) {
  if (existingConfig && options.projectId && options.projectId !== existingConfig.project_id) {
    conflicts.push(conflict(
      "project-identity",
      `Existing project_id ${existingConfig.project_id} cannot be replaced by ${options.projectId}`,
      ".codex/orchestration/project.json",
    ));
  }
  const base = existingConfig ?? defaultProjectConfig(gitRoot, {
    projectId: options.projectId,
    maxParallelExecutors: options.maxParallelExecutors,
    defaultModel: options.defaultModel,
    defaultReasoningEffort: options.defaultReasoningEffort,
    agentsIntegration,
  });
  return validateProjectConfig({
    ...base,
    schema_version: 4,
    project_id: existingConfig?.project_id ?? base.project_id,
    max_parallel_executors: options.maxParallelExecutors ?? base.max_parallel_executors,
    default_model: options.defaultModel === undefined ? base.default_model : options.defaultModel,
    default_reasoning_effort: options.defaultReasoningEffort === undefined
      ? base.default_reasoning_effort
      : options.defaultReasoningEffort,
    agents_integration: agentsIntegration ?? base.agents_integration,
    git_lifecycle: base.git_lifecycle,
  });
}

async function buildInstallationPlan(options) {
  const conflicts = [];
  if (options.setupMode && !["new", "existing"].includes(options.setupMode)) {
    throw new CliError("setup_mode must be one of: new, existing");
  }
  if (options.setupMode) {
    const expectedBranch = options.setupMode === "new"
      ? "codex/codex-flow-v0.5-bootstrap"
      : "codex/codex-flow-v0.5-adoption";
    if (!options.projectId) {
      conflicts.push(conflict(
        "setup-project-id",
        "Plugin setup requires an explicit stable project_id; never derive it from a disposable setup worktree name",
        ".codex/orchestration/project.json",
      ));
    }
    if (options.repository?.branch !== expectedBranch) {
      conflicts.push(conflict(
        "setup-branch",
        `${options.setupMode} setup must run on ${expectedBranch}`,
      ));
    }
    if (options.repository?.cleanliness !== "clean") {
      conflicts.push(conflict(
        "setup-cleanliness",
        `${options.setupMode} setup requires a clean worktree before planning`,
      ));
    }
  }
  const configPath = projectConfigPath(options.gitRoot);
  const rawConfig = await readJson(configPath, { allowMissing: true, guardRoot: options.gitRoot });
  const existingConfig = rawConfig ? validateProjectConfig(rawConfig) : null;
  const agents = await buildAgentsState({
    gitRoot: options.gitRoot,
    packageRoot: options.packageRoot,
    existingConfig,
    options,
    conflicts,
  });
  const config = desiredProjectConfig(
    options.gitRoot,
    existingConfig,
    agents.integration,
    options,
    conflicts,
  );
  const managed = await inspectManaged({ gitRoot: options.gitRoot, packageRoot: options.packageRoot });
  if (
    managed.existingManifest
    && managed.existingManifest.package_version !== PACKAGE_VERSION
  ) {
    conflicts.push(conflict(
      "installed-package-version",
      `Installed Codex Flow ${managed.existingManifest.package_version} requires explicit retirement before fresh ${PACKAGE_VERSION} installation`,
      ".codex/orchestration/version.json",
    ));
  }
  if (managed.drift.length > 0 && !options.force) {
    for (const item of managed.drift) {
      conflicts.push(conflict(
        "managed-runtime-drift",
        `Managed runtime has local drift: ${item.path} (${item.state})`,
        `.codex/orchestration/${item.path}`,
      ));
    }
  }
  for (const path of managed.unexpected) {
    conflicts.push(conflict(
      "managed-runtime-unowned",
      `Orchestration directory contains a file not owned by codex-flow: ${path}`,
      `.codex/orchestration/${path}`,
    ));
  }

  const operations = [];
  for (const file of managed.sourceFiles) {
    const target = resolve(managed.targetRoot, file.relativePath);
    const before = await readOptionalBytes(options.gitRoot, target, "Managed runtime path");
    const record = changeRecord(options.gitRoot, target, before, file.contents, "codex-flow-runtime");
    if (record) operations.push(record);
  }
  const versionPath = resolve(managed.targetRoot, "version.json");
  const versionRecord = changeRecord(
    options.gitRoot,
    versionPath,
    await readOptionalBytes(options.gitRoot, versionPath, "Managed runtime version path"),
    encodeJson(managed.desiredManifest),
    "codex-flow-runtime",
  );
  if (versionRecord) operations.push(versionRecord);
  const configRecord = changeRecord(
    options.gitRoot,
    configPath,
    await readOptionalBytes(options.gitRoot, configPath, "Project configuration path"),
    encodeJson(config),
    "codex-flow-config",
  );
  if (configRecord) operations.push(configRecord);
  for (const obsolete of managed.obsolete) {
    const path = resolve(managed.targetRoot, obsolete);
    const before = await readOptionalBytes(options.gitRoot, path, "Obsolete managed runtime path");
    const record = changeRecord(options.gitRoot, path, before, null, "codex-flow-runtime");
    if (record) operations.push(record);
  }
  if (agents.path && agents.desired !== null) {
    const record = changeRecord(
      options.gitRoot,
      agents.path,
      agents.existing,
      agents.desired,
      agents.mode === "managed" ? "codex-flow-agents-block" : "external-agents-owner",
    );
    if (record) operations.push(record);
  }
  operations.sort((left, right) => left.path.localeCompare(right.path));
  conflicts.sort((left, right) => `${left.code}:${left.path ?? ""}`.localeCompare(`${right.code}:${right.path ?? ""}`));

  const activationRoots = [];
  if (operations.some((item) => item.path.startsWith(".codex/orchestration/"))) {
    activationRoots.push(".codex/orchestration");
  }
  const agentsPath = agents.path ? repositoryRelativePath(options.gitRoot, agents.path) : null;
  if (agentsPath && operations.some((item) => item.path === agentsPath)) activationRoots.push(agentsPath);

  const base = {
    schema_version: PLAN_SCHEMA_VERSION,
    kind: "codex-flow-install-plan",
    package_version: PACKAGE_VERSION,
    setup_mode: options.setupMode ?? null,
    repository: {
      root: options.gitRoot,
      branch: options.repository?.branch ?? null,
      revision: options.repository?.revision ?? null,
      cleanliness: options.repository?.cleanliness ?? null,
    },
    project_id: config.project_id,
    agents: {
      mode: agents.mode,
      path: agentsPath,
      before_sha256: agents.existing === null ? null : sha256(agents.existing),
      after_sha256: agents.desired === null ? null : sha256(agents.desired),
      before_lines: agents.existing === null ? null : lineCount(agents.existing),
      after_lines: agents.desired === null ? null : lineCount(agents.desired),
      contract_version: agents.integration?.contract_version ?? null,
      attestation_reused: agents.attestation_reused,
    },
    operations,
    activation_roots: activationRoots,
    conflicts,
    applicable: conflicts.length === 0,
  };
  const plan = { ...base, plan_id: sha256(stableStringify(base)) };
  return { plan, desired: { agents, config, managed } };
}

export async function createInstallationPlan(options) {
  return (await buildInstallationPlan(options)).plan;
}

async function restoreAgents(gitRoot, agents) {
  if (!agents.path || agents.desired === null || sameBytes(agents.existing, agents.desired)) return;
  if (agents.existing === null) await rm(agents.path, { force: true });
  else await atomicWrite(agents.path, agents.existing, { guardRoot: gitRoot });
}

async function activateInstallation(options, built, hooks) {
  const { plan, desired } = built;
  if (plan.operations.length === 0) {
    return { changed: false, plan_id: plan.plan_id, project_id: plan.project_id };
  }
  const targetRoot = desired.managed.targetRoot;
  const parent = dirname(targetRoot);
  await ensureDirectory(parent, { guardRoot: options.gitRoot });
  const nonce = randomUUID();
  const staging = resolve(parent, `.orchestration-stage-${nonce}`);
  const backup = resolve(parent, `.orchestration-backup-${nonce}`);
  await ensureDirectory(staging, { guardRoot: options.gitRoot });

  let movedCurrent = false;
  let runtimeActivated = false;
  let agentsActivated = false;
  let committed = false;
  try {
    for (const file of desired.managed.sourceFiles) {
      await atomicWrite(resolve(staging, file.relativePath), file.contents, { guardRoot: options.gitRoot });
    }
    await atomicWriteJson(resolve(staging, "version.json"), desired.managed.desiredManifest, {
      guardRoot: options.gitRoot,
    });
    await atomicWriteJson(resolve(staging, "project.json"), desired.config, { guardRoot: options.gitRoot });

    const currentSnapshot = await targetSnapshot(options.gitRoot, targetRoot);
    if (stableStringify(currentSnapshot) !== stableStringify(desired.managed.snapshot)) {
      throw new CliError("Managed runtime changed after planning; refusing activation", 75);
    }
    if (desired.agents.path) {
      const currentAgents = await readOptionalBytes(options.gitRoot, desired.agents.path, "AGENTS instruction path");
      if (!sameBytes(currentAgents, desired.agents.existing)) {
        throw new CliError("AGENTS instructions changed after planning; refusing activation", 75);
      }
    }

    if (await pathExists(targetRoot)) {
      await rename(targetRoot, backup);
      movedCurrent = true;
    }
    await rename(staging, targetRoot);
    runtimeActivated = true;

    if (
      desired.agents.path
      && desired.agents.desired !== null
      && !sameBytes(desired.agents.existing, desired.agents.desired)
    ) {
      await atomicWrite(desired.agents.path, desired.agents.desired, { guardRoot: options.gitRoot });
      agentsActivated = true;
    }
    if (hooks?.afterRuntimeActivation) await hooks.afterRuntimeActivation();
    committed = true;
    if (movedCurrent) await rm(backup, { recursive: true, force: true }).catch(() => {});
    return { changed: true, plan_id: plan.plan_id, project_id: plan.project_id };
  } catch (error) {
    const rollbackErrors = [];
    if (agentsActivated) {
      try {
        await restoreAgents(options.gitRoot, desired.agents);
      } catch (rollbackError) {
        rollbackErrors.push(rollbackError);
      }
    }
    if (runtimeActivated) {
      try {
        await rm(targetRoot, { recursive: true, force: true });
      } catch (rollbackError) {
        rollbackErrors.push(rollbackError);
      }
    }
    if (movedCurrent && await pathExists(backup)) {
      try {
        if (await pathExists(targetRoot)) {
          throw new CliError(`Rollback could not clear activated runtime; prior bytes remain at ${backup}`);
        }
        await rename(backup, targetRoot);
      } catch (rollbackError) {
        rollbackErrors.push(rollbackError);
      }
    }
    if (rollbackErrors.length > 0) {
      throw new AggregateError(
        [error, ...rollbackErrors],
        `Installation failed and rollback was incomplete: ${rollbackErrors.map((item) => item.message).join("; ")}`,
      );
    }
    throw error;
  } finally {
    await rm(staging, { recursive: true, force: true });
    if (committed) await rm(backup, { recursive: true, force: true }).catch(() => {});
  }
}

export async function applyInstallationPlan(options, expectedPlanId, hooks = {}) {
  if (typeof expectedPlanId !== "string" || !/^[a-f0-9]{64}$/.test(expectedPlanId)) {
    throw new CliError("--apply-plan requires a valid plan_id");
  }
  return withRepositoryManagementLock(options, async () => {
    const built = await buildInstallationPlan(options);
    if (built.plan.plan_id !== expectedPlanId) {
      throw new CliError(
        `Installation plan changed; expected ${expectedPlanId}, current ${built.plan.plan_id}`,
        75,
      );
    }
    if (!built.plan.applicable) {
      throw new CliError(`Installation plan has ${built.plan.conflicts.length} unresolved conflict(s)`);
    }
    return activateInstallation(options, built, hooks);
  });
}

export async function checkRepositoryInstallation(options) {
  const plan = await createInstallationPlan(options);
  if (!plan.applicable) {
    throw new CliError(`Repository installation has ${plan.conflicts.length} compatibility conflict(s)`);
  }
  if (plan.operations.length > 0) {
    throw new CliError(`Repository installation requires ${plan.operations.length} planned change(s)`);
  }
  return {
    project_id: plan.project_id,
    changed: false,
    plan_id: plan.plan_id,
    target_root: orchestrationRoot(options.gitRoot),
  };
}
