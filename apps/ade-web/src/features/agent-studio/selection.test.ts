import { describe, expect, it } from "vitest";

import { NEW_RESOURCE_VALUE, activeSessionForConversation, defaultBundle, isArchived, selectedConversationFromQuery } from "./selection";
import type { AgentStudioOptions, AgentStudioSession } from "./types";

const options: AgentStudioOptions = {
  runtime: "ade_native_v3",
  default_bundle_key: "dgx",
  bundles: [{
    key: "dgx", name: "DGX", model_key: "model", reviewer_model_key: "reviewer", embedding_model_key: "embedding",
    prompt_key: "chat", persona_key: "persona", tool_names: ["search_memory"], memory_policy_version: "v1",
    qualification_state: "qualified", deployments: [],
  }],
  default_timeout_seconds: 180,
  default_retry_count: 0,
  max_retry_count: 5,
};

const session = {
  session_id: "conversation-1", idempotent_replay: false,
  agent_definition: { id: "version-1", agent_definition_id: "definition-1", definition_key: "native", version: 1, name: "Native", prompt_key: "chat", prompt_sha256: "p", persona_key: "persona", persona_sha256: "q", tool_names: ["search_memory"], memory_policy_version: "v1", qualification_state: "qualified", deployments: [], archived_at: null, created_at: "2026-09-02T00:00:00Z" },
  memory_subject: { id: "subject-1", external_key: "wei", display_name: "Wei", version: 1, archived_at: null, created_at: "2026-09-02T00:00:00Z", updated_at: null },
  conversation: { id: "conversation-1", agent_definition_id: "version-1", memory_subject_id: "subject-1", title: "A conversation", purpose: "agent_studio" as const, version: 1, archived_at: null, created_at: "2026-09-02T00:00:00Z" },
  latest_run: null,
} satisfies AgentStudioSession;

describe("Agent Studio selection", () => {
  it("uses a conversation id only when the query value is meaningful", () => {
    expect(selectedConversationFromQuery(null)).toBeNull();
    expect(selectedConversationFromQuery("  ")).toBeNull();
    expect(selectedConversationFromQuery(" conversation-1 ")).toBe("conversation-1");
  });

  it("keeps the release-selected qualified bundle as the creation default", () => {
    expect(defaultBundle(options)?.key).toBe("dgx");
    expect(NEW_RESOURCE_VALUE).not.toBe("version-1");
  });

  it("finds the selected immutable conversation and recognizes archive state", () => {
    expect(activeSessionForConversation([session], "conversation-1")).toEqual(session);
    expect(activeSessionForConversation([session], "missing")).toBeNull();
    expect(isArchived(session.conversation)).toBe(false);
    expect(isArchived({ archived_at: "2026-09-02T00:00:00Z" })).toBe(true);
  });
});
