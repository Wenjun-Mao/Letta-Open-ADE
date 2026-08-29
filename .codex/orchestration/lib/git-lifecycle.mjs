import { execFileSync, spawnSync } from "node:child_process";
import { readdir, realpath } from "node:fs/promises";
import { basename, dirname, resolve } from "node:path";
import {
  assertNoSymlinkComponents,
  atomicWriteJson,
  CliError,
  ensureExactJson,
  readJson,
  requireEnum,
  requireExactFields,
  requireText,
  sha256,
  stableStringify,
  withProcessLock,
} from "./core.mjs";
import { gitBranchAvailability, gitCommonDirectoryForState, gitSnapshot } from "./git.mjs";
import { leaseStatus } from "./leases.mjs";
import { validateTaskPacket } from "./task-packet.mjs";
import { taskOperationStatus } from "./task-operations.mjs";

const SAFE_DISPOSITIONS = ["ancestor", "patch-equivalent", "superseded"];
const DISPOSITIONS = [...SAFE_DISPOSITIONS, "unmerged"];
const SHA_PATTERN = /^[0-9a-f]{40,64}$/;
const GIT_TIMEOUT_MS = 30_000;

export class GitCleanupApplyError extends CliError {
  constructor(result, exitCode = 1) {
    super(`Git cleanup ${result.status} at ${result.failed_action}: ${result.error}`, exitCode);
    this.name = "GitCleanupApplyError";
    this.result = result;
  }
}

function cleanupFailureReason(error) {
  const raw = error instanceof Error ? error.message : String(error ?? "");
  const normalized = raw.replace(/\s+/g, " ").trim();
  return (normalized || "Unknown cleanup failure").slice(0, 512);
}

function gitEnvironment() {
  return { ...process.env, GIT_OPTIONAL_LOCKS: "0", GIT_TERMINAL_PROMPT: "0" };
}

function stateGuard(stateRoot) {
  return gitCommonDirectoryForState(stateRoot);
}

function safeId(value, label, { digest = false } = {}) {
  const result = requireText(value, label, { max: 96, safeId: true });
  if (digest && !/^[0-9a-f]{64}$/.test(result)) throw new CliError(`${label} must be a SHA-256 digest`);
  return result;
}

function paths(stateRoot, { operationId = null } = {}) {
  const root = resolve(stateRoot, "git-lifecycle");
  const operation = operationId === null ? null : safeId(operationId, "operation_id");
  return {
    root,
    branchClaim: operation ? resolve(root, "branch-claims", `${operation}.json`) : null,
    ownership: operation ? resolve(root, "ownership", `${operation}.json`) : null,
    integration: operation ? resolve(root, "integrations", `${operation}.json`) : null,
    mutationLock: resolve(root, "mutation.lock.json"),
  };
}

function runGit(cwd, args, label) {
  const result = spawnSync("git", args, {
    cwd,
    env: gitEnvironment(),
    encoding: "utf8",
    timeout: GIT_TIMEOUT_MS,
  });
  if (result.status !== 0) {
    throw new CliError(String(result.stderr || result.stdout).trim() || `${label} failed`);
  }
  return result.stdout.trim();
}

function refTip(cwd, ref) {
  const result = spawnSync("git", ["rev-parse", "--verify", ref], {
    cwd,
    env: gitEnvironment(),
    encoding: "utf8",
    timeout: GIT_TIMEOUT_MS,
  });
  if (result.status === 0) return result.stdout.trim();
  if (result.status === 128) return null;
  throw new CliError(String(result.stderr || result.stdout).trim() || "Git ref inspection failed");
}

function branchName(cwd, value, label) {
  const branch = requireText(value, label, { max: 256 });
  const result = spawnSync("git", ["check-ref-format", "--branch", branch], {
    cwd,
    env: gitEnvironment(),
    encoding: "utf8",
    timeout: GIT_TIMEOUT_MS,
  });
  if (result.status !== 0) throw new CliError(`${label} is not a valid Git branch name`);
  return branch;
}

function validateUpstream(value, { pinned = false, label = "Git upstream" } = {}) {
  if (value === null) return null;
  requireExactFields(value, {
    required: pinned ? ["remote", "ref", "remote_identity"] : ["remote", "ref"],
  }, label);
  const remote = requireText(value.remote, "upstream.remote", { max: 128 });
  if (remote.startsWith("-") || !/^[A-Za-z0-9._-]+$/.test(remote)) {
    throw new CliError("Git upstream remote is invalid");
  }
  const ref = requireText(value.ref, "upstream.ref", { max: 512 });
  if (!ref.startsWith("refs/heads/")) throw new CliError("Git upstream must be a branch ref");
  return {
    remote,
    ref,
    ...(pinned ? { remote_identity: safeId(value.remote_identity, "upstream.remote_identity", { digest: true }) } : {}),
  };
}

function branchUpstream(cwd, branch) {
  const output = runGit(
    cwd,
    ["for-each-ref", "--format=%(upstream:remotename)%00%(upstream:remoteref)", `refs/heads/${branch}`],
    "Git upstream inspection",
  );
  if (!output) return null;
  const [remote, ref] = output.split("\0");
  if (!remote || !ref) return null;
  return validateUpstream({ remote, ref });
}

function remoteIdentity(cwd, remote) {
  const name = validateUpstream({ remote, ref: "refs/heads/placeholder" }).remote;
  const fetchUrls = runGit(
    cwd,
    ["remote", "get-url", "--all", name],
    "Git remote fetch identity inspection",
  ).split("\n").filter(Boolean);
  const pushUrls = runGit(
    cwd,
    ["remote", "get-url", "--push", "--all", name],
    "Git remote push identity inspection",
  ).split("\n").filter(Boolean);
  if (fetchUrls.length !== 1 || pushUrls.length !== 1 || fetchUrls[0] !== pushUrls[0]) {
    throw new CliError("Cleanup requires exactly one identical Git fetch and push URL");
  }
  return sha256(pushUrls[0]);
}

function pinUpstream(cwd, value) {
  const upstream = validateUpstream(value);
  return validateUpstream({
    ...upstream,
    remote_identity: remoteIdentity(cwd, upstream.remote),
  }, { pinned: true });
}

function remoteTip(cwd, upstream) {
  const target = validateUpstream({
    remote: upstream.remote,
    ref: upstream.ref,
    remote_identity: upstream.remote_identity,
  }, { pinned: true });
  if (remoteIdentity(cwd, target.remote) !== target.remote_identity) {
    throw new CliError("Git remote identity drifted");
  }
  branchName(cwd, target.ref.slice("refs/heads/".length), "upstream branch");
  const result = spawnSync("git", ["ls-remote", "--exit-code", "--", target.remote, target.ref], {
    cwd,
    env: gitEnvironment(),
    encoding: "utf8",
    timeout: GIT_TIMEOUT_MS,
  });
  if (result.status === 2) return null;
  if (result.status !== 0) {
    throw new CliError(String(result.stderr || result.stdout).trim() || "Remote branch inspection failed");
  }
  const lines = result.stdout.trim().split("\n").filter(Boolean);
  if (lines.length !== 1) throw new CliError("Remote branch inspection was ambiguous");
  return lines[0].split(/\s+/)[0];
}

function isAncestor(cwd, ancestor, descendant) {
  const result = spawnSync("git", ["merge-base", "--is-ancestor", ancestor, descendant], {
    cwd,
    env: gitEnvironment(),
    encoding: "utf8",
    timeout: GIT_TIMEOUT_MS,
  });
  if (result.status === 0) return true;
  if (result.status === 1) return false;
  throw new CliError(String(result.stderr).trim() || "Git ancestry check failed");
}

function classify(cwd, executorTip, mainTip, supersededBy) {
  if (supersededBy !== null) {
    const supersedingTip = refTip(cwd, supersededBy);
    if (!supersedingTip || !isAncestor(cwd, supersedingTip, mainTip)) {
      throw new CliError("superseded_by must resolve to a revision integrated into main");
    }
    return { disposition: "superseded", superseded_by: supersedingTip };
  }
  if (isAncestor(cwd, executorTip, mainTip)) {
    return { disposition: "ancestor", superseded_by: null };
  }
  const executorMerges = runGit(
    cwd,
    ["rev-list", "--merges", `${mainTip}..${executorTip}`],
    "Git executor merge inspection",
  );
  if (executorMerges) return { disposition: "unmerged", superseded_by: null };
  const cherry = runGit(cwd, ["cherry", mainTip, executorTip], "Git patch-equivalence check");
  const lines = cherry.split("\n").filter(Boolean);
  if (lines.length > 0 && lines.every((line) => line.startsWith("- "))) {
    return { disposition: "patch-equivalent", superseded_by: null };
  }
  return { disposition: "unmerged", superseded_by: null };
}

function worktrees(cwd) {
  const output = execFileSync("git", ["worktree", "list", "--porcelain", "-z"], {
    cwd,
    env: gitEnvironment(),
    encoding: "utf8",
    timeout: GIT_TIMEOUT_MS,
  });
  const result = [];
  let item = null;
  for (const field of output.split("\0")) {
    if (field === "") {
      if (item) result.push(item);
      item = null;
      continue;
    }
    const space = field.indexOf(" ");
    const key = space === -1 ? field : field.slice(0, space);
    const value = space === -1 ? true : field.slice(space + 1);
    if (key === "worktree") item = { path: value, head: null, branch_ref: null };
    else if (!item) throw new CliError("Malformed Git worktree inventory");
    else if (key === "HEAD") item.head = value;
    else if (key === "branch") item.branch_ref = value;
  }
  return result;
}

function worktreeClean(path) {
  return runGit(path, [
    "-c", "status.showUntrackedFiles=all",
    "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching",
  ], "Git worktree cleanliness check") === "";
}

function requireSha(value, label) {
  const result = requireText(value, label, { min: 40, max: 64 });
  if (!SHA_PATTERN.test(result)) throw new CliError(`${label} must be a full Git object id`);
  return result;
}

function recordHash(value) {
  const { ownership_hash: ignored, ...base } = value;
  return sha256(stableStringify(base));
}

function validateBranchClaim(value) {
  requireExactFields(value, {
    required: [
      "schema_version", "kind", "operation_id", "object_id", "worktree_path",
      "branch", "baseline_revision", "claimed_at", "claim_hash",
    ],
  }, "Git executor branch claim");
  if (value.schema_version !== 1 || value.kind !== "codex-flow-git-branch-claim") {
    throw new CliError("Unsupported Git executor branch claim");
  }
  const result = {
    schema_version: 1,
    kind: "codex-flow-git-branch-claim",
    operation_id: safeId(value.operation_id, "operation_id"),
    object_id: requireText(value.object_id, "object_id", { max: 256, safeId: true }),
    worktree_path: requireText(value.worktree_path, "worktree_path", { max: 2048 }),
    branch: requireText(value.branch, "branch", { max: 256 }),
    baseline_revision: requireSha(value.baseline_revision, "baseline_revision"),
    claimed_at: requireText(value.claimed_at, "claimed_at", { max: 64 }),
    claim_hash: safeId(value.claim_hash, "claim_hash", { digest: true }),
  };
  const { claim_hash: ignored, ...base } = result;
  if (sha256(stableStringify(base)) !== result.claim_hash) {
    throw new CliError("Git executor branch claim hash is invalid");
  }
  return result;
}

function claimIsSettled(claim, operation) {
  return operation?.status === "rejected-before-release"
    && operation.resolution?.branch_claim_settlement !== null
    && stableStringify(operation.resolution.branch_claim_settlement.claim) === stableStringify(claim);
}

function validateOwnership(value) {
  requireExactFields(value, {
    required: [
      "schema_version", "kind", "operation_id", "object_id", "executor_id",
      "worktree_path", "branch", "initial_revision", "upstream", "bound_at", "ownership_hash",
    ],
  }, "Git task ownership");
  if (value.schema_version !== 1 || value.kind !== "codex-flow-git-ownership") {
    throw new CliError("Unsupported Git task ownership record");
  }
  const result = {
    schema_version: 1,
    kind: "codex-flow-git-ownership",
    operation_id: safeId(value.operation_id, "operation_id"),
    object_id: requireText(value.object_id, "object_id", { max: 256, safeId: true }),
    executor_id: requireText(value.executor_id, "executor_id", { max: 128, safeId: true }),
    worktree_path: requireText(value.worktree_path, "worktree_path", { max: 2048 }),
    branch: requireText(value.branch, "branch", { max: 256 }),
    initial_revision: requireSha(value.initial_revision, "initial_revision"),
    upstream: validateUpstream(value.upstream, { pinned: true, label: "Git ownership upstream" }),
    bound_at: requireText(value.bound_at, "bound_at", { max: 64 }),
    ownership_hash: safeId(value.ownership_hash, "ownership_hash", { digest: true }),
  };
  if (recordHash(result) !== result.ownership_hash) throw new CliError("Git ownership hash is invalid");
  return result;
}

function validateIntegration(value) {
  requireExactFields(value, {
    required: [
      "schema_version", "kind", "operation_id", "ownership_hash", "main_branch",
      "main_revision", "executor_tip", "upstream", "disposition", "superseded_by", "recorded_at",
    ],
  }, "Git integration record");
  if (value.schema_version !== 1 || value.kind !== "codex-flow-git-integration") {
    throw new CliError("Unsupported Git integration record");
  }
  const result = {
    schema_version: 1,
    kind: "codex-flow-git-integration",
    operation_id: safeId(value.operation_id, "operation_id"),
    ownership_hash: safeId(value.ownership_hash, "ownership_hash", { digest: true }),
    main_branch: requireText(value.main_branch, "main_branch", { max: 256 }),
    main_revision: requireSha(value.main_revision, "main_revision"),
    executor_tip: requireSha(value.executor_tip, "executor_tip"),
    upstream: validateUpstream(value.upstream, { pinned: true, label: "Git integration upstream" }),
    disposition: requireEnum(value.disposition, DISPOSITIONS, "disposition"),
    superseded_by: value.superseded_by === null
      ? null
      : requireSha(value.superseded_by, "superseded_by"),
    recorded_at: requireText(value.recorded_at, "recorded_at", { max: 64 }),
  };
  if ((result.disposition === "superseded") !== (result.superseded_by !== null)) {
    throw new CliError("Git integration supersession fields are inconsistent");
  }
  return result;
}

async function records(directory, validator, stateRoot) {
  await assertNoSymlinkComponents(stateGuard(stateRoot), directory, "Git lifecycle journal path");
  let entries;
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
  const result = [];
  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    if (entry.isSymbolicLink() || !entry.isFile() || !entry.name.endsWith(".json")) {
      throw new CliError(`Git lifecycle journal contains an unsupported entry: ${entry.name}`);
    }
    result.push(validator(await readJson(resolve(directory, entry.name), {
      guardRoot: stateGuard(stateRoot),
    })));
  }
  return result;
}

export async function bindGitOwnership({ git, operationId, now = Date.now(), hooks = {} }) {
  const state = paths(git.stateRoot, { operationId });
  await hooks.beforeMutationLock?.();
  return withProcessLock({
    path: state.mutationLock,
    guardRoot: stateGuard(git.stateRoot),
    label: `Git ownership ${operationId}`,
  }, async () => {
    const operation = (await taskOperationStatus({ stateRoot: git.stateRoot, operationId }))[0];
    if (!operation || operation.status !== "observed") {
      throw new CliError("Git ownership requires an observed task operation");
    }
    if (operation.observation_policy?.state !== "accepted") {
      throw new CliError(
        `Git ownership requires accepted host observation policy: ${operation.observation_policy?.reason_code ?? "missing"}`,
      );
    }
    if (!["local", "host-worktree"].includes(operation.request.environment?.type)) {
      throw new CliError("Git ownership requires a project-backed task operation");
    }
    const hostWorktree = operation.request.environment.type === "host-worktree";
    const requestedPath = operation.request.environment.type === "host-worktree"
      ? operation.observed.evidence.execution_path.value
      : operation.request.environment.project_path;
    const canonical = await realpath(requestedPath).catch(() => null);
    if (!canonical) throw new CliError("Executor worktree does not exist");
    let snapshot = gitSnapshot(canonical);
    if (await realpath(snapshot.root) !== canonical) {
      throw new CliError("Executor path must identify the exact Git worktree root");
    }
    if (await realpath(git.commonDir) !== await realpath(snapshot.commonDir)) {
      throw new CliError("Executor worktree belongs to a different Git repository");
    }
    const executorBranch = hostWorktree
      ? branchName(canonical, operation.request.environment.executor_branch, "executor branch")
      : snapshot.branch;
    const existingRaw = await readJson(state.ownership, {
      allowMissing: true,
      guardRoot: stateGuard(git.stateRoot),
    });
    const existing = existingRaw ? validateOwnership(existingRaw) : null;
    const branchClaimRaw = hostWorktree
      ? await readJson(state.branchClaim, {
        allowMissing: true,
        guardRoot: stateGuard(git.stateRoot),
      })
      : null;
    let branchClaim = branchClaimRaw ? validateBranchClaim(branchClaimRaw) : null;
    if (branchClaim && (
      branchClaim.operation_id !== operation.operation_id
      || branchClaim.object_id !== operation.observed.object_id
      || branchClaim.worktree_path !== canonical
      || branchClaim.branch !== executorBranch
      || branchClaim.baseline_revision !== operation.request.baseline.revision
    )) throw new CliError("Git executor branch claim does not match the observed task operation");
    const claimOperations = new Map((await taskOperationStatus({ stateRoot: git.stateRoot }))
      .map((item) => [item.operation_id, item]));
    const competingClaim = hostWorktree
      ? (await records(resolve(state.root, "branch-claims"), validateBranchClaim, git.stateRoot))
        .find((item) => (
          item.operation_id !== operationId
          && !claimIsSettled(item, claimOperations.get(item.operation_id))
          && (item.branch === executorBranch || item.worktree_path === canonical)
        ))
      : null;
    if (competingClaim) {
      throw new CliError("Executor branch or worktree is already claimed by another task operation");
    }
    const claimed = (await records(resolve(state.root, "ownership"), validateOwnership, git.stateRoot))
      .find((item) => (
        item.operation_id !== operationId
        && (item.branch === executorBranch || item.worktree_path === canonical)
      ));
    if (claimed) throw new CliError("Executor branch or worktree is already owned by another task operation");

    if (hostWorktree) {
      const source = await realpath(operation.request.environment.repository_path);
      if (canonical === source) {
        throw new CliError("Host-created executor worktree must be distinct from its source repository path");
      }
      if (existing && !branchClaim) {
        throw new CliError("Host-worktree Git ownership is missing its branch-claim receipt");
      }
      if (existing && snapshot.branch === "detached") {
        throw new CliError("Bound executor worktree unexpectedly became detached");
      }
      if (!existing) {
        if (snapshot.revision === "unborn") {
          throw new CliError("Host-created executor requires a committed baseline");
        }
        if (snapshot.revision !== operation.request.baseline.revision) {
          throw new CliError("Git ownership must be bound before the executor advances from its authenticated baseline");
        }
        if (!worktreeClean(canonical)) {
          throw new CliError("Host-created executor worktree changed before Git ownership binding");
        }
        if (!branchClaim && snapshot.branch !== "detached") {
          throw new CliError("Host-created executor is on an unexpected named branch");
        }
        if (branchClaim && !["detached", executorBranch].includes(snapshot.branch)) {
          throw new CliError("Claimed executor worktree is on an unexpected named branch");
        }
        const initialInventory = worktrees(git.root).find((item) => item.path === canonical);
        const expectedInitialRef = snapshot.branch === "detached"
          ? null
          : `refs/heads/${executorBranch}`;
        if (
          !initialInventory
          || initialInventory.head !== snapshot.revision
          || initialInventory.branch_ref !== expectedInitialRef
        ) throw new CliError("Host-created path does not match the pre-claim Git worktree inventory");
        const availability = gitBranchAvailability(canonical, executorBranch);
        if (availability.tracked_remote_exists || (!branchClaim && availability.local_exists)) {
          throw new CliError("Task executor branch became unavailable before Git ownership binding");
        }
        if (branchClaim && availability.local_exists) {
          if (refTip(canonical, `refs/heads/${executorBranch}`) !== operation.request.baseline.revision) {
            throw new CliError("Claimed executor branch drifted from its authenticated baseline");
          }
          const otherOwner = worktrees(git.root).find((item) => (
            item.path !== canonical && item.branch_ref === `refs/heads/${executorBranch}`
          ));
          if (otherOwner) throw new CliError("Claimed executor branch is attached to another worktree");
        }
        if (!branchClaim) {
          const claimBase = {
            schema_version: 1,
            kind: "codex-flow-git-branch-claim",
            operation_id: operation.operation_id,
            object_id: operation.observed.object_id,
            worktree_path: canonical,
            branch: executorBranch,
            baseline_revision: operation.request.baseline.revision,
            claimed_at: new Date(now).toISOString(),
          };
          branchClaim = validateBranchClaim({
            ...claimBase,
            claim_hash: sha256(stableStringify(claimBase)),
          });
          await ensureExactJson(state.branchClaim, branchClaim, {
            guardRoot: stateGuard(git.stateRoot),
          });
        }
        if (snapshot.branch === "detached") {
          runGit(
            canonical,
            availability.local_exists
              ? ["switch", executorBranch]
              : ["switch", "--no-track", "-c", executorBranch, operation.request.baseline.revision],
            "Executor branch claim",
          );
          snapshot = gitSnapshot(canonical);
        }
        const claimedAvailability = gitBranchAvailability(canonical, executorBranch);
        if (!claimedAvailability.local_exists || claimedAvailability.tracked_remote_exists) {
          throw new CliError("Executor branch availability changed during Git ownership binding");
        }
      }
    }
    if (snapshot.branch === "detached" || snapshot.revision === "unborn") {
      throw new CliError("Executor Git ownership requires a named branch and committed revision");
    }
    branchName(canonical, snapshot.branch, "executor branch");
    if (hostWorktree && snapshot.branch !== executorBranch) {
      throw new CliError("Executor branch claim did not establish the packet-declared branch");
    }
    const inventory = worktrees(git.root).find((item) => item.path === canonical);
    if (
      !inventory
      || inventory.head !== snapshot.revision
      || inventory.branch_ref !== `refs/heads/${snapshot.branch}`
    ) throw new CliError("Executor path does not match the canonical Git worktree inventory");
    const authorityRoot = hostWorktree
      ? operation.request.environment.repository_path
      : git.root;
    const authorityBranch = hostWorktree
      ? operation.request.environment.starting_branch
      : git.branch;
    const authorityUpstream = branchUpstream(authorityRoot, authorityBranch);
    const base = {
      schema_version: 1,
      kind: "codex-flow-git-ownership",
      operation_id: operation.operation_id,
      object_id: operation.observed.object_id,
      executor_id: operation.request.task_id,
      worktree_path: canonical,
      branch: snapshot.branch,
      initial_revision: snapshot.revision,
      upstream: authorityUpstream === null
        ? null
        : pinUpstream(authorityRoot, {
          remote: authorityUpstream.remote,
          ref: `refs/heads/${snapshot.branch}`,
        }),
      bound_at: new Date(now).toISOString(),
    };
    const ownership = validateOwnership({ ...base, ownership_hash: sha256(stableStringify(base)) });
    if (existing) {
      const bound = existing;
      const unchanged = (
        bound.operation_id === base.operation_id
        && bound.object_id === base.object_id
        && bound.executor_id === base.executor_id
        && bound.worktree_path === base.worktree_path
        && bound.branch === base.branch
        && stableStringify(bound.upstream) === stableStringify(base.upstream)
      );
      if (!unchanged) throw new CliError("Git ownership is already bound to different executor state");
      return bound;
    }
    if (snapshot.revision !== operation.request.baseline.revision) {
      throw new CliError("Git ownership must be bound before the executor branch advances from its authenticated baseline");
    }
    if (hostWorktree && !worktreeClean(canonical)) {
      throw new CliError("Host-created executor worktree changed before Git ownership binding");
    }
    if (hostWorktree) hooks.afterBranchClaim?.({ branch_claim: branchClaim, snapshot });
    await ensureExactJson(state.ownership, ownership, { guardRoot: stateGuard(git.stateRoot) });
    return ownership;
  });
}

export async function authorizeGitBoundTaskRelease({ git, operationId, packet: input }) {
  const packet = validateTaskPacket(input);
  if (packet.environment.type !== "host-worktree") {
    throw new CliError("Git-bound release is reserved for host-worktree packets");
  }
  const operation = (await taskOperationStatus({ stateRoot: git.stateRoot, operationId }))[0];
  if (!operation || operation.status !== "observed") {
    throw new CliError("Task release requires an observed task operation");
  }
  if (operation.observation_policy?.state !== "accepted") {
    throw new CliError(
      `Task release requires accepted host observation policy: ${operation.observation_policy?.reason_code ?? "missing"}`,
    );
  }
  if (operation.packet_hash !== sha256(stableStringify(packet))) {
    throw new CliError("Task release packet does not match the prepared operation");
  }
  const state = paths(git.stateRoot, { operationId });
  const raw = await readJson(state.ownership, {
    allowMissing: true,
    guardRoot: stateGuard(git.stateRoot),
  });
  if (!raw) throw new CliError("Task release requires bound Git ownership");
  const ownership = validateOwnership(raw);
  if (ownership.object_id !== operation.observed.object_id) {
    throw new CliError("Task release ownership does not match the observed host object");
  }
  const canonical = await realpath(ownership.worktree_path).catch(() => null);
  if (!canonical) throw new CliError("Task release worktree no longer exists");
  const snapshot = gitSnapshot(canonical);
  if (
    await realpath(snapshot.root) !== canonical
    || await realpath(snapshot.commonDir) !== await realpath(git.commonDir)
    || snapshot.branch !== ownership.branch
    || snapshot.revision !== ownership.initial_revision
    || snapshot.revision !== packet.baseline.revision
    || !worktreeClean(canonical)
  ) throw new CliError("Task release worktree drifted after Git ownership binding");
  return {
    operation_id: operation.operation_id,
    object_id: ownership.object_id,
    worktree_path: canonical,
    branch: ownership.branch,
    revision: ownership.initial_revision,
    ownership_hash: ownership.ownership_hash,
  };
}

export async function recordGitIntegration({
  git,
  operationId,
  mainBranch,
  supersededBy = null,
  now = Date.now(),
}) {
  const main = branchName(git.root, mainBranch, "main_branch");
  const state = paths(git.stateRoot, { operationId });
  return withProcessLock({
    path: state.mutationLock,
    guardRoot: stateGuard(git.stateRoot),
    label: `Git integration ${operationId}`,
  }, async () => {
    const raw = await readJson(state.ownership, { allowMissing: true, guardRoot: stateGuard(git.stateRoot) });
    if (!raw) throw new CliError("Git ownership is not bound for this operation");
    const ownership = validateOwnership(raw);
    const controller = gitSnapshot(git.root);
    if (controller.branch !== main || controller.cleanliness !== "clean") {
      throw new CliError("Record integration from a clean checkout of the integrating main branch");
    }
    const mainRevision = refTip(git.root, `refs/heads/${main}`);
    const executorTip = refTip(git.root, `refs/heads/${ownership.branch}`);
    if (!mainRevision || !executorTip) throw new CliError("Integration requires local main and executor refs");
    if (ownership.upstream !== null) {
      const configured = branchUpstream(git.root, ownership.branch);
      if (
        configured === null
        || configured.remote !== ownership.upstream.remote
        || configured.ref !== ownership.upstream.ref
        || remoteIdentity(git.root, configured.remote) !== ownership.upstream.remote_identity
      ) throw new CliError("Executor upstream drifted from its bound ownership");
    }
    const result = classify(git.root, executorTip, mainRevision, supersededBy);
    const integration = validateIntegration({
      schema_version: 1,
      kind: "codex-flow-git-integration",
      operation_id: operationId,
      ownership_hash: ownership.ownership_hash,
      main_branch: main,
      main_revision: mainRevision,
      executor_tip: executorTip,
      upstream: ownership.upstream,
      disposition: result.disposition,
      superseded_by: result.superseded_by,
      recorded_at: new Date(now).toISOString(),
    });
    await atomicWriteJson(state.integration, integration, { guardRoot: stateGuard(git.stateRoot) });
    return integration;
  });
}

export async function gitLifecycleAudit({ git, config, inspectRemotes = true }) {
  const state = paths(git.stateRoot);
  const branchClaims = await records(
    resolve(state.root, "branch-claims"),
    validateBranchClaim,
    git.stateRoot,
  );
  const ownerships = await records(resolve(state.root, "ownership"), validateOwnership, git.stateRoot);
  const integrations = await records(resolve(state.root, "integrations"), validateIntegration, git.stateRoot);
  const integrationById = new Map(integrations.map((item) => [item.operation_id, item]));
  const operationRecords = await taskOperationStatus({ stateRoot: git.stateRoot });
  const operationById = new Map(operationRecords.map((item) => [item.operation_id, item]));
  const operations = new Set(operationById.keys());
  const activeOwners = new Set((await leaseStatus({ stateRoot: git.stateRoot }))
    .filter((item) => item.state === "active")
    .map((item) => item.owner));
  const inventory = worktrees(git.root);
  const ownershipById = new Map(ownerships.map((item) => [item.operation_id, item]));
  const claimItems = branchClaims.map((claim) => {
    const operation = operationById.get(claim.operation_id) ?? null;
    const ownership = ownershipById.get(claim.operation_id) ?? null;
    if (operation && (
      operation.request.environment.type !== "host-worktree"
      || operation.observed?.object_id !== claim.object_id
      || operation.observed?.evidence.execution_path.value !== claim.worktree_path
      || operation.request.environment.executor_branch !== claim.branch
      || operation.request.baseline.revision !== claim.baseline_revision
    )) throw new CliError(`Branch claim changed from task-operation authority for ${claim.operation_id}`);
    if (ownership && (
      ownership.object_id !== claim.object_id
      || ownership.worktree_path !== claim.worktree_path
      || ownership.branch !== claim.branch
      || ownership.initial_revision !== claim.baseline_revision
    )) throw new CliError(`Branch claim changed from Git ownership for ${claim.operation_id}`);
    const inventoryItem = inventory.find((item) => item.path === claim.worktree_path) ?? null;
    const settled = claimIsSettled(claim, operation);
    return {
      operation_id: claim.operation_id,
      branch: claim.branch,
      worktree_path: claim.worktree_path,
      baseline_revision: claim.baseline_revision,
      ownership_bound: ownershipById.has(claim.operation_id),
      operation_present: operations.has(claim.operation_id),
      worktree_present: inventoryItem !== null,
      observed_branch_ref: inventoryItem?.branch_ref ?? null,
      observed_revision: inventoryItem?.head ?? null,
      settled,
    };
  });
  const incompleteClaimCount = claimItems.filter((item) => !item.ownership_bound && !item.settled).length;
  const protectedBranches = new Set([...config.git_lifecycle.protected_branches, git.branch]);
  const items = [];

  for (const ownership of ownerships) {
    const integration = integrationById.get(ownership.operation_id) ?? null;
    if (integration && integration.ownership_hash !== ownership.ownership_hash) {
      throw new CliError(`Integration ownership hash changed for ${ownership.operation_id}`);
    }
    const localTip = refTip(git.root, `refs/heads/${ownership.branch}`);
    const matching = inventory.filter((item) => item.branch_ref === `refs/heads/${ownership.branch}`);
    const owned = matching.find((item) => item.path === ownership.worktree_path) ?? null;
    let worktreeState = "missing";
    if (owned) {
      worktreeState = owned.path === git.root ? "current" : worktreeClean(owned.path) ? "clean" : "dirty";
    } else if (matching.length > 0) worktreeState = "mismatched";
    let remote = integration?.upstream && !inspectRemotes
      ? { state: "not-checked", tip: null }
      : { state: "none", tip: null };
    if (inspectRemotes && integration?.upstream) {
      try {
        const tip = remoteTip(git.root, integration.upstream);
        remote = { state: tip === null ? "missing" : "present", tip };
      } catch (error) {
        remote = { state: "unavailable", tip: null, error: error.message };
      }
    }

    const blockers = [];
    if (!operations.has(ownership.operation_id)) blockers.push("orphaned-operation");
    if (protectedBranches.has(ownership.branch)) blockers.push("protected-branch");
    const upstreamBranch = integration?.upstream?.ref.slice("refs/heads/".length) ?? null;
    if (upstreamBranch !== null && protectedBranches.has(upstreamBranch)) blockers.push("protected-upstream");
    if (activeOwners.has(ownership.executor_id) || activeOwners.has(ownership.operation_id)) blockers.push("active-lease");
    if (!integration) blockers.push("integration-unrecorded");
    else if (!SAFE_DISPOSITIONS.includes(integration.disposition)) blockers.push("unmerged");
    if (integration && localTip !== null && localTip !== integration.executor_tip) blockers.push("local-tip-drift");
    if (integration && remote.tip !== null && remote.tip !== integration.executor_tip) blockers.push("remote-tip-drift");
    if (["current", "dirty", "mismatched"].includes(worktreeState)) blockers.push(`worktree-${worktreeState}`);
    if (localTip === null && worktreeState !== "missing") blockers.push("local-branch-missing");
    if (remote.state === "unavailable") blockers.push("remote-unavailable");
    if (remote.state === "not-checked") blockers.push("remote-not-checked");
    const hasResource = (
      localTip !== null
      || worktreeState !== "missing"
      || ["present", "unavailable"].includes(remote.state)
    );
    if (!hasResource) blockers.push("already-missing");

    let classification = integration?.disposition ?? "active";
    if (blockers.includes("orphaned-operation")) classification = "orphaned";
    else if (blockers.includes("protected-branch") || blockers.includes("protected-upstream")) classification = "protected";
    else if (blockers.includes("active-lease") || blockers.includes("integration-unrecorded")) classification = "active";
    else if (blockers.includes("worktree-dirty")) classification = "dirty";
    else if (blockers.includes("unmerged")) classification = "unmerged";
    else if (blockers.includes("already-missing")) classification = "missing";

    const backlog = (
      (integration !== null || blockers.includes("orphaned-operation"))
      && hasResource
      && !blockers.includes("protected-branch")
      && !blockers.includes("protected-upstream")
      && !blockers.includes("active-lease")
    );
    items.push({
      operation_id: ownership.operation_id,
      executor_id: ownership.executor_id,
      branch: ownership.branch,
      worktree_path: ownership.worktree_path,
      worktree_state: worktreeState,
      local_tip: localTip,
      remote,
      integration,
      classification,
      blockers,
      eligible: blockers.length === 0,
      backlog,
    });
  }
  const eligibleCount = items.filter((item) => item.eligible).length;
  const backlogCount = items.filter((item) => item.backlog).length + incompleteClaimCount;
  return {
    mutation_performed: false,
    items,
    branch_claims: claimItems,
    incomplete_claim_count: incompleteClaimCount,
    eligible_count: eligibleCount,
    backlog_count: backlogCount,
    warn_at: config.git_lifecycle.warn_at,
    block_at: config.git_lifecycle.block_at,
    warning: backlogCount >= config.git_lifecycle.warn_at,
    blocked: incompleteClaimCount > 0 || backlogCount >= config.git_lifecycle.block_at,
  };
}

export async function gitLifecycleReadiness(options) {
  const audit = await gitLifecycleAudit({ ...options, inspectRemotes: false });
  return {
    eligible_count: audit.eligible_count,
    backlog_count: audit.backlog_count,
    warning: audit.warning,
    blocked: audit.blocked,
    message: audit.blocked
      ? audit.incomplete_claim_count > 0
        ? `${audit.incomplete_claim_count} executor branch claim(s) require binding recovery before another task wave`
        : `${audit.backlog_count} task Git records require reconciliation and reached the block threshold`
      : audit.warning
        ? `${audit.backlog_count} task Git records require reconciliation and reached the warning threshold`
        : null,
  };
}

function operationIds(value) {
  if (!Array.isArray(value) || value.length === 0 || value.length > 64) {
    throw new CliError("Cleanup requires between 1 and 64 explicit operation IDs");
  }
  const result = value.map((id, index) => safeId(id, `operation_ids[${index}]`));
  if (new Set(result).size !== result.length) throw new CliError("Cleanup operation IDs must be unique");
  return result.sort();
}

export async function createGitCleanupPlan({ git, config, operationIds: requested, mainBranch, includeRemote = false }) {
  const ids = operationIds(requested);
  const main = branchName(git.root, mainBranch, "main_branch");
  const controller = gitSnapshot(git.root);
  if (controller.branch !== main || controller.cleanliness !== "clean") {
    throw new CliError("Create cleanup plans from a clean checkout of the integrating main branch");
  }
  const configuredMainUpstream = branchUpstream(git.root, main);
  if (!configuredMainUpstream) throw new CliError("Cleanup planning requires a pushed main branch with an upstream");
  const mainUpstream = pinUpstream(git.root, configuredMainUpstream);
  const mainRemoteTip = remoteTip(git.root, mainUpstream);
  if (mainRemoteTip !== controller.revision) {
    throw new CliError("Integrating main must exactly match its remote tip before cleanup planning");
  }
  const audit = await gitLifecycleAudit({ git, config });
  const byId = new Map(audit.items.map((item) => [item.operation_id, item]));
  const candidates = [];
  for (const id of ids) {
    const item = byId.get(id);
    if (!item) throw new CliError(`No Git ownership exists for ${id}`);
    if (!item.eligible) throw new CliError(`${id} is not cleanup-eligible: ${item.blockers.join(", ")}`);
    if (!isAncestor(git.root, item.integration.main_revision, controller.revision)) {
      throw new CliError(`${id} integration is not in the current main history`);
    }
    candidates.push({
      operation_id: id,
      branch: item.branch,
      worktree_path: item.worktree_path,
      expected_tip: item.integration.executor_tip,
      disposition: item.integration.disposition,
      remove_worktree: item.worktree_state === "clean",
      delete_local: item.local_tip !== null,
      remote: includeRemote && item.integration.upstream && item.remote.tip !== null
        ? { ...item.integration.upstream, expected_tip: item.remote.tip }
        : null,
    });
  }
  const base = {
    schema_version: 1,
    kind: "codex-flow-git-cleanup-plan",
    repository: {
      common_dir: await realpath(git.commonDir),
      controller_root: await realpath(git.root),
      main_branch: main,
      main_revision: controller.revision,
      main_upstream: { ...mainUpstream, expected_tip: mainRemoteTip },
    },
    include_remote: includeRemote,
    operation_ids: ids,
    candidates,
  };
  return { ...base, plan_id: sha256(stableStringify(base)) };
}

function validatePlan(value) {
  requireExactFields(value, {
    required: [
      "schema_version", "kind", "repository", "include_remote", "operation_ids", "candidates", "plan_id",
    ],
  }, "Git cleanup plan");
  const { plan_id: planId, ...base } = value;
  safeId(planId, "plan_id", { digest: true });
  if (value.schema_version !== 1 || value.kind !== "codex-flow-git-cleanup-plan") {
    throw new CliError("Unsupported Git cleanup plan");
  }
  if (sha256(stableStringify(base)) !== planId) throw new CliError("Git cleanup plan hash is invalid");
  operationIds(value.operation_ids);
  if (!Array.isArray(value.candidates) || value.candidates.length !== value.operation_ids.length) {
    throw new CliError("Git cleanup plan candidate inventory is invalid");
  }
  return value;
}

export async function applyGitCleanupPlan({
  git,
  config,
  expectedPlanId,
  operationIds: requested,
  mainBranch,
  includeRemote = false,
  hooks = {},
  now = Date.now(),
}) {
  const planId = safeId(expectedPlanId, "plan_id", { digest: true });
  const state = paths(git.stateRoot);
  const completedActions = [];
  let failedAction = "preflight";
  const execute = () => withProcessLock({
    path: state.mutationLock,
    guardRoot: stateGuard(git.stateRoot),
    label: "Git cleanup apply",
  }, async () => {
    const plan = validatePlan(await createGitCleanupPlan({
      git,
      config,
      operationIds: requested,
      mainBranch,
      includeRemote,
    }));
    if (plan.plan_id !== planId) {
      throw new CliError(`Cleanup plan changed; expected ${planId}, current ${plan.plan_id}`);
    }
    if (
      await realpath(git.commonDir) !== plan.repository.common_dir
      || await realpath(git.root) !== plan.repository.controller_root
    ) throw new CliError("Cleanup repository identity drifted from the plan");
    const controller = gitSnapshot(git.root);
    if (
      controller.branch !== plan.repository.main_branch
      || controller.revision !== plan.repository.main_revision
      || controller.cleanliness !== "clean"
    ) throw new CliError("Cleanup controller state drifted from the plan");
    if (remoteTip(git.root, plan.repository.main_upstream) !== plan.repository.main_upstream.expected_tip) {
      throw new CliError("Cleanup main remote tip drifted from the plan");
    }

    const revalidate = async (candidate) => {
      const audit = await gitLifecycleAudit({ git: gitSnapshot(git.root), config });
      const current = audit.items.find((item) => item.operation_id === candidate.operation_id);
      if (!current?.eligible) {
        throw new CliError(`${candidate.operation_id} is no longer cleanup-eligible: ${current?.blockers.join(", ") ?? "missing ownership"}`);
      }
      if (
        current.integration.executor_tip !== candidate.expected_tip
        || current.branch !== candidate.branch
        || current.worktree_path !== candidate.worktree_path
      ) throw new CliError(`Cleanup candidate drifted for ${candidate.operation_id}`);
      return current;
    };

    const completeAction = async (candidate, action) => {
      const actionId = `${candidate.operation_id}:${action}`;
      completedActions.push(actionId);
      failedAction = `${actionId}:post-action`;
      if (hooks.afterAction) await hooks.afterAction({ candidate, action });
      failedAction = "between-actions";
    };

    for (const candidate of plan.candidates) {
      if (candidate.remove_worktree) {
        const action = "worktree-remove";
        failedAction = `${candidate.operation_id}:${action}`;
        await revalidate(candidate);
        const item = worktrees(git.root).find((entry) => entry.path === candidate.worktree_path);
        if (!item || item.path === git.root || item.branch_ref !== `refs/heads/${candidate.branch}`
          || item.head !== candidate.expected_tip || !worktreeClean(item.path)) {
          throw new CliError(`Worktree drifted for ${candidate.operation_id}`);
        }
        runGit(git.root, ["worktree", "remove", candidate.worktree_path], "Git worktree removal");
        if (worktrees(git.root).some((entry) => entry.path === candidate.worktree_path)) {
          throw new CliError("Worktree removal was not observed");
        }
        await completeAction(candidate, action);
      }
      if (candidate.delete_local) {
        const action = "local-delete";
        failedAction = `${candidate.operation_id}:${action}`;
        await revalidate(candidate);
        if (worktrees(git.root).some((entry) => entry.branch_ref === `refs/heads/${candidate.branch}`)) {
          throw new CliError(`Local branch is still checked out for ${candidate.operation_id}`);
        }
        const ref = `refs/heads/${candidate.branch}`;
        const current = refTip(git.root, ref);
        if (current !== candidate.expected_tip) throw new CliError(`Local branch drifted for ${candidate.operation_id}`);
        runGit(git.root, ["update-ref", "-d", ref, candidate.expected_tip], "Local branch deletion");
        if (refTip(git.root, ref) !== null) throw new CliError("Local branch deletion was not observed");
        await completeAction(candidate, action);
      }
      if (candidate.remote) {
        const action = "remote-delete";
        failedAction = `${candidate.operation_id}:${action}`;
        await revalidate(candidate);
        const current = remoteTip(git.root, candidate.remote);
        if (current !== candidate.remote.expected_tip) {
          throw new CliError(`Remote branch drifted for ${candidate.operation_id}`);
        }
        runGit(git.root, [
          "push",
          `--force-with-lease=${candidate.remote.ref}:${candidate.remote.expected_tip}`,
          candidate.remote.remote,
          `:${candidate.remote.ref}`,
        ], "Remote branch deletion");
        if (remoteTip(git.root, candidate.remote) !== null) throw new CliError("Remote branch deletion was not observed");
        await completeAction(candidate, action);
      }
    }
    return {
      schema_version: 1,
      kind: "codex-flow-git-cleanup-result",
      plan,
      completed_actions: completedActions,
      status: "complete",
      completed_at: new Date(now).toISOString(),
    };
  });

  try {
    return await execute();
  } catch (error) {
    if (error instanceof GitCleanupApplyError) throw error;
    const result = {
      schema_version: 1,
      kind: "codex-flow-git-cleanup-result",
      plan_id: planId,
      completed_actions: [...completedActions],
      failed_action: failedAction,
      status: completedActions.length > 0 ? "partial" : "failed",
      error: cleanupFailureReason(error),
      failed_at: new Date(now).toISOString(),
    };
    throw new GitCleanupApplyError(result, error instanceof CliError ? error.exitCode : 1);
  }
}
