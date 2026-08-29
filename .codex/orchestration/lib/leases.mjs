import { randomUUID } from "node:crypto";
import { readdir, rename, rm } from "node:fs/promises";
import { basename, dirname, resolve } from "node:path";
import {
  assertNoSymlinkComponents,
  CliError,
  atomicWriteJson,
  ensureDirectory,
  pathExists,
  readJson,
  requireInteger,
  requireText,
  withProcessLock,
} from "./core.mjs";
import { gitCommonDirectoryForState } from "./git.mjs";

function leaseRoot(stateRoot) {
  return resolve(stateRoot, "leases");
}

function leaseDirectory(stateRoot, resource) {
  requireText(resource, "resource", { max: 128, safeId: true });
  const root = leaseRoot(stateRoot);
  const path = resolve(root, resource);
  if (dirname(path) !== root || basename(path) !== resource) throw new CliError("Unsafe lease resource path");
  return path;
}

function leaseGuardRoot(stateRoot) {
  return gitCommonDirectoryForState(stateRoot);
}

async function readLeaseFromDirectory(directory, guardRoot) {
  const payload = await readJson(resolve(directory, "lease.json"), {
    allowMissing: true,
    guardRoot,
  });
  if (!payload) return null;
  if (
    payload.schema_version !== 1 || payload.kind !== "codex-flow-lease"
    || typeof payload.resource !== "string" || typeof payload.owner !== "string"
    || typeof payload.token !== "string" || typeof payload.acquired_at !== "string"
    || typeof payload.expires_at !== "string"
  ) throw new CliError(`Invalid lease state: ${directory}`);
  return payload;
}

function leaseState(payload) {
  const expiresMs = Date.parse(payload.expires_at);
  return Number.isFinite(expiresMs) && expiresMs <= Date.now() ? "expired" : "active";
}

function leaseView(payload, { includeToken = false } = {}) {
  const { token, ...publicPayload } = payload;
  return {
    ...publicPayload,
    ...(includeToken ? { token } : {}),
    state: leaseState(payload),
  };
}

function leaseOperationLock(stateRoot, resource) {
  return resolve(leaseRoot(stateRoot), ".operations", `${resource}.lock.json`);
}

export async function acquireLease({ stateRoot, resource, owner, ttlSeconds = 7200, breakExpired = false }) {
  leaseDirectory(stateRoot, resource);
  requireText(owner, "owner", { max: 128, safeId: true });
  requireInteger(ttlSeconds, "ttl_seconds", { min: 30, max: 7 * 24 * 60 * 60 });
  const guardRoot = leaseGuardRoot(stateRoot);
  return withProcessLock({
    path: leaseOperationLock(stateRoot, resource),
    guardRoot,
    label: `lease operation for ${resource}`,
  }, async () => {
    const directory = leaseDirectory(stateRoot, resource);
    await assertNoSymlinkComponents(guardRoot, directory, "Lease path");
    if (await pathExists(directory)) {
      const existing = await readLeaseFromDirectory(directory, guardRoot);
      if (existing?.owner === owner && leaseState(existing) === "active") {
        return { status: "already-owned", lease: leaseView(existing, { includeToken: true }) };
      }
      if (!existing) throw new CliError(`Lease ${resource} exists without readable state; manual audit required`, 73);
      if (leaseState(existing) !== "expired" || !breakExpired) {
        throw new CliError(`Lease ${resource} is ${leaseState(existing)} and owned by ${existing.owner}`, 73);
      }
      const stale = `${directory}.stale-${randomUUID()}`;
      await rename(directory, stale);
      await rm(stale, { recursive: true, force: true });
    }

    await ensureDirectory(directory, { guardRoot });
    const now = new Date();
    const payload = {
      schema_version: 1,
      kind: "codex-flow-lease",
      resource,
      owner,
      token: randomUUID(),
      acquired_at: now.toISOString(),
      expires_at: new Date(now.getTime() + ttlSeconds * 1000).toISOString(),
    };
    try {
      await atomicWriteJson(resolve(directory, "lease.json"), payload, {
        exclusive: true,
        mode: 0o600,
        guardRoot,
      });
    } catch (error) {
      await rm(directory, { recursive: true, force: true });
      throw error;
    }
    return { status: "acquired", lease: leaseView(payload, { includeToken: true }) };
  });
}

export async function releaseLease({ stateRoot, resource, owner, token = null }) {
  leaseDirectory(stateRoot, resource);
  requireText(owner, "owner", { max: 128, safeId: true });
  if (token !== null) requireText(token, "token", { max: 128, safeId: true });
  const guardRoot = leaseGuardRoot(stateRoot);
  return withProcessLock({
    path: leaseOperationLock(stateRoot, resource),
    guardRoot,
    label: `lease operation for ${resource}`,
  }, async () => {
    const directory = leaseDirectory(stateRoot, resource);
    const existing = await readLeaseFromDirectory(directory, guardRoot);
    if (!existing) return { status: "absent", resource };
    if (existing.owner !== owner) throw new CliError(`Lease ${resource} belongs to ${existing.owner}`, 73);
    if (token === null) throw new CliError(`Lease ${resource} requires its acquisition token for release`, 73);
    if (existing.token !== token) throw new CliError(`Lease ${resource} token does not match`, 73);
    const releasing = `${directory}.releasing-${randomUUID()}`;
    await rename(directory, releasing);
    await rm(releasing, { recursive: true, force: true });
    return { status: "released", resource };
  });
}

export async function leaseStatus({ stateRoot, resource = null }) {
  const guardRoot = leaseGuardRoot(stateRoot);
  if (resource) {
    const payload = await readLeaseFromDirectory(leaseDirectory(stateRoot, resource), guardRoot);
    return payload ? [leaseView(payload)] : [];
  }
  const root = leaseRoot(stateRoot);
  await assertNoSymlinkComponents(guardRoot, root, "Lease state path");
  let entries;
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
  const result = [];
  for (const entry of entries) {
    if (entry.isSymbolicLink()) throw new CliError(`Lease state contains a symbolic link: ${resolve(root, entry.name)}`);
    if (!entry.isDirectory() || entry.name.includes(".stale-") || entry.name.includes(".releasing-")) continue;
    if (entry.name === ".operations") continue;
    const payload = await readLeaseFromDirectory(resolve(root, entry.name), guardRoot);
    if (payload) result.push(leaseView(payload));
  }
  return result.sort((a, b) => a.resource.localeCompare(b.resource));
}
