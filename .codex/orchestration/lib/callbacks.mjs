import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { readdir, stat } from "node:fs/promises";
import { basename, dirname, resolve } from "node:path";
import {
  assertNoSymlinkComponents,
  atomicWriteJson,
  CliError,
  readJson,
  requireExactFields,
  requireInteger,
  requireStringArray,
  requireText,
  sha256,
  stableStringify,
  withProcessLock,
} from "./core.mjs";
import { assertSafeContent } from "./content-safety.mjs";
import { gitCommonDirectoryForState } from "./git.mjs";
import { resolveRecipient, withRecipientBindingLock } from "./recipients.mjs";

export const ACCOUNTING_FIELDS = [
  "PRODUCT",
  "CROSS_CUTTING_PRODUCT_FIX",
  "ENVIRONMENT",
  "PROOF_HARNESS",
];

const RECEIPT_FIELDS = [
  "schema_version",
  "recipient",
  "executor_id",
  "run_id",
  "source_revision",
  "sequence",
  "supersedes_callback_ids",
  "expires_at",
  "classification",
  "branch",
  "commit",
  "upstream",
  "cleanliness",
  "result_or_blocker",
  "next_decision",
  "accounting",
];
const TEXT_LIMITS = {
  source_revision: 128,
  classification: 96,
  branch: 256,
  commit: 128,
  upstream: 256,
  cleanliness: 32,
  result_or_blocker: 512,
  next_decision: 512,
};
const CALLBACK_ID_PATTERN = /^terminal-v2-[a-f0-9]{64}$/;
const EXPLICIT_TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/;
const COMMIT_PATTERN = /^[0-9a-fA-F]{7,128}$/;
const REF_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._/-]*$/;
const TERMINAL_CLASSIFICATIONS = ["PASS", "BLOCKED", "FAIL"];
const CLEANLINESS_VALUES = ["clean", "dirty", "unknown"];
const CALLBACK_STATES = ["persisted", "observed", "consumed", "superseded", "expired"];
const TERMINAL_STATES = new Set(["consumed", "superseded", "expired"]);

function guardRoot(stateRoot) {
  return gitCommonDirectoryForState(stateRoot);
}

function safeChild(directory, filename) {
  const path = resolve(directory, filename);
  if (dirname(path) !== directory || basename(path) !== filename) {
    throw new CliError("Unsafe callback state path");
  }
  return path;
}

function requireTimestamp(value, label) {
  const text = requireText(value, label, { max: 64 });
  if (!EXPLICIT_TIMESTAMP_PATTERN.test(text) || !Number.isFinite(Date.parse(text))) {
    throw new CliError(`${label} must be an ISO timestamp with an explicit UTC offset`);
  }
  return text;
}

function optionalTimestamp(value, label) {
  return value === null ? null : requireTimestamp(value, label);
}

function validateRecipient(value, label = "recipient") {
  requireExactFields(value, { required: ["lineage_id", "thread_id", "generation"] }, label);
  return {
    lineage_id: requireText(value.lineage_id, `${label}.lineage_id`, { max: 128, safeId: true }),
    thread_id: requireText(value.thread_id, `${label}.thread_id`, { max: 128, safeId: true }),
    generation: requireInteger(value.generation, `${label}.generation`, { min: 1 }),
  };
}

function optionalRecipient(value, label) {
  return value === null ? null : validateRecipient(value, label);
}

function callbackIdentity(value) {
  const recipient = validateRecipient(value.recipient);
  return {
    lineage_id: recipient.lineage_id,
    executor_id: requireText(value.executor_id, "executor_id", { max: 128, safeId: true }),
    run_id: requireText(value.run_id, "run_id", { max: 128, safeId: true }),
    sequence: requireInteger(value.sequence, "sequence", { min: 1 }),
  };
}

export function validateTerminalReceipt(value) {
  requireExactFields(value, { required: RECEIPT_FIELDS }, "Terminal receipt");
  if (value.schema_version !== 2) {
    throw new CliError("Unsupported terminal receipt schema_version; expected 2");
  }
  const recipient = validateRecipient(value.recipient);
  const executorId = requireText(value.executor_id, "executor_id", { max: 128, safeId: true });
  const runId = requireText(value.run_id, "run_id", { max: 128, safeId: true });
  const sourceRevision = requireText(value.source_revision, "source_revision", { max: TEXT_LIMITS.source_revision });
  if (!COMMIT_PATTERN.test(sourceRevision)) throw new CliError("source_revision must be a commit hash");
  const sequence = requireInteger(value.sequence, "sequence", { min: 1 });
  const supersedes = requireStringArray(value.supersedes_callback_ids, "supersedes_callback_ids", {
    maxItems: 1,
    maxText: 128,
    safeIds: true,
  });
  for (const id of supersedes) {
    if (!CALLBACK_ID_PATTERN.test(id)) throw new CliError("supersedes_callback_ids must contain v2 callback IDs");
  }
  if (sequence === 1 && supersedes.length > 0) {
    throw new CliError("Initial terminal callback sequence cannot supersede another callback");
  }
  if (sequence > 1 && supersedes.length !== 1) {
    throw new CliError("Terminal callback sequence greater than 1 must supersede exactly one predecessor");
  }
  const expiresAt = requireTimestamp(value.expires_at, "expires_at");
  const classification = requireText(value.classification, "classification", { max: TEXT_LIMITS.classification });
  if (!TERMINAL_CLASSIFICATIONS.includes(classification)) {
    throw new CliError(`classification must be one of: ${TERMINAL_CLASSIFICATIONS.join(", ")}`);
  }
  const branch = requireText(value.branch, "branch", { max: TEXT_LIMITS.branch });
  const commit = requireText(value.commit, "commit", { max: TEXT_LIMITS.commit });
  const upstream = requireText(value.upstream, "upstream", { max: TEXT_LIMITS.upstream });
  const cleanliness = requireText(value.cleanliness, "cleanliness", { max: TEXT_LIMITS.cleanliness });
  if (!CLEANLINESS_VALUES.includes(cleanliness)) {
    throw new CliError(`cleanliness must be one of: ${CLEANLINESS_VALUES.join(", ")}`);
  }
  const resultOrBlocker = requireText(value.result_or_blocker, "result_or_blocker", { max: TEXT_LIMITS.result_or_blocker });
  const nextDecision = requireText(value.next_decision, "next_decision", { max: TEXT_LIMITS.next_decision });
  if (!REF_PATTERN.test(branch)) throw new CliError("branch must be a bounded Git reference");
  if (!COMMIT_PATTERN.test(commit)) throw new CliError("commit must be a commit hash");
  if (!REF_PATTERN.test(upstream)) throw new CliError("upstream must be a bounded Git reference");
  for (const [field, text] of Object.entries({
    classification,
    branch,
    upstream,
    result_or_blocker: resultOrBlocker,
    next_decision: nextDecision,
  })) assertSafeContent("Terminal receipt", field, text);

  requireExactFields(value.accounting, { required: ACCOUNTING_FIELDS }, "Terminal receipt accounting");
  const accounting = {};
  for (const field of ACCOUNTING_FIELDS) {
    const amount = value.accounting[field];
    if (!Number.isFinite(amount) || amount < 0) throw new CliError(`Invalid accounting bucket: ${field}`);
    accounting[field] = amount;
  }
  const normalized = {
    schema_version: 2,
    recipient,
    executor_id: executorId,
    run_id: runId,
    source_revision: sourceRevision,
    sequence,
    supersedes_callback_ids: supersedes,
    expires_at: expiresAt,
    classification,
    branch,
    commit,
    upstream,
    cleanliness,
    result_or_blocker: resultOrBlocker,
    next_decision: nextDecision,
    accounting,
  };
  if (Buffer.byteLength(stableStringify(normalized), "utf8") > 8192) {
    throw new CliError("Terminal receipt exceeds the 8 KiB serialized limit");
  }
  return normalized;
}

export function callbackIdFor(value) {
  const identity = callbackIdentity(validateTerminalReceipt(value));
  return `terminal-v2-${sha256(stableStringify(identity))}`;
}

function callbackId(value) {
  const result = requireText(value, "callback_id", { max: 128, safeId: true });
  if (!CALLBACK_ID_PATTERN.test(result)) throw new CliError("callback_id must be a v2 callback ID");
  return result;
}

function identityLockName(payload) {
  const identity = callbackIdentity(payload);
  return `${sha256(stableStringify({
    lineage_id: identity.lineage_id,
    executor_id: identity.executor_id,
    run_id: identity.run_id,
  }))}.lock.json`;
}

export function callbackPaths(stateRoot, payload) {
  const root = resolve(stateRoot, "callbacks");
  const journal = resolve(root, "journal");
  const id = callbackIdFor(payload);
  return {
    callbacksRoot: root,
    callbackId: id,
    record: safeChild(journal, `${id}.json`),
    lock: safeChild(resolve(root, "locks"), identityLockName(payload)),
  };
}

function callbackPathById(stateRoot, value) {
  const id = callbackId(value);
  return safeChild(resolve(stateRoot, "callbacks", "journal"), `${id}.json`);
}

function validateLifecycle(value) {
  requireExactFields(value, {
    required: ["persisted_at", "observed_at", "consumed_at", "superseded_at", "expired_at"],
  }, "Terminal callback lifecycle");
  return {
    persisted_at: requireTimestamp(value.persisted_at, "lifecycle.persisted_at"),
    observed_at: optionalTimestamp(value.observed_at, "lifecycle.observed_at"),
    consumed_at: optionalTimestamp(value.consumed_at, "lifecycle.consumed_at"),
    superseded_at: optionalTimestamp(value.superseded_at, "lifecycle.superseded_at"),
    expired_at: optionalTimestamp(value.expired_at, "lifecycle.expired_at"),
  };
}

function validateRecord(value) {
  requireExactFields(value, {
    required: [
      "schema_version", "kind", "callback_id", "receipt", "recipient", "state",
      "observed_by_recipient", "consumed_by_recipient", "observation_source",
      "superseded_by_callback_id", "lifecycle",
    ],
  }, "Terminal callback record");
  if (value.schema_version !== 4 || value.kind !== "terminal-callback-record") {
    throw new CliError("Unsupported terminal callback record; v0.5 does not migrate older callback journals");
  }
  const receipt = validateTerminalReceipt(value.receipt);
  const id = callbackId(value.callback_id);
  if (callbackIdFor(receipt) !== id) throw new CliError("Terminal callback record has an invalid callback_id");
  const recipient = validateRecipient(value.recipient, "delivery recipient");
  if (recipient.lineage_id !== receipt.recipient.lineage_id) {
    throw new CliError("Terminal callback delivery recipient lineage does not match its receipt");
  }
  const state = requireText(value.state, "Terminal callback state", { max: 32, safeId: true });
  if (!CALLBACK_STATES.includes(state)) throw new CliError("Terminal callback state is invalid");
  const observed = optionalRecipient(value.observed_by_recipient, "observed_by_recipient");
  const consumed = optionalRecipient(value.consumed_by_recipient, "consumed_by_recipient");
  const source = value.observation_source === null
    ? null
    : requireText(value.observation_source, "observation_source", { max: 32, safeId: true });
  if (source !== null && source !== "journal-monitor") {
    throw new CliError("v0.5 supports journal-monitor observation only");
  }
  const supersededBy = value.superseded_by_callback_id === null
    ? null
    : callbackId(value.superseded_by_callback_id);
  const lifecycle = validateLifecycle(value.lifecycle);
  if ((observed !== null) !== ["observed", "consumed"].includes(state)) {
    throw new CliError("Terminal callback observation state is inconsistent");
  }
  if ((consumed !== null) !== (state === "consumed")) {
    throw new CliError("Terminal callback consumption state is inconsistent");
  }
  if ((source !== null) !== (observed !== null)) {
    throw new CliError("Terminal callback observation source is inconsistent");
  }
  if ((supersededBy !== null) !== (state === "superseded")) {
    throw new CliError("Terminal callback supersession state is inconsistent");
  }
  for (const [expected, timestamp] of [
    [["observed", "consumed"].includes(state), lifecycle.observed_at],
    [state === "consumed", lifecycle.consumed_at],
    [state === "superseded", lifecycle.superseded_at],
    [state === "expired", lifecycle.expired_at],
  ]) {
    if (expected !== (timestamp !== null)) throw new CliError("Terminal callback lifecycle is inconsistent");
  }
  return {
    schema_version: 4,
    kind: "terminal-callback-record",
    callback_id: id,
    receipt,
    recipient,
    state,
    observed_by_recipient: observed,
    consumed_by_recipient: consumed,
    observation_source: source,
    superseded_by_callback_id: supersededBy,
    lifecycle,
  };
}

function newRecord(receipt, id, recipient, now = Date.now()) {
  return validateRecord({
    schema_version: 4,
    kind: "terminal-callback-record",
    callback_id: id,
    receipt,
    recipient,
    state: "persisted",
    observed_by_recipient: null,
    consumed_by_recipient: null,
    observation_source: null,
    superseded_by_callback_id: null,
    lifecycle: {
      persisted_at: new Date(now).toISOString(),
      observed_at: null,
      consumed_at: null,
      superseded_at: null,
      expired_at: null,
    },
  });
}

async function readRecord(path, root, { allowMissing = false } = {}) {
  const stored = await readJson(path, { allowMissing, guardRoot: root });
  return stored ? validateRecord(stored) : null;
}

async function writeRecord(path, record, root) {
  const validated = validateRecord(record);
  await atomicWriteJson(path, validated, { guardRoot: root, mode: 0o600 });
  return validated;
}

function recordExpired(record, now = Date.now()) {
  return Date.parse(record.receipt.expires_at) <= now;
}

async function withCallbackLock({ stateRoot, callbackId: id }, operation) {
  const root = guardRoot(stateRoot);
  const initial = await readRecord(callbackPathById(stateRoot, id), root, { allowMissing: true });
  if (!initial) throw new CliError("Terminal callback record does not exist");
  const paths = callbackPaths(stateRoot, initial.receipt);
  return withProcessLock({
    path: paths.lock,
    guardRoot: root,
    label: `terminal callback ${initial.callback_id}`,
  }, async () => {
    const record = await readRecord(paths.record, root, { allowMissing: true });
    if (!record) throw new CliError("Terminal callback record does not exist");
    return operation({ record, paths, root });
  });
}

function assertReceiptUnchanged(record, receipt) {
  if (stableStringify(record.receipt) !== stableStringify(receipt)) {
    throw new CliError("Changed terminal receipt collides with immutable callback identity", 73);
  }
}

function validateSupersession(prior, current, successorId) {
  const priorIdentity = callbackIdentity(prior.receipt);
  const currentIdentity = callbackIdentity(current);
  if (
    priorIdentity.lineage_id !== currentIdentity.lineage_id
    || priorIdentity.executor_id !== currentIdentity.executor_id
    || priorIdentity.run_id !== currentIdentity.run_id
    || priorIdentity.sequence !== currentIdentity.sequence - 1
  ) throw new CliError("Supersession must reference the immediately preceding callback for the same lineage, executor, and run", 73);
  if (["observed", "consumed"].includes(prior.state)) {
    throw new CliError("An observed or consumed terminal callback cannot be superseded", 73);
  }
  if (prior.state === "superseded" && prior.superseded_by_callback_id !== successorId) {
    throw new CliError("Terminal callback was already superseded by a different callback", 73);
  }
}

export async function deliverCallback({ stateRoot, receipt, now = Date.now(), hooks = {} }) {
  const payload = validateTerminalReceipt(receipt);
  const paths = callbackPaths(stateRoot, payload);
  const root = guardRoot(stateRoot);
  const resolved = await resolveRecipient({ stateRoot, recipient: payload.recipient });
  return withProcessLock({
    path: paths.lock,
    guardRoot: root,
    label: `terminal callback ${paths.callbackId}`,
  }, async () => {
    let record = await readRecord(paths.record, root, { allowMissing: true });
    const created = record === null;
    if (record) assertReceiptUnchanged(record, payload);
    else record = newRecord(payload, paths.callbackId, resolved.recipient, now);
    if (TERMINAL_STATES.has(record.state)) {
      return { status: `already-${record.state}`, callback_id: record.callback_id };
    }
    if (recordExpired(record, now)) {
      record.state = "expired";
      record.lifecycle.expired_at = new Date(now).toISOString();
      await writeRecord(paths.record, record, root);
      throw new CliError("Terminal callback expired before delivery", 73);
    }
    const priors = [];
    for (const priorId of payload.supersedes_callback_ids) {
      const priorPath = callbackPathById(stateRoot, priorId);
      const prior = await readRecord(priorPath, root, { allowMissing: true });
      if (!prior) throw new CliError(`Superseded terminal callback does not exist: ${priorId}`, 73);
      validateSupersession(prior, payload, paths.callbackId);
      priors.push({ path: priorPath, record: prior });
    }
    for (const prior of priors) {
      if (["expired", "superseded"].includes(prior.record.state)) continue;
      prior.record.state = "superseded";
      prior.record.superseded_by_callback_id = paths.callbackId;
      prior.record.lifecycle.superseded_at = new Date(now).toISOString();
      await writeRecord(prior.path, prior.record, root);
      if (hooks.afterSupersede) await hooks.afterSupersede({ callback_id: prior.record.callback_id });
    }
    await writeRecord(paths.record, record, root);
    return {
      status: created ? "persisted" : "already-persisted",
      callback_id: paths.callbackId,
      recipient: resolved.recipient,
      authority: "journal-monitor",
    };
  });
}

function requestedConsumer({ receiptRecipient, recipient }) {
  const requested = validateRecipient(recipient, "consumer recipient");
  if (requested.lineage_id !== receiptRecipient.lineage_id) {
    throw new CliError("Consumer recipient lineage does not match the terminal callback", 73);
  }
  return requested;
}

export async function observeCallback({ stateRoot, callbackId: id, recipient, now = Date.now(), hooks = {} }) {
  const snapshot = await withCallbackLock({ stateRoot, callbackId: id }, async ({ record }) => ({
    receiptRecipient: record.receipt.recipient,
  }));
  const requested = requestedConsumer({ receiptRecipient: snapshot.receiptRecipient, recipient });
  return withRecipientBindingLock({ stateRoot, recipient: requested }, async (resolved) => {
    if (resolved.stale) throw new CliError("Consumer recipient binding is stale; use the current coordinator generation", 73);
    if (hooks.afterRecipientLock) await hooks.afterRecipientLock();
    return withCallbackLock({ stateRoot, callbackId: id }, async ({ record, paths, root }) => {
      if (record.state === "consumed") return { status: "already-consumed", callback_id: record.callback_id };
      if (["superseded", "expired"].includes(record.state)) {
        throw new CliError(`${record.state} terminal callback cannot be observed`, 73);
      }
      if (recordExpired(record, now)) {
        record.state = "expired";
        record.lifecycle.expired_at = new Date(now).toISOString();
        await writeRecord(paths.record, record, root);
        throw new CliError("Expired terminal callback cannot be observed", 73);
      }
      if (record.state === "observed") return { status: "already-observed", callback_id: record.callback_id };
      record.state = "observed";
      record.observed_by_recipient = resolved.recipient;
      record.observation_source = "journal-monitor";
      record.lifecycle.observed_at = new Date(now).toISOString();
      await writeRecord(paths.record, record, root);
      return { status: "observed", callback_id: record.callback_id };
    });
  });
}

export async function consumeCallback({ stateRoot, callbackId: id, recipient, executorId, now = Date.now(), hooks = {} }) {
  requireText(executorId, "executor_id", { max: 128, safeId: true });
  const snapshot = await withCallbackLock({ stateRoot, callbackId: id }, async ({ record }) => ({
    receiptRecipient: record.receipt.recipient,
  }));
  const requested = requestedConsumer({ receiptRecipient: snapshot.receiptRecipient, recipient });
  return withRecipientBindingLock({ stateRoot, recipient: requested }, async (resolved) => {
    if (resolved.stale) throw new CliError("Consumer recipient binding is stale; use the current coordinator generation", 73);
    if (hooks.afterRecipientLock) await hooks.afterRecipientLock();
    return withCallbackLock({ stateRoot, callbackId: id }, async ({ record, paths, root }) => {
      if (executorId !== record.receipt.executor_id) throw new CliError("executor_id does not match the persisted receipt", 73);
      if (record.state === "consumed") return { status: "already-consumed", callback_id: record.callback_id };
      if (["superseded", "expired"].includes(record.state)) {
        throw new CliError(`${record.state} terminal callback cannot be consumed`, 73);
      }
      if (record.state !== "observed") {
        throw new CliError("Terminal callback must be observed before it can be consumed", 73);
      }
      record.state = "consumed";
      record.consumed_by_recipient = resolved.recipient;
      record.lifecycle.consumed_at = new Date(now).toISOString();
      await writeRecord(paths.record, record, root);
      return { status: "consumed", callback_id: record.callback_id };
    });
  });
}

export async function expireCallback({ stateRoot, callbackId: id, now = Date.now() }) {
  const nowMs = now instanceof Date ? now.getTime() : typeof now === "string" ? Date.parse(now) : Number(now);
  if (!Number.isFinite(nowMs)) throw new CliError("expire now must be a valid timestamp");
  return withCallbackLock({ stateRoot, callbackId: id }, async ({ record, paths, root }) => {
    if (record.state === "expired") return { status: "already-expired", callback_id: id };
    if (["observed", "consumed", "superseded"].includes(record.state)) {
      return { status: `already-${record.state}`, callback_id: id };
    }
    if (!recordExpired(record, nowMs)) return { status: "not-expired", callback_id: id };
    record.state = "expired";
    record.lifecycle.expired_at = new Date(nowMs).toISOString();
    await writeRecord(paths.record, record, root);
    return { status: "expired", callback_id: id };
  });
}

async function listJsonFiles(root, stateRoot) {
  const trustedRoot = guardRoot(stateRoot);
  const result = [];
  await assertNoSymlinkComponents(trustedRoot, root, "Callback state path");
  let entries;
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return result;
    throw error;
  }
  for (const entry of entries) {
    const path = resolve(root, entry.name);
    if (entry.isSymbolicLink()) throw new CliError(`Callback state contains a symbolic link: ${path}`);
    if (entry.isDirectory()) result.push(...await listJsonFiles(path, stateRoot));
    else if (entry.isFile() && entry.name.endsWith(".json")) result.push(path);
  }
  return result;
}

export async function expireCallbacks({ stateRoot, now = Date.now() }) {
  const results = [];
  for (const path of await listJsonFiles(resolve(stateRoot, "callbacks", "journal"), stateRoot)) {
    results.push(await expireCallback({ stateRoot, callbackId: basename(path, ".json"), now }));
  }
  return results;
}

export async function callbackStatus(stateRoot) {
  const root = guardRoot(stateRoot);
  const pending = [];
  let consumedCount = 0;
  let supersededCount = 0;
  let expiredCount = 0;
  for (const path of await listJsonFiles(resolve(stateRoot, "callbacks", "journal"), stateRoot)) {
    const record = await readRecord(path, root);
    const age = Math.max(0, Math.floor((Date.now() - (await stat(path)).mtimeMs) / 1000));
    if (record.state === "consumed") consumedCount += 1;
    else if (record.state === "superseded") supersededCount += 1;
    else if (record.state === "expired") expiredCount += 1;
    else {
      pending.push({
        callback_id: record.callback_id,
        lineage_id: record.receipt.recipient.lineage_id,
        recipient_generation: record.recipient.generation,
        executor_id: record.receipt.executor_id,
        run_id: record.receipt.run_id,
        sequence: record.receipt.sequence,
        classification: record.receipt.classification,
        integration: record.state,
        effective_integration: recordExpired(record) ? "expired-due" : record.state,
        age_seconds: age,
      });
    }
  }
  return {
    pending: pending.sort((a, b) => b.age_seconds - a.age_seconds),
    consumed_count: consumedCount,
    superseded_count: supersededCount,
    expired_count: expiredCount,
  };
}

function codexBinaryCandidates() {
  const configured = process.env.CODEX_FLOW_CODEX_BIN?.trim();
  if (configured) return [configured];
  const result = ["codex"];
  if (process.platform === "darwin") {
    for (const path of [
      "/Applications/Codex.app/Contents/Resources/codex",
      "/Applications/ChatGPT.app/Contents/Resources/codex",
    ]) {
      if (existsSync(path)) result.push(path);
    }
  }
  return result;
}

export function findCodexBinary() {
  for (const binary of codexBinaryCandidates()) {
    const result = spawnSync(binary, ["--version"], { encoding: "utf8", timeout: 5000 });
    if (!result.error && result.status === 0) {
      return { binary, version: result.stdout.trim() || result.stderr.trim() };
    }
    if (result.error?.code !== "ENOENT") {
      return { binary, error: result.error?.code ?? `exit-${result.status}` };
    }
  }
  return null;
}
