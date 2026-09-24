// @vitest-environment jsdom
import { act, useEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AgentStudioSession, ConversationState, MemoryEvidence, Run, RunEvent, SubjectMemories } from "./types";
import { useAgentStudio } from "./use-agent-studio";

const navigation = vi.hoisted(() => {
  const state = { query: new URLSearchParams("conversation=A") };
  const router = { replace: vi.fn((url: string) => { state.query = new URLSearchParams(url.split("?")[1] || ""); }) };
  return { state, router };
});
const api = vi.hoisted(() => ({
  getAgentStudioOptions: vi.fn(), listAgentStudioSessions: vi.fn(), listAgentStudioDefinitions: vi.fn(),
  listAgentStudioSubjects: vi.fn(), getAgentStudioSession: vi.fn(), getConversationState: vi.fn(),
  getSubjectMemories: vi.fn(), listConversationRuns: vi.fn(), getRun: vi.fn(), getRunEventLog: vi.fn(),
  acceptTurn: vi.fn(), createAgentStudioSession: vi.fn(), archiveAgentStudioDefinition: vi.fn(),
  archiveAgentStudioSession: vi.fn(), archiveAgentStudioSubject: vi.fn(), cancelRun: vi.fn(),
  restoreAgentStudioDefinition: vi.fn(), restoreAgentStudioSession: vi.fn(),
  restoreAgentStudioSubject: vi.fn(), updateAgentStudioSubject: vi.fn(),
  removeSavedMemory: vi.fn(),
}));
const streams = vi.hoisted(() => ({ calls: [] as Array<{ runId: string; handlers: {
  onEvent: (event: RunEvent) => void; onTerminal: (event: RunEvent) => void; onError: () => void;
} }>, close: vi.fn() }));

vi.mock("next/navigation", () => ({
  usePathname: () => "/agent-studio", useRouter: () => navigation.router,
  useSearchParams: () => navigation.state.query,
}));
vi.mock("./api", () => api);
vi.mock("./event-stream", () => ({
  TERMINAL_RUN_EVENT_TYPES: new Set(["run.completed", "run.failed", "run.cancelled"]),
  openRunEventStream: (runId: string, handlers: typeof streams.calls[number]["handlers"]) => {
    streams.calls.push({ runId, handlers });
    return { close: streams.close };
  },
}));
vi.mock("./use-definition-version", () => ({
  useDefinitionVersion: () => ({
    prompts: [], personas: [], versionPromptKey: "", versionPersonaKey: "", versionName: "",
    setVersionPromptKey: vi.fn(), setVersionPersonaKey: vi.fn(), setVersionName: vi.fn(),
    createDefinitionVersion: vi.fn(),
  }),
}));

const evidence: MemoryEvidence = { message_id: "message-5", conversation_id: "A", message_sequence: 5,
  start_char: 0, end_char: 3, quote: "tea", message_sha256: "a".repeat(64) };
const run = (status: Run["status"]): Run => ({ id: "run-A", conversation_id: "A", status,
  qualification_state: "qualified", attempt_count: 1, timeout_seconds: 180, retry_count: 0,
  cancellation_requested_at: null, error_code: null, error_message: null,
  created_at: "2026-09-22T00:00:00Z", started_at: null, finished_at: null });
const terminalEvent: RunEvent = { id: "event-1", schema_version: 1, run_id: "run-A", sequence: 1,
  attempt: 1, type: "run.completed", occurred_at: "2026-09-22T00:00:00Z", correlation_id: "run-A",
  causation_id: null, visibility: "operator", payload: {} };
const memory = (version: number): SubjectMemories => ({ subject_id: "subject-A", memory_generation: version, facts: [{
  id: "fact-1", key: "tea", fact_type: "person.preference", entity_id: "subject-A", entity_kind: "subject",
  entity_label: "User", qualifier: null, value: "tea", status: "active", version,
  revisions: [], updated_at: "2026-09-22T00:00:00Z",
}] });
function session(id: string, latestRun: Run | null = null): AgentStudioSession {
  return { session_id: id, idempotent_replay: false,
    agent_definition: { id: "definition-v1", agent_definition_id: "definition-root", definition_key: "native",
      version: 1, name: "Native", prompt_key: "prompt", prompt_sha256: "a", persona_key: "persona",
      persona_sha256: "b", tool_names: [], memory_policy_version: "v1", qualification_state: "qualified",
      deployments: [], archived_at: null, created_at: "2026-09-22T00:00:00Z" },
    memory_subject: { id: `subject-${id}`, external_key: id, display_name: id, version: 1,
      archived_at: null, created_at: "2026-09-22T00:00:00Z", updated_at: null },
    conversation: { id, agent_definition_id: "definition-v1", memory_subject_id: `subject-${id}`,
      title: id, purpose: "agent_studio", version: 1, archived_at: null, created_at: "2026-09-22T00:00:00Z" },
    latest_run: latestRun };
}
function state(id: string, before?: number): ConversationState {
  const messages = before === 6 ? [{ id: "message-5", sequence: 5, role: "user" as const,
    content: "tea", run_id: null, created_at: "2026-09-22T00:00:00Z" }] : [];
  return { ...session(id).conversation, messages, message_total: messages.length,
    messages_truncated: false, next_before_sequence: null, summary: null };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

let root: Root;
let container: HTMLDivElement;
let controller: ReturnType<typeof useAgentStudio>;
function Probe() {
  const current = useAgentStudio();
  useEffect(() => { controller = current; });
  return null;
}
async function render() { await act(async () => { root.render(<Probe />); await Promise.resolve(); }); }
async function flush() { await act(async () => { await new Promise((done) => setTimeout(done, 0)); }); }

beforeEach(() => {
  vi.clearAllMocks(); streams.calls.length = 0;
  navigation.state.query = new URLSearchParams("conversation=A");
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div"); document.body.append(container); root = createRoot(container);
  api.getAgentStudioOptions.mockResolvedValue({ runtime: "ade_native", default_bundle_key: "bundle", bundles: [{
    key: "bundle", name: "Bundle", model_key: "model", reviewer_model_key: "reviewer",
    embedding_model_key: "embedding", prompt_key: "prompt", persona_key: "persona", tool_names: [],
    memory_policy_version: "v1", qualification_state: "qualified", deployments: [],
  }], default_timeout_seconds: 180, default_retry_count: 0, max_retry_count: 5 });
  api.listAgentStudioSessions.mockResolvedValue({ items: [session("A"), session("B")], total: 2 });
  api.listAgentStudioDefinitions.mockResolvedValue({ items: [session("A").agent_definition], total: 1 });
  api.listAgentStudioSubjects.mockResolvedValue({ items: [session("A").memory_subject, session("B").memory_subject], total: 2 });
  api.getAgentStudioSession.mockImplementation(async (id: string) => session(id));
  api.getConversationState.mockImplementation(async (id: string, before?: number) => state(id, before));
  api.getSubjectMemories.mockImplementation(async (id: string) => id === "subject-A" ? memory(1) : { subject_id: id, facts: [] });
  api.listConversationRuns.mockResolvedValue({ items: [], total: 0 });
  api.getRun.mockResolvedValue(run("succeeded"));
  api.getRunEventLog.mockResolvedValue({ items: [], total: 0 });
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = false;
});

describe("Agent Studio async ownership", () => {
  it("keeps a live run monitored through same-conversation evidence navigation and refreshes on terminal", async () => {
    api.getAgentStudioSession.mockImplementation(async (id: string) => session(id, id === "A" ? run("running") : null));
    await render();
    expect(streams.calls).toHaveLength(1);
    await act(async () => { await controller.openEvidence(evidence); });
    expect(controller.evidenceMessageId).toBe("message-5");
    api.getSubjectMemories.mockResolvedValue(memory(2));
    await act(async () => { streams.calls[0].handlers.onTerminal(terminalEvent); await Promise.resolve(); });
    await flush();
    expect(controller.run?.status).toBe("succeeded");
    expect(controller.memories?.facts[0].version).toBe(2);
  });

  it("drops late stream and error callbacks after A to B selection", async () => {
    api.getAgentStudioSession.mockImplementation(async (id: string) => session(id, id === "A" ? run("running") : null));
    await render();
    const old = streams.calls[0].handlers;
    await act(async () => { controller.selectConversation("B"); });
    await render();
    await act(async () => { old.onError(); old.onEvent(terminalEvent); old.onTerminal(terminalEvent); });
    expect(controller.session?.conversation.id).toBe("B");
    expect(controller.error).toBe("");
    expect(controller.streamWarning).toBe("");
    expect(api.getRun).not.toHaveBeenCalled();
  });

  it("rejects a late turn acceptance after selection changes", async () => {
    const acceptance = deferred<{ run_id: string; status: string; events_url: string; idempotent_replay: boolean }>();
    api.acceptTurn.mockReturnValue(acceptance.promise);
    await render();
    await act(async () => { controller.setMessage("A turn"); });
    let sending!: Promise<void>;
    await act(async () => { sending = controller.sendMessage(); await Promise.resolve(); });
    await act(async () => { controller.selectConversation("B"); });
    await render();
    await act(async () => { acceptance.resolve({ run_id: "run-A", status: "pending", events_url: "", idempotent_replay: false }); await sending; });
    expect(controller.session?.conversation.id).toBe("B");
    expect(api.getRun).not.toHaveBeenCalled();
    expect(streams.calls).toHaveLength(0);
  });

  it("keeps a newly chosen definition after a same-conversation read refresh", async () => {
    await render();
    await act(async () => { controller.setDefinitionChoice("definition-v2"); });
    await act(async () => { await controller.openEvidence(evidence); });
    expect(controller.definitionChoice).toBe("definition-v2");
  });

  it("returns from a cited historical page to the latest transcript", async () => {
    api.getConversationState.mockImplementation(async (id: string, before?: number) => before === 6 ? state(id, before) : {
      ...state(id), messages: [{ id: "message-100", sequence: 100, role: "assistant", content: "latest",
        run_id: null, created_at: "2026-09-22T00:00:00Z" }],
    });
    await render();
    await act(async () => { await controller.openEvidence(evidence); });
    expect(controller.conversation?.messages[0].id).toBe("message-5");
    await act(async () => { await controller.returnToLatestMessages(); });
    expect(controller.conversation?.messages[0].id).toBe("message-100");
    expect(controller.evidenceMessageId).toBe("");
    expect(api.restoreAgentStudioSession).not.toHaveBeenCalled();
  });

  it("resumes a running monitor after revisiting its conversation", async () => {
    api.getAgentStudioSession.mockImplementation(async (id: string) => session(id, id === "A" ? run("running") : null));
    await render();
    expect(streams.calls.map((call) => call.runId)).toEqual(["run-A"]);
    await act(async () => { controller.selectConversation("B"); });
    await render();
    await act(async () => { controller.selectConversation("A"); });
    await render();
    expect(streams.calls.map((call) => call.runId)).toEqual(["run-A", "run-A"]);
  });

  it("ignores an error from an obsolete same-conversation read", async () => {
    const obsolete = deferred<AgentStudioSession>();
    await render();
    api.getAgentStudioSession.mockReturnValueOnce(obsolete.promise);
    await act(async () => { void controller.openEvidence(evidence); });
    await act(async () => { await controller.returnToLatestMessages(); });
    await act(async () => { obsolete.reject(new Error("obsolete read failed")); await Promise.resolve(); });
    expect(controller.error).toBe("");
    expect(controller.session?.conversation.id).toBe("A");
  });

  it("deduplicates rapid requests for the same older message page", async () => {
    const older = deferred<ConversationState>();
    api.getConversationState.mockImplementation(async (id: string, before?: number) => before === 100 ? older.promise : {
      ...state(id), messages: [{ id: "message-100", sequence: 100, role: "user", content: "latest", run_id: null, created_at: "2026-09-22T00:00:00Z" }],
      message_total: 100, messages_truncated: true, next_before_sequence: 100,
    });
    await render();
    await act(async () => { void controller.loadOlderMessages(); void controller.loadOlderMessages(); });
    expect(api.getConversationState.mock.calls.filter((args) => args[1] === 100)).toHaveLength(1);
    await act(async () => { older.resolve({ ...state("A"), messages: [{ id: "message-1", sequence: 1, role: "user", content: "old", run_id: null, created_at: "2026-09-22T00:00:00Z" }], message_total: 100, messages_truncated: false, next_before_sequence: null }); });
    expect(controller.conversation?.messages.map((item) => item.id)).toEqual(["message-1", "message-100"]);
  });

  it("removes from a subject without selecting or restoring a conversation", async () => {
    navigation.state.query = new URLSearchParams();
    vi.stubGlobal("confirm", vi.fn(() => true));
    api.removeSavedMemory.mockResolvedValue({ action_id: "action-1", outcome: "committed",
      revision_ids: ["revision-1"], resulting_memory_generation: 2, idempotent_replay: false,
      committed_at: "2026-09-24T00:00:00Z" });
    api.getSubjectMemories.mockResolvedValueOnce(memory(1)).mockResolvedValueOnce({
      subject_id: "subject-A", memory_generation: 2, facts: [{ ...memory(1).facts[0],
        status: "forgotten", value: null, version: 2,
        revisions: [{ id: "revision-1", operation: "forget", fact_version: 2, value: null,
          run_id: null, action_id: "action-1", predecessor_revision_ids: [], evidence: [],
          created_at: "2026-09-24T00:00:00Z" }] }],
    });
    await render();
    await act(async () => { await controller.inspectSubject("subject-A"); });
    expect(controller.session).toBeNull();
    await act(async () => { await controller.removeSavedFact("fact-1", 1); });
    expect(api.removeSavedMemory).toHaveBeenCalledWith("subject-A", expect.objectContaining({
      expected_memory_generation: 1, targets: [{ fact_id: "fact-1", expected_version: 1 }],
    }));
    expect(controller.removal?.receipt?.action_id).toBe("action-1");
    expect(controller.inspectedMemories?.facts[0].status).toBe("forgotten");
    expect(api.acceptTurn).not.toHaveBeenCalled();
    expect(api.restoreAgentStudioSession).not.toHaveBeenCalled();
  });

  it("recovers an ambiguous removal with the original action key", async () => {
    navigation.state.query = new URLSearchParams();
    vi.stubGlobal("confirm", vi.fn(() => true));
    api.removeSavedMemory.mockRejectedValueOnce(new Error("network lost"))
      .mockResolvedValueOnce({ action_id: "action-1", outcome: "committed", revision_ids: ["revision-1"],
        resulting_memory_generation: 2, idempotent_replay: true, committed_at: "2026-09-24T00:00:00Z" });
    api.getSubjectMemories.mockResolvedValue(memory(1));
    await render();
    await act(async () => { await controller.inspectSubject("subject-A"); });
    await act(async () => { await controller.removeSavedFact("fact-1", 1); });
    expect(controller.removal?.unconfirmed).toBe(true);
    await act(async () => { await controller.retryRemoval(); });
    expect(api.removeSavedMemory).toHaveBeenCalledTimes(2);
    expect(api.removeSavedMemory.mock.calls[0][1].idempotency_key)
      .toBe(api.removeSavedMemory.mock.calls[1][1].idempotency_key);
    expect(controller.removal?.receipt?.idempotent_replay).toBe(true);
  });
});
