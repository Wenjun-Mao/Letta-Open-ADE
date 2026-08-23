"use client";

import { useEffect, useEffectEvent, useMemo, useState } from "react";
import Link from "next/link";

import {
  LabelExtractionResult,
  LabelSchemaRecord,
  OptionEntry,
  PromptTemplateRecord,
  fetchOptions,
  generateLabels,
  listLabelSchemas,
  listPromptTemplates,
} from "../../lib/api";
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
import { chooseOptionKey } from "../../lib/selection";

import { LABEL_LAB_COPY as COPY } from "./copy";
import { formatGroupLabel, normalizeExtractionGroups } from "./extraction-presenters";

function toErrorMessage(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

export default function LabelLabPage() {
  const { locale } = useI18n();
  const copy = COPY[locale];

  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const [models, setModels] = useState<OptionEntry[]>([]);
  const [prompts, setPrompts] = useState<OptionEntry[]>([]);
  const [schemas, setSchemas] = useState<OptionEntry[]>([]);
  const [promptRecords, setPromptRecords] = useState<PromptTemplateRecord[]>([]);
  const [schemaRecords, setSchemaRecords] = useState<LabelSchemaRecord[]>([]);

  const [model, setModel] = useState("");
  const [promptKey, setPromptKey] = useState("");
  const [schemaKey, setSchemaKey] = useState("");
  const [maxTokens, setMaxTokens] = useState("1024");
  const [timeoutSeconds, setTimeoutSeconds] = useState("60");
  const [repairRetryCount, setRepairRetryCount] = useState("1");
  const [temperature, setTemperature] = useState("0");
  const [topP, setTopP] = useState("1");
  const [topK, setTopK] = useState("");

  const [articleInput, setArticleInput] = useState("");
  const [resultJson, setResultJson] = useState("");
  const [extractionResult, setExtractionResult] = useState<LabelExtractionResult>({});
  const [provider, setProvider] = useState("");
  const [modelUsed, setModelUsed] = useState("");
  const [outputMode, setOutputMode] = useState("");
  const [temperatureUsed, setTemperatureUsed] = useState("");
  const [topPUsed, setTopPUsed] = useState("");
  const [topKUsed, setTopKUsed] = useState("");
  const [selectedAttempt, setSelectedAttempt] = useState("");
  const [finishReason, setFinishReason] = useState("");
  const [responseSeconds, setResponseSeconds] = useState("");
  const [receivedAt, setReceivedAt] = useState("");
  const [usagePromptTokens, setUsagePromptTokens] = useState("");
  const [usageCompletionTokens, setUsageCompletionTokens] = useState("");
  const [usageTotalTokens, setUsageTotalTokens] = useState("");
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [rawRequest, setRawRequest] = useState("");
  const [rawReply, setRawReply] = useState("");

  const selectedModel = useMemo(
    () => models.find((option) => option.key === model) || null,
    [model, models],
  );
  const selectedPrompt = useMemo(
    () => promptRecords.find((record) => record.key === promptKey) || null,
    [promptKey, promptRecords],
  );
  const selectedSchema = useMemo(
    () => schemaRecords.find((record) => record.key === schemaKey) || null,
    [schemaKey, schemaRecords],
  );
  const extractedGroups = useMemo(
    () => normalizeExtractionGroups(extractionResult),
    [extractionResult],
  );

  const capabilityLabel =
    selectedModel?.structured_output_mode === "strict_json_schema"
      ? copy.capabilityStrict
      : selectedModel?.structured_output_mode === "json_schema"
        ? copy.capabilityJsonSchema
        : selectedModel?.structured_output_mode === "best_effort_prompt_json"
          ? copy.capabilityBestEffort
          : "-";

  const loadOptions = async (forceRefresh = false) => {
    setLoadingOptions(true);
    setError("");

    try {
      const [optionsPayload, promptPayload, schemaPayload] = await Promise.all([
        fetchOptions("label", forceRefresh ? { refresh: true } : undefined),
        listPromptTemplates(false, "label"),
        listLabelSchemas(false),
      ]);

      const nextModels = Array.isArray(optionsPayload.models) ? optionsPayload.models : [];
      const nextPrompts = Array.isArray(optionsPayload.prompts) ? optionsPayload.prompts : [];
      const nextSchemas = Array.isArray(optionsPayload.schemas) ? optionsPayload.schemas : [];
      const nextPromptRecords = Array.isArray(promptPayload.items) ? promptPayload.items : [];
      const nextSchemaRecords = Array.isArray(schemaPayload.items) ? schemaPayload.items : [];

      setModels(nextModels);
      setPrompts(nextPrompts);
      setSchemas(nextSchemas);
      setPromptRecords(nextPromptRecords);
      setSchemaRecords(nextSchemaRecords);
      setModel((current) => chooseOptionKey(current, nextModels, optionsPayload.defaults.model || ""));

      const params = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
      const requestedPromptKey = (params?.get("promptKey") || "").trim();
      const requestedSchemaKey = (params?.get("schemaKey") || "").trim();
      setPromptKey((current) => {
        if (current && nextPrompts.some((option) => option.key === current)) {
          return current;
        }
        if (requestedPromptKey && nextPrompts.some((option) => option.key === requestedPromptKey)) {
          return requestedPromptKey;
        }
        return chooseOptionKey("", nextPrompts, optionsPayload.defaults.prompt_key || "");
      });
      setSchemaKey((current) => {
        if (current && nextSchemas.some((option) => option.key === current)) {
          return current;
        }
        if (requestedSchemaKey && nextSchemas.some((option) => option.key === requestedSchemaKey)) {
          return requestedSchemaKey;
        }
        return chooseOptionKey("", nextSchemas, optionsPayload.defaults.schema_key || "");
      });

      if (optionsPayload.labeling) {
        setMaxTokens(`${optionsPayload.labeling.max_tokens}`);
        setTimeoutSeconds(`${optionsPayload.labeling.timeout_seconds}`);
        setRepairRetryCount(`${optionsPayload.labeling.repair_retry_count}`);
        setTemperature(`${optionsPayload.labeling.temperature}`);
        setTopP(`${optionsPayload.labeling.top_p}`);
        setTopK(optionsPayload.labeling.top_k === null || optionsPayload.labeling.top_k === undefined ? "" : `${optionsPayload.labeling.top_k}`);
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
    if (!selectedModel) {
      return;
    }
    const nextTemperature = samplingDefaultString(selectedModel, "label_lab", "temperature");
    const nextTopP = samplingDefaultString(selectedModel, "label_lab", "top_p");
    const nextTopK = samplingDefaultString(selectedModel, "label_lab", "top_k");
    if (nextTemperature !== null) {
      setTemperature(nextTemperature);
    }
    if (nextTopP !== null) {
      setTopP(nextTopP);
    }
    setTopK(nextTopK ?? "");
  }, [selectedModel]);

  const onGenerate = async () => {
    setError("");
    setStatus("");
    setResponseSeconds("");

    if (!model || !promptKey || !schemaKey) {
      setError(copy.selectRequired);
      return;
    }
    if (!articleInput.trim()) {
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
    const parsedRepairRetryCount = parseIntegerInRange(repairRetryCount, 0, 3);
    if (parsedRepairRetryCount === null) {
      setError(copy.invalidRepairRetryCount);
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
      const payload = await generateLabels({
        input: articleInput,
        prompt_key: promptKey,
        schema_key: schemaKey,
        model_key: model,
        max_tokens: parsedMaxTokens,
        timeout_seconds: parsedTimeoutSeconds,
        repair_retry_count: parsedRepairRetryCount,
        temperature: parsedTemperature,
        top_p: parsedTopP,
        top_k: parsedTopK,
      });
      const nextResult = asObject(payload.result) as LabelExtractionResult;
      setResultJson(stringifyPretty(nextResult || {}));
      setExtractionResult(nextResult || {});
      setProvider(payload.source_label || "");
      setModelUsed(payload.provider_model_id || "");
      setOutputMode(payload.output_mode || "");
      setTemperatureUsed(`${payload.temperature}`);
      setTopPUsed(`${payload.top_p}`);
      setTopKUsed(payload.top_k === null || payload.top_k === undefined ? "" : `${payload.top_k}`);
      setSelectedAttempt(payload.selected_attempt || "");
      setFinishReason(payload.finish_reason || "");
      setResponseSeconds((Math.max(0, performance.now() - startedAtMs) / 1000).toFixed(2));
      setReceivedAt(payload.received_at || "");
      const usage = asObject(payload.usage);
      setUsagePromptTokens(asIntString(usage.prompt_tokens));
      setUsageCompletionTokens(asIntString(usage.completion_tokens));
      setUsageTotalTokens(asIntString(usage.total_tokens));
      setValidationErrors(Array.isArray(payload.validation_errors) ? payload.validation_errors : []);
      setRawRequest(stringifyPretty(payload.raw_request || {}));
      setRawReply(stringifyPretty(payload.raw_reply || {}));
      setStatus(`${copy.modelUsed}: ${payload.provider_model_id}`);
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
              <select className="input" value={model} onChange={(event) => setModel(event.target.value)} disabled={loadingOptions || submitting}>
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
              <select className="input" value={promptKey} onChange={(event) => setPromptKey(event.target.value)} disabled={loadingOptions || submitting}>
                {prompts.map((item) => (
                  <option key={item.key} value={item.key}>
                    {formatModelOptionLabel(item)}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>{copy.schema}</span>
              <select className="input" value={schemaKey} onChange={(event) => setSchemaKey(event.target.value)} disabled={loadingOptions || submitting}>
                {schemas.map((item) => (
                  <option key={item.key} value={item.key}>
                    {formatModelOptionLabel(item)}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>{copy.capability}</span>
              <input className="input" value={capabilityLabel} disabled />
            </label>

            <label className="field">
              <span>{copy.maxTokens}</span>
              <input className="input" type="number" min={0} max={8192} step={1} value={maxTokens} onChange={(event) => setMaxTokens(event.target.value)} disabled={submitting} />
            </label>

            <label className="field">
              <span>{copy.timeoutSeconds}</span>
              <input className="input" type="number" min={5} max={600} step={1} value={timeoutSeconds} onChange={(event) => setTimeoutSeconds(event.target.value)} disabled={submitting} />
            </label>

            <label className="field">
              <span>{copy.repairRetryCount}</span>
              <input className="input" type="number" min={0} max={3} step={1} value={repairRetryCount} onChange={(event) => setRepairRetryCount(event.target.value)} disabled={submitting} />
            </label>

            <label className="field">
              <span>{copy.temperature}</span>
              <input className="input" type="number" min={0} max={2} step={0.1} value={temperature} onChange={(event) => setTemperature(event.target.value)} disabled={submitting} />
            </label>

            <label className="field">
              <span>{copy.topP}</span>
              <input className="input" type="number" min={0.01} max={1} step={0.05} value={topP} onChange={(event) => setTopP(event.target.value)} disabled={submitting} />
            </label>

            <label className="field">
              <span>{copy.topK}</span>
              <input className="input" type="number" min={1} step={1} value={topK} onChange={(event) => setTopK(event.target.value)} placeholder="64" disabled={submitting} />
            </label>
          </div>

          <div className="toolbar" style={{ marginTop: 12 }}>
            <button className="button" onClick={() => void onGenerate()} disabled={loadingOptions || submitting}>
              {submitting ? copy.generating : copy.generate}
            </button>
            <button className="button muted" onClick={() => void loadOptions(true)} disabled={submitting}>
              {copy.refreshOptions}
            </button>
            <Link className="button muted" href="/schema-center">
              {copy.manageSchemas}
            </Link>
          </div>
          <p className="muted" style={{ marginTop: 10, fontSize: 12 }}>
            {copy.defaultsFromRuntime}
          </p>
        </div>

        <div className="card studio-panel">
          <h3>{copy.mainContentTitle}</h3>
          <label className="field" style={{ marginTop: 10 }}>
            <span>{copy.articleInput}</span>
            <textarea
              className="input"
              rows={12}
              style={{ minHeight: 220 }}
              value={articleInput}
              onChange={(event) => setArticleInput(event.target.value)}
              placeholder={copy.articleInputPlaceholder}
              disabled={submitting}
            />
          </label>

          <h3 style={{ marginTop: 14 }}>{copy.promptPreview}</h3>
          <div className="code" style={{ marginTop: 10, minHeight: 110, maxHeight: 180, overflowY: "auto", whiteSpace: "pre-wrap" }}>
            {selectedPrompt?.content || copy.rawPlaceholder}
          </div>

          <h3 style={{ marginTop: 14 }}>{copy.schemaPreview}</h3>
          <div className="code" style={{ marginTop: 10, minHeight: 150, maxHeight: 220, overflowY: "auto" }}>
            {selectedSchema ? stringifyPretty(selectedSchema.schema) : selectedPrompt?.output_schema || copy.rawPlaceholder}
          </div>
        </div>

        <div className="card studio-panel">
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
                <div>{copy.provider}: {provider || "-"}</div>
                <div>{copy.modelUsed}: {modelUsed || "-"}</div>
                <div>{copy.outputMode}: {outputMode || "-"}</div>
                <div>{copy.temperatureUsed}: {temperatureUsed || "-"}</div>
                <div>{copy.topPUsed}: {topPUsed || "-"}</div>
                <div>{copy.topKUsed}: {topKUsed || "-"}</div>
                <div>{copy.selectedAttempt}: {selectedAttempt || "-"}</div>
                <div>{copy.finishReason}: {finishReason || "-"}</div>
                <div>{copy.responseSeconds}: {responseSeconds || "-"}</div>
                <div>{copy.receivedAt}: {receivedAt ? formatTimestamp(receivedAt) : "-"}</div>
              </div>
            </div>

            <div className="card" style={{ margin: 0, padding: "10px 12px" }}>
              <div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>
                {copy.tokenMetaTitle}
              </div>
              <div className="list" style={{ marginTop: 6 }}>
                <div>{copy.usagePromptTokens}: {usagePromptTokens || "-"}</div>
                <div>{copy.usageCompletionTokens}: {usageCompletionTokens || "-"}</div>
                <div>{copy.usageTotalTokens}: {usageTotalTokens || "-"}</div>
              </div>
            </div>
          </div>

          <h3 style={{ marginTop: 14 }}>{copy.extractedGroupsTitle}</h3>
          {extractedGroups.length ? (
            <div
              style={{
                marginTop: 10,
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: 10,
              }}
            >
              {extractedGroups.map((group) => (
                <div key={group.key} className="card" style={{ margin: 0, padding: "10px 12px" }}>
                  <div style={{ fontWeight: 700 }}>{formatGroupLabel(group.key)}</div>
                  {group.items.length ? (
                    <ul className="list" style={{ marginTop: 8 }}>
                      {group.items.map((item, index) => (
                        <li key={`${group.key}-${index}`}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="muted" style={{ marginTop: 8 }}>{copy.emptyGroup}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="code" style={{ marginTop: 10, minHeight: 120, whiteSpace: "pre-wrap" }}>
              {copy.extractedGroupsPlaceholder}
            </div>
          )}

          <h3 style={{ marginTop: 14 }}>{copy.resultJsonTitle}</h3>
          <div className="code" style={{ marginTop: 10, minHeight: 220, whiteSpace: "pre-wrap" }}>
            {resultJson || copy.resultJsonPlaceholder}
          </div>
        </div>
      </div>

      <div className="studio-layout" style={{ marginTop: 14 }}>
        <div className="card studio-panel">
          <h3>{copy.internalsTitle}</h3>
          <h3 style={{ marginTop: 14 }}>{copy.validationErrors}</h3>
          <div className="code" style={{ marginTop: 10, minHeight: 90 }}>
            {validationErrors.length ? validationErrors.join("\n") : "-"}
          </div>

          <h3 style={{ marginTop: 14 }}>{copy.rawRequestTitle}</h3>
          <div className="code" style={{ marginTop: 10, minHeight: 160, maxHeight: 320, overflowY: "auto" }}>
            {rawRequest || copy.rawPlaceholder}
          </div>
        </div>

        <div className="card studio-panel">
          <h3>{copy.rawReplyTitle}</h3>
          <div className="code" style={{ marginTop: 10, minHeight: 280, maxHeight: 480, overflowY: "auto" }}>
            {rawReply || copy.rawPlaceholder}
          </div>

          <h3 style={{ marginTop: 14 }}>{copy.notesTitle}</h3>
          <ul className="list">
            <li>{copy.notesOne}</li>
            <li>{copy.notesTwo}</li>
            <li>{copy.notesThree}</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
