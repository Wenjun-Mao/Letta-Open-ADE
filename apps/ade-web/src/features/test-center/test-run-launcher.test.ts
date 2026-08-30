import { describe, expect, it } from "vitest";

import {
  buildTestRunPayload,
  type AgentRuntimeV3AcceptanceFormState,
  type ChatMemoryEvalFormState,
} from "./test-run-launcher";
import {
  hasAgentRuntimeV3AcceptanceDeployments,
  reconcileAgentRuntimeV3AcceptanceForm,
} from "./agent-runtime-v3-acceptance-fields";

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

const v3AcceptanceForm: AgentRuntimeV3AcceptanceFormState = {
  conversationModelKey: "dgx_vllm::qwen3.6-35b-a3b-fp8",
  reviewerModelKey: "dgx_vllm::qwen3.6-35b-a3b-fp8",
  embeddingModelKey: "dgx_embedding_sidecar::qwen3-embedding-0.6b",
  rounds: "3",
  timeoutSeconds: "180",
  retryCount: "0",
  includeLlamaCompatibility: true,
  caseKeys: [],
};

describe("Test Center run launcher", () => {
  it("does not leak chat-memory fields into standard run payloads", () => {
    expect(buildTestRunPayload("ade_api_e2e_check", chatMemoryForm)).toEqual({
      run_type: "ade_api_e2e_check",
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

  it("builds a bounded v3 acceptance payload without chat-memory fields", () => {
    expect(
      buildTestRunPayload(
        "agent_runtime_v3_acceptance",
        chatMemoryForm,
        {
          ...v3AcceptanceForm,
          rounds: "9",
          timeoutSeconds: "0",
          retryCount: "8",
          includeLlamaCompatibility: false,
        },
      ),
    ).toEqual({
      run_type: "agent_runtime_v3_acceptance",
      conversation_model_key: "dgx_vllm::qwen3.6-35b-a3b-fp8",
      reviewer_model_key: "dgx_vllm::qwen3.6-35b-a3b-fp8",
      embedding_model_key: "dgx_embedding_sidecar::qwen3-embedding-0.6b",
      rounds: 3,
      timeout_seconds: 180,
      retry_count: 5,
      include_llama_compatibility: false,
    });
  });

  it("clamps the v3 timeout to the workflow minimum", () => {
    expect(
      buildTestRunPayload(
        "agent_runtime_v3_acceptance",
        chatMemoryForm,
        { ...v3AcceptanceForm, timeoutSeconds: "1" },
      ).timeout_seconds,
    ).toBe(5);
  });

  it("builds a canonical focused diagnostic payload that cannot claim promotion evidence", () => {
    expect(
      buildTestRunPayload(
        "agent_runtime_v3_acceptance",
        chatMemoryForm,
        {
          ...v3AcceptanceForm,
          caseKeys: ["weather_tool_failure", "chat_memory_baseline"],
          rounds: "3",
          includeLlamaCompatibility: true,
        },
      ),
    ).toEqual({
      run_type: "agent_runtime_v3_acceptance",
      conversation_model_key: "dgx_vllm::qwen3.6-35b-a3b-fp8",
      reviewer_model_key: "dgx_vllm::qwen3.6-35b-a3b-fp8",
      embedding_model_key: "dgx_embedding_sidecar::qwen3-embedding-0.6b",
      case_keys: ["chat_memory_baseline", "weather_tool_failure"],
      rounds: 1,
      timeout_seconds: 180,
      retry_count: 0,
      include_llama_compatibility: false,
    });
  });

  it("reconciles changed deployment aliases by role instead of keeping stale defaults", () => {
    const deployment = (deploymentId: string, roles: Array<"conversation" | "reviewer" | "retriever">) => ({
      deployment_id: deploymentId,
      roles,
      lifecycle: "candidate" as const,
      fingerprint: { sha256: `${deploymentId}-fingerprint` },
      qualification: { qualified: false, role_results: [] },
    });
    const deployments = [
        {
          model_key: "new::chat",
          source_id: "new",
          source_label: "New chat",
          provider_model_id: "chat",
          model_type: "llm",
          deployment: deployment("chat", ["conversation", "reviewer"]),
        },
        {
          model_key: "new::embedding",
          source_id: "new",
          source_label: "New embedding",
          provider_model_id: "embedding",
          model_type: "embedding",
          deployment: deployment("embedding", ["retriever"]),
        },
      ];
    expect(
      reconcileAgentRuntimeV3AcceptanceForm(v3AcceptanceForm, deployments),
    ).toMatchObject({
      conversationModelKey: "new::chat",
      reviewerModelKey: "new::chat",
      embeddingModelKey: "new::embedding",
    });
    expect(hasAgentRuntimeV3AcceptanceDeployments(deployments)).toBe(true);
    expect(hasAgentRuntimeV3AcceptanceDeployments(deployments.slice(0, 1))).toBe(false);
  });
});
