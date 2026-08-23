import { useEffect, useEffectEvent, useState } from "react";

import {
  type CreateTestRunPayload,
  type OptionEntry,
  type PlatformRunType,
  fetchOptions,
} from "../../lib/api";
import {
  CHAT_MEMORY_DEFAULT_EMBEDDING,
  CHAT_MEMORY_DEFAULT_MODEL,
  CHAT_MEMORY_DEFAULT_PERSONA,
  CHAT_MEMORY_DEFAULT_PROMPT,
  CHAT_MEMORY_FIXTURES,
  ChatMemoryEvalFields,
  chooseAvailable,
} from "./chat-memory-eval-fields";
import { TEST_RUN_TYPES, type TestCenterCopy } from "./test-center-copy";

export type ChatMemoryEvalFormState = {
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

export function buildTestRunPayload(
  runType: PlatformRunType,
  form: ChatMemoryEvalFormState,
): CreateTestRunPayload {
  if (runType !== "chat_memory_eval") {
    return { run_type: runType };
  }
  return {
    run_type: runType,
    model: form.model,
    prompt_key: form.promptKey,
    persona_key: form.personaKey,
    embedding: form.embedding,
    fixture_key: form.fixtureKey,
    rounds: Math.max(1, Number.parseInt(form.rounds, 10) || 1),
    timeout_seconds: Math.max(1, Number.parseFloat(form.timeoutSeconds) || 180),
    retry_count: Math.max(0, Number.parseInt(form.retryCount, 10) || 0),
    judge_enabled: form.judgeEnabled,
  };
}

function toErrorMessage(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

type Props = {
  copy: TestCenterCopy;
  busy: boolean;
  loading: boolean;
  onCreateRun: (payload: CreateTestRunPayload) => Promise<void>;
  onRefreshRuns: () => Promise<void>;
  onError: (message: string) => void;
};

export function TestRunLauncher(props: Props) {
  const [runType, setRunType] = useState<PlatformRunType>("platform_api_e2e_check");
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [chatModels, setChatModels] = useState<OptionEntry[]>([]);
  const [chatPrompts, setChatPrompts] = useState<OptionEntry[]>([]);
  const [chatPersonas, setChatPersonas] = useState<OptionEntry[]>([]);
  const [chatEmbeddings, setChatEmbeddings] = useState<OptionEntry[]>([]);
  const [evalModel, setEvalModel] = useState(CHAT_MEMORY_DEFAULT_MODEL);
  const [evalPromptKey, setEvalPromptKey] = useState(CHAT_MEMORY_DEFAULT_PROMPT);
  const [evalPersonaKey, setEvalPersonaKey] = useState(CHAT_MEMORY_DEFAULT_PERSONA);
  const [evalEmbedding, setEvalEmbedding] = useState(CHAT_MEMORY_DEFAULT_EMBEDDING);
  const [evalFixtureKey, setEvalFixtureKey] = useState(CHAT_MEMORY_FIXTURES[0]);
  const [evalRounds, setEvalRounds] = useState("3");
  const [evalTimeoutSeconds, setEvalTimeoutSeconds] = useState("180");
  const [evalRetryCount, setEvalRetryCount] = useState("0");
  const [evalJudgeEnabled, setEvalJudgeEnabled] = useState(true);

  const form: ChatMemoryEvalFormState = {
    model: evalModel,
    promptKey: evalPromptKey,
    personaKey: evalPersonaKey,
    embedding: evalEmbedding,
    fixtureKey: evalFixtureKey,
    rounds: evalRounds,
    timeoutSeconds: evalTimeoutSeconds,
    retryCount: evalRetryCount,
    judgeEnabled: evalJudgeEnabled,
  };

  const refreshChatOptions = async () => {
    const payload = await fetchOptions("chat");
    const models = Array.isArray(payload.models) ? payload.models.filter((item) => item.available !== false) : [];
    const prompts = Array.isArray(payload.prompts) ? payload.prompts : [];
    const personas = Array.isArray(payload.personas) ? payload.personas : [];
    const embeddings = Array.isArray(payload.embeddings) ? payload.embeddings.filter((item) => item.available !== false) : [];
    setChatModels(models);
    setChatPrompts(prompts);
    setChatPersonas(personas);
    setChatEmbeddings(embeddings);
    setEvalModel((current) => chooseAvailable(current, models, CHAT_MEMORY_DEFAULT_MODEL));
    setEvalPromptKey((current) => chooseAvailable(current, prompts, payload.defaults?.prompt_key || CHAT_MEMORY_DEFAULT_PROMPT));
    setEvalPersonaKey((current) => chooseAvailable(current, personas, payload.defaults?.persona_key || CHAT_MEMORY_DEFAULT_PERSONA));
    setEvalEmbedding((current) => chooseAvailable(current, embeddings, payload.defaults?.embedding || CHAT_MEMORY_DEFAULT_EMBEDDING));
  };

  const refreshChatOptionsEffect = useEffectEvent(refreshChatOptions);
  const reportError = useEffectEvent(props.onError);

  useEffect(() => {
    let cancelled = false;
    void refreshChatOptionsEffect()
      .catch((exc) => {
        if (!cancelled) {
          reportError(toErrorMessage(exc));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setOptionsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const disabled = props.busy || props.loading || optionsLoading;

  return (
    <div className="card">
      <h3>{props.copy.createRunTitle}</h3>
      <div className="form-grid">
        <label className="field">
          <span>{props.copy.runType}</span>
          <select className="input" value={runType} onChange={(e) => setRunType(e.target.value as PlatformRunType)}>
            {TEST_RUN_TYPES.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        {runType === "chat_memory_eval" ? (
          <ChatMemoryEvalFields
            copy={props.copy}
            chatModels={chatModels}
            chatPrompts={chatPrompts}
            chatPersonas={chatPersonas}
            chatEmbeddings={chatEmbeddings}
            evalModel={evalModel}
            evalPromptKey={evalPromptKey}
            evalPersonaKey={evalPersonaKey}
            evalEmbedding={evalEmbedding}
            evalFixtureKey={evalFixtureKey}
            evalRounds={evalRounds}
            evalTimeoutSeconds={evalTimeoutSeconds}
            evalRetryCount={evalRetryCount}
            evalJudgeEnabled={evalJudgeEnabled}
            setEvalModel={setEvalModel}
            setEvalPromptKey={setEvalPromptKey}
            setEvalPersonaKey={setEvalPersonaKey}
            setEvalEmbedding={setEvalEmbedding}
            setEvalFixtureKey={setEvalFixtureKey}
            setEvalRounds={setEvalRounds}
            setEvalTimeoutSeconds={setEvalTimeoutSeconds}
            setEvalRetryCount={setEvalRetryCount}
            setEvalJudgeEnabled={setEvalJudgeEnabled}
          />
        ) : null}
      </div>
      <div className="toolbar" style={{ marginTop: 10 }}>
        <button
          className="button"
          onClick={() => void props.onCreateRun(buildTestRunPayload(runType, form))}
          disabled={disabled}
        >
          {props.busy ? props.copy.submitting : props.copy.createRun}
        </button>
        <button className="button muted" onClick={() => void props.onRefreshRuns()} disabled={disabled}>
          {props.copy.refreshRuns}
        </button>
      </div>
    </div>
  );
}
