import { expect, it } from "vitest";

import { NEW_RESOURCE_VALUE } from "./selection";
import { sessionDraftPayload } from "./session-draft";
import type { AgentStudioOptions } from "./types";

const options: AgentStudioOptions = {
  runtime: "ade_native", default_bundle_key: "bundle", bundles: [{ key: "bundle", name: "Bundle",
    model_key: "model", reviewer_model_key: "reviewer", embedding_model_key: "embedding",
    prompt_key: "prompt", persona_key: "persona", tool_names: ["search_memory"],
    memory_policy_version: "v1", qualification_state: "qualified", deployments: [] }],
  default_timeout_seconds: 180, default_retry_count: 0, max_retry_count: 5,
};

it("preserves an explicitly selected subject and definition when creating a new conversation", () => {
  const payload = sessionDraftPayload(options, { title: "  Next conversation ", definitionChoice: "definition-v2",
    definitionName: "unused", definitionKey: "unused", subjectChoice: "subject-1",
    subjectName: "unused", subjectKey: "unused" }, "request-1");
  expect(payload).toMatchObject({ title: "Next conversation", agent_definition_id: "definition-v2",
    memory_subject_id: "subject-1", idempotency_key: "request-1" });
  expect(payload.new_definition).toBeUndefined();
  expect(payload.new_subject).toBeUndefined();
});

it("requires a name and key for an intentionally new subject", () => {
  expect(() => sessionDraftPayload(options, { title: "Next", definitionChoice: "definition-v2",
    definitionName: "unused", definitionKey: "unused", subjectChoice: NEW_RESOURCE_VALUE,
    subjectName: " ", subjectKey: "new-person" }, "request-2")).toThrow("subject name and external key");
});
