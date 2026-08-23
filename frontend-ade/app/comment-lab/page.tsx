"use client";

import { useEffect, useEffectEvent, useState } from "react";

import { CommentingTaskShape, OptionEntry, fetchOptions, generateComment } from "../../lib/api";
import {
  formatModelOptionLabel,
  parseIntegerInRange,
  parseNonNegativeInteger,
  parseOptionalPositiveInteger,
  parsePositiveNumber,
  parseTemperature,
  parseTopP,
  samplingDefaultString,
} from "../../lib/generation-controls";
import { useI18n } from "../../lib/i18n";
import {
  asIntegerString as asIntString,
  asRecord as asObject,
  formatLocalTimestamp as formatTimestamp,
  prettyJson as stringifyPretty,
} from "../../lib/json-display";

import { COMMENT_LAB_COPY as COPY } from "./copy";
import {
  formatRawReplyForHuman,
  formatRawRequestForHuman,
  previewText,
} from "./provider-payload-formatters";

function toErrorMessage(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

function pickSelectedKey(current: string, options: OptionEntry[], fallback: string): string {
  if (current && options.some((option) => option.key === current)) {
    return current;
  }
  const preferred = options.find((option) => option.is_default)?.key || "";
  return preferred || options[0]?.key || fallback;
}

export default function CommentLabPage() {
  const { locale } = useI18n();
  const copy = COPY[locale];

  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const [models, setModels] = useState<OptionEntry[]>([]);
  const [prompts, setPrompts] = useState<OptionEntry[]>([]);
  const [personas, setPersonas] = useState<OptionEntry[]>([]);

  const [model, setModel] = useState("");
  const [promptKey, setPromptKey] = useState("");
  const [personaKey, setPersonaKey] = useState("");
  const [maxTokens, setMaxTokens] = useState("0");
  const [timeoutSeconds, setTimeoutSeconds] = useState("180");
  const [retryCount, setRetryCount] = useState("0");
  const [taskShape, setTaskShape] = useState<CommentingTaskShape>("classic");
  const [cachePrompt, setCachePrompt] = useState(false);
  const [enableThinking, setEnableThinking] = useState(false);
  const [temperature, setTemperature] = useState("0.6");
  const [topP, setTopP] = useState("1");
  const [topK, setTopK] = useState("");

  const [userInput, setUserInput] = useState("");
  const [output, setOutput] = useState("");
  const [provider, setProvider] = useState("");
  const [modelUsed, setModelUsed] = useState("");
  const [maxTokensUsed, setMaxTokensUsed] = useState("");
  const [timeoutUsed, setTimeoutUsed] = useState("");
  const [taskShapeUsed, setTaskShapeUsed] = useState("");
  const [cachePromptUsed, setCachePromptUsed] = useState("");
  const [enableThinkingUsed, setEnableThinkingUsed] = useState("");
  const [temperatureUsed, setTemperatureUsed] = useState("");
  const [topPUsed, setTopPUsed] = useState("");
  const [topKUsed, setTopKUsed] = useState("");
  const [usagePromptTokens, setUsagePromptTokens] = useState("");
  const [usageCompletionTokens, setUsageCompletionTokens] = useState("");
  const [usageTotalTokens, setUsageTotalTokens] = useState("");
  const [usageReasoningTokens, setUsageReasoningTokens] = useState("");
  const [responseSeconds, setResponseSeconds] = useState("");
  const [receivedAt, setReceivedAt] = useState("");
  const [selectedAttempt, setSelectedAttempt] = useState("");
  const [finishReason, setFinishReason] = useState("");
  const [rawRequest, setRawRequest] = useState("");
  const [rawRequestReadable, setRawRequestReadable] = useState("");
  const [rawReply, setRawReply] = useState("");
  const [rawReplyReadable, setRawReplyReadable] = useState("");
  const [popOutCard, setPopOutCard] = useState<{ title: string; readable: string; raw: string } | null>(null);

  const loadOptions = async (forceRefresh = false) => {
    setLoadingOptions(true);
    setError("");

    try {
      const payload = await fetchOptions("comment", forceRefresh ? { refresh: true } : undefined);
      const nextModels = Array.isArray(payload.models) ? payload.models : [];
      const nextPrompts = Array.isArray(payload.prompts) ? payload.prompts : [];
      const nextPersonas = Array.isArray(payload.personas) ? payload.personas : [];

      setModels(nextModels);
      setPrompts(nextPrompts);
      setPersonas(nextPersonas);

      setModel((current) => (current && nextModels.some((option) => option.key === current) ? current : ""));
      const params = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
      const requestedPromptKey = (params?.get("promptKey") || "").trim();
      const requestedPersonaKey = (params?.get("personaKey") || "").trim();

      setPromptKey((current) => {
        if (current && nextPrompts.some((option) => option.key === current)) {
          return current;
        }
        if (requestedPromptKey && nextPrompts.some((option) => option.key === requestedPromptKey)) {
          return requestedPromptKey;
        }
        return pickSelectedKey("", nextPrompts, payload.defaults.prompt_key || "");
      });
      setPersonaKey((current) => {
        if (current && nextPersonas.some((option) => option.key === current)) {
          return current;
        }
        if (requestedPersonaKey && nextPersonas.some((option) => option.key === requestedPersonaKey)) {
          return requestedPersonaKey;
        }
        return pickSelectedKey("", nextPersonas, payload.defaults.persona_key || "");
      });
      if (payload.commenting) {
        setMaxTokens(`${payload.commenting.max_tokens}`);
        setTimeoutSeconds(`${payload.commenting.timeout_seconds}`);
        setTaskShape(payload.commenting.task_shape);
        setCachePrompt(Boolean(payload.commenting.cache_prompt));
        setTemperature(`${payload.commenting.temperature}`);
        setTopP(`${payload.commenting.top_p}`);
        setTopK(payload.commenting.top_k === null || payload.commenting.top_k === undefined ? "" : `${payload.commenting.top_k}`);
      }

      setStatus(copy.optionsRefreshed);
    } catch (exc) {
      setError(`${copy.loadingError}: ${toErrorMessage(exc)}`);
    } finally {
      setLoadingOptions(false);
    }
  };

  const loadInitialOptions = useEffectEvent(loadOptions);

  useEffect(() => {
    void loadInitialOptions();
  }, []);

  useEffect(() => {
    const selected = models.find((option) => option.key === model);
    if (!selected) {
      return;
    }
    const nextTemperature = samplingDefaultString(selected, "comment_lab", "temperature");
    const nextTopP = samplingDefaultString(selected, "comment_lab", "top_p");
    const nextTopK = samplingDefaultString(selected, "comment_lab", "top_k");
    if (nextTemperature !== null) {
      setTemperature(nextTemperature);
    }
    if (nextTopP !== null) {
      setTopP(nextTopP);
    }
    setTopK(nextTopK ?? "");
    setEnableThinking(Boolean(selected.thinking_default_enabled));
  }, [model, models]);

  const onGenerate = async () => {
    setError("");
    setStatus("");
    setPopOutCard(null);
    setResponseSeconds("");

    if (!model || !promptKey || !personaKey) {
      setError(copy.selectRequired);
      return;
    }

    if (!userInput.trim()) {
      setError(copy.inputRequired);
      return;
    }

    const parsedMaxTokens = parseNonNegativeInteger(maxTokens);
    if (parsedMaxTokens === null) {
      setError(copy.invalidMaxTokens);
      return;
    }

    const parsedTimeoutSeconds = parsePositiveNumber(timeoutSeconds);
    if (parsedTimeoutSeconds === null) {
      setError(copy.invalidTimeout);
      return;
    }
    const parsedRetryCount = parseIntegerInRange(retryCount, 0, 5);
    if (parsedRetryCount === null) {
      setError(copy.invalidRetryCount);
      return;
    }
    const parsedTemperature = parseTemperature(temperature);
    if (parsedTemperature === null) {
      setError(copy.invalidTemperature);
      return;
    }
    const parsedTopP = parseTopP(topP);
    if (parsedTopP === null) {
      setError(copy.invalidTopP);
      return;
    }
    const parsedTopK = parseOptionalPositiveInteger(topK);
    if (parsedTopK === null) {
      setError(copy.invalidTopK);
      return;
    }

    setSubmitting(true);
    const startedAtMs = performance.now();
    try {
      const payload = await generateComment({
        input: userInput,
        prompt_key: promptKey,
        persona_key: personaKey,
        model_key: model,
        max_tokens: parsedMaxTokens,
        timeout_seconds: parsedTimeoutSeconds,
        retry_count: parsedRetryCount,
        task_shape: taskShape,
        cache_prompt: cachePrompt,
        enable_thinking: enableThinking,
        temperature: parsedTemperature,
        top_p: parsedTopP,
        top_k: parsedTopK,
      });
      setOutput(payload.content || "");
      setProvider(payload.provider || "");
      setModelUsed(payload.provider_model_id || payload.model || "");
      setMaxTokensUsed(`${payload.max_tokens}`);
      setTimeoutUsed(`${payload.timeout_seconds}`);
      setTaskShapeUsed(payload.task_shape || "");
      setCachePromptUsed(payload.cache_prompt ? "true" : "false");
      setEnableThinkingUsed(payload.enable_thinking ? "true" : "false");
      setTemperatureUsed(`${payload.temperature}`);
      setTopPUsed(`${payload.top_p}`);
      setTopKUsed(payload.top_k === null || payload.top_k === undefined ? "" : `${payload.top_k}`);
      const usage = asObject(payload.usage);
      const completionTokensDetails = asObject(usage.completion_tokens_details);
      setUsagePromptTokens(asIntString(usage.prompt_tokens));
      setUsageCompletionTokens(asIntString(usage.completion_tokens));
      setUsageTotalTokens(asIntString(usage.total_tokens));
      setUsageReasoningTokens(asIntString(completionTokensDetails.reasoning_tokens));
      setResponseSeconds((Math.max(0, performance.now() - startedAtMs) / 1000).toFixed(2));
      setReceivedAt(payload.received_at || "");
      setSelectedAttempt(payload.selected_attempt || "");
      setFinishReason(payload.finish_reason || "");
      setRawRequest(stringifyPretty(payload.raw_request || {}));
      setRawRequestReadable(formatRawRequestForHuman(payload.raw_request || {}));
      setRawReply(stringifyPretty(payload.raw_reply || {}));
      setRawReplyReadable(formatRawReplyForHuman(payload.raw_reply || {}));
      setStatus(`${copy.modelUsed}: ${payload.provider_model_id || payload.model}`);
    } catch (exc) {
      setResponseSeconds("");
      setError(`${copy.generateError}: ${toErrorMessage(exc)}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section>
      <div className="kicker">{copy.kicker}</div>
      <h1 className="section-title">{copy.title}</h1>
      <p className="muted" style={{ maxWidth: 860 }}>
        {copy.intro}
      </p>

      {status ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#86efac" }}>
          <p>{status}</p>
        </div>
      ) : null}

      {error ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#fecaca" }}>
          <p>{error}</p>
        </div>
      ) : null}

      <div className="studio-layout" style={{ marginTop: 14 }}>
        <div className="card studio-panel">
          <h3>{copy.tuningTitle}</h3>
          <div className="form-grid" style={{ marginTop: 10 }}>
            <label className="field">
              <span>{copy.model}</span>
              <select
                className="input"
                value={model}
                onChange={(event) => setModel(event.target.value)}
                disabled={loadingOptions || submitting}
              >
                <option value="">{copy.selectModel}</option>
                {models.map((item) => (
                  <option key={item.key} value={item.key}>
                    {formatModelOptionLabel(item)}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>{copy.prompt}</span>
              <select
                className="input"
                value={promptKey}
                onChange={(event) => setPromptKey(event.target.value)}
                disabled={loadingOptions || submitting}
              >
                {prompts.map((item) => (
                  <option key={item.key} value={item.key}>
                    {formatModelOptionLabel(item)}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>{copy.persona}</span>
              <select
                className="input"
                value={personaKey}
                onChange={(event) => setPersonaKey(event.target.value)}
                disabled={loadingOptions || submitting}
              >
                {personas.map((item) => (
                  <option key={item.key} value={item.key}>
                    {formatModelOptionLabel(item)}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>{copy.maxTokens}</span>
              <input
                className="input"
                type="number"
                min={0}
                max={8192}
                step={1}
                value={maxTokens}
                onChange={(event) => setMaxTokens(event.target.value)}
                disabled={submitting}
              />
              <span className="muted" style={{ fontSize: 12 }}>
                {copy.maxTokensHint}
              </span>
            </label>

            <label className="field">
              <span>{copy.timeoutSeconds}</span>
              <input
                className="input"
                type="number"
                min={5}
                max={600}
                step={1}
                value={timeoutSeconds}
                onChange={(event) => setTimeoutSeconds(event.target.value)}
                disabled={submitting}
              />
            </label>

            <label className="field">
              <span>{copy.retryCount}</span>
              <input
                className="input"
                type="number"
                min={0}
                max={5}
                step={1}
                value={retryCount}
                onChange={(event) => setRetryCount(event.target.value)}
                disabled={submitting}
              />
              <span className="muted" style={{ fontSize: 12 }}>
                {copy.retryCountHint}
              </span>
            </label>

            <label className="field">
              <span>{copy.taskShape}</span>
              <select
                className="input"
                value={taskShape}
                onChange={(event) => setTaskShape(event.target.value as CommentingTaskShape)}
                disabled={submitting}
              >
                <option value="classic">{copy.taskShapeClassic}</option>
                <option value="all_in_system">{copy.taskShapeAllInSystem}</option>
                <option value="structured_output">{copy.taskShapeStructuredOutput}</option>
              </select>
            </label>

            <label className="field">
              <span>{copy.temperature}</span>
              <input
                className="input"
                type="number"
                min={0}
                max={2}
                step={0.1}
                value={temperature}
                onChange={(event) => setTemperature(event.target.value)}
                disabled={submitting}
              />
            </label>

            <label className="field">
              <span>{copy.topP}</span>
              <input
                className="input"
                type="number"
                min={0.01}
                max={1}
                step={0.05}
                value={topP}
                onChange={(event) => setTopP(event.target.value)}
                disabled={submitting}
              />
            </label>

            <label className="field">
              <span>{copy.topK}</span>
              <input
                className="input"
                type="number"
                min={1}
                step={1}
                value={topK}
                onChange={(event) => setTopK(event.target.value)}
                placeholder="64"
                disabled={submitting}
              />
            </label>

            <label className="field">
              <span>{copy.cachePrompt}</span>
              <label className="muted" style={{ fontSize: 12 }}>
                <input
                  type="checkbox"
                  checked={cachePrompt}
                  onChange={(event) => setCachePrompt(event.target.checked)}
                  disabled={submitting}
                  style={{ marginRight: 8 }}
                />
                {copy.cachePromptHint}
              </label>
            </label>

            <label className="field">
              <span>{copy.enableThinking}</span>
              <label className="muted" style={{ fontSize: 12 }}>
                <input
                  type="checkbox"
                  checked={enableThinking}
                  onChange={(event) => setEnableThinking(event.target.checked)}
                  disabled={submitting}
                  style={{ marginRight: 8 }}
                />
                {copy.enableThinkingHint}
              </label>
            </label>
          </div>

          <div className="toolbar" style={{ marginTop: 12 }}>
            <button className="button" onClick={() => void onGenerate()} disabled={loadingOptions || submitting}>
              {submitting ? copy.generating : copy.generate}
            </button>
            <button className="button muted" onClick={() => void loadOptions(true)} disabled={submitting}>
              {copy.refreshOptions}
            </button>
          </div>
          <p className="muted" style={{ marginTop: 10, fontSize: 12 }}>
            {copy.defaultsFromEnv}
          </p>
        </div>

        <div className="card studio-panel">
          <h3>{copy.mainContentTitle}</h3>
          <label className="field" style={{ marginTop: 10 }}>
            <span>{copy.userInput}</span>
            <textarea
              className="input"
              rows={12}
              style={{ minHeight: 240 }}
              value={userInput}
              onChange={(event) => setUserInput(event.target.value)}
              placeholder={copy.userInputPlaceholder}
              disabled={submitting}
            />
          </label>

          <hr className="studio-divider" />

          <h3>{copy.outputTitle}</h3>
          <div
            style={{
              marginTop: 10,
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 10,
            }}
          >
            <div className="card" style={{ margin: 0, padding: "10px 12px" }}>
              <div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>
                {copy.runtimeMetaTitle}
              </div>
              <div className="list" style={{ marginTop: 6 }}>
                <div>
                  {copy.provider}: {provider || "-"}
                </div>
                <div>
                  {copy.modelUsed}: {modelUsed || "-"}
                </div>
                <div>
                  {copy.taskShapeUsed}: {taskShapeUsed || "-"}
                </div>
                <div>
                  {copy.cachePromptUsed}: {cachePromptUsed || "-"}
                </div>
                <div>
                  {copy.enableThinkingUsed}: {enableThinkingUsed || "-"}
                </div>
                <div>
                  {copy.temperatureUsed}: {temperatureUsed || "-"}
                </div>
                <div>
                  {copy.topPUsed}: {topPUsed || "-"}
                </div>
                <div>
                  {copy.topKUsed}: {topKUsed || "-"}
                </div>
                <div>
                  {copy.maxTokensUsed}: {maxTokensUsed || "-"}
                </div>
                <div>
                  {copy.timeoutUsed}: {timeoutUsed || "-"}
                </div>
              </div>
            </div>

            <div className="card" style={{ margin: 0, padding: "10px 12px" }}>
              <div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>
                {copy.timingMetaTitle}
              </div>
              <div className="list" style={{ marginTop: 6 }}>
                <div>
                  {copy.responseSeconds}: {responseSeconds || "-"}
                </div>
                <div>
                  {copy.receivedAt}: {receivedAt ? formatTimestamp(receivedAt) : "-"}
                </div>
              </div>
            </div>

            <div className="card" style={{ margin: 0, padding: "10px 12px" }}>
              <div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>
                {copy.tokenMetaTitle}
              </div>
              <div className="list" style={{ marginTop: 6 }}>
                <div>
                  {copy.usagePromptTokens}: {usagePromptTokens || "-"}
                </div>
                <div>
                  {copy.usageCompletionTokens}: {usageCompletionTokens || "-"}
                </div>
                <div>
                  {copy.usageReasoningTokens}: {usageReasoningTokens || "-"}
                </div>
                <div>
                  {copy.usageTotalTokens}: {usageTotalTokens || "-"}
                </div>
              </div>
            </div>
          </div>
          <div className="code" style={{ marginTop: 10, minHeight: 280 }}>
            {output || copy.outputPlaceholder}
          </div>
        </div>

        <div className="card studio-panel">
          <h3>{copy.innerWorksTitle}</h3>
          <div className="list" style={{ marginTop: 0 }}>
            <div>
              {copy.selectedAttempt}: {selectedAttempt || "-"}
            </div>
            <div>
              {copy.finishReason}: {finishReason || "-"}
            </div>
          </div>

          <div className="toolbar" style={{ marginTop: 14, justifyContent: "space-between" }}>
            <h3 style={{ margin: 0 }}>{copy.rawRequestTitle}</h3>
            <button
              className="button muted"
              onClick={() =>
                setPopOutCard({
                  title: copy.rawRequestTitle,
                  readable: rawRequestReadable,
                  raw: rawRequest,
                })
              }
              disabled={!rawRequest}
            >
              {copy.popOutCard}
            </button>
          </div>
          <div className="code" style={{ marginTop: 10, minHeight: 150, maxHeight: 220, overflowY: "auto" }}>
            {previewText(rawRequestReadable) || copy.rawRequestPlaceholder}
          </div>

          <div className="toolbar" style={{ marginTop: 14, justifyContent: "space-between" }}>
            <h3 style={{ margin: 0 }}>{copy.rawReplyTitle}</h3>
            <button
              className="button muted"
              onClick={() =>
                setPopOutCard({
                  title: copy.rawReplyTitle,
                  readable: rawReplyReadable,
                  raw: rawReply,
                })
              }
              disabled={!rawReply}
            >
              {copy.popOutCard}
            </button>
          </div>
          <div className="code" style={{ marginTop: 10, minHeight: 150, maxHeight: 220, overflowY: "auto" }}>
            {previewText(rawReplyReadable) || copy.rawReplyPlaceholder}
          </div>

          <h3 style={{ marginTop: 14 }}>{copy.notesTitle}</h3>
          <ul className="list">
            <li>{copy.notesOne}</li>
            <li>{copy.notesTwo}</li>
            <li>{copy.notesThree}</li>
            <li>{copy.notesFour}</li>
          </ul>
        </div>
      </div>

      {popOutCard ? (
        <div className="editor-overlay" onClick={() => setPopOutCard(null)}>
          <div
            className="editor-card"
            style={{ width: "min(1100px, 100%)", maxHeight: "88vh", overflowY: "auto" }}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="toolbar" style={{ justifyContent: "space-between" }}>
              <h3 style={{ margin: 0 }}>{popOutCard.title}</h3>
              <button className="button muted" onClick={() => setPopOutCard(null)}>
                {copy.closeCard}
              </button>
            </div>

            <h3 style={{ marginTop: 14 }}>{copy.readableView}</h3>
            <div className="code" style={{ marginTop: 10, minHeight: 220, maxHeight: 380, overflowY: "auto" }}>
              {popOutCard.readable || "-"}
            </div>

            <details style={{ marginTop: 14 }}>
              <summary>{copy.rawJsonView}</summary>
              <div className="code" style={{ marginTop: 10, minHeight: 180, maxHeight: 420, overflowY: "auto" }}>
                {popOutCard.raw || "-"}
              </div>
            </details>
          </div>
        </div>
      ) : null}
    </section>
  );
}
