import { isAbsolute } from "node:path";
import {
  CliError,
  requireEnum,
  requireExactFields,
  requireInteger,
  requireNullableText,
  requireStringArray,
  requireText,
  stableStringify,
} from "./core.mjs";
import { REASONING_EFFORTS } from "./config.mjs";

const RFC3339_OFFSET_TIMESTAMP = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/;

const PACKET_FIELDS = [
  "schema_version",
  "task_id",
  "run_id",
  "title",
  "objective",
  "role",
  "execution_kind",
  "launch_deadline",
  "baseline",
  "environment",
  "host_placement",
  "model",
  "reasoning_effort",
  "ownership",
  "dependencies",
  "shared_resources",
  "verification",
  "callback",
  "integration_gate",
  "cleanup_owner",
  "stop_policy",
];

const HOST_PLACEMENT_MODES = ["same-project", "cross-project", "projectless", "inherited"];
const MAX_HOST_PLACEMENT_REASON_LENGTH = 512;

function hasValidCalendarFields(match) {
  const [, year, month, day, hour, minute, second] = match;
  const date = new Date(0);
  date.setUTCFullYear(Number(year), Number(month) - 1, Number(day));
  date.setUTCHours(Number(hour), Number(minute), Number(second), 0);
  return (
    date.getUTCFullYear() === Number(year)
    && date.getUTCMonth() === Number(month) - 1
    && date.getUTCDate() === Number(day)
    && date.getUTCHours() === Number(hour)
    && date.getUTCMinutes() === Number(minute)
    && date.getUTCSeconds() === Number(second)
  );
}

export function validateLaunchDeadline(value, label = "launch_deadline") {
  requireExactFields(value, { required: ["at", "timezone"] }, label);
  const at = requireText(value.at, `${label}.at`, { max: 64 });
  const match = RFC3339_OFFSET_TIMESTAMP.exec(at);
  if (!match || !hasValidCalendarFields(match) || !Number.isFinite(Date.parse(at))) {
    throw new CliError(`${label}.at must be an RFC3339 timestamp with an explicit UTC offset`);
  }

  const timezone = requireText(value.timezone, `${label}.timezone`, { max: 128 });
  if (/^(?:UTC|GMT)?[+-]\d/.test(timezone)) {
    throw new CliError(`${label}.timezone must be an IANA timezone name`);
  }
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: timezone }).format(Date.parse(at));
  } catch {
    throw new CliError(`${label}.timezone must be a valid IANA timezone name`);
  }
  return { at, timezone };
}

export function isLaunchExpired(deadline, now = Date.now()) {
  const value = validateLaunchDeadline(deadline);
  const nowMilliseconds = now instanceof Date ? now.getTime() : now;
  if (!Number.isFinite(nowMilliseconds)) throw new CliError("Launch expiry clock must be a finite timestamp");
  return Date.parse(value.at) <= nowMilliseconds;
}

export function validateTaskBaseline(value, label = "baseline") {
  requireExactFields(value, { required: ["revision", "cleanliness"] }, label);
  return {
    revision: requireText(value.revision, `${label}.revision`, { max: 256 }),
    cleanliness: requireEnum(value.cleanliness, ["clean", "dirty-authorized"], `${label}.cleanliness`),
  };
}

export function validateTaskEnvironment(value, label = "environment") {
  const type = requireEnum(value?.type, ["local", "host-worktree", "projectless"], `${label}.type`);
  if (type === "projectless") {
    requireExactFields(value, { required: ["type"] }, label);
    return { type };
  }
  if (type === "local") {
    requireExactFields(value, { required: ["type", "project_path"] }, label);
    const projectPath = requireText(value.project_path, `${label}.project_path`, { max: 1024 });
    if (!isAbsolute(projectPath)) throw new CliError(`${label}.project_path must be absolute`);
    return { type, project_path: projectPath };
  }
  requireExactFields(value, {
    required: ["type", "repository_path", "starting_branch", "executor_branch"],
  }, label);
  const repositoryPath = requireText(value.repository_path, `${label}.repository_path`, { max: 1024 });
  if (!isAbsolute(repositoryPath)) throw new CliError(`${label}.repository_path must be absolute`);
  const environment = {
    type,
    repository_path: repositoryPath,
    starting_branch: requireText(value.starting_branch, `${label}.starting_branch`, { max: 256 }),
    executor_branch: requireText(value.executor_branch, `${label}.executor_branch`, { max: 256 }),
  };
  if (environment.starting_branch === environment.executor_branch) {
    throw new CliError(`${label}.executor_branch must differ from starting_branch`);
  }
  return environment;
}

export function validateHostPlacement(value, label = "host_placement") {
  requireExactFields(value, { required: ["mode", "target_project_id", "reason"] }, label);
  const mode = requireEnum(value.mode, HOST_PLACEMENT_MODES, `${label}.mode`);
  const targetProjectId = value.target_project_id === null
    ? null
    : requireText(value.target_project_id, `${label}.target_project_id`, { max: 128, safeId: true });
  const reason = requireNullableText(value.reason, `${label}.reason`, {
    max: MAX_HOST_PLACEMENT_REASON_LENGTH,
  });
  if (mode === "same-project" && (targetProjectId === null || reason !== null)) {
    throw new CliError("same-project host placement requires an exact project ID and no reason");
  }
  if (mode === "cross-project" && (targetProjectId === null || reason === null)) {
    throw new CliError("cross-project host placement requires an exact project ID and a reason");
  }
  if (mode === "projectless" && (targetProjectId !== null || reason === null)) {
    throw new CliError("projectless host placement requires a null project ID and a reason");
  }
  if (mode === "inherited" && (targetProjectId !== null || reason !== null)) {
    throw new CliError("inherited host placement requires a null project ID and no reason");
  }
  return { mode, target_project_id: targetProjectId, reason };
}

export function validateHostPlacementForTask({ executionKind, environment, hostPlacement }) {
  if (executionKind === "subagent" && hostPlacement.mode !== "inherited") {
    throw new CliError("Subagent host placement must be inherited");
  }
  if (executionKind === "task-thread" && hostPlacement.mode === "inherited") {
    throw new CliError("Task-thread host placement cannot be inherited");
  }
  if (executionKind === "task-thread" && environment.type === "projectless" && hostPlacement.mode !== "projectless") {
    throw new CliError("Projectless task-thread execution requires projectless host placement");
  }
  if (executionKind === "task-thread" && environment.type !== "projectless" && !["same-project", "cross-project"].includes(hostPlacement.mode)) {
    throw new CliError("Project-backed task-thread execution requires same-project or cross-project host placement");
  }
  return hostPlacement;
}

export function normalizeOwnedPath(value, label) {
  const text = requireText(value, label, { max: 512 }).replaceAll("\\", "/").replace(/\/+$/, "");
  if (
    text === "" || text === "." || text.startsWith("/") || isAbsolute(text)
    || /^[A-Za-z]:\//.test(text) || text.split("/").includes("..")
    || /[*?\[\]{}]/.test(text) || text === ".git" || text.startsWith(".git/")
  ) {
    throw new CliError(`${label} must be a bounded repository-relative path without globs or parent traversal`);
  }
  return text.replace(/^\.\//, "");
}

function validatePaths(value, label, { allowEmpty = true } = {}) {
  const raw = requireStringArray(value, label, { maxItems: 128, maxText: 512, allowEmpty });
  const normalized = raw.map((entry, index) => normalizeOwnedPath(entry, `${label}[${index}]`));
  if (new Set(normalized).size !== normalized.length) throw new CliError(`${label} contains equivalent duplicate paths`);
  return normalized;
}

function pathsOverlap(left, right) {
  return left === right || left.startsWith(`${right}/`) || right.startsWith(`${left}/`);
}

function rejectOverlappingPaths(paths, label) {
  for (let left = 0; left < paths.length; left += 1) {
    for (let right = left + 1; right < paths.length; right += 1) {
      if (pathsOverlap(paths[left], paths[right])) {
        throw new CliError(`${label} contains overlapping paths: ${paths[left]} / ${paths[right]}`);
      }
    }
  }
}

export function validateTaskPacket(value) {
  requireExactFields(value, { required: PACKET_FIELDS }, "Task packet");
  if (value.schema_version !== 5) throw new CliError("Unsupported task packet schema_version");
  const taskId = requireText(value.task_id, "task_id", { max: 128, safeId: true });
  const runId = requireText(value.run_id, "run_id", { max: 128, safeId: true });
  const title = requireText(value.title, "title", { max: 160 });
  const objective = requireText(value.objective, "objective", { max: 2000 });
  const role = requireEnum(value.role, ["coordinator", "executor"], "role");
  const executionKind = requireEnum(value.execution_kind, ["task-thread", "subagent"], "execution_kind");
  const launchDeadline = validateLaunchDeadline(value.launch_deadline);

  const baseline = validateTaskBaseline(value.baseline);
  const environment = validateTaskEnvironment(value.environment);
  const hostPlacement = validateHostPlacement(value.host_placement);
  if (environment.type === "host-worktree") {
    if (executionKind !== "task-thread") {
      throw new CliError("host-worktree execution requires a user-visible task-thread");
    }
    if (baseline.cleanliness !== "clean") {
      throw new CliError("host-worktree baseline cleanliness must be clean");
    }
  }
  validateHostPlacementForTask({ executionKind, environment, hostPlacement });

  const model = requireNullableText(value.model, "model", { max: 128 });
  requireEnum(value.reasoning_effort, REASONING_EFFORTS, "reasoning_effort");

  requireExactFields(value.ownership, {
    required: ["write_paths", "read_paths", "exclusions"],
  }, "ownership");
  const ownership = {
    write_paths: validatePaths(value.ownership.write_paths, "ownership.write_paths", { allowEmpty: false }),
    read_paths: validatePaths(value.ownership.read_paths, "ownership.read_paths"),
    exclusions: validatePaths(value.ownership.exclusions, "ownership.exclusions"),
  };
  rejectOverlappingPaths(ownership.write_paths, "ownership.write_paths");
  for (const writePath of ownership.write_paths) {
    for (const excludedPath of ownership.exclusions) {
      if (pathsOverlap(writePath, excludedPath)) {
        throw new CliError(`ownership write path overlaps an explicit exclusion: ${writePath} / ${excludedPath}`);
      }
    }
  }

  const dependencies = requireStringArray(value.dependencies, "dependencies", {
    maxItems: 128,
    maxText: 128,
    safeIds: true,
  });
  const sharedResources = requireStringArray(value.shared_resources, "shared_resources", {
    maxItems: 64,
    maxText: 128,
    safeIds: true,
  });
  const verification = requireStringArray(value.verification, "verification", {
    maxItems: 64,
    maxText: 512,
    allowEmpty: false,
  });

  requireExactFields(value.callback, {
    required: ["recipient", "executor_id", "receipt_schema_version"],
  }, "callback");
  requireExactFields(value.callback.recipient, {
    required: ["lineage_id", "thread_id", "generation"],
  }, "callback.recipient");
  const callback = {
    recipient: {
      lineage_id: requireText(value.callback.recipient.lineage_id, "callback.recipient.lineage_id", {
        max: 128,
        safeId: true,
      }),
      thread_id: requireText(value.callback.recipient.thread_id, "callback.recipient.thread_id", {
        max: 128,
        safeId: true,
      }),
      generation: requireInteger(value.callback.recipient.generation, "callback.recipient.generation", {
        min: 1,
        max: 2147483647,
      }),
    },
    executor_id: requireText(value.callback.executor_id, "callback.executor_id", { max: 128, safeId: true }),
    receipt_schema_version: requireInteger(value.callback.receipt_schema_version, "callback.receipt_schema_version", {
      min: 2,
      max: 2,
    }),
  };
  if (callback.executor_id !== taskId) throw new CliError("callback.executor_id must equal task_id");

  requireExactFields(value.integration_gate, {
    required: ["gate_id", "reproof"],
  }, "integration_gate");
  const integrationGate = {
    gate_id: requireText(value.integration_gate.gate_id, "integration_gate.gate_id", { max: 128, safeId: true }),
    reproof: requireStringArray(value.integration_gate.reproof, "integration_gate.reproof", {
      maxItems: 64,
      maxText: 512,
      allowEmpty: false,
    }),
  };
  const cleanupOwner = requireText(value.cleanup_owner, "cleanup_owner", { max: 128, safeId: true });

  requireExactFields(value.stop_policy, {
    required: ["urgent", "ordinary_completion"],
  }, "stop_policy");
  const urgent = requireStringArray(value.stop_policy.urgent, "stop_policy.urgent", {
    maxItems: 3,
    maxText: 32,
    safeIds: true,
    allowEmpty: false,
  });
  const requiredUrgent = ["approval", "blocker", "high-risk-drift"];
  if (stableStringify([...urgent].sort()) !== stableStringify(requiredUrgent)) {
    throw new CliError("stop_policy.urgent must contain blocker, approval, and high-risk-drift exactly");
  }
  requireEnum(
    value.stop_policy.ordinary_completion,
    ["journal-monitor"],
    "stop_policy.ordinary_completion",
  );

  return {
    schema_version: 5,
    task_id: taskId,
    run_id: runId,
    title,
    objective,
    role,
    execution_kind: executionKind,
    launch_deadline: launchDeadline,
    baseline,
    environment,
    host_placement: hostPlacement,
    model,
    reasoning_effort: value.reasoning_effort,
    ownership,
    dependencies,
    shared_resources: sharedResources,
    verification,
    callback,
    integration_gate: integrationGate,
    cleanup_owner: cleanupOwner,
    stop_policy: {
      urgent: ["blocker", "approval", "high-risk-drift"],
      ordinary_completion: value.stop_policy.ordinary_completion,
    },
  };
}

export function applyTaskDefaults(packet, projectConfig) {
  const value = validateTaskPacket(packet);
  return {
    ...value,
    model: value.model ?? projectConfig.default_model,
    reasoning_effort: value.reasoning_effort ?? projectConfig.default_reasoning_effort,
  };
}

function renderValidatedTaskPacket(value) {
  const environment = value.environment.type === "host-worktree"
    ? `\`host-worktree\` from \`${value.environment.starting_branch}\` onto \`${value.environment.executor_branch}\``
    : `\`${value.environment.type}\`${value.environment.project_path ? ` at \`${value.environment.project_path}\`` : ""}`;
  const lines = [
    `# ${value.title}`,
    "",
    value.objective,
    "",
    "## Execution Contract",
    "",
    `- Task ID: \`${value.task_id}\``,
    `- Run ID: \`${value.run_id}\``,
    `- Role: \`${value.role}\` (${value.execution_kind})`,
    `- Launch deadline: \`${value.launch_deadline.at}\` (${value.launch_deadline.timezone})`,
    `- Baseline: \`${value.baseline.revision}\` (${value.baseline.cleanliness})`,
    `- Environment: ${environment}`,
    `- Host placement: \`${value.host_placement.mode}\`${value.host_placement.target_project_id ? ` -> \`${value.host_placement.target_project_id}\`` : ""}${value.host_placement.reason ? ` (${value.host_placement.reason})` : ""}`,
    ...(value.environment.type === "host-worktree" ? [
      `- Saved project path: \`${value.environment.repository_path}\` identifies the host-addressable project; it is not this executor's working directory.`,
      "- Execution path: the host-observed, Git-bound `worktree_path` in the operation ownership record is authoritative; authenticate it against the current working directory.",
      "- Upstream: absence is expected until this executor branch is pushed for the first time and is not a provenance blocker by itself.",
    ] : []),
    `- Model: ${value.model ? `\`${value.model}\`` : "host default"}`,
    `- Reasoning effort: ${value.reasoning_effort ? `\`${value.reasoning_effort}\`` : "host default"}`,
    `- Callback recipient: \`${value.callback.recipient.thread_id}\` in lineage \`${value.callback.recipient.lineage_id}\` (generation ${value.callback.recipient.generation})`,
    `- Ordinary completion authority: \`${value.stop_policy.ordinary_completion}\``,
    `- Integration gate: \`${value.integration_gate.gate_id}\` (${value.integration_gate.reproof.length} reproof check${value.integration_gate.reproof.length === 1 ? "" : "s"})`,
    `- Cleanup owner: \`${value.cleanup_owner}\``,
    "",
    "Write ownership:",
    ...value.ownership.write_paths.map((path) => `- \`${path}\``),
    "",
    "Read context:",
    ...(value.ownership.read_paths.length ? value.ownership.read_paths.map((path) => `- \`${path}\``) : ["- None declared"]),
    "",
    "Explicit exclusions:",
    ...(value.ownership.exclusions.length ? value.ownership.exclusions.map((path) => `- \`${path}\``) : ["- None declared"]),
    "",
    "Dependencies:",
    ...(value.dependencies.length ? value.dependencies.map((id) => `- \`${id}\``) : ["- None"]),
    "",
    "Exclusive resources:",
    ...(value.shared_resources.length ? value.shared_resources.map((id) => `- \`${id}\``) : ["- None"]),
    "",
    "Verification:",
    ...value.verification.map((item) => `- ${item}`),
    "",
    "Before acting, run the pinned executor role entrypoint and validate this packet. Preserve unrelated and sibling changes. Steer only a true blocker, approval request, or high-risk drift. Persist ordinary terminal completion exactly once through the packet's declared authority.",
    "",
    "## Machine-Readable Packet",
    "",
    "```json",
    stableStringify(value, 2),
    "```",
    "",
  ];
  return lines.join("\n");
}

export function renderTaskPacket(packet) {
  const value = validateTaskPacket(packet);
  if (value.environment.type === "host-worktree") {
    throw new CliError("host-worktree packets may be rendered only through a Git-bound task-operation release");
  }
  return renderValidatedTaskPacket(value);
}

export function renderReleasedTaskPacket(packet) {
  const value = validateTaskPacket(packet);
  if (value.environment.type !== "host-worktree") {
    throw new CliError("Released task rendering is reserved for host-worktree packets");
  }
  return renderValidatedTaskPacket(value);
}

export function renderHostWorktreeBootstrap(packet, operationId) {
  const value = validateTaskPacket(packet);
  if (value.environment.type !== "host-worktree") {
    throw new CliError("Bootstrap rendering is reserved for host-worktree packets");
  }
  const id = requireText(operationId, "operation_id", { max: 96, safeId: true });
  return [
    `# ${value.title}`,
    "",
    "This is a worktree bootstrap turn only.",
    "",
    `- Task operation: \`${id}\``,
    `- Expected starting revision: \`${value.baseline.revision}\``,
    "- Do not run repository commands, inspect project files, modify files, or begin the task.",
    "- End this turn and wait for the coordinator to authenticate the host-created worktree, bind Git ownership, and send the released task packet.",
    "",
  ].join("\n");
}
