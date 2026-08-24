import { describe, expect, it } from "vitest";

import type { ScenarioOptions } from "@/features/model-catalog/api";
import { reconcileAgentCreationSettings, resolveInitialAgentCreationSettings } from "./creation-settings";

const options: ScenarioOptions = {
  scenario: "chat",
  models: [{ key: "model-a", label: "Model A", description: "" }],
  embeddings: [{ key: "embedding-a", label: "Embedding A", description: "" }],
  prompts: [{ key: "chat_v20260516", label: "Current", description: "" }],
  personas: [{ key: "chat_linxiaotang", label: "Persona", description: "" }],
  schemas: [],
  defaults: {
    scenario: "chat",
    model: "model-a",
    prompt_key: "chat_v20260516",
    persona_key: "chat_linxiaotang",
    embedding: "embedding-a",
    schema_key: "",
  },
  agent_studio: { temperature: 0.7, top_p: 0.9, top_k: 20 },
};

describe("Agent Studio creation settings", () => {
  it("honors valid prompt and persona query parameters without forcing a model", () => {
    expect(resolveInitialAgentCreationSettings(options, "?promptKey=chat_v20260516&personaKey=chat_linxiaotang")).toMatchObject({
      model: "",
      promptKey: "chat_v20260516",
      personaKey: "chat_linxiaotang",
      embedding: "embedding-a",
    });
  });

  it("falls back to backend defaults for invalid query parameters", () => {
    expect(resolveInitialAgentCreationSettings(options, "?promptKey=missing&personaKey=missing")).toMatchObject({
      promptKey: "chat_v20260516",
      personaKey: "chat_linxiaotang",
    });
  });

  it("keeps valid selections on refresh and restores only missing values", () => {
    expect(
      reconcileAgentCreationSettings(
        {
          model: "model-a",
          promptKey: "missing",
          personaKey: "chat_linxiaotang",
          embedding: "missing",
          temperature: "",
          topP: "0.5",
          topK: "",
        },
        options,
      ),
    ).toEqual({
      model: "model-a",
      promptKey: "chat_v20260516",
      personaKey: "chat_linxiaotang",
      embedding: "embedding-a",
      temperature: "0.7",
      topP: "0.5",
      topK: "20",
    });
  });

  it("does not silently choose a different model when a refreshed catalog drops the selection", () => {
    expect(
      reconcileAgentCreationSettings(
        {
          model: "missing-model",
          promptKey: "chat_v20260516",
          personaKey: "chat_linxiaotang",
          embedding: "embedding-a",
          temperature: "",
          topP: "",
          topK: "",
        },
        options,
      ).model,
    ).toBe("");
  });
});
