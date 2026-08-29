import { randomUUID } from "node:crypto";
import { readdir } from "node:fs/promises";
import { basename, dirname, resolve } from "node:path";
import {
  assertNoSymlinkComponents,
  atomicWriteJson,
  CliError,
  readJson,
  requireExactFields,
  requireInteger,
  requireText,
  withProcessLock,
} from "./core.mjs";
import { gitCommonDirectoryForState } from "./git.mjs";

const BINDING_KIND = "terminal-recipient-registry";
const EXPLICIT_TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/;

function validTimestamp(value) {
  return EXPLICIT_TIMESTAMP_PATTERN.test(value) && Number.isFinite(Date.parse(value));
}

function guardRoot(stateRoot) {
  return gitCommonDirectoryForState(stateRoot);
}

function safeChild(directory, filename) {
  const path = resolve(directory, filename);
  if (dirname(path) !== directory || basename(path) !== filename) {
    throw new CliError("Unsafe recipient registry path");
  }
  return path;
}

function recipientInput(value, label = "recipient") {
  requireExactFields(value, {
    required: ["lineage_id", "thread_id", "generation"],
  }, label);
  return {
    lineage_id: requireText(value.lineage_id, `${label}.lineage_id`, { max: 128, safeId: true }),
    thread_id: requireText(value.thread_id, `${label}.thread_id`, { max: 128, safeId: true }),
    generation: requireInteger(value.generation, `${label}.generation`, { min: 1 }),
  };
}

function bindingArguments({ recipient = null, lineageId, threadId, generation }) {
  if (recipient !== null) return recipientInput(recipient);
  return recipientInput({
    lineage_id: lineageId,
    thread_id: threadId,
    generation,
  }, "recipient binding");
}

function suppliedFenceToken({ fenceToken = undefined, fence_token = undefined, token = undefined }, required) {
  const values = [fenceToken, fence_token, token].filter((value) => value !== undefined && value !== null);
  if (values.length > 1 && new Set(values).size !== 1) {
    throw new CliError("Recipient fence token was supplied more than once with different values");
  }
  if (values.length === 0) {
    if (required) throw new CliError("Recipient rebind requires the current fence token", 73);
    return null;
  }
  return requireText(values[0], "fence_token", { max: 128, safeId: true });
}

function validateRegistry(value) {
  requireExactFields(value, {
    required: ["schema_version", "kind", "lineage_id", "current", "bindings"],
  }, "Recipient registry");
  if (value.schema_version !== 2 || value.kind !== BINDING_KIND) {
    throw new CliError("Invalid recipient registry schema");
  }
  const lineageId = requireText(value.lineage_id, "Recipient registry lineage_id", { max: 128, safeId: true });
  requireExactFields(value.current, {
    required: ["thread_id", "generation", "fence_token", "bound_at"],
  }, "Recipient registry current binding");
  const current = {
    thread_id: requireText(value.current.thread_id, "Recipient registry current thread_id", { max: 128, safeId: true }),
    generation: requireInteger(value.current.generation, "Recipient registry current generation", { min: 1 }),
    fence_token: requireText(value.current.fence_token, "Recipient registry current fence_token", { max: 128, safeId: true }),
    bound_at: requireText(value.current.bound_at, "Recipient registry current bound_at", { max: 64 }),
  };
  if (!validTimestamp(current.bound_at)) throw new CliError("Recipient registry current bound_at is invalid");
  if (!Array.isArray(value.bindings) || value.bindings.length === 0 || value.bindings.length > 256) {
    throw new CliError("Recipient registry bindings must contain 1 to 256 entries");
  }
  const bindings = value.bindings.map((binding, index) => {
    requireExactFields(binding, {
      required: ["thread_id", "generation", "bound_at"],
    }, `Recipient registry bindings[${index}]`);
    const normalized = {
      thread_id: requireText(binding.thread_id, `Recipient registry bindings[${index}].thread_id`, { max: 128, safeId: true }),
      generation: requireInteger(binding.generation, `Recipient registry bindings[${index}].generation`, { min: 1 }),
      bound_at: requireText(binding.bound_at, `Recipient registry bindings[${index}].bound_at`, { max: 64 }),
    };
    if (!validTimestamp(normalized.bound_at)) {
      throw new CliError(`Recipient registry bindings[${index}].bound_at is invalid`);
    }
    return normalized;
  });
  for (let index = 1; index < bindings.length; index += 1) {
    if (bindings[index].generation !== bindings[index - 1].generation + 1) {
      throw new CliError("Recipient registry generations must advance one at a time");
    }
  }
  const latest = bindings.at(-1);
  if (bindings[0].generation !== 1) {
    throw new CliError("Recipient registry binding history must start at generation 1");
  }
  if (latest.thread_id !== current.thread_id || latest.generation !== current.generation) {
    throw new CliError("Recipient registry current binding does not match its binding history");
  }
  return {
    schema_version: 2,
    kind: BINDING_KIND,
    lineage_id: lineageId,
    current,
    bindings,
  };
}

function registryPaths(stateRoot, lineageId) {
  requireText(lineageId, "lineage_id", { max: 128, safeId: true });
  const root = resolve(stateRoot, "recipients");
  const bindings = resolve(root, "bindings");
  const locks = resolve(root, "locks");
  return {
    root,
    registry: safeChild(bindings, `${lineageId}.json`),
    lock: safeChild(locks, `${lineageId}.lock.json`),
  };
}

export function recipientPaths(stateRoot, lineageId) {
  return registryPaths(stateRoot, lineageId);
}

function publicBinding(registry) {
  return {
    lineage_id: registry.lineage_id,
    thread_id: registry.current.thread_id,
    generation: registry.current.generation,
    fence_token: registry.current.fence_token,
  };
}

function deliveryRecipient(registry) {
  return {
    lineage_id: registry.lineage_id,
    thread_id: registry.current.thread_id,
    generation: registry.current.generation,
  };
}

function statusView(registry) {
  return {
    lineage_id: registry.lineage_id,
    current: {
      thread_id: registry.current.thread_id,
      generation: registry.current.generation,
      bound_at: registry.current.bound_at,
    },
    binding_count: registry.bindings.length,
    bindings: registry.bindings.map((binding) => ({ ...binding })),
  };
}

async function readRegistry(paths, stateRoot) {
  const stored = await readJson(paths.registry, {
    allowMissing: true,
    guardRoot: guardRoot(stateRoot),
  });
  return stored ? validateRegistry(stored) : null;
}

export async function bindRecipient({
  stateRoot,
  recipient = null,
  lineageId,
  threadId,
  generation = 1,
  fenceToken,
  fence_token,
  token,
}) {
  const binding = bindingArguments({ recipient, lineageId, threadId, generation });
  if (binding.generation !== 1) throw new CliError("Initial recipient binding must use generation 1");
  const requestedToken = suppliedFenceToken({ fenceToken, fence_token, token }, false);
  const paths = registryPaths(stateRoot, binding.lineage_id);
  const root = guardRoot(stateRoot);
  return withProcessLock({
    path: paths.lock,
    guardRoot: root,
    label: `recipient binding ${binding.lineage_id}`,
  }, async () => {
    const existing = await readRegistry(paths, stateRoot);
    if (existing) {
      const current = publicBinding(existing);
      if (current.thread_id !== binding.thread_id || current.generation !== binding.generation) {
        throw new CliError(`Recipient lineage ${binding.lineage_id} is already bound at generation ${current.generation}`, 73);
      }
      if (requestedToken !== null && requestedToken !== current.fence_token) {
        throw new CliError("Recipient initial binding fence token does not match", 73);
      }
      return {
        status: "already-bound",
        recipient: requestedToken === null ? deliveryRecipient(existing) : current,
      };
    }
    const now = new Date().toISOString();
    const registry = {
      schema_version: 2,
      kind: BINDING_KIND,
      lineage_id: binding.lineage_id,
      current: {
        thread_id: binding.thread_id,
        generation: binding.generation,
        fence_token: requestedToken ?? randomUUID(),
        bound_at: now,
      },
      bindings: [{
        thread_id: binding.thread_id,
        generation: binding.generation,
        bound_at: now,
      }],
    };
    await atomicWriteJson(paths.registry, registry, { guardRoot: root, mode: 0o600 });
    return { status: "bound", recipient: publicBinding(registry) };
  });
}

export const initialBindRecipient = bindRecipient;

export async function rebindRecipient({
  stateRoot,
  recipient = null,
  lineageId,
  threadId,
  generation,
  fenceToken,
  fence_token,
  token,
  nextFenceToken,
}) {
  const binding = bindingArguments({ recipient, lineageId, threadId, generation });
  const currentToken = suppliedFenceToken({ fenceToken, fence_token, token }, true);
  const nextToken = nextFenceToken === undefined || nextFenceToken === null
    ? randomUUID()
    : requireText(nextFenceToken, "next_fence_token", { max: 128, safeId: true });
  const paths = registryPaths(stateRoot, binding.lineage_id);
  const root = guardRoot(stateRoot);
  return withProcessLock({
    path: paths.lock,
    guardRoot: root,
    label: `recipient binding ${binding.lineage_id}`,
  }, async () => {
    const existing = await readRegistry(paths, stateRoot);
    if (!existing) throw new CliError(`Recipient lineage ${binding.lineage_id} has no initial binding`, 73);
    if (
      binding.thread_id === existing.current.thread_id
      && binding.generation === existing.current.generation
      && nextToken === existing.current.fence_token
    ) {
      return { status: "already-rebound", recipient: publicBinding(existing) };
    }
    if (existing.current.fence_token !== currentToken) {
      throw new CliError("Recipient rebind fence token does not match the authoritative binding", 73);
    }
    if (binding.generation !== existing.current.generation + 1) {
      throw new CliError(`Recipient rebind must advance generation ${existing.current.generation} to ${existing.current.generation + 1}`, 73);
    }
    if (binding.thread_id === existing.current.thread_id) {
      throw new CliError("Recipient rebind must name a different thread", 73);
    }
    if (nextToken === currentToken) throw new CliError("Recipient rebind must rotate its fence token", 73);
    const now = new Date().toISOString();
    const registry = {
      ...existing,
      current: {
        thread_id: binding.thread_id,
        generation: binding.generation,
        fence_token: nextToken,
        bound_at: now,
      },
      bindings: [...existing.bindings, {
        thread_id: binding.thread_id,
        generation: binding.generation,
        bound_at: now,
      }],
    };
    await atomicWriteJson(paths.registry, registry, { guardRoot: root, mode: 0o600 });
    return { status: "rebound", recipient: publicBinding(registry) };
  });
}

export async function currentRecipient({ stateRoot, lineageId }) {
  const paths = registryPaths(stateRoot, lineageId);
  const registry = await readRegistry(paths, stateRoot);
  if (!registry) throw new CliError(`Recipient lineage ${lineageId} has no authoritative binding`, 73);
  return deliveryRecipient(registry);
}

export async function recipientStatus({ stateRoot, lineageId }) {
  const paths = registryPaths(stateRoot, lineageId);
  const registry = await readRegistry(paths, stateRoot);
  if (!registry) return null;
  return statusView(registry);
}

export async function recipientStatuses({ stateRoot }) {
  const bindingsRoot = resolve(stateRoot, "recipients", "bindings");
  const trustedRoot = guardRoot(stateRoot);
  await assertNoSymlinkComponents(trustedRoot, bindingsRoot, "Recipient registry path");
  let entries;
  try {
    entries = await readdir(bindingsRoot, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
  const result = [];
  for (const entry of entries) {
    const path = resolve(bindingsRoot, entry.name);
    if (entry.isSymbolicLink()) throw new CliError(`Recipient registry contains a symbolic link: ${path}`);
    if (!entry.isFile() || !entry.name.endsWith(".json")) continue;
    const stored = await readJson(path, { guardRoot: trustedRoot });
    result.push(statusView(validateRegistry(stored)));
  }
  return result.sort((left, right) => left.lineage_id.localeCompare(right.lineage_id));
}

export async function resolveRecipient({ stateRoot, recipient }) {
  const requested = recipientInput(recipient);
  const paths = registryPaths(stateRoot, requested.lineage_id);
  const registry = await readRegistry(paths, stateRoot);
  if (!registry) throw new CliError(`Recipient lineage ${requested.lineage_id} has no authoritative binding`, 73);
  return resolveFromRegistry(registry, requested);
}

function resolveFromRegistry(registry, requested) {
  const known = registry.bindings.find((binding) => binding.generation === requested.generation);
  if (!known || known.thread_id !== requested.thread_id) {
    throw new CliError("Recipient packet does not match an authoritative lineage binding", 73);
  }
  if (requested.generation > registry.current.generation) {
    throw new CliError("Recipient packet generation is newer than the authoritative binding", 73);
  }
  return {
    recipient: deliveryRecipient(registry),
    stale: requested.generation < registry.current.generation,
  };
}

export async function withRecipientBindingLock({ stateRoot, recipient }, operation) {
  const requested = recipientInput(recipient);
  const paths = registryPaths(stateRoot, requested.lineage_id);
  return withProcessLock({
    path: paths.lock,
    guardRoot: guardRoot(stateRoot),
    label: `recipient binding ${requested.lineage_id}`,
  }, async () => {
    const registry = await readRegistry(paths, stateRoot);
    if (!registry) throw new CliError(`Recipient lineage ${requested.lineage_id} has no authoritative binding`, 73);
    return operation(resolveFromRegistry(registry, requested));
  });
}
