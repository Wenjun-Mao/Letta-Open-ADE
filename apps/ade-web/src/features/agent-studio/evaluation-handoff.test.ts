import { describe, expect, it } from "vitest";

import {
  CHAT_MEMORY_EVAL_DEFAULT_ROUNDS,
  buildChatMemoryEvaluationHref,
} from "./evaluation-handoff";

describe("Agent Studio evaluation handoff", () => {
  it("builds a Test Center chat-memory evaluation URL from the creation setup", () => {
    const href = buildChatMemoryEvaluationHref({
      model: "openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8",
      promptKey: "chat_v20260516",
      personaKey: "chat_linxiaotang",
      embedding: "letta/letta-free",
      timeoutSeconds: "180",
      retryCount: "0",
    });

    const url = new URL(href, "https://ade.local");
    expect(url.pathname).toBe("/test-center");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      runType: "chat_memory_eval",
      model: "openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8",
      promptKey: "chat_v20260516",
      personaKey: "chat_linxiaotang",
      embedding: "letta/letta-free",
      timeoutSeconds: "180",
      retryCount: "0",
      rounds: String(CHAT_MEMORY_EVAL_DEFAULT_ROUNDS),
      judgeEnabled: "true",
    });
  });

  it("preserves special characters in the selected configuration", () => {
    const href = buildChatMemoryEvaluationHref({
      model: "router/model?edition=fast&region=ca",
      promptKey: "chat & memory",
      personaKey: "persona/zh?name=Lin",
      embedding: "embed + retrieval",
      timeoutSeconds: "180.5",
      retryCount: "2",
    });

    const url = new URL(href, "https://ade.local");
    expect(url.searchParams.get("model")).toBe("router/model?edition=fast&region=ca");
    expect(url.searchParams.get("promptKey")).toBe("chat & memory");
    expect(url.searchParams.get("personaKey")).toBe("persona/zh?name=Lin");
    expect(url.searchParams.get("embedding")).toBe("embed + retrieval");
    expect(url.searchParams.get("timeoutSeconds")).toBe("180.5");
    expect(url.searchParams.get("retryCount")).toBe("2");
  });
});
