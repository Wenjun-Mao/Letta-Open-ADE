import { execFileSync, spawnSync } from "node:child_process";
import { isAbsolute, resolve } from "node:path";
import { CliError, PACKAGE_VERSION } from "./core.mjs";

export const CODEX_FLOW_STATE_NAMESPACE = `v${PACKAGE_VERSION}`;

export function gitCommonDirectoryForState(stateRoot) {
  return resolve(stateRoot, "..", "..");
}

export function gitOutput(cwd, args) {
  try {
    return execFileSync("git", args, {
      cwd,
      env: { ...process.env, GIT_OPTIONAL_LOCKS: "0" },
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    }).trim();
  } catch (error) {
    const detail = String(error?.stderr ?? "").trim();
    throw new CliError(detail || `Git command failed: git ${args.join(" ")}`);
  }
}

export function discoverGit(cwd = process.cwd()) {
  const root = gitOutput(cwd, ["rev-parse", "--show-toplevel"]);
  const absoluteCommon = spawnSync("git", ["rev-parse", "--path-format=absolute", "--git-common-dir"], {
    cwd,
    env: { ...process.env, GIT_OPTIONAL_LOCKS: "0" },
    encoding: "utf8",
  });
  const rawCommon = absoluteCommon.status === 0
    ? absoluteCommon.stdout.trim()
    : gitOutput(cwd, ["rev-parse", "--git-common-dir"]);
  const commonDir = isAbsolute(rawCommon) ? rawCommon : resolve(cwd, rawCommon);
  return {
    root,
    commonDir,
    stateRoot: resolve(commonDir, "codex-flow", CODEX_FLOW_STATE_NAMESPACE),
  };
}

export function gitSnapshot(cwd = process.cwd()) {
  const context = discoverGit(cwd);
  const branchResult = spawnSync("git", ["symbolic-ref", "--quiet", "--short", "HEAD"], {
    cwd: context.root,
    env: { ...process.env, GIT_OPTIONAL_LOCKS: "0" },
    encoding: "utf8",
  });
  const branch = branchResult.status === 0 ? branchResult.stdout.trim() : "detached";
  const revisionResult = spawnSync("git", ["rev-parse", "--verify", "HEAD"], {
    cwd: context.root,
    env: { ...process.env, GIT_OPTIONAL_LOCKS: "0" },
    encoding: "utf8",
  });
  const revision = revisionResult.status === 0 ? revisionResult.stdout.trim() : "unborn";
  const porcelain = gitOutput(context.root, ["status", "--porcelain=v1"]);
  let upstream = null;
  const upstreamResult = spawnSync("git", ["rev-parse", "--abbrev-ref", "@{upstream}"], {
    cwd: context.root,
    env: { ...process.env, GIT_OPTIONAL_LOCKS: "0" },
    encoding: "utf8",
  });
  if (upstreamResult.status === 0) upstream = upstreamResult.stdout.trim();
  return {
    ...context,
    branch,
    revision,
    upstream,
    cleanliness: porcelain === "" ? "clean" : "dirty",
  };
}

export function validateGitBranchName(cwd, value, label = "Git branch") {
  if (typeof value !== "string" || value.length === 0 || value.length > 256) {
    throw new CliError(`${label} is not a valid Git branch name`);
  }
  const result = spawnSync("git", ["check-ref-format", "--branch", value], {
    cwd,
    env: { ...process.env, GIT_OPTIONAL_LOCKS: "0" },
    encoding: "utf8",
  });
  if (result.status !== 0) throw new CliError(`${label} is not a valid Git branch name`);
  return value;
}

export function gitLocalBranchRevision(cwd, branch) {
  const name = validateGitBranchName(cwd, branch, "Task starting branch");
  const result = spawnSync("git", ["rev-parse", "--verify", `refs/heads/${name}^{commit}`], {
    cwd,
    env: { ...process.env, GIT_OPTIONAL_LOCKS: "0" },
    encoding: "utf8",
  });
  if (result.status !== 0) throw new CliError("Task starting branch does not exist locally");
  return result.stdout.trim();
}

export function gitBranchAvailability(cwd, branch) {
  const name = validateGitBranchName(cwd, branch, "Task executor branch");
  const local = spawnSync("git", ["show-ref", "--verify", "--quiet", `refs/heads/${name}`], {
    cwd,
    env: { ...process.env, GIT_OPTIONAL_LOCKS: "0" },
    encoding: "utf8",
  });
  if (![0, 1].includes(local.status)) {
    throw new CliError(String(local.stderr || local.stdout).trim() || "Executor branch inspection failed");
  }
  const tracked = spawnSync(
    "git",
    ["for-each-ref", "--format=%(refname:strip=3)", "refs/remotes"],
    {
      cwd,
      env: { ...process.env, GIT_OPTIONAL_LOCKS: "0" },
      encoding: "utf8",
    },
  );
  if (tracked.status !== 0) {
    throw new CliError(String(tracked.stderr || tracked.stdout).trim() || "Tracked remote branch inspection failed");
  }
  return {
    branch: name,
    local_exists: local.status === 0,
    tracked_remote_exists: tracked.stdout.split("\n").filter(Boolean).includes(name),
  };
}

export function requireAvailableGitBranch(cwd, branch) {
  const availability = gitBranchAvailability(cwd, branch);
  if (availability.local_exists || availability.tracked_remote_exists) {
    throw new CliError("Task executor branch already exists locally or in fetched remote-tracking state");
  }
  return availability.branch;
}
