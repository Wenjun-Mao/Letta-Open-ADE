import { createHash, randomUUID } from "node:crypto";
import {
  lstat,
  mkdir,
  open,
  readFile,
  realpath,
  rename,
  rm,
  stat,
} from "node:fs/promises";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { hostname } from "node:os";

export const PACKAGE_VERSION = "0.5.1";
export const SAFE_ID = /^[A-Za-z0-9_.-]+$/;

export class CliError extends Error {
  constructor(message, exitCode = 1) {
    super(message);
    this.name = "CliError";
    this.exitCode = exitCode;
  }
}

export function isPlainObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function requireObject(value, label) {
  if (!isPlainObject(value)) throw new CliError(`${label} must be an object`);
  return value;
}

export function requireExactFields(value, { required, optional = [] }, label) {
  requireObject(value, label);
  const allowed = new Set([...required, ...optional]);
  for (const key of Object.keys(value)) {
    if (!allowed.has(key)) throw new CliError(`${label} field is not allowed: ${key}`);
  }
  for (const key of required) {
    if (!(key in value)) throw new CliError(`${label} requires field: ${key}`);
  }
}

export function requireText(value, label, { max = 512, safeId = false } = {}) {
  if (typeof value !== "string" || value.trim() === "" || value.length > max) {
    throw new CliError(`${label} must be nonempty text no longer than ${max} characters`);
  }
  if (safeId && !SAFE_ID.test(value)) throw new CliError(`${label} must be a safe identifier`);
  return value;
}

export function requireNullableText(value, label, { max = 256 } = {}) {
  if (value === null) return null;
  return requireText(value, label, { max });
}

export function requireStringArray(value, label, {
  maxItems = 128,
  maxText = 512,
  safeIds = false,
  allowEmpty = true,
} = {}) {
  if (!Array.isArray(value) || value.length > maxItems || (!allowEmpty && value.length === 0)) {
    throw new CliError(`${label} must be an array with at most ${maxItems} entries`);
  }
  const result = value.map((entry, index) => requireText(entry, `${label}[${index}]`, {
    max: maxText,
    safeId: safeIds,
  }));
  if (new Set(result).size !== result.length) throw new CliError(`${label} contains duplicates`);
  return result;
}

export function requireInteger(value, label, { min = 0, max = Number.MAX_SAFE_INTEGER } = {}) {
  if (!Number.isInteger(value) || value < min || value > max) {
    throw new CliError(`${label} must be an integer from ${min} to ${max}`);
  }
  return value;
}

export function requireEnum(value, allowed, label) {
  if (!allowed.includes(value)) {
    throw new CliError(`${label} must be one of: ${allowed.map(String).join(", ")}`);
  }
  return value;
}

export function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (!isPlainObject(value)) return value;
  return Object.fromEntries(
    Object.keys(value).sort().map((key) => [key, canonicalize(value[key])]),
  );
}

export function stableStringify(value, spacing = 0) {
  return JSON.stringify(canonicalize(value), null, spacing);
}

export function sha256(value) {
  const bytes = Buffer.isBuffer(value) ? value : Buffer.from(String(value));
  return createHash("sha256").update(bytes).digest("hex");
}

export async function sha256File(path) {
  return sha256(await readFile(path));
}

export async function pathExists(path) {
  try {
    await stat(path);
    return true;
  } catch (error) {
    if (error?.code === "ENOENT") return false;
    throw error;
  }
}

function isContained(root, target) {
  const child = relative(root, target);
  return child === "" || (!child.startsWith(`..${sep}`) && child !== ".." && !isAbsolute(child));
}

export async function assertNoSymlinkComponents(root, target, label = "Path") {
  const lexicalRoot = resolve(root);
  const lexicalTarget = resolve(target);
  if (!isContained(lexicalRoot, lexicalTarget)) {
    throw new CliError(`${label} escapes its trusted root`);
  }
  const rootInfo = await lstat(lexicalRoot).catch((error) => {
    if (error?.code === "ENOENT") throw new CliError(`${label} trusted root does not exist`);
    throw error;
  });
  if (!rootInfo.isDirectory()) throw new CliError(`${label} trusted root is not a directory`);

  const rootReal = await realpath(lexicalRoot);
  let cursor = lexicalRoot;
  const parts = relative(lexicalRoot, lexicalTarget).split(sep).filter(Boolean);
  for (let index = 0; index < parts.length; index += 1) {
    cursor = join(cursor, parts[index]);
    let info;
    try {
      info = await lstat(cursor);
    } catch (error) {
      if (error?.code === "ENOENT") break;
      throw error;
    }
    if (info.isSymbolicLink()) throw new CliError(`${label} contains a symbolic link: ${cursor}`);
    if (index < parts.length - 1 && !info.isDirectory()) {
      throw new CliError(`${label} has a non-directory ancestor: ${cursor}`);
    }
    const actual = await realpath(cursor);
    if (!isContained(rootReal, actual)) throw new CliError(`${label} resolves outside its trusted root`);
  }
  return lexicalTarget;
}

export async function ensureDirectory(path, { guardRoot = null, mode } = {}) {
  const target = resolve(path);
  if (!guardRoot) {
    await mkdir(target, { recursive: true, mode });
    return target;
  }
  const root = resolve(guardRoot);
  await assertNoSymlinkComponents(root, target, "Directory path");
  let cursor = root;
  for (const part of relative(root, target).split(sep).filter(Boolean)) {
    cursor = join(cursor, part);
    try {
      await mkdir(cursor, { mode });
    } catch (error) {
      if (error?.code !== "EEXIST") throw error;
    }
    const info = await lstat(cursor);
    if (info.isSymbolicLink() || !info.isDirectory()) {
      throw new CliError(`Directory path is not a real directory: ${cursor}`);
    }
  }
  await assertNoSymlinkComponents(root, target, "Directory path");
  return target;
}

export async function readJson(path, { allowMissing = false, guardRoot = null } = {}) {
  try {
    if (guardRoot) await assertNoSymlinkComponents(guardRoot, path, "JSON path");
    const raw = await readFile(path, "utf8");
    return JSON.parse(raw);
  } catch (error) {
    if (allowMissing && error?.code === "ENOENT") return null;
    if (error instanceof SyntaxError) throw new CliError(`Invalid JSON: ${path}`);
    throw error;
  }
}

export async function readJsonInput(path) {
  if (path) return readJson(path);
  let raw = "";
  for await (const chunk of process.stdin) raw += chunk;
  if (raw.trim() === "") throw new CliError("Expected JSON on stdin or --file <path>");
  try {
    return JSON.parse(raw);
  } catch {
    throw new CliError("Standard input is not valid JSON");
  }
}

export async function atomicWrite(path, contents, {
  exclusive = false,
  mode,
  guardRoot = null,
} = {}) {
  await ensureDirectory(dirname(path), { guardRoot });
  if (guardRoot) await assertNoSymlinkComponents(guardRoot, path, "Write path");
  if (exclusive) {
    const handle = await open(path, "wx", mode);
    try {
      await handle.writeFile(contents, "utf8");
      await handle.sync();
    } finally {
      await handle.close();
    }
    return;
  }
  const temporary = `${path}.${process.pid}.${randomUUID()}.tmp`;
  try {
    const handle = await open(temporary, "wx", mode);
    try {
      await handle.writeFile(contents, "utf8");
      await handle.sync();
    } finally {
      await handle.close();
    }
    await rename(temporary, path);
  } finally {
    await rm(temporary, { force: true }).catch(() => {});
  }
}

export async function atomicWriteJson(path, value, options = {}) {
  return atomicWrite(path, `${stableStringify(value, 2)}\n`, options);
}

export async function ensureExactJson(path, value, options = {}) {
  try {
    await atomicWriteJson(path, value, { ...options, exclusive: true });
    return "created";
  } catch (error) {
    if (error?.code !== "EEXIST") throw error;
  }
  const existing = await readJson(path, { guardRoot: options.guardRoot ?? null });
  if (stableStringify(existing) !== stableStringify(value)) {
    throw new CliError(`Existing state does not match: ${path}`);
  }
  return "existing";
}

export async function directorySize(path) {
  const { readdir } = await import("node:fs/promises");
  let total = 0;
  let entries;
  try {
    entries = await readdir(path, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return 0;
    throw error;
  }
  for (const entry of entries) {
    const child = join(path, entry.name);
    if (entry.isDirectory()) total += await directorySize(child);
    else if (entry.isFile()) total += (await stat(child)).size;
  }
  return total;
}

function processIsAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error?.code === "EPERM";
  }
}

export async function withProcessLock({ path, guardRoot, label }, operation) {
  const lockPath = resolve(path);
  const lock = {
    schema_version: 1,
    kind: "codex-flow-process-lock",
    host: hostname(),
    pid: process.pid,
    token: randomUUID(),
    started_at: new Date().toISOString(),
  };
  await ensureDirectory(dirname(lockPath), { guardRoot });
  try {
    await atomicWriteJson(lockPath, lock, {
      exclusive: true,
      mode: 0o600,
      guardRoot,
    });
  } catch (error) {
    if (error?.code !== "EEXIST") throw error;
    const existing = await readJson(lockPath, { guardRoot }).catch(() => null);
    if (
      existing?.kind === "codex-flow-process-lock"
      && existing.host === hostname()
      && Number.isInteger(existing.pid)
      && !processIsAlive(existing.pid)
    ) {
      const stale = `${lockPath}.stale-${randomUUID()}`;
      await rename(lockPath, stale).catch((renameError) => {
        if (renameError?.code !== "ENOENT") throw renameError;
      });
      await rm(stale, { force: true });
      return withProcessLock({ path: lockPath, guardRoot, label }, operation);
    }
    throw new CliError(`${label} is already in progress; retry after its owner finishes`, 75);
  }

  try {
    return await operation(lock);
  } finally {
    const current = await readJson(lockPath, { allowMissing: true, guardRoot }).catch(() => null);
    if (current?.token === lock.token) await rm(lockPath, { force: true });
  }
}

export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KiB", "MiB", "GiB", "TiB"];
  let value = bytes;
  let unit = "B";
  for (const candidate of units) {
    value /= 1024;
    unit = candidate;
    if (value < 1024) break;
  }
  return `${value.toFixed(value >= 10 ? 1 : 2)} ${unit}`;
}
