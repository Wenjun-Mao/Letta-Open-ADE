import {
  CliError,
  requireEnum,
  requireExactFields,
  requireInteger,
  requireStringArray,
  requireText,
} from "./core.mjs";
import { isLaunchExpired, normalizeOwnedPath, validateLaunchDeadline } from "./task-packet.mjs";

function pathsOverlap(left, right) {
  return left === right || left.startsWith(`${right}/`) || right.startsWith(`${left}/`);
}

function validateTask(value, index, now) {
  const label = `tasks[${index}]`;
  requireExactFields(value, {
    required: [
      "id",
      "title",
      "role",
      "execution_kind",
      "launch_deadline",
      "mode",
      "dependencies",
      "write_paths",
      "shared_resources",
      "serial_gate",
    ],
  }, label);
  const id = requireText(value.id, `${label}.id`, { max: 128, safeId: true });
  const role = requireEnum(value.role, ["coordinator", "executor"], `${label}.role`);
  const executionKind = requireEnum(value.execution_kind, ["task-thread", "subagent"], `${label}.execution_kind`);
  const launchDeadline = validateLaunchDeadline(value.launch_deadline, `${label}.launch_deadline`);
  const mode = requireEnum(value.mode, ["read", "write"], `${label}.mode`);
  const writePaths = requireStringArray(value.write_paths, `${label}.write_paths`, {
    maxItems: 128,
    maxText: 512,
  }).map((path, pathIndex) => normalizeOwnedPath(path, `${label}.write_paths[${pathIndex}]`));
  if (new Set(writePaths).size !== writePaths.length) throw new CliError(`${label}.write_paths contains duplicates`);
  for (let left = 0; left < writePaths.length; left += 1) {
    for (let right = left + 1; right < writePaths.length; right += 1) {
      if (pathsOverlap(writePaths[left], writePaths[right])) {
        throw new CliError(`${label}.write_paths contains overlapping paths: ${writePaths[left]} / ${writePaths[right]}`);
      }
    }
  }
  if (mode === "read" && writePaths.length > 0) throw new CliError(`${label} is read-only but declares write paths`);
  if (mode === "write" && writePaths.length === 0) throw new CliError(`${label} must declare at least one write path`);
  if (typeof value.serial_gate !== "boolean") throw new CliError(`${label}.serial_gate must be boolean`);
  return {
    id,
    title: requireText(value.title, `${label}.title`, { max: 160 }),
    role,
    execution_kind: executionKind,
    launch_deadline: launchDeadline,
    launch_expired: isLaunchExpired(launchDeadline, now),
    mode,
    dependencies: requireStringArray(value.dependencies, `${label}.dependencies`, {
      maxItems: 128,
      maxText: 128,
      safeIds: true,
    }),
    write_paths: writePaths,
    shared_resources: requireStringArray(value.shared_resources, `${label}.shared_resources`, {
      maxItems: 64,
      maxText: 128,
      safeIds: true,
    }),
    serial_gate: value.serial_gate,
  };
}

function dependencyClosure(tasksById, taskId, visiting = new Set(), memo = new Map()) {
  if (memo.has(taskId)) return memo.get(taskId);
  if (visiting.has(taskId)) throw new CliError(`Plan dependency cycle includes ${taskId}`);
  visiting.add(taskId);
  const closure = new Set();
  for (const dependency of tasksById.get(taskId).dependencies) {
    closure.add(dependency);
    for (const ancestor of dependencyClosure(tasksById, dependency, visiting, memo)) closure.add(ancestor);
  }
  visiting.delete(taskId);
  memo.set(taskId, closure);
  return closure;
}

function ordered(closures, leftId, rightId) {
  return closures.get(leftId).has(rightId) || closures.get(rightId).has(leftId);
}

function computeWaves(tasks, maxConcurrency) {
  const remaining = new Map(tasks.map((task) => [task.id, task]));
  const completed = new Set();
  const waves = [];
  while (remaining.size > 0) {
    const ready = [...remaining.values()].filter((task) => task.dependencies.every((id) => completed.has(id)));
    if (ready.length === 0) throw new CliError("Plan has no schedulable task; dependency cycle remains");
    const serial = ready.find((task) => task.serial_gate);
    const wave = serial ? [serial] : ready.slice(0, maxConcurrency);
    waves.push(wave.map((task) => task.id));
    for (const task of wave) {
      remaining.delete(task.id);
      completed.add(task.id);
    }
  }
  return waves;
}

export function validatePlan(value, { projectMaxConcurrency = 32, now = Date.now() } = {}) {
  requireExactFields(value, {
    required: ["schema_version", "plan_id", "baseline_revision", "max_concurrency", "tasks"],
  }, "Plan");
  if (value.schema_version !== 2) throw new CliError("Unsupported plan schema_version");
  const maxConcurrency = requireInteger(value.max_concurrency, "max_concurrency", {
    min: 1,
    max: Math.min(32, projectMaxConcurrency),
  });
  if (!Array.isArray(value.tasks) || value.tasks.length === 0 || value.tasks.length > 256) {
    throw new CliError("Plan tasks must be a nonempty array with at most 256 tasks");
  }
  const tasks = value.tasks.map((task, index) => validateTask(task, index, now));
  const tasksById = new Map();
  for (const task of tasks) {
    if (tasksById.has(task.id)) throw new CliError(`Duplicate plan task id: ${task.id}`);
    tasksById.set(task.id, task);
  }
  for (const task of tasks) {
    for (const dependency of task.dependencies) {
      if (!tasksById.has(dependency)) throw new CliError(`Task ${task.id} has unknown dependency: ${dependency}`);
      if (dependency === task.id) throw new CliError(`Task ${task.id} depends on itself`);
    }
  }

  const closures = new Map();
  for (const task of tasks) closures.set(task.id, dependencyClosure(tasksById, task.id));

  for (let leftIndex = 0; leftIndex < tasks.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < tasks.length; rightIndex += 1) {
      const left = tasks[leftIndex];
      const right = tasks[rightIndex];
      if (ordered(closures, left.id, right.id)) continue;
      for (const leftPath of left.write_paths) {
        for (const rightPath of right.write_paths) {
          if (pathsOverlap(leftPath, rightPath)) {
            throw new CliError(`Unordered tasks ${left.id} and ${right.id} have overlapping write paths: ${leftPath} / ${rightPath}`);
          }
        }
      }
      const shared = left.shared_resources.filter((resource) => right.shared_resources.includes(resource));
      if (shared.length > 0) {
        throw new CliError(`Unordered tasks ${left.id} and ${right.id} share exclusive resources: ${shared.join(", ")}`);
      }
    }
  }

  return {
    schema_version: 2,
    plan_id: requireText(value.plan_id, "plan_id", { max: 128, safeId: true }),
    baseline_revision: requireText(value.baseline_revision, "baseline_revision", { max: 256 }),
    max_concurrency: maxConcurrency,
    tasks,
    launch_expired: tasks.some((task) => task.launch_expired),
    waves: computeWaves(tasks, maxConcurrency),
  };
}
