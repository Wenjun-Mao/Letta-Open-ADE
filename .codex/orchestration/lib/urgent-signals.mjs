import { readdir } from "node:fs/promises";
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
import { withRecipientBindingLock } from "./recipients.mjs";

const SIGNAL_FIELDS = [
  "schema_version",
  "recipient",
  "executor_id",
  "run_id",
  "sequence",
  "supersedes_urgent_ids",
  "expires_at",
  "classification",
  "summary",
  "requested_action",
];
const SIGNAL_ID_PATTERN = /^urgent-v1-[a-f0-9]{64}$/;
const ATTEMPT_ID_PATTERN = /^urgent-attempt-v1-[a-f0-9]{64}$/;
const EXPLICIT_TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/;
const CLASSIFICATIONS = ["blocker", "approval", "high-risk-drift"];
const SIGNAL_STATES = ["persisted", "observed", "consumed", "superseded", "expired"];
const ATTEMPT_OUTCOMES = ["accepted", "failed", "ambiguous"];
const HOST_CALL_RESULTS = {
  sent: "accepted",
  "rejected-before-send": "failed",
  ambiguous: "ambiguous",
};
const RETRY_REASONS = ["host-ambiguous", "recipient-rebound", "operator-approved-retry"];
const TERMINAL_STATES = new Set(["consumed", "superseded", "expired"]);
const HOST_PROMPT_LIMIT_BYTES = 2048;

function guardRoot(stateRoot) {
  return gitCommonDirectoryForState(stateRoot);
}

function safeChild(directory, filename) {
  const path = resolve(directory, filename);
  if (dirname(path) !== directory || basename(path) !== filename) {
    throw new CliError("Unsafe urgent-signal state path");
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

function nowMilliseconds(value) {
  const result = value instanceof Date
    ? value.getTime()
    : typeof value === "string"
      ? Date.parse(value)
      : Number(value);
  if (!Number.isFinite(result)) throw new CliError("Urgent-signal time must be valid");
  return result;
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

function signalIdentity(value) {
  const recipient = validateRecipient(value.recipient);
  return {
    lineage_id: recipient.lineage_id,
    executor_id: requireText(value.executor_id, "executor_id", { max: 128, safeId: true }),
    run_id: requireText(value.run_id, "run_id", { max: 128, safeId: true }),
    sequence: requireInteger(value.sequence, "sequence", { min: 1 }),
  };
}

export function validateUrgentSignal(value) {
  requireExactFields(value, { required: SIGNAL_FIELDS }, "Urgent signal");
  if (value.schema_version !== 1) {
    throw new CliError("Unsupported urgent signal schema_version; expected 1");
  }
  const recipient = validateRecipient(value.recipient);
  const executorId = requireText(value.executor_id, "executor_id", { max: 128, safeId: true });
  const runId = requireText(value.run_id, "run_id", { max: 128, safeId: true });
  const sequence = requireInteger(value.sequence, "sequence", { min: 1 });
  const supersedes = requireStringArray(value.supersedes_urgent_ids, "supersedes_urgent_ids", {
    maxItems: 1,
    maxText: 128,
    safeIds: true,
  });
  for (const id of supersedes) {
    if (!SIGNAL_ID_PATTERN.test(id)) {
      throw new CliError("supersedes_urgent_ids must contain v1 urgent IDs");
    }
  }
  if (sequence === 1 && supersedes.length > 0) {
    throw new CliError("Initial urgent signal sequence cannot supersede another signal");
  }
  if (sequence > 1 && supersedes.length !== 1) {
    throw new CliError("Urgent signal sequence greater than 1 must supersede exactly one predecessor");
  }
  const expiresAt = requireTimestamp(value.expires_at, "expires_at");
  const classification = requireText(value.classification, "classification", { max: 32, safeId: true });
  if (!CLASSIFICATIONS.includes(classification)) {
    throw new CliError(`classification must be one of: ${CLASSIFICATIONS.join(", ")}`);
  }
  const summary = requireText(value.summary, "summary", { max: 512 });
  const requestedAction = requireText(value.requested_action, "requested_action", { max: 512 });
  assertSafeContent("Urgent signal", "summary", summary);
  assertSafeContent("Urgent signal", "requested_action", requestedAction);
  const normalized = {
    schema_version: 1,
    recipient,
    executor_id: executorId,
    run_id: runId,
    sequence,
    supersedes_urgent_ids: supersedes,
    expires_at: expiresAt,
    classification,
    summary,
    requested_action: requestedAction,
  };
  if (Buffer.byteLength(stableStringify(normalized), "utf8") > 4096) {
    throw new CliError("Urgent signal exceeds the 4 KiB serialized limit");
  }
  return normalized;
}

export function urgentIdFor(value) {
  return `urgent-v1-${sha256(stableStringify(signalIdentity(validateUrgentSignal(value))))}`;
}

function urgentId(value) {
  const result = requireText(value, "urgent_id", { max: 128, safeId: true });
  if (!SIGNAL_ID_PATTERN.test(result)) throw new CliError("urgent_id must be a v1 urgent ID");
  return result;
}

export function urgentAttemptIdFor(urgentIdValue, attemptSequence, recipient) {
  const id = urgentId(urgentIdValue);
  const sequence = requireInteger(attemptSequence, "attempt_sequence", { min: 1, max: 64 });
  const target = validateRecipient(recipient, "attempt recipient");
  return `urgent-attempt-v1-${sha256(stableStringify({
    urgent_id: id,
    attempt_sequence: sequence,
    recipient: target,
  }))}`;
}

function attemptId(value) {
  const result = requireText(value, "delivery_attempt_id", { max: 128, safeId: true });
  if (!ATTEMPT_ID_PATTERN.test(result)) {
    throw new CliError("delivery_attempt_id must be a v1 urgent attempt ID");
  }
  return result;
}

function identityLockName(signal) {
  const identity = signalIdentity(signal);
  return `${sha256(stableStringify({
    lineage_id: identity.lineage_id,
    executor_id: identity.executor_id,
    run_id: identity.run_id,
  }))}.lock.json`;
}

export function urgentSignalPaths(stateRoot, signal) {
  const root = resolve(stateRoot, "urgent-signals");
  const id = urgentIdFor(signal);
  return {
    urgentRoot: root,
    urgentId: id,
    record: safeChild(resolve(root, "journal"), `${id}.json`),
    lock: safeChild(resolve(root, "locks"), identityLockName(signal)),
  };
}

function urgentPathById(stateRoot, value) {
  const id = urgentId(value);
  return safeChild(resolve(stateRoot, "urgent-signals", "journal"), `${id}.json`);
}

function validateAttempt(value, urgentIdValue) {
  requireExactFields(value, {
    required: [
      "attempt_sequence",
      "delivery_attempt_id",
      "recipient",
      "retry_reason",
      "prepared_at",
      "outcome",
      "reconciled_at",
      "first_observed_at",
      "observation_count",
    ],
  }, "Urgent delivery attempt");
  const sequence = requireInteger(value.attempt_sequence, "attempt_sequence", { min: 1, max: 64 });
  const recipient = validateRecipient(value.recipient, "attempt recipient");
  const id = attemptId(value.delivery_attempt_id);
  if (id !== urgentAttemptIdFor(urgentIdValue, sequence, recipient)) {
    throw new CliError("Urgent delivery attempt has an invalid delivery_attempt_id");
  }
  const retryReason = value.retry_reason === null
    ? null
    : requireText(value.retry_reason, "attempt.retry_reason", { max: 64, safeId: true });
  if (sequence === 1 && retryReason !== null) {
    throw new CliError("Initial urgent delivery attempt cannot have a retry reason");
  }
  if (sequence > 1 && !RETRY_REASONS.includes(retryReason)) {
    throw new CliError(`Retrying urgent delivery requires one of: ${RETRY_REASONS.join(", ")}`);
  }
  const preparedAt = requireTimestamp(value.prepared_at, "attempt.prepared_at");
  const outcome = value.outcome === null
    ? null
    : requireText(value.outcome, "attempt.outcome", { max: 32, safeId: true });
  if (outcome !== null && !ATTEMPT_OUTCOMES.includes(outcome)) {
    throw new CliError(`attempt.outcome must be one of: ${ATTEMPT_OUTCOMES.join(", ")}`);
  }
  const reconciledAt = optionalTimestamp(value.reconciled_at, "attempt.reconciled_at");
  if ((outcome !== null) !== (reconciledAt !== null)) {
    throw new CliError("Urgent delivery attempt reconciliation state is inconsistent");
  }
  const firstObservedAt = optionalTimestamp(value.first_observed_at, "attempt.first_observed_at");
  const observationCount = requireInteger(value.observation_count, "attempt.observation_count", {
    min: 0,
    max: 2147483647,
  });
  if ((firstObservedAt !== null) !== (observationCount > 0)) {
    throw new CliError("Urgent delivery attempt observation state is inconsistent");
  }
  return {
    attempt_sequence: sequence,
    delivery_attempt_id: id,
    recipient,
    retry_reason: retryReason,
    prepared_at: preparedAt,
    outcome,
    reconciled_at: reconciledAt,
    first_observed_at: firstObservedAt,
    observation_count: observationCount,
  };
}

function validateLifecycle(value) {
  requireExactFields(value, {
    required: ["persisted_at", "observed_at", "consumed_at", "superseded_at", "expired_at"],
  }, "Urgent signal lifecycle");
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
      "schema_version",
      "kind",
      "urgent_id",
      "signal",
      "recipient",
      "state",
      "observed_by_recipient",
      "consumed_by_recipient",
      "first_observed_attempt_id",
      "superseded_by_urgent_id",
      "attempts",
      "lifecycle",
    ],
  }, "Urgent signal record");
  if (value.schema_version !== 1 || value.kind !== "urgent-signal-record") {
    throw new CliError("Unsupported urgent-signal record; v0.5 does not migrate older urgent journals");
  }
  const signal = validateUrgentSignal(value.signal);
  const id = urgentId(value.urgent_id);
  if (urgentIdFor(signal) !== id) throw new CliError("Urgent signal record has an invalid urgent_id");
  const recipient = validateRecipient(value.recipient, "delivery recipient");
  if (recipient.lineage_id !== signal.recipient.lineage_id) {
    throw new CliError("Urgent signal delivery recipient lineage does not match its signal");
  }
  const state = requireText(value.state, "Urgent signal state", { max: 32, safeId: true });
  if (!SIGNAL_STATES.includes(state)) throw new CliError("Urgent signal state is invalid");
  const observed = optionalRecipient(value.observed_by_recipient, "observed_by_recipient");
  const consumed = optionalRecipient(value.consumed_by_recipient, "consumed_by_recipient");
  const firstAttempt = value.first_observed_attempt_id === null
    ? null
    : attemptId(value.first_observed_attempt_id);
  const supersededBy = value.superseded_by_urgent_id === null
    ? null
    : urgentId(value.superseded_by_urgent_id);
  if (!Array.isArray(value.attempts) || value.attempts.length > 64) {
    throw new CliError("Urgent signal attempts must contain at most 64 entries");
  }
  const attempts = value.attempts.map((attempt) => validateAttempt(attempt, id));
  for (let index = 0; index < attempts.length; index += 1) {
    if (attempts[index].attempt_sequence !== index + 1) {
      throw new CliError("Urgent delivery attempt sequences must be contiguous");
    }
  }
  const lifecycle = validateLifecycle(value.lifecycle);
  if ((observed !== null) !== ["observed", "consumed"].includes(state)) {
    throw new CliError("Urgent signal observation state is inconsistent");
  }
  if ((consumed !== null) !== (state === "consumed")) {
    throw new CliError("Urgent signal consumption state is inconsistent");
  }
  if ((firstAttempt !== null) !== (observed !== null)) {
    throw new CliError("Urgent signal first observation state is inconsistent");
  }
  if (firstAttempt !== null && !attempts.some((attempt) => (
    attempt.delivery_attempt_id === firstAttempt && attempt.observation_count > 0
  ))) {
    throw new CliError("Urgent signal first observation attempt is invalid");
  }
  if ((supersededBy !== null) !== (state === "superseded")) {
    throw new CliError("Urgent signal supersession state is inconsistent");
  }
  for (const [expected, timestamp] of [
    [["observed", "consumed"].includes(state), lifecycle.observed_at],
    [state === "consumed", lifecycle.consumed_at],
    [state === "superseded", lifecycle.superseded_at],
    [state === "expired", lifecycle.expired_at],
  ]) {
    if (expected !== (timestamp !== null)) throw new CliError("Urgent signal lifecycle is inconsistent");
  }
  const normalized = {
    schema_version: 1,
    kind: "urgent-signal-record",
    urgent_id: id,
    signal,
    recipient,
    state,
    observed_by_recipient: observed,
    consumed_by_recipient: consumed,
    first_observed_attempt_id: firstAttempt,
    superseded_by_urgent_id: supersededBy,
    attempts,
    lifecycle,
  };
  if (Buffer.byteLength(stableStringify(normalized), "utf8") > 32768) {
    throw new CliError("Urgent signal record exceeds the 32 KiB serialized limit");
  }
  return normalized;
}

function newRecord(signal, id, recipient, now) {
  return validateRecord({
    schema_version: 1,
    kind: "urgent-signal-record",
    urgent_id: id,
    signal,
    recipient,
    state: "persisted",
    observed_by_recipient: null,
    consumed_by_recipient: null,
    first_observed_attempt_id: null,
    superseded_by_urgent_id: null,
    attempts: [],
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
  return Date.parse(record.signal.expires_at) <= nowMilliseconds(now);
}

async function withUrgentLock({ stateRoot, urgentId: id }, operation) {
  const root = guardRoot(stateRoot);
  const initial = await readRecord(urgentPathById(stateRoot, id), root, { allowMissing: true });
  if (!initial) throw new CliError("Urgent signal record does not exist");
  const paths = urgentSignalPaths(stateRoot, initial.signal);
  return withProcessLock({
    path: paths.lock,
    guardRoot: root,
    label: `urgent signal ${initial.urgent_id}`,
  }, async () => {
    const record = await readRecord(paths.record, root, { allowMissing: true });
    if (!record) throw new CliError("Urgent signal record does not exist");
    return operation({ record, paths, root });
  });
}

function assertSignalUnchanged(record, signal) {
  if (stableStringify(record.signal) !== stableStringify(signal)) {
    throw new CliError("Changed urgent signal collides with immutable urgent identity", 73);
  }
}

function validateSupersession(prior, current, successorId) {
  const priorIdentity = signalIdentity(prior.signal);
  const currentIdentity = signalIdentity(current);
  if (
    priorIdentity.lineage_id !== currentIdentity.lineage_id
    || priorIdentity.executor_id !== currentIdentity.executor_id
    || priorIdentity.run_id !== currentIdentity.run_id
    || priorIdentity.sequence !== currentIdentity.sequence - 1
  ) {
    throw new CliError("Urgent supersession must reference the immediately preceding signal for the same lineage, executor, and run", 73);
  }
  if (prior.state === "superseded" && prior.superseded_by_urgent_id !== successorId) {
    throw new CliError("Urgent signal was already superseded by a different successor", 73);
  }
}

export async function persistUrgentSignal({ stateRoot, signal: input, now = Date.now() }) {
  const signal = validateUrgentSignal(input);
  const paths = urgentSignalPaths(stateRoot, signal);
  const root = guardRoot(stateRoot);
  return withRecipientBindingLock({ stateRoot, recipient: signal.recipient }, async (resolved) => {
    return withProcessLock({
      path: paths.lock,
      guardRoot: root,
      label: `urgent signal ${paths.urgentId}`,
    }, async () => {
      let record = await readRecord(paths.record, root, { allowMissing: true });
      const created = record === null;
      if (record) assertSignalUnchanged(record, signal);
      else record = newRecord(signal, paths.urgentId, resolved.recipient, nowMilliseconds(now));
      if (TERMINAL_STATES.has(record.state)) {
        return { status: `already-${record.state}`, urgent_id: record.urgent_id };
      }
      if (recordExpired(record, now)) {
        record.state = "expired";
        record.lifecycle.expired_at = new Date(nowMilliseconds(now)).toISOString();
        await writeRecord(paths.record, record, root);
        throw new CliError("Urgent signal expired before persistence", 73);
      }
      for (const priorId of signal.supersedes_urgent_ids) {
        const priorPath = urgentPathById(stateRoot, priorId);
        const prior = await readRecord(priorPath, root, { allowMissing: true });
        if (!prior) throw new CliError(`Superseded urgent signal does not exist: ${priorId}`, 73);
        validateSupersession(prior, signal, paths.urgentId);
        if (prior.state === "persisted") {
          prior.state = "superseded";
          prior.superseded_by_urgent_id = paths.urgentId;
          prior.lifecycle.superseded_at = new Date(nowMilliseconds(now)).toISOString();
          await writeRecord(priorPath, prior, root);
        }
      }
      if (created) await writeRecord(paths.record, record, root);
      return {
        status: created ? "persisted" : "already-persisted",
        urgent_id: paths.urgentId,
        recipient: resolved.recipient,
        authority: "journal-direct",
      };
    });
  });
}

function hostCallResultForOutcome(outcome) {
  return Object.entries(HOST_CALL_RESULTS).find(([, stored]) => stored === outcome)?.[0] ?? null;
}

function directHostPrompt(record, attempt) {
  const envelope = {
    schema_version: 1,
    kind: "codex-flow-urgent-direct",
    urgent_id: record.urgent_id,
    delivery_attempt_id: attempt.delivery_attempt_id,
    classification: record.signal.classification,
    summary: record.signal.summary,
    recipient: attempt.recipient,
  };
  const prompt = stableStringify(envelope);
  if (Buffer.byteLength(prompt, "utf8") > HOST_PROMPT_LIMIT_BYTES) {
    throw new CliError("Urgent host prompt exceeds the 2 KiB delivery limit", 73);
  }
  return prompt;
}

export async function prepareUrgentAttempt({
  stateRoot,
  urgentId: id,
  attemptSequence,
  retryReason = null,
  now = Date.now(),
}) {
  const sequence = requireInteger(attemptSequence, "attempt_sequence", { min: 1, max: 64 });
  const requestedReason = retryReason === null
    ? null
    : requireText(retryReason, "retry_reason", { max: 64, safeId: true });
  const snapshot = await withUrgentLock({ stateRoot, urgentId: id }, async ({ record }) => ({
    signalRecipient: record.signal.recipient,
  }));
  return withRecipientBindingLock({ stateRoot, recipient: snapshot.signalRecipient }, async (resolved) => {
    return withUrgentLock({ stateRoot, urgentId: id }, async ({ record, paths, root }) => {
      if (record.state !== "persisted") {
        throw new CliError(`${record.state} urgent signal cannot prepare a delivery attempt`, 73);
      }
      if (recordExpired(record, now)) {
        record.state = "expired";
        record.lifecycle.expired_at = new Date(nowMilliseconds(now)).toISOString();
        await writeRecord(paths.record, record, root);
        throw new CliError("Expired urgent signal cannot prepare a delivery attempt", 73);
      }
      const existing = record.attempts.find((attempt) => attempt.attempt_sequence === sequence);
      if (existing) {
        if (existing.retry_reason !== requestedReason) {
          throw new CliError("Changed retry reason collides with an existing urgent delivery attempt", 73);
        }
        if (stableStringify(existing.recipient) !== stableStringify(resolved.recipient)) {
          throw new CliError("Existing urgent delivery attempt targets a prior coordinator generation; prepare an explicit recipient-rebound retry", 73);
        }
        return {
          status: existing.outcome === null
            ? "already-prepared"
            : `already-${hostCallResultForOutcome(existing.outcome)}`,
          dispatch_permitted: false,
          urgent_id: record.urgent_id,
          delivery_attempt_id: existing.delivery_attempt_id,
          host_prompt: directHostPrompt(record, existing),
        };
      }
      if (sequence !== record.attempts.length + 1) {
        throw new CliError("Urgent delivery attempt sequences must be contiguous", 73);
      }
      const prior = record.attempts.at(-1);
      if (prior && prior.outcome === null) {
        throw new CliError("Prior urgent delivery attempt must be reconciled before preparing another", 73);
      }
      if (sequence === 1 && requestedReason !== null) {
        throw new CliError("Initial urgent delivery attempt cannot have a retry reason", 73);
      }
      if (sequence > 1 && !RETRY_REASONS.includes(requestedReason)) {
        throw new CliError(`Retrying urgent delivery requires one of: ${RETRY_REASONS.join(", ")}`, 73);
      }
      const attempt = {
        attempt_sequence: sequence,
        delivery_attempt_id: urgentAttemptIdFor(record.urgent_id, sequence, resolved.recipient),
        recipient: resolved.recipient,
        retry_reason: requestedReason,
        prepared_at: new Date(nowMilliseconds(now)).toISOString(),
        outcome: null,
        reconciled_at: null,
        first_observed_at: null,
        observation_count: 0,
      };
      const hostPrompt = directHostPrompt(record, attempt);
      record.attempts.push(attempt);
      await writeRecord(paths.record, record, root);
      return {
        status: "prepared",
        dispatch_permitted: true,
        urgent_id: record.urgent_id,
        delivery_attempt_id: attempt.delivery_attempt_id,
        host_prompt: hostPrompt,
      };
    });
  });
}

export async function reconcileUrgentAttempt({
  stateRoot,
  urgentId: id,
  deliveryAttemptId,
  hostCallResult,
  now = Date.now(),
}) {
  const requestedAttemptId = attemptId(deliveryAttemptId);
  const requestedResult = requireText(hostCallResult, "host_call_result", { max: 32, safeId: true });
  const requestedOutcome = HOST_CALL_RESULTS[requestedResult];
  if (!requestedOutcome) {
    throw new CliError(`host_call_result must be one of: ${Object.keys(HOST_CALL_RESULTS).join(", ")}`);
  }
  return withUrgentLock({ stateRoot, urgentId: id }, async ({ record, paths, root }) => {
    const attempt = record.attempts.find((entry) => entry.delivery_attempt_id === requestedAttemptId);
    if (!attempt) throw new CliError("Urgent delivery attempt does not exist", 73);
    if (attempt.outcome !== null) {
      if (attempt.outcome !== requestedOutcome) {
        throw new CliError("Urgent delivery attempt already has a different immutable host-call result", 73);
      }
      return {
        status: `already-${hostCallResultForOutcome(attempt.outcome)}`,
        urgent_id: record.urgent_id,
        delivery_attempt_id: attempt.delivery_attempt_id,
      };
    }
    if (requestedOutcome === "failed" && attempt.observation_count > 0) {
      throw new CliError("Observed urgent delivery attempt cannot be reconciled as rejected-before-send", 73);
    }
    attempt.outcome = requestedOutcome;
    attempt.reconciled_at = new Date(nowMilliseconds(now)).toISOString();
    await writeRecord(paths.record, record, root);
    return {
      status: requestedResult,
      urgent_id: record.urgent_id,
      delivery_attempt_id: attempt.delivery_attempt_id,
    };
  });
}

function requestedConsumer({ signalRecipient, recipient }) {
  const requested = validateRecipient(recipient, "consumer recipient");
  if (requested.lineage_id !== signalRecipient.lineage_id) {
    throw new CliError("Consumer recipient lineage does not match the urgent signal", 73);
  }
  return requested;
}

export async function observeUrgentSignal({
  stateRoot,
  urgentId: id,
  deliveryAttemptId,
  recipient,
  now = Date.now(),
  hooks = {},
}) {
  const requestedAttemptId = attemptId(deliveryAttemptId);
  const snapshot = await withUrgentLock({ stateRoot, urgentId: id }, async ({ record }) => ({
    signalRecipient: record.signal.recipient,
  }));
  const requested = requestedConsumer({ signalRecipient: snapshot.signalRecipient, recipient });
  return withRecipientBindingLock({ stateRoot, recipient: requested }, async (resolved) => {
    if (resolved.stale) {
      throw new CliError("Consumer recipient binding is stale; use the current coordinator generation", 73);
    }
    if (hooks.afterRecipientLock) await hooks.afterRecipientLock();
    return withUrgentLock({ stateRoot, urgentId: id }, async ({ record, paths, root }) => {
      const attempt = record.attempts.find((entry) => entry.delivery_attempt_id === requestedAttemptId);
      if (!attempt) throw new CliError("Urgent delivery attempt does not exist", 73);
      if (stableStringify(attempt.recipient) !== stableStringify(resolved.recipient)) {
        throw new CliError("Urgent delivery attempt targets a stale coordinator generation", 73);
      }
      const observedAt = new Date(nowMilliseconds(now)).toISOString();
      attempt.observation_count += 1;
      if (attempt.first_observed_at === null) attempt.first_observed_at = observedAt;

      if (record.state === "persisted" && recordExpired(record, now)) {
        record.state = "expired";
        record.lifecycle.expired_at = observedAt;
        await writeRecord(paths.record, record, root);
        return {
          status: "already-expired",
          disposition: "suppress",
          urgent_id: record.urgent_id,
          delivery_attempt_id: attempt.delivery_attempt_id,
        };
      }
      if (["superseded", "expired"].includes(record.state)) {
        await writeRecord(paths.record, record, root);
        return {
          status: `already-${record.state}`,
          disposition: "suppress",
          urgent_id: record.urgent_id,
          delivery_attempt_id: attempt.delivery_attempt_id,
        };
      }
      if (record.first_observed_attempt_id === null) {
        record.state = "observed";
        record.observed_by_recipient = resolved.recipient;
        record.first_observed_attempt_id = attempt.delivery_attempt_id;
        record.lifecycle.observed_at = observedAt;
        await writeRecord(paths.record, record, root);
        return {
          status: "observed",
          disposition: "process",
          urgent_id: record.urgent_id,
          delivery_attempt_id: attempt.delivery_attempt_id,
          signal: record.signal,
          consume_arguments: {
            urgent_id: record.urgent_id,
            lineage_id: resolved.recipient.lineage_id,
            thread_id: resolved.recipient.thread_id,
            generation: resolved.recipient.generation,
            sender_executor_id: record.signal.executor_id,
          },
        };
      }
      const duplicateKind = attempt.observation_count > 1 ? "host-replay" : "sender-attempt";
      await writeRecord(paths.record, record, root);
      return {
        status: `duplicate-${duplicateKind}`,
        disposition: "suppress",
        urgent_id: record.urgent_id,
        delivery_attempt_id: attempt.delivery_attempt_id,
      };
    });
  });
}

export async function consumeUrgentSignal({
  stateRoot,
  urgentId: id,
  recipient,
  senderExecutorId,
  now = Date.now(),
  hooks = {},
}) {
  const requestedExecutor = requireText(senderExecutorId, "sender_executor_id", { max: 128, safeId: true });
  const snapshot = await withUrgentLock({ stateRoot, urgentId: id }, async ({ record }) => ({
    signalRecipient: record.signal.recipient,
  }));
  const requested = requestedConsumer({ signalRecipient: snapshot.signalRecipient, recipient });
  return withRecipientBindingLock({ stateRoot, recipient: requested }, async (resolved) => {
    if (resolved.stale) {
      throw new CliError("Consumer recipient binding is stale; use the current coordinator generation", 73);
    }
    if (hooks.afterRecipientLock) await hooks.afterRecipientLock();
    return withUrgentLock({ stateRoot, urgentId: id }, async ({ record, paths, root }) => {
      if (requestedExecutor !== record.signal.executor_id) {
        throw new CliError("sender_executor_id does not match the persisted urgent signal", 73);
      }
      if (record.state === "consumed") {
        return { status: "already-consumed", urgent_id: record.urgent_id };
      }
      if (["superseded", "expired"].includes(record.state)) {
        throw new CliError(`${record.state} urgent signal cannot be consumed`, 73);
      }
      if (record.state !== "observed") {
        throw new CliError("Urgent signal must be observed before it can be consumed", 73);
      }
      record.state = "consumed";
      record.consumed_by_recipient = resolved.recipient;
      record.lifecycle.consumed_at = new Date(nowMilliseconds(now)).toISOString();
      await writeRecord(paths.record, record, root);
      return { status: "consumed", urgent_id: record.urgent_id };
    });
  });
}

export async function expireUrgentSignal({ stateRoot, urgentId: id, now = Date.now() }) {
  const time = nowMilliseconds(now);
  return withUrgentLock({ stateRoot, urgentId: id }, async ({ record, paths, root }) => {
    if (record.state === "expired") return { status: "already-expired", urgent_id: record.urgent_id };
    if (["observed", "consumed", "superseded"].includes(record.state)) {
      return { status: `already-${record.state}`, urgent_id: record.urgent_id };
    }
    if (!recordExpired(record, time)) return { status: "not-expired", urgent_id: record.urgent_id };
    record.state = "expired";
    record.lifecycle.expired_at = new Date(time).toISOString();
    await writeRecord(paths.record, record, root);
    return { status: "expired", urgent_id: record.urgent_id };
  });
}

async function listJsonFiles(root, stateRoot) {
  const trustedRoot = guardRoot(stateRoot);
  const result = [];
  await assertNoSymlinkComponents(trustedRoot, root, "Urgent-signal state path");
  let entries;
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return result;
    throw error;
  }
  for (const entry of entries) {
    const path = resolve(root, entry.name);
    if (entry.isSymbolicLink()) throw new CliError(`Urgent-signal state contains a symbolic link: ${path}`);
    if (entry.isDirectory()) result.push(...await listJsonFiles(path, stateRoot));
    else if (entry.isFile() && entry.name.endsWith(".json")) result.push(path);
  }
  return result;
}

export async function expireUrgentSignals({ stateRoot, now = Date.now() }) {
  const results = [];
  for (const path of await listJsonFiles(resolve(stateRoot, "urgent-signals", "journal"), stateRoot)) {
    results.push(await expireUrgentSignal({
      stateRoot,
      urgentId: basename(path, ".json"),
      now,
    }));
  }
  return results;
}

export async function urgentSignalStatus(stateRoot) {
  const root = guardRoot(stateRoot);
  const pending = [];
  let consumedCount = 0;
  let supersededCount = 0;
  let expiredCount = 0;
  let hostReplayCount = 0;
  let senderAttemptDuplicateCount = 0;
  for (const path of await listJsonFiles(resolve(stateRoot, "urgent-signals", "journal"), stateRoot)) {
    const record = await readRecord(path, root);
    const age = Math.max(0, Math.floor((Date.now() - Date.parse(record.lifecycle.persisted_at)) / 1000));
    const latestRecipient = record.attempts.at(-1)?.recipient ?? record.recipient;
    for (const attempt of record.attempts) {
      hostReplayCount += Math.max(0, attempt.observation_count - 1);
      if (
        attempt.observation_count > 0
        && record.first_observed_attempt_id !== null
        && attempt.delivery_attempt_id !== record.first_observed_attempt_id
      ) senderAttemptDuplicateCount += 1;
    }
    if (record.state === "consumed") consumedCount += 1;
    else if (record.state === "superseded") supersededCount += 1;
    else if (record.state === "expired") expiredCount += 1;
    else {
      pending.push({
        urgent_id: record.urgent_id,
        lineage_id: record.signal.recipient.lineage_id,
        recipient_generation: latestRecipient.generation,
        executor_id: record.signal.executor_id,
        run_id: record.signal.run_id,
        sequence: record.signal.sequence,
        classification: record.signal.classification,
        state: record.state,
        effective_state: recordExpired(record) ? "expired-due" : record.state,
        attempt_count: record.attempts.length,
        observed_attempt_count: record.attempts.filter((attempt) => attempt.observation_count > 0).length,
        observation_count: record.attempts.reduce((sum, attempt) => sum + attempt.observation_count, 0),
        age_seconds: age,
      });
    }
  }
  return {
    pending: pending.sort((left, right) => right.age_seconds - left.age_seconds),
    consumed_count: consumedCount,
    superseded_count: supersededCount,
    expired_count: expiredCount,
    host_replay_count: hostReplayCount,
    sender_attempt_duplicate_count: senderAttemptDuplicateCount,
  };
}
