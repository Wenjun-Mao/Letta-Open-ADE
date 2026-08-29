import { describe, expect, it } from "vitest";

import type { ChatMemoryEvaluationMetrics } from "./api";
import {
  DEFAULT_CHAT_MEMORY_EVALUATION_FORM,
  buildPromptCenterEvaluationHref,
  diffMemoryLines,
  formatPassRate,
  isEvaluationRunning,
  reconcileChatMemoryEvaluationForm,
  summarizeDeterministicFailures,
  toChatMemoryEvaluationForm,
  resolveChatMemoryEvaluationLaunchState,
} from "./chat-memory-evaluation-helpers";

describe("chat-memory evaluation launch state", () => {
  it("hydrates the focused launcher from a valid evaluation URL", () => {
    expect(
      resolveChatMemoryEvaluationLaunchState(
        "?runType=chat_memory_eval&model=model-b&promptKey=chat_custom&personaKey=chat_persona&embedding=embed-b&fixtureKey=fixture-b&rounds=4&timeoutSeconds=240.5&retryCount=2&judgeEnabled=false",
      ),
    ).toEqual({
      runType: "chat_memory_eval",
      form: {
        model: "model-b",
        promptKey: "chat_custom",
        personaKey: "chat_persona",
        embedding: "embed-b",
        fixtureKey: "fixture-b",
        rounds: "4",
        timeoutSeconds: "240.5",
        retryCount: "2",
        judgeEnabled: false,
      },
    });
  });

  it("uses safe defaults for unsupported run types and invalid numeric query values", () => {
    expect(
      resolveChatMemoryEvaluationLaunchState(
        "?runType=unsupported&rounds=0&timeoutSeconds=601&retryCount=6&judgeEnabled=nope",
      ),
    ).toEqual({
      runType: "ade_api_e2e_check",
      form: DEFAULT_CHAT_MEMORY_EVALUATION_FORM,
    });
  });

  it("keeps the v3 acceptance launcher selectable without applying chat fields to its payload", () => {
    expect(
      resolveChatMemoryEvaluationLaunchState("?runType=agent_runtime_v3_acceptance"),
    ).toMatchObject({ runType: "agent_runtime_v3_acceptance" });
  });

  it("reconciles stale query selections with the available chat options", () => {
    expect(
      reconcileChatMemoryEvaluationForm(
        {
          ...DEFAULT_CHAT_MEMORY_EVALUATION_FORM,
          model: "missing-model",
          promptKey: "missing-prompt",
          personaKey: "chat_persona",
          embedding: "missing-embedding",
        },
        {
          models: [{ key: "model-a", label: "Model A", description: "" }],
          prompts: [{ key: "chat_default", label: "Default", description: "" }],
          personas: [{ key: "chat_persona", label: "Persona", description: "" }],
          embeddings: [{ key: "embed-a", label: "Embedding", description: "" }],
          defaults: {
            model: "model-a",
            prompt_key: "chat_default",
            persona_key: "chat_persona",
            embedding: "embed-a",
          },
        },
      ),
    ).toMatchObject({
      model: "model-a",
      promptKey: "chat_default",
      personaKey: "chat_persona",
      embedding: "embed-a",
    });
  });
});

describe("chat-memory evaluation display helpers", () => {
  const metrics: ChatMemoryEvaluationMetrics = {
    rounds_total: 4,
    rounds_passed: 3,
    rounds_failed: 1,
    errors: 0,
    pass_rate: 0.75,
    average_elapsed_seconds: 12.345,
    forbidden_hit_count: 0,
    memory_changed_rounds: 4,
    expected_facts_passed_rounds: 3,
    memory_tool_call_count: 7,
    total_tool_call_count: 9,
    cleanup_passed_rounds: 4,
  };

  it("formats pass rates and identifies only unfinished evaluations for polling", () => {
    expect(formatPassRate(metrics.pass_rate)).toBe("75%");
    expect(isEvaluationRunning({ run_status: "running", ready: false })).toBe(true);
    expect(isEvaluationRunning({ run_status: "running", ready: true })).toBe(true);
    expect(isEvaluationRunning({ run_status: "completed", ready: true })).toBe(false);
    expect(isEvaluationRunning({ run_status: "failed", ready: false })).toBe(false);
    expect(isEvaluationRunning({ run_status: "interrupted", ready: false })).toBe(false);
  });

  it("builds Prompt Center links and rerun presets from the selected evaluation setup", () => {
    expect(buildPromptCenterEvaluationHref("prompt", { prompt_key: "chat_custom", persona_key: "chat_persona" })).toBe(
      "/prompt-center?tab=prompts&scenario=chat&key=chat_custom",
    );
    expect(buildPromptCenterEvaluationHref("persona", { prompt_key: "chat_custom", persona_key: "chat_persona" })).toBe(
      "/prompt-center?tab=personas&scenario=chat&key=chat_persona",
    );
    expect(
      toChatMemoryEvaluationForm({
        model: "model-b",
        prompt_key: "chat_custom",
        persona_key: "chat_persona",
        embedding: "embed-b",
        fixture_key: "fixture-b",
        rounds: 5,
        timeout_seconds: 240,
        retry_count: 2,
        judge_enabled: false,
      }),
    ).toEqual({
      model: "model-b",
      promptKey: "chat_custom",
      personaKey: "chat_persona",
      embedding: "embed-b",
      fixtureKey: "recent_user_chat_turns",
      rounds: "5",
      timeoutSeconds: "240",
      retryCount: "2",
      judgeEnabled: false,
    });
  });

  it("reports added and removed memory lines while respecting duplicates", () => {
    expect(
      diffMemoryLines(
        "Name: unknown\n- likes tea\n- likes tea",
        "Name: 张伟\n- likes tea\n- has dog Rocky",
      ),
    ).toEqual({
      removed: ["Name: unknown", "- likes tea"],
      added: ["Name: 张伟", "- has dog Rocky"],
    });
    expect(diffMemoryLines("unchanged", "unchanged")).toEqual({
      removed: [],
      added: [],
    });
  });

  it("turns deterministic score fields into explicit failure evidence", () => {
    expect(
      summarizeDeterministicFailures({
        pass: false,
        forbidden_hits: ["我是AI"],
        human_memory_changed: false,
        expected_facts_passed: false,
        missing_expected_facts: ["dog_breed"],
      }),
    ).toEqual({
      forbiddenHits: ["我是AI"],
      missingExpectedFacts: ["dog_breed"],
      memoryDidNotChange: true,
      expectedFactsFailed: true,
    });
  });
});
