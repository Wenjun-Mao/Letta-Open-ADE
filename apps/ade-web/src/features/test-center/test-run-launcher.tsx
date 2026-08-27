import { useEffect, useEffectEvent, useState } from "react";

import {
  type CreateTestRunPayload,
  type TestRunType,
} from "./api";
import { fetchOptions, type OptionEntry } from "@/features/model-catalog/api";
import {
  ChatMemoryEvalFields,
} from "./chat-memory-eval-fields";
import {
  DEFAULT_CHAT_MEMORY_EVALUATION_FORM,
  reconcileChatMemoryEvaluationForm,
  resolveChatMemoryEvaluationLaunchState,
  type ChatMemoryEvaluationForm,
} from "./chat-memory-evaluation-helpers";
import { TEST_RUN_TYPES, type TestCenterCopy } from "./test-center-copy";

export type ChatMemoryEvalFormState = ChatMemoryEvaluationForm;

export function buildTestRunPayload(
  runType: TestRunType,
  form: ChatMemoryEvalFormState,
): CreateTestRunPayload {
  if (runType !== "chat_memory_eval") {
    return { run_type: runType };
  }
  const rounds = Number.parseInt(form.rounds, 10);
  const timeoutSeconds = Number.parseFloat(form.timeoutSeconds);
  const retryCount = Number.parseInt(form.retryCount, 10);
  return {
    run_type: runType,
    model: form.model,
    prompt_key: form.promptKey,
    persona_key: form.personaKey,
    embedding: form.embedding,
    fixture_key: form.fixtureKey,
    rounds: Number.isInteger(rounds) ? Math.min(100, Math.max(1, rounds)) : 1,
    timeout_seconds: Number.isFinite(timeoutSeconds) && timeoutSeconds > 0 ? Math.min(600, timeoutSeconds) : 180,
    retry_count: Number.isInteger(retryCount) ? Math.min(5, Math.max(0, retryCount)) : 0,
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
  preset: ChatMemoryEvaluationForm | null;
  onCreateRun: (payload: CreateTestRunPayload) => Promise<void>;
  onRefreshRuns: () => Promise<void>;
  onError: (message: string) => void;
};

export function TestRunLauncher(props: Props) {
  const [runType, setRunType] = useState<TestRunType>("ade_api_e2e_check");
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [chatModels, setChatModels] = useState<OptionEntry[]>([]);
  const [chatPrompts, setChatPrompts] = useState<OptionEntry[]>([]);
  const [chatPersonas, setChatPersonas] = useState<OptionEntry[]>([]);
  const [chatEmbeddings, setChatEmbeddings] = useState<OptionEntry[]>([]);
  const [evalModel, setEvalModel] = useState(DEFAULT_CHAT_MEMORY_EVALUATION_FORM.model);
  const [evalPromptKey, setEvalPromptKey] = useState(DEFAULT_CHAT_MEMORY_EVALUATION_FORM.promptKey);
  const [evalPersonaKey, setEvalPersonaKey] = useState(DEFAULT_CHAT_MEMORY_EVALUATION_FORM.personaKey);
  const [evalEmbedding, setEvalEmbedding] = useState(DEFAULT_CHAT_MEMORY_EVALUATION_FORM.embedding);
  const [evalFixtureKey, setEvalFixtureKey] = useState(DEFAULT_CHAT_MEMORY_EVALUATION_FORM.fixtureKey);
  const [evalRounds, setEvalRounds] = useState(DEFAULT_CHAT_MEMORY_EVALUATION_FORM.rounds);
  const [evalTimeoutSeconds, setEvalTimeoutSeconds] = useState(DEFAULT_CHAT_MEMORY_EVALUATION_FORM.timeoutSeconds);
  const [evalRetryCount, setEvalRetryCount] = useState(DEFAULT_CHAT_MEMORY_EVALUATION_FORM.retryCount);
  const [evalJudgeEnabled, setEvalJudgeEnabled] = useState(DEFAULT_CHAT_MEMORY_EVALUATION_FORM.judgeEnabled);

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

  const applyForm = (nextForm: ChatMemoryEvaluationForm) => {
    setEvalModel(nextForm.model);
    setEvalPromptKey(nextForm.promptKey);
    setEvalPersonaKey(nextForm.personaKey);
    setEvalEmbedding(nextForm.embedding);
    setEvalFixtureKey(nextForm.fixtureKey);
    setEvalRounds(nextForm.rounds);
    setEvalTimeoutSeconds(nextForm.timeoutSeconds);
    setEvalRetryCount(nextForm.retryCount);
    setEvalJudgeEnabled(nextForm.judgeEnabled);
  };

  const refreshChatOptions = async (requestedForm: ChatMemoryEvaluationForm) => {
    const payload = await fetchOptions("chat");
    const models = Array.isArray(payload.models) ? payload.models.filter((item) => item.available !== false) : [];
    const prompts = Array.isArray(payload.prompts) ? payload.prompts : [];
    const personas = Array.isArray(payload.personas) ? payload.personas : [];
    const embeddings = Array.isArray(payload.embeddings) ? payload.embeddings.filter((item) => item.available !== false) : [];
    setChatModels(models);
    setChatPrompts(prompts);
    setChatPersonas(personas);
    setChatEmbeddings(embeddings);
    applyForm(reconcileChatMemoryEvaluationForm(requestedForm, {
      models,
      prompts,
      personas,
      embeddings,
      defaults: payload.defaults,
    }));
  };

  const refreshChatOptionsEffect = useEffectEvent(refreshChatOptions);
  const reportError = useEffectEvent(props.onError);

  useEffect(() => {
    if (!props.preset) {
      return;
    }
    setRunType("chat_memory_eval");
    applyForm(props.preset);
  }, [props.preset]);

  useEffect(() => {
    let cancelled = false;
    const launchState = resolveChatMemoryEvaluationLaunchState(
      typeof window === "undefined" ? "" : window.location.search,
    );
    setRunType(launchState.runType);
    applyForm(launchState.form);
    void refreshChatOptionsEffect(launchState.form)
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
          <select className="input" value={runType} onChange={(e) => setRunType(e.target.value as TestRunType)}>
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
