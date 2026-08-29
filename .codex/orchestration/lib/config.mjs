import { basename, isAbsolute, resolve } from "node:path";
import {
  atomicWriteJson,
  CliError,
  requireObject,
  requireEnum,
  requireExactFields,
  requireInteger,
  requireNullableText,
  requireText,
} from "./core.mjs";

export const REASONING_EFFORTS = [
  null, "none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra",
];

export const EXTERNAL_AGENTS_CONTRACT_VERSION = "1";
export const DEFAULT_GIT_LIFECYCLE = {
  protected_branches: ["main", "master"],
  warn_at: 5,
  block_at: 10,
};

export function validateGitLifecycle(value) {
  requireObject(value, "git_lifecycle");
  requireExactFields(value, {
    required: ["protected_branches", "warn_at", "block_at"],
  }, "git_lifecycle");
  if (!Array.isArray(value.protected_branches) || value.protected_branches.length > 32) {
    throw new CliError("git_lifecycle.protected_branches must contain at most 32 branch names");
  }
  const protectedBranches = value.protected_branches.map((branch, index) => (
    requireText(branch, `git_lifecycle.protected_branches[${index}]`, { max: 256 })
  ));
  if (new Set(protectedBranches).size !== protectedBranches.length) {
    throw new CliError("git_lifecycle.protected_branches must be unique");
  }
  const warnAt = requireInteger(value.warn_at, "git_lifecycle.warn_at", { min: 1, max: 10000 });
  const blockAt = requireInteger(value.block_at, "git_lifecycle.block_at", { min: 1, max: 10000 });
  if (blockAt < warnAt) throw new CliError("git_lifecycle.block_at must be greater than or equal to warn_at");
  return {
    protected_branches: protectedBranches,
    warn_at: warnAt,
    block_at: blockAt,
  };
}

export function validateRepositoryRelativePath(value, label = "path") {
  requireText(value, label, { max: 512 });
  if (
    isAbsolute(value)
    || value.includes("\\")
    || value.split("/").some((part) => part === "" || part === "." || part === "..")
  ) {
    throw new CliError(`${label} must be a normalized repository-relative path using forward slashes`);
  }
  return value;
}

export function validateAgentsIntegration(value) {
  requireObject(value, "agents_integration");
  if (value.mode === "managed") {
    requireExactFields(value, { required: ["mode"] }, "agents_integration");
    return { mode: "managed" };
  }
  if (value.mode === "external") {
    requireExactFields(value, {
      required: ["mode", "path", "sha256", "contract_version", "attested"],
    }, "agents_integration");
    validateRepositoryRelativePath(value.path, "agents_integration.path");
    if (typeof value.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(value.sha256)) {
      throw new CliError("agents_integration.sha256 must be a lowercase SHA-256 digest");
    }
    if (value.contract_version !== EXTERNAL_AGENTS_CONTRACT_VERSION) {
      throw new CliError("Unsupported external AGENTS contract version");
    }
    if (value.attested !== true) {
      throw new CliError("External AGENTS integration must be explicitly attested");
    }
    return {
      mode: "external",
      path: value.path,
      sha256: value.sha256,
      contract_version: value.contract_version,
      attested: true,
    };
  }
  throw new CliError("agents_integration.mode must be one of: managed, external");
}

export function orchestrationRoot(gitRoot) {
  return resolve(gitRoot, ".codex", "orchestration");
}

export function projectConfigPath(gitRoot) {
  return resolve(orchestrationRoot(gitRoot), "project.json");
}

export function inferProjectId(gitRoot) {
  const raw = basename(gitRoot).replace(/[^A-Za-z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "");
  if (raw === "") throw new CliError("Could not infer a safe project id");
  return raw;
}

export function defaultProjectConfig(gitRoot, overrides = {}) {
  return {
    schema_version: 4,
    project_id: overrides.projectId ?? inferProjectId(gitRoot),
    max_parallel_executors: overrides.maxParallelExecutors ?? 2,
    default_model: overrides.defaultModel === undefined ? "gpt-5.6-terra" : overrides.defaultModel,
    default_reasoning_effort: overrides.defaultReasoningEffort === undefined
      ? "xhigh"
      : overrides.defaultReasoningEffort,
    agents_integration: overrides.agentsIntegration ?? { mode: "managed" },
    git_lifecycle: validateGitLifecycle(overrides.gitLifecycle ?? DEFAULT_GIT_LIFECYCLE),
  };
}

export function validateProjectConfig(value) {
  if (value?.schema_version !== 4) {
    throw new CliError("codex-flow v0.5 requires a fresh schema 4 initialization; older orchestration state is not migrated");
  }
  requireExactFields(value, {
    required: [
      "schema_version",
      "project_id",
      "max_parallel_executors",
      "default_model",
      "default_reasoning_effort",
      "agents_integration",
      "git_lifecycle",
    ],
  }, "Project configuration");
  requireText(value.project_id, "project_id", { max: 128, safeId: true });
  requireInteger(value.max_parallel_executors, "max_parallel_executors", { min: 1, max: 32 });
  requireNullableText(value.default_model, "default_model", { max: 128 });
  requireEnum(value.default_reasoning_effort, REASONING_EFFORTS, "default_reasoning_effort");
  return {
    schema_version: 4,
    project_id: value.project_id,
    max_parallel_executors: value.max_parallel_executors,
    default_model: value.default_model,
    default_reasoning_effort: value.default_reasoning_effort,
    agents_integration: validateAgentsIntegration(value.agents_integration),
    git_lifecycle: validateGitLifecycle(value.git_lifecycle),
  };
}

export async function writeProjectConfig(gitRoot, value) {
  const config = validateProjectConfig(value);
  await atomicWriteJson(projectConfigPath(gitRoot), config, { guardRoot: gitRoot });
  return config;
}
