import { describe, expect, it } from "vitest";

import { COMMENT_LAB_COPY } from "./copy";
import { buildCommentGenerationRequest, type CommentGenerationForm } from "./generation-request";

const validForm: CommentGenerationForm = {
  model: "router::model",
  promptKey: "comment_v1",
  personaKey: "comment_persona",
  maxTokens: "512",
  timeoutSeconds: "180",
  retryCount: "0",
  taskShape: "classic",
  cachePrompt: false,
  enableThinking: true,
  temperature: "0.6",
  topP: "1",
  topK: "",
  userInput: "Keep the original spacing.",
};

describe("buildCommentGenerationRequest", () => {
  it("preserves the generation payload for valid input", () => {
    expect(buildCommentGenerationRequest(validForm, COMMENT_LAB_COPY.en)).toEqual({
      error: null,
      request: {
        input: "Keep the original spacing.",
        prompt_key: "comment_v1",
        persona_key: "comment_persona",
        model_key: "router::model",
        max_tokens: 512,
        timeout_seconds: 180,
        retry_count: 0,
        task_shape: "classic",
        cache_prompt: false,
        enable_thinking: true,
        temperature: 0.6,
        top_p: 1,
        top_k: undefined,
      },
    });
  });

  it("reports the existing validation copy before a request is made", () => {
    expect(buildCommentGenerationRequest({ ...validForm, retryCount: "6" }, COMMENT_LAB_COPY.en)).toEqual({
      request: null,
      error: COMMENT_LAB_COPY.en.invalidRetryCount,
    });
    expect(buildCommentGenerationRequest({ ...validForm, userInput: "  " }, COMMENT_LAB_COPY.en)).toEqual({
      request: null,
      error: COMMENT_LAB_COPY.en.inputRequired,
    });
  });
});
