import type { OptionEntry } from "@/features/model-catalog/api";

import type {
  ChatMemoryEvaluationConfig,
  ChatMemoryEvaluationMetrics,
  EvaluationListItem,
  TestRunType,
} from "./api";

export const CHAT_MEMORY_DEFAULT_MODEL = "openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8";
export const CHAT_MEMORY_DEFAULT_PROMPT = "chat_v20260516";
export const CHAT_MEMORY_DEFAULT_PERSONA = "chat_linxiaotang";
export const CHAT_MEMORY_DEFAULT_EMBEDDING = "letta/letta-free";
export const CHAT_MEMORY_FIXTURES = ["recent_user_chat_turns"];

export type ChatMemoryEvaluationForm = {
  model: string;
  promptKey: string;
  personaKey: string;
  embedding: string;
  fixtureKey: string;
  rounds: string;
  timeoutSeconds: string;
  retryCount: string;
  judgeEnabled: boolean;
};

export const DEFAULT_CHAT_MEMORY_EVALUATION_FORM: ChatMemoryEvaluationForm = {
  model: CHAT_MEMORY_DEFAULT_MODEL,
  promptKey: CHAT_MEMORY_DEFAULT_PROMPT,
  personaKey: CHAT_MEMORY_DEFAULT_PERSONA,
  embedding: CHAT_MEMORY_DEFAULT_EMBEDDING,
  fixtureKey: CHAT_MEMORY_FIXTURES[0],
  rounds: "3",
  timeoutSeconds: "180",
  retryCount: "0",
  judgeEnabled: true,
};

type ChatMemoryOptionSet = {
  models: OptionEntry[];
  prompts: OptionEntry[];
  personas: OptionEntry[];
  embeddings: OptionEntry[];
  defaults?: {
    model?: string;
    prompt_key?: string;
    persona_key?: string;
    embedding?: string;
  };
};

const VALID_RUN_TYPES = new Set<TestRunType>([
  "ade_api_e2e_check",
  "ade_mvp_smoke_e2e_check",
  "chat_memory_eval",
]);

const TERMINAL_EVALUATION_STATUSES = new Set([
  "cancelled",
  "canceled",
  "completed",
  "error",
  "failed",
  "finished",
  "interrupted",
  "passed",
  "succeeded",
]);

function queryString(params: URLSearchParams, key: string, fallback: string): string {
  return (params.get(key) || "").trim() || fallback;
}

function queryInteger(params: URLSearchParams, key: string, fallback: string, min: number, max: number): string {
  const value = Number.parseInt((params.get(key) || "").trim(), 10);
  return Number.isInteger(value) && value >= min && value <= max ? String(value) : fallback;
}

function queryNumber(params: URLSearchParams, key: string, fallback: string, min: number, max: number): string {
  const value = Number.parseFloat((params.get(key) || "").trim());
  return Number.isFinite(value) && value >= min && value <= max ? String(value) : fallback;
}

function queryBoolean(params: URLSearchParams, key: string, fallback: boolean): boolean {
  const value = (params.get(key) || "").trim().toLowerCase();
  if (value === "true") {
    return true;
  }
  if (value === "false") {
    return false;
  }
  return fallback;
}

export function resolveChatMemoryEvaluationLaunchState(search: string): {
  runType: TestRunType;
  form: ChatMemoryEvaluationForm;
} {
  const params = new URLSearchParams(search);
  const requestedRunType = (params.get("runType") || "").trim() as TestRunType;
  const runType = VALID_RUN_TYPES.has(requestedRunType) ? requestedRunType : "ade_api_e2e_check";

  return {
    runType,
    form: {
      model: queryString(params, "model", DEFAULT_CHAT_MEMORY_EVALUATION_FORM.model),
      promptKey: queryString(params, "promptKey", DEFAULT_CHAT_MEMORY_EVALUATION_FORM.promptKey),
      personaKey: queryString(params, "personaKey", DEFAULT_CHAT_MEMORY_EVALUATION_FORM.personaKey),
      embedding: queryString(params, "embedding", DEFAULT_CHAT_MEMORY_EVALUATION_FORM.embedding),
      fixtureKey: queryString(params, "fixtureKey", DEFAULT_CHAT_MEMORY_EVALUATION_FORM.fixtureKey),
      rounds: queryInteger(params, "rounds", DEFAULT_CHAT_MEMORY_EVALUATION_FORM.rounds, 1, 100),
      timeoutSeconds: queryNumber(params, "timeoutSeconds", DEFAULT_CHAT_MEMORY_EVALUATION_FORM.timeoutSeconds, 1, 600),
      retryCount: queryInteger(params, "retryCount", DEFAULT_CHAT_MEMORY_EVALUATION_FORM.retryCount, 0, 5),
      judgeEnabled: queryBoolean(params, "judgeEnabled", DEFAULT_CHAT_MEMORY_EVALUATION_FORM.judgeEnabled),
    },
  };
}

export function chooseAvailableOption(current: string, options: OptionEntry[], preferred: string): string {
  const keys = new Set(options.map((item) => String(item.key || "").trim()).filter(Boolean));
  if (current && keys.has(current)) {
    return current;
  }
  if (preferred && keys.has(preferred)) {
    return preferred;
  }
  return options[0]?.key || current || preferred;
}

export function reconcileChatMemoryEvaluationForm(
  current: ChatMemoryEvaluationForm,
  options: ChatMemoryOptionSet,
): ChatMemoryEvaluationForm {
  return {
    ...current,
    model: chooseAvailableOption(current.model, options.models, options.defaults?.model || CHAT_MEMORY_DEFAULT_MODEL),
    promptKey: chooseAvailableOption(
      current.promptKey,
      options.prompts,
      options.defaults?.prompt_key || CHAT_MEMORY_DEFAULT_PROMPT,
    ),
    personaKey: chooseAvailableOption(
      current.personaKey,
      options.personas,
      options.defaults?.persona_key || CHAT_MEMORY_DEFAULT_PERSONA,
    ),
    embedding: chooseAvailableOption(
      current.embedding,
      options.embeddings,
      options.defaults?.embedding || CHAT_MEMORY_DEFAULT_EMBEDDING,
    ),
    fixtureKey: CHAT_MEMORY_FIXTURES.includes(current.fixtureKey)
      ? current.fixtureKey
      : DEFAULT_CHAT_MEMORY_EVALUATION_FORM.fixtureKey,
  };
}

export function toChatMemoryEvaluationForm(config: ChatMemoryEvaluationConfig): ChatMemoryEvaluationForm {
  return {
    model: config.model || DEFAULT_CHAT_MEMORY_EVALUATION_FORM.model,
    promptKey: config.prompt_key || DEFAULT_CHAT_MEMORY_EVALUATION_FORM.promptKey,
    personaKey: config.persona_key || DEFAULT_CHAT_MEMORY_EVALUATION_FORM.personaKey,
    embedding: config.embedding || DEFAULT_CHAT_MEMORY_EVALUATION_FORM.embedding,
    fixtureKey: CHAT_MEMORY_FIXTURES.includes(config.fixture_key)
      ? config.fixture_key
      : DEFAULT_CHAT_MEMORY_EVALUATION_FORM.fixtureKey,
    rounds: String(config.rounds || DEFAULT_CHAT_MEMORY_EVALUATION_FORM.rounds),
    timeoutSeconds: String(config.timeout_seconds || DEFAULT_CHAT_MEMORY_EVALUATION_FORM.timeoutSeconds),
    retryCount: String(config.retry_count ?? DEFAULT_CHAT_MEMORY_EVALUATION_FORM.retryCount),
    judgeEnabled: config.judge_enabled,
  };
}

export function buildPromptCenterEvaluationHref(
  target: "prompt" | "persona",
  config: Pick<ChatMemoryEvaluationConfig, "prompt_key" | "persona_key">,
): string {
  const params = new URLSearchParams({
    tab: target === "prompt" ? "prompts" : "personas",
    scenario: "chat",
    key: target === "prompt" ? config.prompt_key : config.persona_key,
  });
  return `/prompt-center?${params.toString()}`;
}

export function formatPassRate(passRate: number): string {
  const normalized = Number.isFinite(passRate) ? Math.min(1, Math.max(0, passRate)) : 0;
  return `${Math.round(normalized * 100)}%`;
}

export function formatElapsedSeconds(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return "-";
  }
  return `${seconds.toFixed(seconds >= 10 ? 1 : 2)}s`;
}

export function isEvaluationRunning(evaluation: Pick<EvaluationListItem, "run_status" | "ready">): boolean {
  const status = evaluation.run_status.trim().toLowerCase();
  if (TERMINAL_EVALUATION_STATUSES.has(status)) {
    return false;
  }
  return !evaluation.ready || ["canceling", "cancelling", "in_progress", "pending", "queued", "running", "starting"].includes(status);
}

export function metricFraction(numerator: number, denominator: number): string {
  return `${numerator}/${denominator}`;
}

export type MemoryLineDiff = {
  removed: string[];
  added: string[];
};

function memoryLines(value: string): string[] {
  return value
    .replace(/\r\n?/g, "\n")
    .split("\n")
    .map((line) => line.trimEnd())
    .filter((line) => line.trim().length > 0);
}

function unmatchedLines(source: string[], target: string[]): string[] {
  const remaining = new Map<string, number>();
  target.forEach((line) => remaining.set(line, (remaining.get(line) || 0) + 1));

  return source.filter((line) => {
    const count = remaining.get(line) || 0;
    if (count === 0) {
      return true;
    }
    remaining.set(line, count - 1);
    return false;
  });
}

export function diffMemoryLines(before: string, after: string): MemoryLineDiff {
  const beforeLines = memoryLines(before);
  const afterLines = memoryLines(after);
  return {
    removed: unmatchedLines(beforeLines, afterLines),
    added: unmatchedLines(afterLines, beforeLines),
  };
}

export type DeterministicFailureSummary = {
  forbiddenHits: string[];
  missingExpectedFacts: string[];
  memoryDidNotChange: boolean;
  expectedFactsFailed: boolean;
};

function scoreStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => {
    if (typeof item === "string" && item.trim()) {
      return [item.trim()];
    }
    if (item && typeof item === "object") {
      const record = item as Record<string, unknown>;
      const label = record.label || record.key;
      if (typeof label === "string" && label.trim()) {
        return [label.trim()];
      }
    }
    return [];
  });
}

export function summarizeDeterministicFailures(
  score: Record<string, unknown>,
): DeterministicFailureSummary {
  return {
    forbiddenHits: scoreStringList(score.forbidden_hits),
    missingExpectedFacts: scoreStringList(score.missing_expected_facts),
    memoryDidNotChange: score.human_memory_changed === false,
    expectedFactsFailed: score.expected_facts_passed === false,
  };
}
