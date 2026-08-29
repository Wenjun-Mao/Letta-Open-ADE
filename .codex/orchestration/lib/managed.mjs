import { randomUUID } from "node:crypto";
import { readdir, readFile, rename, rm } from "node:fs/promises";
import { basename, dirname, join, relative, resolve, sep } from "node:path";
import {
  assertNoSymlinkComponents,
  CliError,
  PACKAGE_VERSION,
  atomicWrite,
  atomicWriteJson,
  ensureDirectory,
  pathExists,
  readJson,
  sha256,
  sha256File,
  stableStringify,
  withProcessLock,
} from "./core.mjs";
import {
  orchestrationRoot,
  projectConfigPath,
  validateProjectConfig,
} from "./config.mjs";

const START_PATTERN = /<!-- codex-flow:start v[^\s]+ -->/g;
const END_MARKER = "<!-- codex-flow:end -->";

async function walkFiles(root) {
  const result = [];
  const entries = await readdir(root, { withFileTypes: true });
  for (const entry of entries) {
    const path = join(root, entry.name);
    if (entry.isSymbolicLink()) throw new CliError(`Managed package source contains a symbolic link: ${path}`);
    if (entry.isDirectory()) result.push(...await walkFiles(path));
    else if (entry.isFile()) result.push(path);
  }
  return result;
}

function validateManagedRelativePath(value) {
  if (
    typeof value !== "string" || value === "" || value.startsWith("/")
    || value.includes("\\") || value.split("/").includes("..")
    || !["bin/", "lib/", "schemas/", "roles/", "references/"].some((prefix) => value.startsWith(prefix))
  ) {
    throw new CliError(`Installed codex-flow manifest contains an unsafe path: ${value}`);
  }
  return value;
}

function targetRelativePath(packageRoot, source) {
  const relativeSource = relative(packageRoot, source).split(sep).join("/");
  if (relativeSource.startsWith("bin/") || relativeSource.startsWith("lib/") || relativeSource.startsWith("schemas/")) {
    return relativeSource;
  }
  if (relativeSource.startsWith("templates/roles/")) {
    return relativeSource.slice("templates/".length);
  }
  if (relativeSource.startsWith("templates/references/")) {
    return relativeSource.slice("templates/".length);
  }
  throw new CliError(`Unsupported managed source: ${relativeSource}`);
}

export async function sourceManagedFiles(packageRoot) {
  const roots = ["bin", "lib", "schemas", "templates/roles", "templates/references"];
  const files = [];
  for (const root of roots) {
    const sourceRoot = resolve(packageRoot, root);
    for (const source of await walkFiles(sourceRoot)) {
      const contents = await readFile(source);
      files.push({
        source,
        relativePath: targetRelativePath(packageRoot, source),
        contents,
        hash: sha256(contents),
      });
    }
  }
  return files.sort((a, b) => a.relativePath.localeCompare(b.relativePath));
}

function manifestFor(files) {
  return {
    schema_version: 1,
    package_version: PACKAGE_VERSION,
    files: Object.fromEntries(files.map((file) => [file.relativePath, file.hash])),
  };
}

function validateManifest(value) {
  if (
    typeof value !== "object" || value === null || Array.isArray(value)
    || value.schema_version !== 1
    || typeof value.package_version !== "string"
    || typeof value.files !== "object" || value.files === null || Array.isArray(value.files)
  ) {
    throw new CliError("Installed codex-flow version manifest is invalid");
  }
  for (const [path, hash] of Object.entries(value.files)) {
    validateManagedRelativePath(path);
    if (typeof hash !== "string" || !/^[a-f0-9]{64}$/.test(hash)) {
      throw new CliError("Installed codex-flow version manifest contains an invalid file record");
    }
  }
  return value;
}

async function driftAgainstManifest(targetRoot, manifest, guardRoot) {
  const drift = [];
  for (const [relativePath, expectedHash] of Object.entries(manifest.files)) {
    const target = resolve(targetRoot, relativePath);
    await assertNoSymlinkComponents(guardRoot, target, "Managed runtime path");
    if (!await pathExists(target)) {
      drift.push({ path: relativePath, state: "missing" });
      continue;
    }
    const actualHash = await sha256File(target);
    if (actualHash !== expectedHash) drift.push({ path: relativePath, state: "modified" });
  }
  return drift;
}

export async function targetSnapshot(gitRoot, targetRoot) {
  await assertNoSymlinkComponents(gitRoot, targetRoot, "Managed runtime root");
  const files = {};
  async function visit(directory) {
    let entries;
    try {
      entries = await readdir(directory, { withFileTypes: true });
    } catch (error) {
      if (error?.code === "ENOENT") return;
      throw error;
    }
    for (const entry of entries) {
      const path = join(directory, entry.name);
      if (entry.isSymbolicLink()) throw new CliError(`Managed runtime contains a symbolic link: ${path}`);
      if (entry.isDirectory()) await visit(path);
      else if (entry.isFile()) files[relative(targetRoot, path).split(sep).join("/")] = await sha256File(path);
      else throw new CliError(`Managed runtime contains an unsupported filesystem entry: ${path}`);
    }
  }
  await visit(targetRoot);
  return files;
}

function managedMarkerRange(existing) {
  const starts = [...existing.matchAll(START_PATTERN)];
  const endCount = existing.split(END_MARKER).length - 1;
  if (starts.length !== endCount || starts.length > 1) {
    throw new CliError("AGENTS.md contains malformed or duplicate codex-flow managed markers");
  }
  if (starts.length === 0) return null;
  const start = starts[0].index;
  const endIndex = existing.indexOf(END_MARKER, start);
  if (endIndex < start) throw new CliError("AGENTS.md contains malformed or duplicate codex-flow managed markers");
  return { start, end: endIndex + END_MARKER.length };
}

export function replaceManagedAgentsBlock(existing, block) {
  const range = managedMarkerRange(existing);
  if (!range) {
    const prefix = existing === "" ? "" : `${existing.replace(/\s*$/, "")}\n\n`;
    return `${prefix}${block.trim()}\n`;
  }
  return `${existing.slice(0, range.start)}${block.trim()}${existing.slice(range.end)}`.replace(/\s*$/, "\n");
}

export function removeManagedAgentsBlock(existing) {
  const range = managedMarkerRange(existing);
  if (!range) return existing;
  const before = existing.slice(0, range.start).trimEnd();
  const after = existing.slice(range.end).trimStart();
  if (before === "" && after === "") return "";
  if (before === "") return `${after.trimEnd()}\n`;
  if (after === "") return `${before}\n`;
  return `${before}\n\n${after.trimEnd()}\n`;
}

export async function inspectManaged({ gitRoot, packageRoot }) {
  const targetRoot = orchestrationRoot(gitRoot);
  await assertNoSymlinkComponents(gitRoot, targetRoot, "Managed runtime root");
  const manifestPath = resolve(targetRoot, "version.json");
  const existingManifestRaw = await readJson(manifestPath, { allowMissing: true, guardRoot: gitRoot });
  const existingManifest = existingManifestRaw ? validateManifest(existingManifestRaw) : null;
  const sourceFiles = await sourceManagedFiles(packageRoot);
  const desiredManifest = manifestFor(sourceFiles);
  const drift = existingManifest ? await driftAgainstManifest(targetRoot, existingManifest, gitRoot) : [];
  const desiredDrift = [];
  for (const file of sourceFiles) {
    const target = resolve(targetRoot, file.relativePath);
    await assertNoSymlinkComponents(gitRoot, target, "Managed runtime path");
    if (!await pathExists(target)) desiredDrift.push({ path: file.relativePath, state: "missing" });
    else if (await sha256File(target) !== file.hash) desiredDrift.push({ path: file.relativePath, state: "outdated" });
  }
  const snapshot = await targetSnapshot(gitRoot, targetRoot);
  const expectedPaths = new Set([
    ...sourceFiles.map((file) => file.relativePath),
    ...Object.keys(existingManifest?.files ?? {}),
    "project.json",
    "version.json",
  ]);
  const unexpected = Object.keys(snapshot).filter((path) => !expectedPaths.has(path));
  const obsolete = existingManifest
    ? Object.keys(existingManifest.files).filter((path) => !(path in desiredManifest.files))
    : [];
  return {
    targetRoot,
    manifestPath,
    existingManifest,
    desiredManifest,
    sourceFiles,
    drift,
    desiredDrift,
    unexpected,
    obsolete,
    snapshot,
  };
}

export async function inspectInstalledRuntime(gitRoot) {
  const targetRoot = orchestrationRoot(gitRoot);
  await assertNoSymlinkComponents(gitRoot, targetRoot, "Managed runtime root");
  const manifestPath = resolve(targetRoot, "version.json");
  const raw = await readJson(manifestPath, { allowMissing: true, guardRoot: gitRoot });
  if (!raw) return { installed: false, targetRoot, manifestPath, manifest: null, drift: [] };
  const manifest = validateManifest(raw);
  const drift = await driftAgainstManifest(targetRoot, manifest, gitRoot);
  const snapshot = await targetSnapshot(gitRoot, targetRoot);
  const allowed = new Set([...Object.keys(manifest.files), "project.json", "version.json"]);
  const unexpected = Object.keys(snapshot).filter((path) => !allowed.has(path));
  return { installed: true, targetRoot, manifestPath, manifest, drift, unexpected };
}

async function syncManagedUnlocked({ gitRoot, packageRoot, check = false, force = false }) {
  const inspection = await inspectManaged({ gitRoot, packageRoot });
  if (
    inspection.existingManifest
    && inspection.existingManifest.package_version !== PACKAGE_VERSION
  ) {
    throw new CliError(
      `Installed Codex Flow ${inspection.existingManifest.package_version} requires explicit retirement before fresh ${PACKAGE_VERSION} installation`,
    );
  }
  if (inspection.drift.length > 0 && !force) {
    const paths = inspection.drift.map((item) => `${item.path} (${item.state})`).join(", ");
    throw new CliError(`Managed runtime has local drift; refusing to overwrite: ${paths}`);
  }
  if (inspection.unexpected.length > 0) {
    throw new CliError(`Orchestration directory contains files not owned by codex-flow: ${inspection.unexpected.join(", ")}`);
  }
  if (check) {
    if (!inspection.existingManifest) throw new CliError("Pinned codex-flow runtime is not installed");
    if (stableStringify(inspection.existingManifest) !== stableStringify(inspection.desiredManifest)) {
      throw new CliError("Pinned codex-flow runtime is not at the current package version");
    }
    if (inspection.desiredDrift.length > 0) throw new CliError("Pinned codex-flow runtime files do not match their source package");
    if (inspection.obsolete.length > 0) throw new CliError("Pinned codex-flow runtime contains obsolete managed files");
    return { changed: false, ...inspection };
  }
  const changed = !inspection.existingManifest
    || stableStringify(inspection.existingManifest) !== stableStringify(inspection.desiredManifest)
    || inspection.desiredDrift.length > 0
    || inspection.obsolete.length > 0;
  if (!changed) return { changed: false, ...inspection };

  const parent = dirname(inspection.targetRoot);
  await ensureDirectory(parent, { guardRoot: gitRoot });
  const nonce = randomUUID();
  const staging = resolve(parent, `.orchestration-stage-${nonce}`);
  const backup = resolve(parent, `.orchestration-backup-${nonce}`);
  await ensureDirectory(staging, { guardRoot: gitRoot });
  try {
    for (const file of inspection.sourceFiles) {
      await atomicWrite(resolve(staging, file.relativePath), file.contents, { guardRoot: gitRoot });
    }
    await atomicWriteJson(resolve(staging, "version.json"), inspection.desiredManifest, { guardRoot: gitRoot });
    const projectPath = projectConfigPath(gitRoot);
    if (await pathExists(projectPath)) {
      await assertNoSymlinkComponents(gitRoot, projectPath, "Project configuration path");
      await atomicWrite(resolve(staging, "project.json"), await readFile(projectPath), { guardRoot: gitRoot });
    }

    const beforeActivation = await targetSnapshot(gitRoot, inspection.targetRoot);
    if (stableStringify(beforeActivation) !== stableStringify(inspection.snapshot)) {
      throw new CliError("Managed runtime changed during sync; refusing to overwrite concurrent edits", 75);
    }

    let movedCurrent = false;
    try {
      if (await pathExists(inspection.targetRoot)) {
        await rename(inspection.targetRoot, backup);
        movedCurrent = true;
      }
      await rename(staging, inspection.targetRoot);
      if (movedCurrent) await rm(backup, { recursive: true, force: true });
    } catch (error) {
      if (movedCurrent && !await pathExists(inspection.targetRoot) && await pathExists(backup)) {
        await rename(backup, inspection.targetRoot);
      }
      throw error;
    }
  } finally {
    await rm(staging, { recursive: true, force: true });
  }
  return { changed: true, ...inspection };
}

function requireManagementState(options) {
  if (!options.stateRoot || !options.stateGuardRoot) {
    throw new CliError("Managed repository operations require Git common-directory state");
  }
}

export async function withRepositoryManagementLock(options, operation) {
  requireManagementState(options);
  return withProcessLock({
    path: resolve(options.stateRoot, "locks", "managed-runtime.lock"),
    guardRoot: options.stateGuardRoot,
    label: "codex-flow repository management",
  }, operation);
}

export async function syncManaged(options) {
  if (options.check) return syncManagedUnlocked(options);
  return withRepositoryManagementLock(options, () => syncManagedUnlocked(options));
}

export async function inspectAgentsBlock({ gitRoot, packageRoot }) {
  const agentsPath = resolve(gitRoot, "AGENTS.md");
  await assertNoSymlinkComponents(gitRoot, agentsPath, "AGENTS.md path");
  const block = await readFile(resolve(packageRoot, "templates", "agents-block.md"), "utf8");
  const existing = await readFile(agentsPath, "utf8").catch((error) => {
    if (error?.code === "ENOENT") return "";
    throw error;
  });
  const desired = replaceManagedAgentsBlock(existing, block);
  return { agentsPath, existing, desired };
}

export async function inspectExternalAgents({ gitRoot, integration }) {
  const path = resolve(gitRoot, integration.path);
  await assertNoSymlinkComponents(gitRoot, path, "External AGENTS instruction path");
  const contents = await readFile(path, "utf8").catch((error) => {
    if (error?.code === "ENOENT") {
      throw new CliError(`External AGENTS instruction file is missing: ${integration.path}`);
    }
    throw error;
  });
  if (contents.trim() === "") throw new CliError("External AGENTS instruction file is empty");
  const range = managedMarkerRange(contents);
  if (range) throw new CliError("External AGENTS instruction file still contains a codex-flow managed block");
  const hash = sha256(contents);
  if (hash !== integration.sha256) {
    throw new CliError("External AGENTS instruction attestation has drifted; explicit re-attestation is required");
  }
  return { path, contents, hash };
}

export async function ensureAgentsBlock({ gitRoot, packageRoot, check = false }) {
  const { agentsPath, existing, desired } = await inspectAgentsBlock({ gitRoot, packageRoot });
  if (desired === existing) return { path: agentsPath, changed: false };
  if (check) throw new CliError("AGENTS.md codex-flow managed block is missing or outdated");
  const current = await readFile(agentsPath, "utf8").catch((error) => {
    if (error?.code === "ENOENT") return "";
    throw error;
  });
  if (current !== existing) throw new CliError("AGENTS.md changed during sync; refusing to overwrite concurrent edits", 75);
  await atomicWrite(agentsPath, desired, { guardRoot: gitRoot });
  return { path: agentsPath, changed: true };
}

export async function synchronizeRepository(options) {
  const rawConfig = await readJson(projectConfigPath(options.gitRoot), {
    allowMissing: true,
    guardRoot: options.gitRoot,
  });
  if (!rawConfig) throw new CliError("Project orchestration configuration is missing");
  if (rawConfig.schema_version !== 4) {
    throw new CliError("codex-flow v0.5 requires a fresh schema 4 initialization; older orchestration state is not migrated");
  }
  const config = validateProjectConfig(rawConfig);
  if (options.check) {
    if (config.agents_integration.mode === "external") {
      await inspectExternalAgents({ gitRoot: options.gitRoot, integration: config.agents_integration });
    }
    const runtime = await syncManagedUnlocked(options);
    const agents = config.agents_integration.mode === "managed"
      ? await ensureAgentsBlock(options)
      : { changed: false };
    return { changed: runtime.changed || agents.changed };
  }
  return withRepositoryManagementLock(options, async () => {
    if (config.agents_integration.mode === "managed") await inspectAgentsBlock(options);
    else await inspectExternalAgents({ gitRoot: options.gitRoot, integration: config.agents_integration });
    const runtime = await syncManagedUnlocked(options);
    const agents = config.agents_integration.mode === "managed"
      ? await ensureAgentsBlock(options)
      : { changed: false };
    return { changed: runtime.changed || agents.changed };
  });
}
