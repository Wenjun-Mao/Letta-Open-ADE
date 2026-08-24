"use client";

import { useEffect, useEffectEvent, useMemo, useState, type Dispatch, type SetStateAction } from "react";

import { generateLabels, type LabelExtractionResult } from "./api";
import { LABEL_LAB_COPY } from "./copy";
import { formatGroupLabel, normalizeExtractionGroups } from "./extraction-presenters";
import { buildLabelGenerationRequest, type LabelGenerationForm } from "./generation-request";
import { fetchOptions, type OptionEntry } from "@/features/model-catalog/api";
import { listPromptTemplates, type PromptTemplateRecord } from "@/features/prompt-center/api";
import { listLabelSchemas, type LabelSchemaRecord } from "@/features/schema-center/api";
import { samplingDefaultString } from "@/shared/generation-controls";
import { asIntegerString, asRecord, prettyJson } from "@/shared/json-display";
import { chooseOptionKey } from "@/shared/selection";

type Copy = (typeof LABEL_LAB_COPY)[keyof typeof LABEL_LAB_COPY];
type Setter<T> = Dispatch<SetStateAction<T>>;

export type LabelLabResult = {
  resultJson: string;
  extractionResult: LabelExtractionResult;
  provider: string;
  modelUsed: string;
  outputMode: string;
  temperatureUsed: string;
  topPUsed: string;
  topKUsed: string;
  selectedAttempt: string;
  finishReason: string;
  responseSeconds: string;
  receivedAt: string;
  usagePromptTokens: string;
  usageCompletionTokens: string;
  usageTotalTokens: string;
  validationErrors: string[];
  rawRequest: string;
  rawReply: string;
};

export type LabelLabController = {
  loadingOptions: boolean;
  submitting: boolean;
  error: string;
  status: string;
  models: OptionEntry[];
  prompts: OptionEntry[];
  schemas: OptionEntry[];
  form: LabelGenerationForm;
  selectedPrompt: PromptTemplateRecord | null;
  selectedSchema: LabelSchemaRecord | null;
  extractedGroups: Array<{ key: string; items: string[] }>;
  capabilityLabel: string;
  result: LabelLabResult;
  setModel: Setter<string>;
  setPromptKey: Setter<string>;
  setSchemaKey: Setter<string>;
  setMaxTokens: Setter<string>;
  setTimeoutSeconds: Setter<string>;
  setRepairRetryCount: Setter<string>;
  setTemperature: Setter<string>;
  setTopP: Setter<string>;
  setTopK: Setter<string>;
  setArticleInput: Setter<string>;
  loadOptions: (forceRefresh?: boolean) => Promise<void>;
  generate: () => Promise<void>;
};

function toErrorMessage(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

export function useLabelLab(copy: Copy): LabelLabController {
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
  const [result, setResult] = useState<LabelLabResult>({
    resultJson: "", extractionResult: {}, provider: "", modelUsed: "", outputMode: "", temperatureUsed: "", topPUsed: "",
    topKUsed: "", selectedAttempt: "", finishReason: "", responseSeconds: "", receivedAt: "", usagePromptTokens: "",
    usageCompletionTokens: "", usageTotalTokens: "", validationErrors: [], rawRequest: "", rawReply: "",
  });

  const form: LabelGenerationForm = {
    model, promptKey, schemaKey, maxTokens, timeoutSeconds, repairRetryCount, temperature, topP, topK, articleInput,
  };
  const selectedModel = useMemo(() => models.find((option) => option.key === model) || null, [model, models]);
  const selectedPrompt = useMemo(() => promptRecords.find((record) => record.key === promptKey) || null, [promptKey, promptRecords]);
  const selectedSchema = useMemo(() => schemaRecords.find((record) => record.key === schemaKey) || null, [schemaKey, schemaRecords]);
  const extractedGroups = useMemo(() => normalizeExtractionGroups(result.extractionResult), [result.extractionResult]);
  const capabilityLabel = selectedModel?.structured_output_mode === "strict_json_schema"
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
      setModels(nextModels);
      setPrompts(nextPrompts);
      setSchemas(nextSchemas);
      setPromptRecords(Array.isArray(promptPayload.items) ? promptPayload.items : []);
      setSchemaRecords(Array.isArray(schemaPayload.items) ? schemaPayload.items : []);
      setModel((current) => chooseOptionKey(current, nextModels, optionsPayload.defaults.model || ""));
      const params = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
      const requestedPromptKey = (params?.get("promptKey") || "").trim();
      const requestedSchemaKey = (params?.get("schemaKey") || "").trim();
      setPromptKey((current) => current && nextPrompts.some((option) => option.key === current)
        ? current
        : requestedPromptKey && nextPrompts.some((option) => option.key === requestedPromptKey)
          ? requestedPromptKey
          : chooseOptionKey("", nextPrompts, optionsPayload.defaults.prompt_key || ""));
      setSchemaKey((current) => current && nextSchemas.some((option) => option.key === current)
        ? current
        : requestedSchemaKey && nextSchemas.some((option) => option.key === requestedSchemaKey)
          ? requestedSchemaKey
          : chooseOptionKey("", nextSchemas, optionsPayload.defaults.schema_key || ""));
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
  useEffect(() => { void loadInitialOptions(); }, []);
  useEffect(() => {
    if (!selectedModel) return;
    const nextTemperature = samplingDefaultString(selectedModel, "label_lab", "temperature");
    const nextTopP = samplingDefaultString(selectedModel, "label_lab", "top_p");
    const nextTopK = samplingDefaultString(selectedModel, "label_lab", "top_k");
    if (nextTemperature !== null) setTemperature(nextTemperature);
    if (nextTopP !== null) setTopP(nextTopP);
    setTopK(nextTopK ?? "");
  }, [selectedModel]);

  const generate = async () => {
    setError("");
    setStatus("");
    setResult((current) => ({ ...current, responseSeconds: "" }));
    const built = buildLabelGenerationRequest(form, copy);
    if (!built.request) {
      setError(built.error);
      return;
    }
    setSubmitting(true);
    const startedAtMs = performance.now();
    try {
      const payload = await generateLabels(built.request);
      const extractionResult = asRecord(payload.result) as LabelExtractionResult;
      const usage = asRecord(payload.usage);
      setResult({
        resultJson: prettyJson(extractionResult || {}), extractionResult: extractionResult || {}, provider: payload.source_label || "",
        modelUsed: payload.provider_model_id || "", outputMode: payload.output_mode || "", temperatureUsed: `${payload.temperature}`,
        topPUsed: `${payload.top_p}`, topKUsed: payload.top_k === null || payload.top_k === undefined ? "" : `${payload.top_k}`,
        selectedAttempt: payload.selected_attempt || "", finishReason: payload.finish_reason || "",
        responseSeconds: (Math.max(0, performance.now() - startedAtMs) / 1000).toFixed(2), receivedAt: payload.received_at || "",
        usagePromptTokens: asIntegerString(usage.prompt_tokens), usageCompletionTokens: asIntegerString(usage.completion_tokens),
        usageTotalTokens: asIntegerString(usage.total_tokens), validationErrors: Array.isArray(payload.validation_errors) ? payload.validation_errors : [],
        rawRequest: prettyJson(payload.raw_request || {}), rawReply: prettyJson(payload.raw_reply || {}),
      });
      setStatus(`${copy.modelUsed}: ${payload.provider_model_id}`);
    } catch (exc) {
      setResult((current) => ({ ...current, responseSeconds: "" }));
      setError(`${copy.generateError}: ${toErrorMessage(exc)}`);
    } finally {
      setSubmitting(false);
    }
  };

  return {
    loadingOptions, submitting, error, status, models, prompts, schemas, form, selectedPrompt, selectedSchema,
    extractedGroups, capabilityLabel, result, setModel, setPromptKey, setSchemaKey, setMaxTokens, setTimeoutSeconds,
    setRepairRetryCount, setTemperature, setTopP, setTopK, setArticleInput, loadOptions, generate,
  };
}
