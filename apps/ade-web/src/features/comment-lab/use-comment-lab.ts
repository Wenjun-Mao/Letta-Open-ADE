"use client";

import { useEffect, useEffectEvent, useState, type Dispatch, type SetStateAction } from "react";

import { generateComment, type CommentingTaskShape } from "./api";
import { COMMENT_LAB_COPY } from "./copy";
import { buildCommentGenerationRequest, type CommentGenerationForm } from "./generation-request";
import { formatRawReplyForHuman, formatRawRequestForHuman } from "./provider-payload-formatters";
import { fetchOptions, type OptionEntry } from "@/features/model-catalog/api";
import { samplingDefaultString } from "@/shared/generation-controls";
import { asIntegerString, asRecord, prettyJson } from "@/shared/json-display";

type Copy = (typeof COMMENT_LAB_COPY)[keyof typeof COMMENT_LAB_COPY];

type Setter<T> = Dispatch<SetStateAction<T>>;

export type CommentLabResult = {
  output: string;
  provider: string;
  modelUsed: string;
  maxTokensUsed: string;
  timeoutUsed: string;
  taskShapeUsed: string;
  cachePromptUsed: string;
  enableThinkingUsed: string;
  temperatureUsed: string;
  topPUsed: string;
  topKUsed: string;
  usagePromptTokens: string;
  usageCompletionTokens: string;
  usageTotalTokens: string;
  usageReasoningTokens: string;
  responseSeconds: string;
  receivedAt: string;
  selectedAttempt: string;
  finishReason: string;
  rawRequest: string;
  rawRequestReadable: string;
  rawReply: string;
  rawReplyReadable: string;
};

export type PopOutCard = { title: string; readable: string; raw: string };

export type CommentLabController = {
  loadingOptions: boolean;
  submitting: boolean;
  error: string;
  status: string;
  models: OptionEntry[];
  prompts: OptionEntry[];
  personas: OptionEntry[];
  form: CommentGenerationForm;
  result: CommentLabResult;
  popOutCard: PopOutCard | null;
  setModel: Setter<string>;
  setPromptKey: Setter<string>;
  setPersonaKey: Setter<string>;
  setMaxTokens: Setter<string>;
  setTimeoutSeconds: Setter<string>;
  setRetryCount: Setter<string>;
  setTaskShape: Setter<CommentingTaskShape>;
  setCachePrompt: Setter<boolean>;
  setEnableThinking: Setter<boolean>;
  setTemperature: Setter<string>;
  setTopP: Setter<string>;
  setTopK: Setter<string>;
  setUserInput: Setter<string>;
  setPopOutCard: Setter<PopOutCard | null>;
  loadOptions: (forceRefresh?: boolean) => Promise<void>;
  generate: () => Promise<void>;
};

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

export function useCommentLab(copy: Copy): CommentLabController {
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
  const [result, setResult] = useState<CommentLabResult>({
    output: "", provider: "", modelUsed: "", maxTokensUsed: "", timeoutUsed: "", taskShapeUsed: "",
    cachePromptUsed: "", enableThinkingUsed: "", temperatureUsed: "", topPUsed: "", topKUsed: "",
    usagePromptTokens: "", usageCompletionTokens: "", usageTotalTokens: "", usageReasoningTokens: "",
    responseSeconds: "", receivedAt: "", selectedAttempt: "", finishReason: "", rawRequest: "",
    rawRequestReadable: "", rawReply: "", rawReplyReadable: "",
  });
  const [popOutCard, setPopOutCard] = useState<PopOutCard | null>(null);

  const form: CommentGenerationForm = {
    model, promptKey, personaKey, maxTokens, timeoutSeconds, retryCount, taskShape, cachePrompt,
    enableThinking, temperature, topP, topK, userInput,
  };

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
      setPromptKey((current) => current && nextPrompts.some((option) => option.key === current)
        ? current
        : requestedPromptKey && nextPrompts.some((option) => option.key === requestedPromptKey)
          ? requestedPromptKey
          : pickSelectedKey("", nextPrompts, payload.defaults.prompt_key || ""));
      setPersonaKey((current) => current && nextPersonas.some((option) => option.key === current)
        ? current
        : requestedPersonaKey && nextPersonas.some((option) => option.key === requestedPersonaKey)
          ? requestedPersonaKey
          : pickSelectedKey("", nextPersonas, payload.defaults.persona_key || ""));
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
    if (!selected) return;
    const nextTemperature = samplingDefaultString(selected, "comment_lab", "temperature");
    const nextTopP = samplingDefaultString(selected, "comment_lab", "top_p");
    const nextTopK = samplingDefaultString(selected, "comment_lab", "top_k");
    if (nextTemperature !== null) setTemperature(nextTemperature);
    if (nextTopP !== null) setTopP(nextTopP);
    setTopK(nextTopK ?? "");
    setEnableThinking(Boolean(selected.thinking_default_enabled));
  }, [model, models]);

  const generate = async () => {
    setError("");
    setStatus("");
    setPopOutCard(null);
    setResult((current) => ({ ...current, responseSeconds: "" }));
    const built = buildCommentGenerationRequest(form, copy);
    if (!built.request) {
      setError(built.error);
      return;
    }
    setSubmitting(true);
    const startedAtMs = performance.now();
    try {
      const payload = await generateComment(built.request);
      const usage = asRecord(payload.usage);
      const completionTokensDetails = asRecord(usage.completion_tokens_details);
      setResult({
        output: payload.content || "", provider: payload.provider || "", modelUsed: payload.provider_model_id || payload.model || "",
        maxTokensUsed: `${payload.max_tokens}`, timeoutUsed: `${payload.timeout_seconds}`, taskShapeUsed: payload.task_shape || "",
        cachePromptUsed: payload.cache_prompt ? "true" : "false", enableThinkingUsed: payload.enable_thinking ? "true" : "false",
        temperatureUsed: `${payload.temperature}`, topPUsed: `${payload.top_p}`,
        topKUsed: payload.top_k === null || payload.top_k === undefined ? "" : `${payload.top_k}`,
        usagePromptTokens: asIntegerString(usage.prompt_tokens), usageCompletionTokens: asIntegerString(usage.completion_tokens),
        usageTotalTokens: asIntegerString(usage.total_tokens), usageReasoningTokens: asIntegerString(completionTokensDetails.reasoning_tokens),
        responseSeconds: (Math.max(0, performance.now() - startedAtMs) / 1000).toFixed(2), receivedAt: payload.received_at || "",
        selectedAttempt: payload.selected_attempt || "", finishReason: payload.finish_reason || "",
        rawRequest: prettyJson(payload.raw_request || {}), rawRequestReadable: formatRawRequestForHuman(payload.raw_request || {}),
        rawReply: prettyJson(payload.raw_reply || {}), rawReplyReadable: formatRawReplyForHuman(payload.raw_reply || {}),
      });
      setStatus(`${copy.modelUsed}: ${payload.provider_model_id || payload.model}`);
    } catch (exc) {
      setResult((current) => ({ ...current, responseSeconds: "" }));
      setError(`${copy.generateError}: ${toErrorMessage(exc)}`);
    } finally {
      setSubmitting(false);
    }
  };

  return {
    loadingOptions, submitting, error, status, models, prompts, personas, form, result, popOutCard,
    setModel, setPromptKey, setPersonaKey, setMaxTokens, setTimeoutSeconds, setRetryCount, setTaskShape,
    setCachePrompt, setEnableThinking, setTemperature, setTopP, setTopK, setUserInput, setPopOutCard,
    loadOptions, generate,
  };
}
