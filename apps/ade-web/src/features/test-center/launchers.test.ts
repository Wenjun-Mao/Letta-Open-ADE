import { describe, expect, it } from "vitest";

import {
  behaviorEvaluationFormFromDefaults,
  buildBehaviorEvaluationPayload,
} from "./behavior-evaluation-launcher";
import {
  buildNativeRuntimeQualificationPayload,
  nativeRuntimeQualificationFormFromDefaults,
} from "./native-runtime-qualification-launcher";

const behaviorDefaults = {
  model: "default::chat",
  prompt_key: "chat_default",
  persona_key: "chat_persona",
  embedding: "default::embedding",
  fixture_key: "recent_user_chat_turns",
  rounds: 3,
  timeout_seconds: 180,
  retry_count: 0,
  judge_enabled: true,
};

const nativeDefaults = {
  conversation_model_key: "native::conversation",
  reviewer_model_key: "native::reviewer",
  embedding_model_key: "native::embedding",
  prompt_key: "chat_default",
  persona_key: "chat_persona",
  rounds: 3,
  timeout_seconds: 180,
  retry_count: 0,
  include_llama_compatibility: true,
};

describe("Test Center launchers", () => {
  it("uses behavior defaults delivered by Test Center rather than frontend model constants", () => {
    const form = behaviorEvaluationFormFromDefaults(behaviorDefaults);

    expect(form).toMatchObject({
      model: "default::chat",
      fixtureKey: "recent_user_chat_turns",
      rounds: "3",
      timeoutSeconds: "180",
      retryCount: "0",
    });
    expect(
      buildBehaviorEvaluationPayload(
        { ...form, model: "", retryCount: "2" },
        behaviorDefaults,
      ),
    ).toEqual({
      run_type: "chat_memory_eval",
      model: "default::chat",
      prompt_key: "chat_default",
      persona_key: "chat_persona",
      embedding: "default::embedding",
      fixture_key: "recent_user_chat_turns",
      rounds: 3,
      timeout_seconds: 180,
      retry_count: 2,
      judge_enabled: true,
    });
  });

  it("uses the backend case order and enforces focused diagnostic semantics", () => {
    const form = nativeRuntimeQualificationFormFromDefaults(nativeDefaults);
    const payload = buildNativeRuntimeQualificationPayload(
      {
        ...form,
        caseKeys: ["weather_tool_failure", "chat_memory_baseline", "stale_case"],
        rounds: "3",
        retryCount: "1",
        includeLlamaCompatibility: true,
      },
      nativeDefaults,
      ["chat_memory_baseline", "weather_tool_failure"],
    );

    expect(payload).toEqual({
      run_type: "agent_runtime_acceptance",
      conversation_model_key: "native::conversation",
      reviewer_model_key: "native::reviewer",
      embedding_model_key: "native::embedding",
      prompt_key: "chat_default",
      persona_key: "chat_persona",
      case_keys: ["chat_memory_baseline", "weather_tool_failure"],
      rounds: 1,
      timeout_seconds: 180,
      retry_count: 1,
      include_llama_compatibility: false,
    });
  });

  it("keeps a full qualification run on server-provided defaults", () => {
    const form = nativeRuntimeQualificationFormFromDefaults(nativeDefaults);

    expect(
      buildNativeRuntimeQualificationPayload(form, nativeDefaults, ["chat_memory_baseline"]),
    ).toEqual({
      run_type: "agent_runtime_acceptance",
      conversation_model_key: "native::conversation",
      reviewer_model_key: "native::reviewer",
      embedding_model_key: "native::embedding",
      prompt_key: "chat_default",
      persona_key: "chat_persona",
      rounds: 3,
      timeout_seconds: 180,
      retry_count: 0,
      include_llama_compatibility: true,
    });
  });
});
