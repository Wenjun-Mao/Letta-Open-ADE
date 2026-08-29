import { spawnSync } from "node:child_process";
import { lstat, readdir, realpath } from "node:fs/promises";
import { basename, dirname, isAbsolute, resolve } from "node:path";
import {
  assertNoSymlinkComponents,
  atomicWriteJson,
  CliError,
  ensureExactJson,
  readJson,
  requireEnum,
  requireExactFields,
  requireInteger,
  requireText,
  sha256,
  stableStringify,
  withProcessLock,
} from "./core.mjs";
import { REASONING_EFFORTS } from "./config.mjs";
import {
  requireAvailableGitBranch,
  gitCommonDirectoryForState,
  gitLocalBranchRevision,
  gitSnapshot,
} from "./git.mjs";
import {
  isLaunchExpired,
  validateLaunchDeadline,
  validateHostPlacement,
  validateHostPlacementForTask,
  validateTaskBaseline,
  validateTaskEnvironment,
  validateTaskPacket,
} from "./task-packet.mjs";

const OPERATION_KIND = "codex-flow-task-create-operation";
const MAX_ATTEMPTS = 32;
const MAX_HOST_PREFLIGHTS = 64;
const SHA_PATTERN = /^[0-9a-f]{40,64}$/;
const GIT_TIMEOUT_MS = 30_000;
const EXPLICIT_TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/;
const SUPPORT_STATES = ["supported", "unsupported", "unknown", "not-required"];
const SUPPORT_BASES = [
  "tool-schema",
  "open-selector",
  "closed-selector",
  "fixed-role",
  "host-contract",
  "not-required",
  "unavailable",
];
const DISCOVERY_QUERY_STATES = ["supported", "rejected", "unavailable", "not-applicable"];
const DISCOVERY_FALLBACKS = ["bounded-unfiltered", "exact-read", "none"];
const HOST_SESSION_FAILURE_CODES = [
  "argument-serialization",
  "adapter-unavailable",
  "backend-unavailable",
  "schema-runtime-drift",
  "host-control-failure",
];
const TITLE_SOURCES = ["host-observed", "unavailable"];
const TITLE_NORMALIZATIONS = ["none", "bounded-host-write", "not-applicable"];
const VISIBILITY_SOURCES = ["host-observed", "host-contract"];
const SELECTOR_EVIDENCE_SOURCES = [
  "host-observed",
  "host-accepted",
  "role-contract",
  "unavailable",
];
const HOST_LABEL_SOURCES = ["host-observed", "unavailable"];
const EXECUTION_PATH_SOURCES = ["host-observed", "not-required", "unavailable"];
const PROJECT_PLACEMENT_SOURCES = ["host-observed", "host-accepted", "not-applicable", "unavailable"];
const REJECTION_REASON_CODES = [
  "operator-cancelled",
  "host-object-archived",
  "pre-release-validation-failed",
  "host-placement-rejected",
];
const OBSERVATION_POLICY_REASON_CODES = [
  "execution-kind-mismatch",
  "title-unavailable",
  "title-mismatch",
  "visibility-mismatch",
  "model-mismatch",
  "reasoning-effort-mismatch",
  "execution-path-unverified",
  "project-placement-unavailable",
  "project-placement-not-applicable",
  "project-placement-mismatch",
  "project-placement-unexpected",
];

function operationGuardRoot(stateRoot) {
  return gitCommonDirectoryForState(stateRoot);
}

function safeChild(directory, filename) {
  const path = resolve(directory, filename);
  if (dirname(path) !== directory || basename(path) !== filename) {
    throw new CliError("Unsafe task-operation state path");
  }
  return path;
}

function operationPaths(stateRoot, operationId) {
  requireText(operationId, "operation_id", { max: 96, safeId: true });
  const root = resolve(stateRoot, "task-operations");
  return {
    root,
    record: safeChild(resolve(root, "records"), `${operationId}.json`),
    lock: safeChild(resolve(root, "locks"), `${operationId}.lock.json`),
  };
}

function gitLifecycleMutationLockPath(stateRoot) {
  const root = resolve(stateRoot, "git-lifecycle");
  return safeChild(root, "mutation.lock.json");
}

function nowIso(now = Date.now()) {
  return new Date(now).toISOString();
}

function gitResult(cwd, args, label) {
  const result = spawnSync("git", args, {
    cwd,
    env: { ...process.env, GIT_OPTIONAL_LOCKS: "0", GIT_TERMINAL_PROMPT: "0" },
    encoding: "utf8",
    timeout: GIT_TIMEOUT_MS,
  });
  if (result.status !== 0) throw new CliError(String(result.stderr || result.stdout).trim() || `${label} failed`);
  return result.stdout.trim();
}

function gitRefTip(cwd, ref) {
  const result = spawnSync("git", ["rev-parse", "--verify", ref], {
    cwd,
    env: { ...process.env, GIT_OPTIONAL_LOCKS: "0", GIT_TERMINAL_PROMPT: "0" },
    encoding: "utf8",
    timeout: GIT_TIMEOUT_MS,
  });
  if (result.status === 0) return result.stdout.trim();
  if (result.status === 128) return null;
  throw new CliError(String(result.stderr || result.stdout).trim() || "Git ref inspection failed");
}

function launchExpired(deadline, now = Date.now()) {
  return isLaunchExpired(deadline, now);
}

function requireTimestamp(value, label) {
  const text = requireText(value, label, { max: 64 });
  if (!EXPLICIT_TIMESTAMP_PATTERN.test(text) || !Number.isFinite(Date.parse(text))) {
    throw new CliError(`${label} must be an ISO timestamp with an explicit UTC offset`);
  }
  return text;
}

function operationIdFromFields(projectId, taskId, runId, executionKind, hostPlacement) {
  return `task-operation-v2-${sha256(stableStringify({
    schema_version: 2,
    project_id: projectId,
    task_id: taskId,
    run_id: runId,
    execution_kind: executionKind,
    host_placement: hostPlacement,
  }))}`;
}

async function canonicalExistingPath(path, label) {
  try {
    return await realpath(resolve(path));
  } catch (error) {
    if (error?.code === "ENOENT") throw new CliError(`${label} does not exist`);
    throw error;
  }
}

async function authenticateTaskBaseline({ stateRoot, baseline, environment }) {
  if (environment.type === "projectless") return;

  const sourcePath = environment.type === "host-worktree"
    ? environment.repository_path
    : environment.project_path;
  const projectRoot = await canonicalExistingPath(sourcePath, "Task packet repository path");
  const snapshot = gitSnapshot(projectRoot);
  const discoveredRoot = await canonicalExistingPath(snapshot.root, "Discovered Git worktree root");
  if (projectRoot !== discoveredRoot) {
    throw new CliError("Task packet repository path must identify an exact Git worktree root");
  }

  const operationCommon = await canonicalExistingPath(
    gitCommonDirectoryForState(stateRoot),
    "Task-operation Git common directory",
  );
  const projectCommon = await canonicalExistingPath(snapshot.commonDir, "Task packet Git common directory");
  if (operationCommon !== projectCommon) {
    throw new CliError("Task packet project does not share this operation journal's Git common directory");
  }
  if (environment.type === "host-worktree") {
    if (gitLocalBranchRevision(projectRoot, environment.starting_branch) !== baseline.revision) {
      throw new CliError("Task packet baseline revision does not match the host-worktree starting branch");
    }
    requireAvailableGitBranch(projectRoot, environment.executor_branch);
  } else {
    if (baseline.revision !== snapshot.revision) {
      throw new CliError("Task packet baseline revision does not match the project HEAD");
    }
    const cleanliness = snapshot.cleanliness === "clean" ? "clean" : "dirty-authorized";
    if (baseline.cleanliness !== cleanliness) {
      throw new CliError("Task packet baseline cleanliness does not match the project worktree");
    }
  }
}

export function taskOperationIdFor(projectId, packet) {
  const validated = validateTaskPacket(packet);
  return operationIdFromFields(
    projectId,
    validated.task_id,
    validated.run_id,
    validated.execution_kind,
    validated.host_placement,
  );
}

function requireNullableText(value, label, options = {}) {
  return value === null ? null : requireText(value, label, options);
}

function validateSupportEvidence(value, label) {
  requireExactFields(value, { required: ["state", "basis"] }, label);
  const state = requireEnum(value.state, SUPPORT_STATES, `${label}.state`);
  const basis = requireEnum(value.basis, SUPPORT_BASES, `${label}.basis`);
  if ((state === "not-required") !== (basis === "not-required")) {
    throw new CliError(`${label} not-required state and basis must match`);
  }
  if (state === "unknown" && basis !== "unavailable") {
    throw new CliError(`${label} unknown support requires unavailable evidence`);
  }
  if (state === "unsupported" && ["not-required", "unavailable", "open-selector"].includes(basis)) {
    throw new CliError(`${label} unsupported state requires positive closed-contract evidence`);
  }
  if (state === "supported" && ["not-required", "unavailable"].includes(basis)) {
    throw new CliError(`${label} supported state requires positive evidence`);
  }
  return { state, basis };
}

export function validateHostCapabilityEvidence(value) {
  requireExactFields(value, {
    required: [
      "schema_version", "adapter_id", "host_session_id", "checked_at",
      "execution_kind", "environment_type", "placement_mode", "support", "thread_discovery",
    ],
  }, "Host capability evidence");
  if (value.schema_version !== 3) throw new CliError("Unsupported host capability evidence schema_version");
  requireExactFields(value.support, {
    required: ["execution_kind", "environment", "execution_path", "project_placement", "model", "reasoning_effort"],
  }, "Host capability support");
  requireExactFields(value.thread_discovery, {
    required: ["query", "fallback"],
  }, "Host thread-discovery evidence");
  const query = requireEnum(
    value.thread_discovery.query,
    DISCOVERY_QUERY_STATES,
    "thread_discovery.query",
  );
  const fallback = requireEnum(
    value.thread_discovery.fallback,
    DISCOVERY_FALLBACKS,
    "thread_discovery.fallback",
  );
  if (query === "supported" && fallback !== "none") {
    throw new CliError("Supported filtered discovery cannot declare a fallback");
  }
  if (query === "not-applicable" && fallback !== "none") {
    throw new CliError("Not-applicable thread discovery cannot declare a fallback");
  }
  const executionKind = requireEnum(value.execution_kind, ["task-thread", "subagent"], "execution_kind");
  const placementMode = requireEnum(value.placement_mode, [
    "same-project", "cross-project", "projectless", "inherited",
  ], "placement_mode");
  const environmentType = requireEnum(
    value.environment_type,
    ["local", "host-worktree", "projectless"],
    "environment_type",
  );
  if (executionKind === "task-thread") {
    if (query === "not-applicable" || (query !== "supported" && fallback === "none")) {
      throw new CliError("Task-thread capability evidence requires a bounded reread path");
    }
  } else if (query !== "not-applicable" || fallback !== "none") {
    throw new CliError("Subagent capability evidence must mark thread discovery not-applicable");
  }
  if (executionKind === "subagent" && placementMode !== "inherited") {
    throw new CliError("Subagent capability evidence must use inherited placement");
  }
  if (executionKind === "task-thread" && placementMode === "inherited") {
    throw new CliError("Task-thread capability evidence cannot use inherited placement");
  }
  const support = {
    execution_kind: validateSupportEvidence(value.support.execution_kind, "support.execution_kind"),
    environment: validateSupportEvidence(value.support.environment, "support.environment"),
    execution_path: validateSupportEvidence(value.support.execution_path, "support.execution_path"),
    project_placement: validateSupportEvidence(value.support.project_placement, "support.project_placement"),
    model: validateSupportEvidence(value.support.model, "support.model"),
    reasoning_effort: validateSupportEvidence(value.support.reasoning_effort, "support.reasoning_effort"),
  };
  if (["projectless", "inherited"].includes(placementMode) && support.project_placement.state !== "not-required") {
    throw new CliError("Projectless and inherited placement capability must be not-required");
  }
  if (["same-project", "cross-project"].includes(placementMode) && support.project_placement.state === "not-required") {
    throw new CliError("Project-backed placement capability cannot be not-required");
  }
  return {
    schema_version: 3,
    adapter_id: requireText(value.adapter_id, "adapter_id", { max: 128, safeId: true }),
    host_session_id: requireText(value.host_session_id, "host_session_id", { max: 128, safeId: true }),
    checked_at: requireTimestamp(value.checked_at, "checked_at"),
    execution_kind: executionKind,
    environment_type: environmentType,
    placement_mode: placementMode,
    support,
    thread_discovery: { query, fallback },
  };
}

function hostPreflightIdFor(evidence) {
  return `host-preflight-v3-${sha256(stableStringify(validateHostCapabilityEvidence(evidence)))}`;
}

function validateStoredHostPreflight(value) {
  if (value === null) return null;
  requireExactFields(value, {
    required: [
      "preflight_id", "schema_version", "adapter_id", "host_session_id", "checked_at",
      "execution_kind", "environment_type", "placement_mode", "support", "thread_discovery",
    ],
  }, "Stored host preflight");
  const evidence = validateHostCapabilityEvidence({
    schema_version: value.schema_version,
    adapter_id: value.adapter_id,
    host_session_id: value.host_session_id,
    checked_at: value.checked_at,
    execution_kind: value.execution_kind,
    environment_type: value.environment_type,
    placement_mode: value.placement_mode,
    support: value.support,
    thread_discovery: value.thread_discovery,
  });
  const preflightId = requireText(value.preflight_id, "preflight_id", { max: 96, safeId: true });
  if (preflightId !== hostPreflightIdFor(evidence)) throw new CliError("Host preflight ID is invalid");
  return { preflight_id: preflightId, ...evidence };
}

function validateTaskRequest(value) {
  requireExactFields(value, {
    required: [
      "task_id", "run_id", "role", "execution_kind", "title", "launch_deadline",
      "model", "reasoning_effort", "baseline", "environment", "host_placement",
    ],
  }, "Task operation request");
  const executionKind = requireEnum(value.execution_kind, ["task-thread", "subagent"], "request.execution_kind");
  const environment = validateTaskEnvironment(value.environment, "request.environment");
  const hostPlacement = validateHostPlacement(value.host_placement, "request.host_placement");
  validateHostPlacementForTask({ executionKind, environment, hostPlacement });
  return {
    task_id: requireText(value.task_id, "request.task_id", { max: 128, safeId: true }),
    run_id: requireText(value.run_id, "request.run_id", { max: 128, safeId: true }),
    role: requireEnum(value.role, ["coordinator", "executor"], "request.role"),
    execution_kind: executionKind,
    title: requireText(value.title, "request.title", { max: 160 }),
    launch_deadline: validateLaunchDeadline(value.launch_deadline, "request.launch_deadline"),
    model: requireNullableText(value.model, "request.model", { max: 128 }),
    reasoning_effort: requireEnum(value.reasoning_effort, REASONING_EFFORTS, "request.reasoning_effort"),
    baseline: validateTaskBaseline(value.baseline, "request.baseline"),
    environment,
    host_placement: hostPlacement,
  };
}

function preflightIncompatibility(request, preflight) {
  if (preflight.execution_kind !== request.execution_kind) {
    throw new CliError("Host preflight execution kind does not match the task request");
  }
  if (preflight.environment_type !== request.environment.type) {
    throw new CliError("Host preflight environment type does not match the task request");
  }
  if (preflight.placement_mode !== request.host_placement.mode) {
    throw new CliError("Host preflight placement mode does not match the task request");
  }
  const checks = [
    ["execution-kind", preflight.support.execution_kind.state, true],
    ["environment", preflight.support.environment.state, true],
    ["execution-path", preflight.support.execution_path.state, request.environment.type === "host-worktree"],
    ["project-placement", preflight.support.project_placement.state, request.host_placement.target_project_id !== null],
    ["model", preflight.support.model.state, request.model !== null],
    ["reasoning-effort", preflight.support.reasoning_effort.state, request.reasoning_effort !== null],
  ];
  for (const [field, state, required] of checks) {
    if (!required) {
      if (state !== "not-required") {
        throw new CliError(`Host preflight ${field} support must be not-required when the task does not request it`);
      }
      continue;
    }
    if (state === "supported") continue;
    return `${field}-${state === "unsupported" ? "unsupported" : "unverified"}`;
  }
  return null;
}

function validateAttempt(value, index) {
  const label = `Task operation attempts[${index}]`;
  requireExactFields(value, {
    required: [
      "attempt_id", "sequence", "status", "started_at", "ambiguous_after", "finished_at",
      "host_preflight_id", "failure_code",
    ],
  }, label);
  const status = requireEnum(value.status, [
    "dispatching", "ambiguous", "not-created", "observed", "failed", "host-session-blocked",
  ], `${label}.status`);
  const failureCode = value.failure_code === null
    ? null
    : requireEnum(value.failure_code, HOST_SESSION_FAILURE_CODES, `${label}.failure_code`);
  if ((status === "host-session-blocked") !== (failureCode !== null)) {
    throw new CliError(`${label} host-session status and failure code are inconsistent`);
  }
  return {
    attempt_id: requireText(value.attempt_id, `${label}.attempt_id`, { max: 96, safeId: true }),
    sequence: requireInteger(value.sequence, `${label}.sequence`, { min: 1, max: MAX_ATTEMPTS }),
    status,
    started_at: requireTimestamp(value.started_at, `${label}.started_at`),
    ambiguous_after: requireTimestamp(value.ambiguous_after, `${label}.ambiguous_after`),
    finished_at: value.finished_at === null
      ? null
      : requireTimestamp(value.finished_at, `${label}.finished_at`),
    host_preflight_id: requireText(value.host_preflight_id, `${label}.host_preflight_id`, {
      max: 96,
      safeId: true,
    }),
    failure_code: failureCode,
  };
}

function validateTitleEvidence(value) {
  requireExactFields(value, { required: ["source", "value", "normalization"] }, "title evidence");
  const source = requireEnum(value.source, TITLE_SOURCES, "title evidence.source");
  const normalization = requireEnum(value.normalization, TITLE_NORMALIZATIONS, "title evidence.normalization");
  const title = requireNullableText(value.value, "title evidence.value", { max: 160 });
  if (source === "unavailable" && (title !== null || normalization !== "not-applicable")) {
    throw new CliError("Unavailable title evidence must have a null value and not-applicable normalization");
  }
  if (source === "host-observed" && (title === null || !["none", "bounded-host-write"].includes(normalization))) {
    throw new CliError("Host-observed title evidence requires a value and bounded normalization state");
  }
  return { source, value: title, normalization };
}

function validateVisibilityEvidence(value) {
  requireExactFields(value, { required: ["source", "value"] }, "visibility evidence");
  const source = requireEnum(value.source, VISIBILITY_SOURCES, "visibility evidence.source");
  if (typeof value.value !== "boolean") throw new CliError("visibility evidence.value must be boolean");
  return { source, value: value.value };
}

function validateSelectorObservation(value, label, { reasoning = false } = {}) {
  requireExactFields(value, { required: ["source", "value"] }, label);
  const source = requireEnum(value.source, SELECTOR_EVIDENCE_SOURCES, `${label}.source`);
  const selected = value.value === null
    ? null
    : reasoning
      ? requireEnum(value.value, REASONING_EFFORTS, `${label}.value`)
      : requireText(value.value, `${label}.value`, { max: 128 });
  if (source === "unavailable" && selected !== null) {
    throw new CliError(`${label} unavailable evidence must have a null value`);
  }
  if (source !== "unavailable" && selected === null) {
    throw new CliError(`${label} ${source} evidence requires a value`);
  }
  return { source, value: selected };
}

function validateHostLabelEvidence(value) {
  requireExactFields(value, { required: ["source", "value"] }, "host label evidence");
  const source = requireEnum(value.source, HOST_LABEL_SOURCES, "host label evidence.source");
  const label = requireNullableText(value.value, "host label evidence.value", { max: 160 });
  if ((source === "unavailable") !== (label === null)) {
    throw new CliError("Host label source and value are inconsistent");
  }
  return { source, value: label };
}

function validateExecutionPathEvidence(value) {
  requireExactFields(value, { required: ["source", "value"] }, "execution path evidence");
  const source = requireEnum(value.source, EXECUTION_PATH_SOURCES, "execution path evidence.source");
  const path = requireNullableText(value.value, "execution path evidence.value", { max: 1024 });
  if (source === "host-observed") {
    if (path === null || !isAbsolute(path)) {
      throw new CliError("Host-observed execution path must be an absolute path");
    }
  } else if (path !== null) {
    throw new CliError(`${source} execution path evidence must have a null value`);
  }
  return { source, value: path };
}

function validateProjectPlacementEvidence(value) {
  requireExactFields(value, { required: ["source", "value"] }, "project placement evidence");
  const source = requireEnum(value.source, PROJECT_PLACEMENT_SOURCES, "project placement evidence.source");
  const projectId = value.value === null
    ? null
    : requireText(value.value, "project placement evidence.value", { max: 128, safeId: true });
  if (["host-observed", "host-accepted"].includes(source) && projectId === null) {
    throw new CliError(`${source} project placement evidence requires an exact project ID`);
  }
  if (["not-applicable", "unavailable"].includes(source) && projectId !== null) {
    throw new CliError(`${source} project placement evidence must have a null value`);
  }
  return { source, value: projectId };
}

function validateObservationEvidence(value) {
  requireExactFields(value, {
    required: [
      "schema_version", "title", "visibility", "model", "reasoning_effort",
      "host_label", "execution_path", "project_placement",
    ],
  }, "Host observation evidence");
  if (value.schema_version !== 3) throw new CliError("Unsupported host observation evidence schema_version");
  return {
    schema_version: 3,
    title: validateTitleEvidence(value.title),
    visibility: validateVisibilityEvidence(value.visibility),
    model: validateSelectorObservation(value.model, "model evidence"),
    reasoning_effort: validateSelectorObservation(value.reasoning_effort, "reasoning evidence", { reasoning: true }),
    host_label: validateHostLabelEvidence(value.host_label),
    execution_path: validateExecutionPathEvidence(value.execution_path),
    project_placement: validateProjectPlacementEvidence(value.project_placement),
  };
}

export function validateHostObservationEvidence(value) {
  return validateObservationEvidence(value);
}

function rejectedObservationPolicy(reasonCode) {
  return { state: "rejected", reason_code: reasonCode };
}

function observationPolicyFor(observed, request) {
  const { actual_kind: actualKind, evidence } = observed;
  if (actualKind !== request.execution_kind) {
    return rejectedObservationPolicy("execution-kind-mismatch");
  }
  if (actualKind === "task-thread") {
    if (evidence.title.source === "unavailable") {
      return rejectedObservationPolicy("title-unavailable");
    }
    if (evidence.title.value !== request.title) {
      return rejectedObservationPolicy("title-mismatch");
    }
  } else if (evidence.title.source !== "unavailable" && evidence.title.value !== request.title) {
    return rejectedObservationPolicy("title-mismatch");
  }
  if (evidence.visibility.value !== (actualKind === "task-thread")) {
    return rejectedObservationPolicy("visibility-mismatch");
  }
  if (
    request.model !== null
    && evidence.model.source !== "unavailable"
    && evidence.model.value !== request.model
  ) return rejectedObservationPolicy("model-mismatch");
  if (
    request.reasoning_effort !== null
    && evidence.reasoning_effort.source !== "unavailable"
    && evidence.reasoning_effort.value !== request.reasoning_effort
  ) return rejectedObservationPolicy("reasoning-effort-mismatch");
  if (request.environment.type === "host-worktree") {
    if (evidence.execution_path.source !== "host-observed") {
      return rejectedObservationPolicy("execution-path-unverified");
    }
  } else if (evidence.execution_path.source !== "not-required") {
    return rejectedObservationPolicy("execution-path-unverified");
  }
  const expectedProjectId = request.host_placement.target_project_id;
  const placement = evidence.project_placement;
  if (expectedProjectId === null) {
    if (placement.source !== "not-applicable" || placement.value !== null) {
      return rejectedObservationPolicy("project-placement-unexpected");
    }
  } else {
    if (placement.source === "unavailable") {
      return rejectedObservationPolicy("project-placement-unavailable");
    }
    if (placement.source === "not-applicable") {
      return rejectedObservationPolicy("project-placement-not-applicable");
    }
    if (placement.value !== expectedProjectId) {
      return rejectedObservationPolicy("project-placement-mismatch");
    }
  }
  return { state: "accepted", reason_code: null };
}

function observationEvidenceQuality(observed, request) {
  if (observed === null) return null;
  const gaps = [];
  if (observed.evidence.title.source === "unavailable") gaps.push("title-unavailable");
  if (observed.evidence.visibility.source !== "host-observed") {
    gaps.push(`visibility-${observed.evidence.visibility.source}`);
  }
  if (request.model !== null && observed.evidence.model.source !== "host-observed") {
    gaps.push(`model-${observed.evidence.model.source}`);
  }
  if (request.reasoning_effort !== null && observed.evidence.reasoning_effort.source !== "host-observed") {
    gaps.push(`reasoning-effort-${observed.evidence.reasoning_effort.source}`);
  }
  if (
    request.environment.type === "host-worktree"
    && observed.evidence.execution_path.source !== "host-observed"
  ) gaps.push(`execution-path-${observed.evidence.execution_path.source}`);
  if (
    request.host_placement.target_project_id !== null
    && observed.evidence.project_placement.source !== "host-observed"
  ) gaps.push(`project-placement-${observed.evidence.project_placement.source}`);
  return { quality: gaps.length === 0 ? "complete" : "partial", gaps };
}

function validateObserved(value) {
  if (value === null) return null;
  requireExactFields(value, {
    required: ["object_id", "actual_kind", "evidence", "observed_at"],
  }, "Task operation observed result");
  const actualKind = requireEnum(value.actual_kind, ["task-thread", "subagent"], "observed.actual_kind");
  return {
    object_id: requireText(value.object_id, "observed.object_id", { max: 256, safeId: true }),
    actual_kind: actualKind,
    evidence: validateObservationEvidence(value.evidence),
    observed_at: requireTimestamp(value.observed_at, "observed.observed_at"),
  };
}

function validateObservationPolicy(value, request, observed) {
  if (observed === null) {
    if (value !== null) throw new CliError("Task operation without an observed host object cannot retain observation policy");
    return null;
  }
  requireExactFields(value, { required: ["state", "reason_code"] }, "Task operation observation policy");
  const state = requireEnum(value.state, ["accepted", "rejected"], "observation_policy.state");
  const reasonCode = value.reason_code === null
    ? null
    : requireEnum(value.reason_code, OBSERVATION_POLICY_REASON_CODES, "observation_policy.reason_code");
  if ((state === "accepted") !== (reasonCode === null)) {
    throw new CliError("Task operation observation policy state and reason are inconsistent");
  }
  const expected = observationPolicyFor(observed, request);
  if (stableStringify({ state, reason_code: reasonCode }) !== stableStringify(expected)) {
    throw new CliError("Task operation observation policy does not match its request and observed evidence");
  }
  return expected;
}

function validateSettledBranchClaim(value, request, observed, operationId) {
  if (value === null) return null;
  requireExactFields(value, { required: ["claim", "local_branch_state"] }, "resolution.branch_claim_settlement");
  if (request.environment.type !== "host-worktree") {
    throw new CliError("Only host-worktree rejection may settle a branch claim");
  }
  const claim = value.claim;
  requireExactFields(claim, {
    required: [
      "schema_version", "kind", "operation_id", "object_id", "worktree_path",
      "branch", "baseline_revision", "claimed_at", "claim_hash",
    ],
  }, "resolution branch claim");
  if (claim.schema_version !== 1 || claim.kind !== "codex-flow-git-branch-claim") {
    throw new CliError("Unsupported settled Git branch claim");
  }
  const result = {
    schema_version: 1,
    kind: "codex-flow-git-branch-claim",
    operation_id: requireText(claim.operation_id, "resolution branch claim.operation_id", { max: 96, safeId: true }),
    object_id: requireText(claim.object_id, "resolution branch claim.object_id", { max: 256, safeId: true }),
    worktree_path: requireText(claim.worktree_path, "resolution branch claim.worktree_path", { max: 2048 }),
    branch: requireText(claim.branch, "resolution branch claim.branch", { max: 256 }),
    baseline_revision: requireText(claim.baseline_revision, "resolution branch claim.baseline_revision", { min: 40, max: 64 }),
    claimed_at: requireTimestamp(claim.claimed_at, "resolution branch claim.claimed_at"),
    claim_hash: requireText(claim.claim_hash, "resolution branch claim.claim_hash", { max: 96, safeId: true }),
  };
  if (!SHA_PATTERN.test(result.baseline_revision) || !/^[0-9a-f]{64}$/.test(result.claim_hash)) {
    throw new CliError("Settled Git branch claim hash is invalid");
  }
  const { claim_hash: ignored, ...base } = result;
  if (sha256(stableStringify(base)) !== result.claim_hash) throw new CliError("Settled Git branch claim hash is invalid");
  if (
    result.operation_id !== operationId
    || result.object_id !== observed.object_id
    || result.worktree_path !== observed.evidence.execution_path.value
    || result.branch !== request.environment.executor_branch
    || result.baseline_revision !== request.baseline.revision
  ) throw new CliError("Settled Git branch claim does not match task-operation authority");
  return {
    claim: result,
    local_branch_state: requireEnum(value.local_branch_state, ["absent"], "resolution branch claim.local_branch_state"),
  };
}

function validateRejectionResolution(value, request, observed, operationId) {
  if (value === null) return null;
  requireExactFields(value, {
    required: ["disposition", "reason_code", "host_object_state", "execution_path_state", "branch_claim_settlement", "recorded_at"],
  }, "Task operation resolution");
  if (observed === null) {
    throw new CliError("Rejected-before-release resolution requires an observed host object");
  }
  const disposition = requireEnum(value.disposition, ["rejected-before-release"], "resolution.disposition");
  const reasonCode = requireEnum(value.reason_code, REJECTION_REASON_CODES, "resolution.reason_code");
  const hostObjectState = requireEnum(value.host_object_state, ["archived"], "resolution.host_object_state");
  const executionPathState = requireEnum(
    value.execution_path_state,
    ["absent", "not-applicable"],
    "resolution.execution_path_state",
  );
  const requiresAbsentPath = request.environment.type === "host-worktree";
  if (requiresAbsentPath && executionPathState !== "absent") {
    throw new CliError("Host-worktree rejection requires an absent execution path");
  }
  if (!requiresAbsentPath && executionPathState !== "not-applicable") {
    throw new CliError("Non-host-worktree rejection must mark execution path not-applicable");
  }
  return {
    disposition,
    reason_code: reasonCode,
    host_object_state: hostObjectState,
    execution_path_state: executionPathState,
    branch_claim_settlement: validateSettledBranchClaim(value.branch_claim_settlement, request, observed, operationId),
    recorded_at: requireTimestamp(value.recorded_at, "resolution.recorded_at"),
  };
}

function validateIncompatibility(value) {
  if (value === null) return null;
  requireExactFields(value, {
    required: [
      "type", "stage", "reason_code", "preflight_id", "host_session_id",
      "attempt_id", "recorded_at",
    ],
  }, "Task operation incompatibility");
  const type = requireEnum(value.type, ["selector-incompatible", "host-session-failure"], "incompatibility.type");
  const stage = requireEnum(value.stage, ["preflight", "dispatch"], "incompatibility.stage");
  const reasonCode = requireText(value.reason_code, "incompatibility.reason_code", { max: 64, safeId: true });
  if (type === "host-session-failure" && !HOST_SESSION_FAILURE_CODES.includes(reasonCode)) {
    throw new CliError("Host-session incompatibility reason is invalid");
  }
  if (type === "selector-incompatible" && !/^(?:execution-kind|environment|execution-path|project-placement|model|reasoning-effort)-(?:unsupported|unverified)$/.test(reasonCode)) {
    throw new CliError("Selector incompatibility reason is invalid");
  }
  const attemptId = requireNullableText(value.attempt_id, "incompatibility.attempt_id", { max: 96, safeId: true });
  if ((stage === "dispatch") !== (attemptId !== null)) {
    throw new CliError("Task incompatibility stage and attempt identity are inconsistent");
  }
  if (type === "selector-incompatible" && stage !== "preflight") {
    throw new CliError("Selector incompatibility must be recorded at preflight");
  }
  if (type === "host-session-failure" && stage !== "dispatch") {
    throw new CliError("Host-session failure must be bound to a dispatch attempt");
  }
  return {
    type,
    stage,
    reason_code: reasonCode,
    preflight_id: requireText(value.preflight_id, "incompatibility.preflight_id", { max: 96, safeId: true }),
    host_session_id: requireText(value.host_session_id, "incompatibility.host_session_id", { max: 128, safeId: true }),
    attempt_id: attemptId,
    recorded_at: requireTimestamp(value.recorded_at, "incompatibility.recorded_at"),
  };
}

function validateOperationRecord(value) {
  requireExactFields(value, {
    required: [
      "schema_version", "kind", "operation_id", "project_id", "packet_hash", "request",
      "host_preflights", "active_host_preflight_id", "status", "attempts", "observed", "incompatibility",
      "observation_policy", "resolution", "created_at", "updated_at",
    ],
  }, "Task operation record");
  if (value.schema_version !== 9 || value.kind !== OPERATION_KIND) {
    throw new CliError("Unsupported task-operation record");
  }
  const request = validateTaskRequest(value.request);
  if (!Array.isArray(value.attempts) || value.attempts.length > MAX_ATTEMPTS) {
    throw new CliError(`Task operation attempts must contain at most ${MAX_ATTEMPTS} entries`);
  }
  const projectId = requireText(value.project_id, "project_id", { max: 128, safeId: true });
  const packetHash = requireText(value.packet_hash, "packet_hash", { max: 64, safeId: true });
  if (!/^[a-f0-9]{64}$/.test(packetHash)) throw new CliError("packet_hash must be a SHA-256 digest");
  const operationId = requireText(value.operation_id, "operation_id", { max: 96, safeId: true });
  if (operationId !== operationIdFromFields(
    projectId,
    request.task_id,
    request.run_id,
    request.execution_kind,
    request.host_placement,
  )) {
    throw new CliError("Task operation ID does not match its immutable request identity");
  }
  if (!Array.isArray(value.host_preflights) || value.host_preflights.length > MAX_HOST_PREFLIGHTS) {
    throw new CliError(`Task operation host preflights must contain at most ${MAX_HOST_PREFLIGHTS} entries`);
  }
  const hostPreflights = value.host_preflights.map(validateStoredHostPreflight);
  if (hostPreflights.some((item) => item === null)) {
    throw new CliError("Task operation host preflight history cannot contain null entries");
  }
  const hostPreflightIds = new Set(hostPreflights.map((item) => item.preflight_id));
  if (hostPreflightIds.size !== hostPreflights.length) {
    throw new CliError("Task operation host preflight IDs must be unique");
  }
  for (let index = 1; index < hostPreflights.length; index += 1) {
    if (Date.parse(hostPreflights[index].checked_at) < Date.parse(hostPreflights[index - 1].checked_at)) {
      throw new CliError("Task operation host preflight history must be chronological");
    }
  }
  const activeHostPreflightId = requireNullableText(
    value.active_host_preflight_id,
    "active_host_preflight_id",
    { max: 96, safeId: true },
  );
  if ((activeHostPreflightId === null) !== (hostPreflights.length === 0)) {
    throw new CliError("Task operation active host preflight and history are inconsistent");
  }
  const hostPreflight = activeHostPreflightId === null
    ? null
    : hostPreflights.find((item) => item.preflight_id === activeHostPreflightId) ?? null;
  if (activeHostPreflightId !== null && hostPreflight === null) {
    throw new CliError("Task operation active host preflight does not exist in its history");
  }
  if (activeHostPreflightId !== null && activeHostPreflightId !== hostPreflights.at(-1).preflight_id) {
    throw new CliError("Task operation active host preflight must be the newest history entry");
  }
  const attempts = value.attempts.map(validateAttempt);
  for (let index = 0; index < attempts.length; index += 1) {
    const attempt = attempts[index];
    if (attempt.sequence !== index + 1) throw new CliError("Task operation attempt sequence is not contiguous");
    const expected = `task-attempt-v1-${sha256(`${operationId}:${index + 1}`)}`;
    if (attempt.attempt_id !== expected) throw new CliError("Task operation attempt ID is invalid");
    if (attempt.status === "dispatching" && attempt.finished_at !== null) {
      throw new CliError("Dispatching task operation attempt cannot have finished_at");
    }
    if (attempt.status !== "dispatching" && attempt.finished_at === null) {
      throw new CliError(`Task operation attempt ${attempt.status} is missing finished_at`);
    }
    if (!hostPreflightIds.has(attempt.host_preflight_id)) {
      throw new CliError("Task operation attempt references unknown host-preflight evidence");
    }
    const attemptPreflight = hostPreflights.find((item) => item.preflight_id === attempt.host_preflight_id);
    if (Date.parse(attemptPreflight.checked_at) > Date.parse(attempt.started_at)) {
      throw new CliError("Task operation attempt predates its host-preflight evidence");
    }
  }
  const status = requireEnum(value.status, [
    "prepared", "dispatching", "ambiguous", "observed", "failed", "expired",
    "host-incompatible", "host-session-blocked", "rejected-before-release",
  ], "status");
  const observed = validateObserved(value.observed);
  const observationPolicy = validateObservationPolicy(value.observation_policy, request, observed);
  if (["observed", "rejected-before-release"].includes(status) !== (observed !== null && observationPolicy !== null)) {
    throw new CliError("Task operation status, host observation, and observation policy are inconsistent");
  }
  const resolution = validateRejectionResolution(value.resolution, request, observed, operationId);
  if ((status === "rejected-before-release") !== (resolution !== null)) {
    throw new CliError("Task operation status and rejection resolution are inconsistent");
  }
  const incompatibility = validateIncompatibility(value.incompatibility);
  if (status === "rejected-before-release" && incompatibility !== null) {
    throw new CliError("Rejected-before-release task operation cannot retain an incompatibility");
  }
  if ((status === "host-incompatible") !== (incompatibility?.type === "selector-incompatible")) {
    if (status === "host-incompatible" || incompatibility?.type === "selector-incompatible") {
      throw new CliError("Task operation selector-incompatibility state is inconsistent");
    }
  }
  if ((status === "host-session-blocked") !== (incompatibility?.type === "host-session-failure")) {
    if (status === "host-session-blocked" || incompatibility?.type === "host-session-failure") {
      throw new CliError("Task operation host-session state is inconsistent");
    }
  }
  const preflightReason = hostPreflight ? preflightIncompatibility(request, hostPreflight) : null;
  if (status === "host-incompatible") {
    if (hostPreflight === null || incompatibility.reason_code !== preflightReason) {
      throw new CliError("Task operation selector incompatibility does not match its host preflight");
    }
  } else if (preflightReason !== null) {
    throw new CliError("Compatible task-operation state contains an incompatible host preflight");
  }
  if (incompatibility !== null && (
    hostPreflight === null
    || incompatibility.preflight_id !== hostPreflight.preflight_id
    || incompatibility.host_session_id !== hostPreflight.host_session_id
  )) throw new CliError("Task incompatibility is not bound to its host preflight");
  const lastAttempt = attempts.at(-1);
  if (status === "dispatching" && lastAttempt?.status !== "dispatching") {
    throw new CliError("Dispatching task operation is missing its active attempt");
  }
  if (["ambiguous", "observed", "failed", "host-session-blocked"].includes(status) && lastAttempt?.status !== status) {
    throw new CliError(`Task operation ${status} state does not match its latest attempt`);
  }
  if (status === "rejected-before-release" && lastAttempt?.status !== "observed") {
    throw new CliError("Rejected-before-release task operation must retain an observed latest attempt");
  }
  if (status === "host-session-blocked" && (
    incompatibility.attempt_id !== lastAttempt.attempt_id
    || incompatibility.reason_code !== lastAttempt.failure_code
    || incompatibility.preflight_id !== lastAttempt.host_preflight_id
  )) {
    throw new CliError("Task operation host-session failure does not match its blocked attempt");
  }
  if (status === "prepared" && lastAttempt && !["not-created", "host-session-blocked"].includes(lastAttempt.status)) {
    throw new CliError("Prepared retry state requires a safely closed latest attempt");
  }
  if (["dispatching", "ambiguous", "observed", "host-session-blocked", "rejected-before-release"].includes(status) && hostPreflight === null) {
    throw new CliError(`Task operation ${status} is missing host preflight evidence`);
  }
  return {
    schema_version: 9,
    kind: OPERATION_KIND,
    operation_id: operationId,
    project_id: projectId,
    packet_hash: packetHash,
    request,
    host_preflights: hostPreflights,
    active_host_preflight_id: activeHostPreflightId,
    status,
    attempts,
    observed,
    observation_policy: observationPolicy,
    incompatibility,
    resolution,
    created_at: requireTimestamp(value.created_at, "created_at"),
    updated_at: requireTimestamp(value.updated_at, "updated_at"),
  };
}

function activeHostPreflight(record) {
  if (record.active_host_preflight_id === null) return null;
  return record.host_preflights.find(
    (item) => item.preflight_id === record.active_host_preflight_id,
  ) ?? null;
}

async function readOperation(paths, guardRoot) {
  const raw = await readJson(paths.record, { allowMissing: true, guardRoot });
  return raw ? validateOperationRecord(raw) : null;
}

async function writeOperation(paths, guardRoot, record) {
  const validated = validateOperationRecord(record);
  await atomicWriteJson(paths.record, validated, { guardRoot });
  return validated;
}

function operationView(record, now = Date.now()) {
  let effectiveStatus = record.status;
  if (record.status === "dispatching") {
    const active = record.attempts.at(-1);
    if (active && Date.parse(active.ambiguous_after) <= now) effectiveStatus = "ambiguous-due";
  }
  const evidence = observationEvidenceQuality(record.observed, record.request);
  return {
    ...record,
    effective_status: effectiveStatus,
    observation_evidence: evidence,
  };
}

export async function prepareTaskOperation({ stateRoot, projectId, packet: input, now = Date.now() }) {
  requireText(projectId, "project_id", { max: 128, safeId: true });
  const packet = validateTaskPacket(input);
  await authenticateTaskBaseline({
    stateRoot,
    baseline: packet.baseline,
    environment: packet.environment,
  });
  const operationId = taskOperationIdFor(projectId, packet);
  const paths = operationPaths(stateRoot, operationId);
  const guardRoot = operationGuardRoot(stateRoot);
  return withProcessLock({
    path: paths.lock,
    guardRoot,
    label: `task operation ${operationId}`,
  }, async () => {
    const existing = await readOperation(paths, guardRoot);
    const packetHash = sha256(stableStringify(packet));
    if (existing) {
      if (existing.packet_hash !== packetHash) {
        throw new CliError("Task operation identity collides with a different packet");
      }
      return operationView(existing, now);
    }
    const timestamp = nowIso(now);
    const record = {
      schema_version: 9,
      kind: OPERATION_KIND,
      operation_id: operationId,
      project_id: projectId,
      packet_hash: packetHash,
      request: {
        task_id: packet.task_id,
        run_id: packet.run_id,
        role: packet.role,
        execution_kind: packet.execution_kind,
        title: packet.title,
        launch_deadline: packet.launch_deadline,
        model: packet.model,
        reasoning_effort: packet.reasoning_effort,
        baseline: packet.baseline,
        environment: packet.environment,
        host_placement: packet.host_placement,
      },
      host_preflights: [],
      active_host_preflight_id: null,
      status: launchExpired(packet.launch_deadline, now) ? "expired" : "prepared",
      attempts: [],
      observed: null,
      observation_policy: null,
      incompatibility: null,
      resolution: null,
      created_at: timestamp,
      updated_at: timestamp,
    };
    await ensureExactJson(paths.record, validateOperationRecord(record), { guardRoot });
    return operationView(record, now);
  });
}

export async function authorizeHostWorktreeBootstrap({ stateRoot, operationId, packet: input, now = Date.now() }) {
  const packet = validateTaskPacket(input);
  if (packet.environment.type !== "host-worktree") {
    throw new CliError("Bootstrap authorization is reserved for host-worktree packets");
  }
  const operation = (await taskOperationStatus({ stateRoot, operationId, now }))[0];
  if (!operation || operation.status !== "dispatching") {
    throw new CliError("Host-worktree bootstrap requires an active dispatch attempt");
  }
  if (operation.packet_hash !== sha256(stableStringify(packet))) {
    throw new CliError("Bootstrap packet does not match the prepared operation");
  }
  return {
    operation_id: operation.operation_id,
    attempt_id: operation.attempts.at(-1).attempt_id,
    packet,
  };
}

export async function recordTaskOperationHostPreflight({
  stateRoot,
  operationId,
  evidence: input,
  now = Date.now(),
}) {
  const evidence = validateHostCapabilityEvidence(input);
  const hostPreflight = {
    preflight_id: hostPreflightIdFor(evidence),
    ...evidence,
  };
  const paths = operationPaths(stateRoot, operationId);
  const guardRoot = operationGuardRoot(stateRoot);
  return withProcessLock({
    path: paths.lock,
    guardRoot,
    label: `task operation ${operationId}`,
  }, async () => {
    const record = await readOperation(paths, guardRoot);
    if (!record) throw new CliError("Task operation does not exist");
    const activePreflight = activeHostPreflight(record);
    if (["dispatching", "ambiguous", "observed", "failed", "expired", "rejected-before-release"].includes(record.status)) {
      throw new CliError(`Task operation cannot accept host preflight evidence while ${record.status}`, 74);
    }
    if (
      record.status === "host-session-blocked"
      && activePreflight?.host_session_id === hostPreflight.host_session_id
    ) {
      throw new CliError("The blocked host session cannot be retried; record a preflight from a new host session", 75);
    }
    if (
      activePreflight !== null
      && Date.parse(hostPreflight.checked_at) < Date.parse(activePreflight.checked_at)
    ) {
      throw new CliError("Host preflight evidence cannot move backward in time");
    }
    if (Date.parse(hostPreflight.checked_at) > now + 5 * 60 * 1000) {
      throw new CliError("Host preflight evidence cannot be more than five minutes in the future");
    }
    const repeatedRejectedQuery = record.host_preflights.find((item) => (
      item.host_session_id === hostPreflight.host_session_id
      && item.thread_discovery.query === "rejected"
      && hostPreflight.thread_discovery.query === "rejected"
      && item.preflight_id !== hostPreflight.preflight_id
    ));
    if (repeatedRejectedQuery) {
      throw new CliError("Filtered thread discovery was already rejected in this host session");
    }
    const reason = preflightIncompatibility(record.request, hostPreflight);
    if (!record.host_preflights.some((item) => item.preflight_id === hostPreflight.preflight_id)) {
      if (record.host_preflights.length >= MAX_HOST_PREFLIGHTS) {
        throw new CliError("Task operation host-preflight limit reached", 74);
      }
      record.host_preflights.push(hostPreflight);
    }
    record.active_host_preflight_id = hostPreflight.preflight_id;
    record.incompatibility = reason === null ? null : {
      type: "selector-incompatible",
      stage: "preflight",
      reason_code: reason,
      preflight_id: hostPreflight.preflight_id,
      host_session_id: hostPreflight.host_session_id,
      attempt_id: null,
      recorded_at: nowIso(now),
    };
    record.status = reason === null ? "prepared" : "host-incompatible";
    record.updated_at = nowIso(now);
    return operationView(await writeOperation(paths, guardRoot, record), now);
  });
}

export async function beginTaskOperationAttempt({
  stateRoot,
  operationId,
  timeoutSeconds = 60,
  now = Date.now(),
}) {
  requireInteger(timeoutSeconds, "timeout_seconds", { min: 5, max: 600 });
  const paths = operationPaths(stateRoot, operationId);
  const guardRoot = operationGuardRoot(stateRoot);
  return withProcessLock({
    path: paths.lock,
    guardRoot,
    label: `task operation ${operationId}`,
  }, async () => {
    const record = await readOperation(paths, guardRoot);
    if (!record) throw new CliError("Task operation does not exist");
    if (record.status === "observed") return { status: "already-observed", operation: operationView(record, now) };
    if (["failed", "expired", "rejected-before-release"].includes(record.status)) {
      throw new CliError(`Task operation is terminal: ${record.status}`, 74);
    }
    if (record.status === "host-incompatible") {
      throw new CliError(`Host selector is incompatible: ${record.incompatibility.reason_code}`, 74);
    }
    if (record.status === "host-session-blocked") {
      throw new CliError("Host session is blocked; record a compatible preflight from a new host session", 75);
    }
    if (record.status === "ambiguous") {
      throw new CliError("Task operation is ambiguous; inspect the host and reconcile before retrying", 75);
    }
    if (record.status === "dispatching") {
      const active = record.attempts.at(-1);
      if (active && Date.parse(active.ambiguous_after) <= now) {
        active.status = "ambiguous";
        active.finished_at = nowIso(now);
        record.status = "ambiguous";
        record.updated_at = nowIso(now);
        await writeOperation(paths, guardRoot, record);
        throw new CliError("Prior task operation exceeded its bounded wait; inspect the host before retrying", 75);
      }
      throw new CliError("Task operation dispatch is already in progress", 75);
    }
    if (launchExpired(record.request.launch_deadline, now)) {
      record.status = "expired";
      record.updated_at = nowIso(now);
      await writeOperation(paths, guardRoot, record);
      throw new CliError("Task launch deadline has expired; no new host operation may start", 74);
    }
    const hostPreflight = activeHostPreflight(record);
    if (hostPreflight === null) {
      throw new CliError("Task operation requires host capability preflight before dispatch", 75);
    }
    const preflightReason = preflightIncompatibility(record.request, hostPreflight);
    if (preflightReason !== null) {
      throw new CliError(`Host selector is incompatible: ${preflightReason}`, 74);
    }
    await authenticateTaskBaseline({
      stateRoot,
      baseline: record.request.baseline,
      environment: record.request.environment,
    });
    if (record.attempts.length >= MAX_ATTEMPTS) throw new CliError("Task operation attempt limit reached", 74);
    const sequence = record.attempts.length + 1;
    const attemptId = `task-attempt-v1-${sha256(`${operationId}:${sequence}`)}`;
    const attempt = {
      attempt_id: attemptId,
      sequence,
      status: "dispatching",
      started_at: nowIso(now),
      ambiguous_after: nowIso(now + timeoutSeconds * 1000),
      finished_at: null,
      host_preflight_id: hostPreflight.preflight_id,
      failure_code: null,
    };
    record.attempts.push(attempt);
    record.status = "dispatching";
    record.updated_at = nowIso(now);
    await writeOperation(paths, guardRoot, record);
    return {
      status: "dispatching",
      operation_id: operationId,
      attempt,
      request: record.request,
    };
  });
}

export async function reconcileTaskOperation({
  stateRoot,
  operationId,
  attemptId,
  outcome,
  objectId = null,
  actualKind = null,
  evidence = null,
  reasonCode = null,
  now = Date.now(),
}) {
  const paths = operationPaths(stateRoot, operationId);
  const guardRoot = operationGuardRoot(stateRoot);
  requireText(attemptId, "attempt_id", { max: 96, safeId: true });
  requireEnum(outcome, [
    "observed", "not-created", "ambiguous", "failed", "host-session-blocked",
  ], "outcome");
  if (outcome !== "observed" && (objectId !== null || actualKind !== null || evidence !== null)) {
    throw new CliError("Only an observed reconciliation may contain host observation fields");
  }
  if (outcome !== "host-session-blocked" && reasonCode !== null) {
    throw new CliError("Only a host-session-blocked reconciliation may contain a reason code");
  }
  return withProcessLock({
    path: paths.lock,
    guardRoot,
    label: `task operation ${operationId}`,
  }, async () => {
    const record = await readOperation(paths, guardRoot);
    if (!record) throw new CliError("Task operation does not exist");
    const attempt = record.attempts.find((item) => item.attempt_id === attemptId);
    if (!attempt) throw new CliError("Task operation attempt does not exist");
    if (!["dispatching", "ambiguous"].includes(attempt.status)) {
      if (attempt.status === outcome) {
        if (outcome === "observed" && (objectId !== null || actualKind !== null || evidence !== null)) {
          requireText(objectId, "object_id", { max: 256, safeId: true });
          requireEnum(actualKind, ["task-thread", "subagent"], "actual_kind");
          const observedEvidence = validateObservationEvidence(evidence);
          if (
            record.observed?.object_id !== objectId
            || record.observed?.actual_kind !== actualKind
            || stableStringify(record.observed?.evidence) !== stableStringify(observedEvidence)
          ) throw new CliError("Observed task operation replay conflicts with its recorded host evidence");
        }
        if (
          outcome === "host-session-blocked"
          && reasonCode !== null
          && attempt.failure_code !== reasonCode
        ) throw new CliError("Host-session reconciliation replay conflicts with its recorded reason code");
        return operationView(record, now);
      }
      throw new CliError(`Task operation attempt is already reconciled as ${attempt.status}`);
    }
    const timestamp = nowIso(now);
    if (outcome === "observed") {
      requireText(objectId, "object_id", { max: 256, safeId: true });
      requireEnum(actualKind, ["task-thread", "subagent"], "actual_kind");
      record.observed = {
        object_id: objectId,
        actual_kind: actualKind,
        evidence: validateObservationEvidence(evidence),
        observed_at: timestamp,
      };
      record.observation_policy = observationPolicyFor(record.observed, record.request);
      record.status = "observed";
    } else if (outcome === "not-created") {
      record.status = launchExpired(record.request.launch_deadline, now) ? "expired" : "prepared";
    } else if (outcome === "host-session-blocked") {
      const failureCode = requireEnum(reasonCode, HOST_SESSION_FAILURE_CODES, "reason_code");
      const hostPreflight = activeHostPreflight(record);
      if (hostPreflight === null || attempt.host_preflight_id !== hostPreflight.preflight_id) {
        throw new CliError("Host-session failure is not bound to the current preflight");
      }
      attempt.failure_code = failureCode;
      record.status = "host-session-blocked";
      record.incompatibility = {
        type: "host-session-failure",
        stage: "dispatch",
        reason_code: failureCode,
        preflight_id: hostPreflight.preflight_id,
        host_session_id: hostPreflight.host_session_id,
        attempt_id: attempt.attempt_id,
        recorded_at: timestamp,
      };
    } else {
      record.status = outcome;
    }
    attempt.status = outcome;
    attempt.finished_at = timestamp;
    record.updated_at = timestamp;
    return operationView(await writeOperation(paths, guardRoot, record), now);
  });
}

async function hostWorktreePathIsAbsent(path) {
  try {
    await lstat(path);
    return false;
  } catch (error) {
    if (error?.code === "ENOENT") return true;
    throw error;
  }
}

function settledClaimFor(record, claim) {
  const settlement = record.resolution?.branch_claim_settlement;
  return settlement !== null && stableStringify(settlement.claim) === stableStringify(claim);
}

async function settleBranchClaim({ record, claimPath, guardRoot, hooks }) {
  const raw = await readJson(claimPath, { allowMissing: true, guardRoot });
  if (raw === null) return null;
  const settlement = validateSettledBranchClaim({ claim: raw, local_branch_state: "absent" }, record.request, record.observed, record.operation_id);
  const claim = settlement.claim;
  const source = record.request.environment.repository_path;
  const ref = `refs/heads/${claim.branch}`;
  const attached = gitResult(source, ["worktree", "list", "--porcelain"], "Git worktree inspection")
    .split("\n")
    .some((line) => line === `branch ${ref}`);
  if (attached) throw new CliError("Task operation rejection is not allowed while the claimed branch is checked out");
  const remote = gitResult(source, ["for-each-ref", "--format=%(refname)", "refs/remotes"], "Git remote-tracking inspection")
    .split("\n")
    .filter(Boolean)
    .some((item) => item.endsWith(`/${claim.branch}`));
  if (remote) throw new CliError("Task operation rejection is not allowed while fetched remote branch evidence exists");
  const tip = gitRefTip(source, ref);
  if (tip !== null && tip !== claim.baseline_revision) {
    throw new CliError("Task operation rejection is not allowed after claimed branch drift");
  }
  if (tip !== null) {
    gitResult(source, ["update-ref", "-d", ref, claim.baseline_revision], "Git claimed branch deletion");
    hooks.afterClaimBranchDeletion?.({ claim });
  }
  return { claim, local_branch_state: "absent" };
}

export async function rejectTaskOperationBeforeRelease({
  stateRoot,
  operationId,
  reasonCode,
  hostObjectState,
  now = Date.now(),
  hooks = {},
}) {
  const reason = requireEnum(reasonCode, REJECTION_REASON_CODES, "reason_code");
  const objectState = requireEnum(hostObjectState, ["archived"], "host_object_state");
  const paths = operationPaths(stateRoot, operationId);
  const guardRoot = operationGuardRoot(stateRoot);
  return withProcessLock({
    path: gitLifecycleMutationLockPath(stateRoot),
    guardRoot,
    label: `Git lifecycle mutation ${operationId}`,
  }, async () => {
    return withProcessLock({
      path: paths.lock,
      guardRoot,
      label: `task operation ${operationId}`,
    }, async () => {
      const record = await readOperation(paths, guardRoot);
      if (!record) throw new CliError("Task operation does not exist");
      if (record.status === "rejected-before-release") {
        const resolution = record.resolution;
        if (
          resolution.reason_code !== reason
          || resolution.host_object_state !== objectState
        ) throw new CliError("Rejected-before-release replay conflicts with its recorded resolution");
        if (record.resolution.branch_claim_settlement !== null) {
          const ownershipPath = safeChild(resolve(stateRoot, "git-lifecycle", "ownership"), `${record.operation_id}.json`);
          if (await readJson(ownershipPath, { allowMissing: true, guardRoot }) !== null) {
            throw new CliError("Task operation rejection is not allowed after Git ownership binding");
          }
          if (!await hostWorktreePathIsAbsent(record.observed.evidence.execution_path.value)) {
            throw new CliError("Host-worktree execution path still exists; archive and remove it before rejection");
          }
          const branchClaimPath = safeChild(resolve(stateRoot, "git-lifecycle", "branch-claims"), `${record.operation_id}.json`);
          const raw = await readJson(branchClaimPath, { allowMissing: true, guardRoot });
          if (raw !== null && !settledClaimFor(record, validateSettledBranchClaim({ claim: raw, local_branch_state: "absent" }, record.request, record.observed, record.operation_id).claim)) {
            throw new CliError("Rejected-before-release replay conflicts with its recorded branch claim settlement");
          }
        }
        return operationView(record, now);
      }
      if (record.status !== "observed") {
        throw new CliError("Task operation rejection requires an observed host object");
      }
      const ownershipPath = safeChild(
        resolve(stateRoot, "git-lifecycle", "ownership"),
        `${record.operation_id}.json`,
      );
      const branchClaimPath = safeChild(
        resolve(stateRoot, "git-lifecycle", "branch-claims"),
        `${record.operation_id}.json`,
      );
      if (await readJson(ownershipPath, { allowMissing: true, guardRoot }) !== null) {
        throw new CliError("Task operation rejection is not allowed after Git ownership binding");
      }
      const executionPathState = record.request.environment.type === "host-worktree"
        ? "absent"
        : "not-applicable";
      if (executionPathState === "absent") {
        const path = record.observed.evidence.execution_path.value;
        if (!await hostWorktreePathIsAbsent(path)) {
          throw new CliError("Host-worktree execution path still exists; archive and remove it before rejection");
        }
      }
      const branchClaimSettlement = executionPathState === "absent"
        ? await settleBranchClaim({ record, claimPath: branchClaimPath, guardRoot, hooks })
        : null;
      record.status = "rejected-before-release";
      record.resolution = {
        disposition: "rejected-before-release",
        reason_code: reason,
        host_object_state: objectState,
        execution_path_state: executionPathState,
        branch_claim_settlement: branchClaimSettlement,
        recorded_at: nowIso(now),
      };
      record.updated_at = nowIso(now);
      return operationView(await writeOperation(paths, guardRoot, record), now);
    });
  });
}

async function listOperationRecords(root, guardRoot) {
  await assertNoSymlinkComponents(guardRoot, root, "Task-operation state path");
  let entries;
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
  const records = [];
  for (const entry of entries) {
    const path = resolve(root, entry.name);
    if (entry.isSymbolicLink()) throw new CliError(`Task-operation state contains a symbolic link: ${path}`);
    if (!entry.isFile() || !entry.name.endsWith(".json")) continue;
    records.push(validateOperationRecord(await readJson(path, { guardRoot })));
  }
  return records;
}

export async function taskOperationStatus({ stateRoot, operationId = null, now = Date.now() }) {
  const guardRoot = operationGuardRoot(stateRoot);
  if (operationId) {
    const paths = operationPaths(stateRoot, operationId);
    const record = await readOperation(paths, guardRoot);
    return record ? [operationView(record, now)] : [];
  }
  const records = await listOperationRecords(resolve(stateRoot, "task-operations", "records"), guardRoot);
  return records
    .map((record) => operationView(record, now))
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at));
}
