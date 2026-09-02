import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { AgentRuntimeParityDetail, AgentRuntimeParityListItem } from "./api";
import {
  AgentRuntimeParityResultView,
  legacyBaselineRoundProgress,
  parityRoundProgress,
} from "./agent-runtime-parity-result-view";
import { getTestCenterCopy } from "./test-center-copy";

const result: AgentRuntimeParityListItem = {
  run_id: "run-1",
  run_status: "succeeded",
  created_at: "",
  finished_at: "",
  ready: true,
  evidence_schema_version: 2,
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
  native_rounds_passed: 3,
  legacy_rounds_passed: 0,
  native_not_worse_than_legacy: true,
  rounds_passed: 3,
  artifact_digests: null,
};

describe("Agent Runtime parity result projection", () => {
  it("shows the candidate and observed baseline progress independently", () => {
    expect(parityRoundProgress(result)).toBe("3/3/3");
    expect(legacyBaselineRoundProgress(result)).toBe("0/3/3");
  });

  it("uses the compatibility candidate count but never invents a legacy baseline count", () => {
    const historicalReceipt = {
      ...result,
      native_rounds_passed: null,
      legacy_rounds_passed: null,
    };

    expect(parityRoundProgress(historicalReceipt)).toBe("3/3/3");
    expect(legacyBaselineRoundProgress(historicalReceipt)).toBe("-");
  });

  it("does not invent progress before verified artifacts are ready", () => {
    expect(parityRoundProgress({ ...result, rounds_requested: null })).toBe("-");
  });

  it("keeps a passing native candidate distinct from a failing Letta baseline", () => {
    const detail: AgentRuntimeParityDetail = {
      ...result,
      checks: {},
      comparability_checks: {},
      cleanup: {
        completed: true,
        legacy_completed: true,
        native_completed: true,
        legacy_creation_indeterminate: false,
      },
      provenance: {
        source_revision: "revision",
        source_dirty: false,
        source_fingerprint: "fingerprint",
      },
      rounds: [{
        round: 1,
        passed: true,
        legacy_passed: false,
        native_passed: true,
        native_not_worse_than_legacy: true,
        legacy_checks: {},
        native_checks: {},
      }],
      turns: [],
    };

    const markup = renderToStaticMarkup(createElement(AgentRuntimeParityResultView, {
      copy: getTestCenterCopy("en"),
      busy: false,
      items: [result],
      selectedId: result.run_id,
      selectedSummary: result,
      selected: detail,
      artifacts: [],
      selectedArtifactId: "",
      artifactContent: "",
      onSelect: () => {},
      onRefresh: () => {},
      onReadArtifact: () => {},
    }));

    expect(markup).toContain("Native candidate meets the cutover contract");
    expect(markup).toContain("ADE-native v3 candidate: <strong>Passed</strong>");
    expect(markup).toContain("Letta v2 baseline: <strong>Failed</strong>");
    expect(markup).toContain("Native does not trail Letta");
    expect(markup).not.toContain("equivalent");
  });

  it("labels divergent schema-v1 evidence as a historical two-engine gate", () => {
    const historical: AgentRuntimeParityDetail = {
      ...result,
      evidence_schema_version: 1,
      passed: false,
      checks: {},
      comparability_checks: {},
      cleanup: {
        completed: true,
        legacy_completed: true,
        native_completed: true,
        legacy_creation_indeterminate: false,
      },
      provenance: {
        source_revision: "revision",
        source_dirty: false,
        source_fingerprint: "fingerprint",
      },
      rounds: [],
      turns: [],
    };

    const markup = renderToStaticMarkup(createElement(AgentRuntimeParityResultView, {
      copy: getTestCenterCopy("en"),
      busy: false,
      items: [historical],
      selectedId: historical.run_id,
      selectedSummary: historical,
      selected: historical,
      artifacts: [],
      selectedArtifactId: "",
      artifactContent: "",
      onSelect: () => {},
      onRefresh: () => {},
      onReadArtifact: () => {},
    }));

    expect(markup).toContain("Historical schema-v1 outcome");
    expect(markup).toContain("Historical two-engine gate failed");
    expect(markup).toContain("cannot approve cutover");
    expect(markup).not.toContain("Native candidate does not meet the cutover contract");
  });
});
