import { describe, expect, it } from "vitest";

import type { AgentRuntimeParityListItem } from "./api";
import { parityRoundProgress } from "./agent-runtime-parity-result-view";

const result: AgentRuntimeParityListItem = {
  run_id: "run-1",
  run_status: "succeeded",
  created_at: "",
  finished_at: "",
  ready: true,
  config: {
    prompt_key: "chat_v20260516",
    persona_key: "chat_linxiaotang",
    legacy_model: "legacy",
    legacy_embedding: "legacy-embedding",
    native_conversation_model: "conversation",
    native_reviewer_model: "reviewer",
    native_embedding_model: "embedding",
    rounds: 3,
    timeout_seconds: 180,
    retry_count: 0,
  },
  passed: true,
  inputs_comparable: true,
  cleanup_complete: true,
  rounds_requested: 3,
  rounds_completed: 3,
  rounds_passed: 3,
  artifact_digests: null,
};

describe("Agent Runtime parity result projection", () => {
  it("shows passed, completed, and requested rounds in evidence order", () => {
    expect(parityRoundProgress(result)).toBe("3/3/3");
  });

  it("does not invent progress before verified artifacts are ready", () => {
    expect(parityRoundProgress({ ...result, rounds_requested: null })).toBe("-");
  });
});
