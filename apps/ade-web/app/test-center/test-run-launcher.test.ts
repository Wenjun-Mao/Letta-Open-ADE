import { describe, expect, it } from "vitest";

import { buildTestRunPayload, type ChatMemoryEvalFormState } from "./test-run-launcher";

const chatMemoryForm: ChatMemoryEvalFormState = {
  model: "openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8",
  promptKey: "chat_v20260516",
  personaKey: "chat_linxiaotang",
  embedding: "letta/letta-free",
  fixtureKey: "recent_user_chat_turns",
  rounds: "3",
  timeoutSeconds: "180",
  retryCount: "0",
  judgeEnabled: true,
};

describe("Test Center run launcher", () => {
  it("does not leak chat-memory fields into standard run payloads", () => {
    expect(buildTestRunPayload("platform_api_e2e_check", chatMemoryForm)).toEqual({
      run_type: "platform_api_e2e_check",
    });
  });

  it("builds the focused chat-memory payload with the established numeric fallbacks", () => {
    expect(
      buildTestRunPayload("chat_memory_eval", {
        ...chatMemoryForm,
        rounds: "0",
        timeoutSeconds: "0",
        retryCount: "-1",
        judgeEnabled: false,
      }),
    ).toEqual({
      run_type: "chat_memory_eval",
      model: "openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8",
      prompt_key: "chat_v20260516",
      persona_key: "chat_linxiaotang",
      embedding: "letta/letta-free",
      fixture_key: "recent_user_chat_turns",
      rounds: 1,
      timeout_seconds: 180,
      retry_count: 0,
      judge_enabled: false,
    });
  });
});
