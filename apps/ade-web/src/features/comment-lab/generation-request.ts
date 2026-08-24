import type { CommentingGenerateRequest, CommentingTaskShape } from "./api";
import type { COMMENT_LAB_COPY } from "./copy";
import {
  parseIntegerInRange,
  parseNonNegativeInteger,
  parseOptionalPositiveInteger,
  parsePositiveNumber,
  parseTemperature,
  parseTopP,
} from "@/shared/generation-controls";

type Copy = (typeof COMMENT_LAB_COPY)[keyof typeof COMMENT_LAB_COPY];

export type CommentGenerationForm = {
  model: string;
  promptKey: string;
  personaKey: string;
  maxTokens: string;
  timeoutSeconds: string;
  retryCount: string;
  taskShape: CommentingTaskShape;
  cachePrompt: boolean;
  enableThinking: boolean;
  temperature: string;
  topP: string;
  topK: string;
  userInput: string;
};

export type CommentGenerationRequestResult =
  | { request: CommentingGenerateRequest; error: null }
  | { request: null; error: string };

/** Keeps client-side validation and the API request shape together. */
export function buildCommentGenerationRequest(
  form: CommentGenerationForm,
  copy: Copy,
): CommentGenerationRequestResult {
  if (!form.model || !form.promptKey || !form.personaKey) {
    return { request: null, error: copy.selectRequired };
  }
  if (!form.userInput.trim()) {
    return { request: null, error: copy.inputRequired };
  }

  const maxTokens = parseNonNegativeInteger(form.maxTokens);
  if (maxTokens === null) {
    return { request: null, error: copy.invalidMaxTokens };
  }
  const timeoutSeconds = parsePositiveNumber(form.timeoutSeconds);
  if (timeoutSeconds === null) {
    return { request: null, error: copy.invalidTimeout };
  }
  const retryCount = parseIntegerInRange(form.retryCount, 0, 5);
  if (retryCount === null) {
    return { request: null, error: copy.invalidRetryCount };
  }
  const temperature = parseTemperature(form.temperature);
  if (temperature === null) {
    return { request: null, error: copy.invalidTemperature };
  }
  const topP = parseTopP(form.topP);
  if (topP === null) {
    return { request: null, error: copy.invalidTopP };
  }
  const topK = parseOptionalPositiveInteger(form.topK);
  if (topK === null) {
    return { request: null, error: copy.invalidTopK };
  }

  return {
    error: null,
    request: {
      input: form.userInput,
      prompt_key: form.promptKey,
      persona_key: form.personaKey,
      model_key: form.model,
      max_tokens: maxTokens,
      timeout_seconds: timeoutSeconds,
      retry_count: retryCount,
      task_shape: form.taskShape,
      cache_prompt: form.cachePrompt,
      enable_thinking: form.enableThinking,
      temperature,
      top_p: topP,
      top_k: topK,
    },
  };
}
