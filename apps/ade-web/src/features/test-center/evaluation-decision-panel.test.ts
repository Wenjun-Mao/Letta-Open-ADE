import { describe, expect, it } from "vitest";

import type { EvaluationListItem } from "./api";
import { decisionLabel, isPromotableEvaluation } from "./evaluation-decision-panel";
import { getTestCenterCopy } from "./test-center-copy";

function evaluation(overrides: Partial<EvaluationListItem> = {}): EvaluationListItem {
  return {
    run_id: "run-1",
    run_status: "passed",
    created_at: "",
    finished_at: "",
    ready: true,
    evidence_sha256: "0".repeat(64),
    config: {
      model: "model",
      prompt_key: "prompt",
      persona_key: "persona",
      embedding: "embedding",
      fixture_key: "fixture",
      rounds: 1,
      timeout_seconds: 180,
      retry_count: 0,
      judge_enabled: false,
    },
    metrics: {
      rounds_total: 1,
      rounds_passed: 1,
      rounds_failed: 0,
      errors: 0,
      pass_rate: 1,
      average_elapsed_seconds: 1,
      forbidden_hit_count: 0,
      memory_changed_rounds: 1,
      expected_facts_passed_rounds: 1,
      memory_tool_call_count: 1,
      total_tool_call_count: 1,
      cleanup_passed_rounds: 1,
    },
    provenance: {
      run_id: "run-1",
      captured_at: "",
      configuration_sha256: "a".repeat(64),
      provenance_sha256: "b".repeat(64),
      fixture_sha256: "c".repeat(64),
      prompt_content_sha256: "d".repeat(64),
      persona_content_sha256: "e".repeat(64),
      model_identity_sha256: "f".repeat(64),
      embedding_identity_sha256: null,
    },
    decision: null,
    preferred_baseline: false,
    ...overrides,
  };
}

describe("evaluation decisions", () => {
  it("only promotes complete deterministic passes with provenance", () => {
    expect(isPromotableEvaluation(evaluation())).toBe(true);
    expect(isPromotableEvaluation(evaluation({ provenance: null }))).toBe(false);
    expect(isPromotableEvaluation(evaluation({ metrics: { ...evaluation().metrics!, rounds_failed: 1 } }))).toBe(false);
  });

  it("uses explicit bilingual decision labels", () => {
    expect(decisionLabel("promote", getTestCenterCopy("en"))).toBe("Promoted baseline");
    expect(decisionLabel("reject", getTestCenterCopy("zh"))).toBe("已拒绝");
  });
});
