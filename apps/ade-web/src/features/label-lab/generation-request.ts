import type { LabelingGenerateRequest } from "./api";
import type { LABEL_LAB_COPY } from "./copy";
import {
  parseIntegerInRange,
  parseNonNegativeInteger,
  parseOptionalPositiveInteger,
  parsePositiveNumber,
  parseTemperature,
  parseTopP,
} from "@/shared/generation-controls";

type Copy = (typeof LABEL_LAB_COPY)[keyof typeof LABEL_LAB_COPY];

export type LabelGenerationForm = {
  model: string;
  promptKey: string;
  schemaKey: string;
  maxTokens: string;
  timeoutSeconds: string;
  repairRetryCount: string;
  temperature: string;
  topP: string;
  topK: string;
  articleInput: string;
};

export type LabelGenerationRequestResult =
  | { request: LabelingGenerateRequest; error: null }
  | { request: null; error: string };

/** Keeps Label Lab validation and its API payload under one tested contract. */
export function buildLabelGenerationRequest(form: LabelGenerationForm, copy: Copy): LabelGenerationRequestResult {
  if (!form.model || !form.promptKey || !form.schemaKey) {
    return { request: null, error: copy.selectRequired };
  }
  if (!form.articleInput.trim()) {
    return { request: null, error: copy.inputRequired };
  }
  const maxTokens = parseNonNegativeInteger(form.maxTokens);
  if (maxTokens === null) return { request: null, error: copy.invalidMaxTokens };
  const timeoutSeconds = parsePositiveNumber(form.timeoutSeconds);
  if (timeoutSeconds === null) return { request: null, error: copy.invalidTimeout };
  const repairRetryCount = parseIntegerInRange(form.repairRetryCount, 0, 3);
  if (repairRetryCount === null) return { request: null, error: copy.invalidRepairRetryCount };
  const temperature = parseTemperature(form.temperature);
  if (temperature === null) return { request: null, error: copy.invalidTemperature };
  const topP = parseTopP(form.topP);
  if (topP === null) return { request: null, error: copy.invalidTopP };
  const topK = parseOptionalPositiveInteger(form.topK);
  if (topK === null) return { request: null, error: copy.invalidTopK };

  return {
    error: null,
    request: {
      input: form.articleInput,
      prompt_key: form.promptKey,
      schema_key: form.schemaKey,
      model_key: form.model,
      max_tokens: maxTokens,
      timeout_seconds: timeoutSeconds,
      repair_retry_count: repairRetryCount,
      temperature,
      top_p: topP,
      top_k: topK,
    },
  };
}
