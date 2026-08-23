"use client";

import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";

import {
  OptionEntry,
  PlatformArtifact,
  PlatformRunRecord,
  PlatformRunType,
  cancelTestRun,
  createTestRun,
  fetchOptions,
  getTestRun,
  listRunArtifacts,
  listTestRuns,
  readRunArtifact,
  isAbortError,
} from "../../lib/api";
import { useI18n } from "../../lib/i18n";
import { isCurrentRequest, type RequestIdentity } from "../../lib/request-identity";
import {
  CHAT_MEMORY_DEFAULT_EMBEDDING,
  CHAT_MEMORY_DEFAULT_MODEL,
  CHAT_MEMORY_DEFAULT_PERSONA,
  CHAT_MEMORY_DEFAULT_PROMPT,
  CHAT_MEMORY_FIXTURES,
  ChatMemoryEvalFields,
  chooseAvailable,
} from "./chat-memory-eval-fields";

const COPY = {
  en: {
    kicker: "MVP Module",
    title: "Test Center",
    createRunTitle: "Create Test Run",
    runType: "Run type",
    chatMemoryTitle: "Chat Memory Eval",
    model: "Model",
    prompt: "Prompt",
    persona: "Persona",
    embedding: "Embedding",
    fixture: "Fixture",
    rounds: "Rounds",
    timeoutSeconds: "Timeout (seconds)",
    retryCount: "Retry Count",
    judgeEnabled: "Advisory LLM judge",
    submitting: "Submitting...",
    createRun: "Create Run",
    refreshRuns: "Refresh Runs",
    runsTitle: "Runs",
    selectRun: "Select run",
    refreshSelectedRun: "Refresh Selected Run",
    cancelRun: "Cancel Run",
    artifactsTitle: "Artifacts",
    refreshArtifacts: "Refresh Artifacts",
    noArtifacts: "No artifacts discovered yet.",
    yes: "yes",
    no: "no",
    open: "Open",
    activeArtifact: "Active artifact",
    noActiveArtifact: "none",
    artifactContentPlaceholder: "Artifact content appears here.",
    outputTail: "Run Output Tail",
    statusTitle: "Status",
    errorTitle: "Error",
    createdRun: "Created run",
    cancelRequested: "Cancel requested for",
    selectRunPlaceholder: "Select run",
    id: "ID",
    type: "Type",
    exists: "Exists",
    action: "Action",
  },
  zh: {
    kicker: "MVP 模块",
    title: "测试中心",
    createRunTitle: "创建测试运行",
    runType: "运行类型",
    chatMemoryTitle: "聊天记忆评测",
    model: "模型",
    prompt: "提示词",
    persona: "人设",
    embedding: "Embedding",
    fixture: "对话样本",
    rounds: "轮数",
    timeoutSeconds: "超时（秒）",
    retryCount: "重试次数",
    judgeEnabled: "启用辅助 LLM 评审",
    submitting: "提交中...",
    createRun: "创建运行",
    refreshRuns: "刷新运行列表",
    runsTitle: "运行记录",
    selectRun: "选择运行",
    refreshSelectedRun: "刷新当前运行",
    cancelRun: "取消运行",
    artifactsTitle: "产物",
    refreshArtifacts: "刷新产物",
    noArtifacts: "暂无产物。",
    yes: "是",
    no: "否",
    open: "打开",
    activeArtifact: "当前产物",
    noActiveArtifact: "无",
    artifactContentPlaceholder: "产物内容显示在此。",
    outputTail: "运行输出尾部",
    statusTitle: "状态",
    errorTitle: "错误",
    createdRun: "已创建运行",
    cancelRequested: "已请求取消",
    selectRunPlaceholder: "请选择运行",
    id: "ID",
    type: "类型",
    exists: "存在",
    action: "操作",
  },
} as const;

const RUN_TYPES: PlatformRunType[] = [
  "platform_api_e2e_check",
  "ade_mvp_smoke_e2e_check",
  "chat_memory_eval",
];

function toErrorMessage(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

export default function TestCenterPage() {
  const { locale } = useI18n();
  const copy = COPY[locale];

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const [runs, setRuns] = useState<PlatformRunRecord[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedRun, setSelectedRun] = useState<PlatformRunRecord | null>(null);
  const selectedRunIdRef = useRef("");
  const selectedRunVersionRef = useRef(0);
  const selectedRunAbortControllerRef = useRef<AbortController | null>(null);
  const artifactAbortControllerRef = useRef<AbortController | null>(null);

  const [runType, setRunType] = useState<PlatformRunType>("platform_api_e2e_check");
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

  const [artifacts, setArtifacts] = useState<PlatformArtifact[]>([]);
  const [selectedArtifactId, setSelectedArtifactId] = useState("");
  const [artifactContent, setArtifactContent] = useState("");

  const selectedRunSummary = useMemo(() => {
    if (selectedRun) {
      return selectedRun;
    }
    return runs.find((item) => item.run_id === selectedRunId) || null;
  }, [runs, selectedRun, selectedRunId]);

  const currentRunRequest = (runId: string): RequestIdentity => ({
    resourceId: runId,
    version: selectedRunVersionRef.current,
  });

  const isCurrentRunRequest = (identity: RequestIdentity): boolean =>
    isCurrentRequest(identity, selectedRunIdRef.current, selectedRunVersionRef.current);

  const selectRun = (runId: string) => {
    if (runId !== selectedRunIdRef.current) {
      selectedRunIdRef.current = runId;
      selectedRunVersionRef.current += 1;
      selectedRunAbortControllerRef.current?.abort();
      const hadActiveArtifactRequest = artifactAbortControllerRef.current !== null;
      artifactAbortControllerRef.current?.abort();
      selectedRunAbortControllerRef.current = null;
      artifactAbortControllerRef.current = null;
      if (hadActiveArtifactRequest) {
        setBusy(false);
      }
      setSelectedRun(null);
      setArtifacts([]);
      setSelectedArtifactId("");
      setArtifactContent("");
    }
    setSelectedRunId(runId);
  };

  const refreshRuns = async () => {
    const payload = await listTestRuns();
    const items = Array.isArray(payload.items) ? payload.items : [];
    setRuns(items);

    const currentRunId = selectedRunIdRef.current;
    if (!currentRunId && items.length > 0) {
      selectRun(items[0].run_id);
    } else if (currentRunId && !items.some((item) => item.run_id === currentRunId)) {
      selectRun(items[0]?.run_id || "");
    }
  };

  const refreshSelectedRun = async (runId: string, identity = currentRunRequest(runId)) => {
    if (!runId) {
      return false;
    }
    const controller = new AbortController();
    selectedRunAbortControllerRef.current?.abort();
    selectedRunAbortControllerRef.current = controller;
    const [run, artifactPayload] = await Promise.all([
      getTestRun(runId, { signal: controller.signal }),
      listRunArtifacts(runId, { signal: controller.signal }),
    ]);
    if (!isCurrentRunRequest(identity) || selectedRunAbortControllerRef.current !== controller) {
      return false;
    }
    setSelectedRun(run);
    setArtifacts(artifactPayload.items || []);
    return true;
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

  const refreshRunsEffect = useEffectEvent(refreshRuns);
  const refreshChatOptionsEffect = useEffectEvent(refreshChatOptions);
  const refreshSelectedRunEffect = useEffectEvent(refreshSelectedRun);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError("");
      try {
        await Promise.all([refreshRunsEffect(), refreshChatOptionsEffect()]);
      } catch (exc) {
        if (!cancelled) {
          setError(toErrorMessage(exc));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    void run();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      void refreshRunsEffect().catch(() => undefined);
      if (selectedRunId) {
        void refreshSelectedRunEffect(selectedRunId).catch(() => undefined);
      }
    }, 4000);
    return () => clearInterval(timer);
  }, [selectedRunId]);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }
    const identity = currentRunRequest(selectedRunId);
    void refreshSelectedRunEffect(selectedRunId, identity).catch((exc) => {
      if (isCurrentRunRequest(identity) && !isAbortError(exc)) {
        setError(toErrorMessage(exc));
      }
    });
  }, [selectedRunId]);

  const onCreateRun = async () => {
    setBusy(true);
    setError("");
    setStatus("");
    try {
      const payload = {
        run_type: runType,
        ...(runType === "chat_memory_eval"
          ? {
              model: evalModel,
              prompt_key: evalPromptKey,
              persona_key: evalPersonaKey,
              embedding: evalEmbedding,
              fixture_key: evalFixtureKey,
              rounds: Math.max(1, Number.parseInt(evalRounds, 10) || 1),
              timeout_seconds: Math.max(1, Number.parseFloat(evalTimeoutSeconds) || 180),
              retry_count: Math.max(0, Number.parseInt(evalRetryCount, 10) || 0),
              judge_enabled: evalJudgeEnabled,
            }
          : {}),
      };
      const created = await createTestRun({
        ...payload,
      });
      setStatus(`${copy.createdRun} ${created.run_id}`);
      selectRun(created.run_id);
      await refreshRuns();
      await refreshSelectedRun(created.run_id);
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const onCancelSelected = async () => {
    if (!selectedRunId) {
      return;
    }
    const targetRunId = selectedRunId;
    const identity = currentRunRequest(targetRunId);
    setBusy(true);
    setError("");
    setStatus("");
    try {
      const payload = await cancelTestRun(targetRunId);
      if (!isCurrentRunRequest(identity)) {
        return;
      }
      setStatus(`${copy.cancelRequested} ${payload.run_id}`);
      await refreshSelectedRun(targetRunId, identity);
      await refreshRuns();
    } catch (exc) {
      if (isCurrentRunRequest(identity) && !isAbortError(exc)) {
        setError(toErrorMessage(exc));
      }
    } finally {
      setBusy(false);
    }
  };

  const onReadArtifact = async (artifactId: string) => {
    if (!selectedRunId) {
      return;
    }
    const targetRunId = selectedRunId;
    const identity = currentRunRequest(targetRunId);
    const controller = new AbortController();
    artifactAbortControllerRef.current?.abort();
    artifactAbortControllerRef.current = controller;
    setBusy(true);
    setError("");
    try {
      const payload = await readRunArtifact(targetRunId, artifactId, 250, { signal: controller.signal });
      if (!isCurrentRunRequest(identity) || artifactAbortControllerRef.current !== controller) {
        return;
      }
      setSelectedArtifactId(artifactId);
      setArtifactContent(payload.content || "");
    } catch (exc) {
      if (isCurrentRunRequest(identity) && !isAbortError(exc)) {
        setError(toErrorMessage(exc));
      }
    } finally {
      if (artifactAbortControllerRef.current === controller) {
        artifactAbortControllerRef.current = null;
        setBusy(false);
      }
    }
  };

  return (
    <section>
      <div className="kicker">{copy.kicker}</div>
      <h1 className="section-title">{copy.title}</h1>

      <div className="card">
        <h3>{copy.createRunTitle}</h3>
        <div className="form-grid">
          <label className="field">
            <span>{copy.runType}</span>
            <select className="input" value={runType} onChange={(e) => setRunType(e.target.value as PlatformRunType)}>
              {RUN_TYPES.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          {runType === "chat_memory_eval" ? (
            <ChatMemoryEvalFields
              copy={copy}
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
          <button className="button" onClick={() => void onCreateRun()} disabled={busy || loading}>
            {busy ? copy.submitting : copy.createRun}
          </button>
          <button className="button muted" onClick={() => void refreshRuns()} disabled={busy || loading}>
            {copy.refreshRuns}
          </button>
        </div>
      </div>

      <div className="card-grid" style={{ marginTop: 14 }}>
        <div className="card">
          <h3>{copy.runsTitle}</h3>
          <label className="field">
            <span>{copy.selectRun}</span>
            <select
              className="input"
              value={selectedRunId}
              onChange={(e) => selectRun(e.target.value)}
              disabled={runs.length === 0}
            >
              <option value="">{copy.selectRunPlaceholder}</option>
              {runs.map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {run.run_type} ({run.status})
                </option>
              ))}
            </select>
          </label>

          <div className="toolbar" style={{ marginTop: 10 }}>
            <button className="button muted" onClick={() => void refreshSelectedRun(selectedRunId)} disabled={!selectedRunId}>
              {copy.refreshSelectedRun}
            </button>
            <button className="button" onClick={() => void onCancelSelected()} disabled={!selectedRunId || busy}>
              {copy.cancelRun}
            </button>
          </div>

          <div className="code" style={{ marginTop: 10, minHeight: 180 }}>
            {JSON.stringify(selectedRunSummary, null, 2)}
          </div>
        </div>

        <div className="card">
          <h3>{copy.artifactsTitle}</h3>
          <div className="toolbar" style={{ marginBottom: 10 }}>
            <button
              className="button muted"
              onClick={() => (selectedRunId ? void refreshSelectedRun(selectedRunId) : undefined)}
              disabled={!selectedRunId}
            >
              {copy.refreshArtifacts}
            </button>
          </div>

          {artifacts.length === 0 ? (
            <p className="muted">{copy.noArtifacts}</p>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{copy.id}</th>
                    <th>{copy.type}</th>
                    <th>{copy.exists}</th>
                    <th>{copy.action}</th>
                  </tr>
                </thead>
                <tbody>
                  {artifacts.map((artifact) => (
                    <tr key={artifact.artifact_id}>
                      <td>{artifact.artifact_id}</td>
                      <td>{artifact.type}</td>
                      <td>{artifact.exists ? copy.yes : copy.no}</td>
                      <td>
                        <button className="button" onClick={() => void onReadArtifact(artifact.artifact_id)}>
                          {copy.open}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="muted" style={{ marginTop: 10 }}>
            {copy.activeArtifact}: {selectedArtifactId || copy.noActiveArtifact}
          </p>
          <div className="code" style={{ minHeight: 180 }}>{artifactContent || copy.artifactContentPlaceholder}</div>
        </div>
      </div>

      {selectedRun?.output_tail?.length ? (
        <div className="card" style={{ marginTop: 14 }}>
          <h3>{copy.outputTail}</h3>
          <div className="code" style={{ minHeight: 180 }}>
            {(selectedRun.output_tail || []).join("\n")}
          </div>
        </div>
      ) : null}

      {status ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#bbf7d0" }}>
          <h3>{copy.statusTitle}</h3>
          <p className="muted">{status}</p>
        </div>
      ) : null}

      {error ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#fecaca" }}>
          <h3>{copy.errorTitle}</h3>
          <p className="muted">{error}</p>
        </div>
      ) : null}
    </section>
  );
}
