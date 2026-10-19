// @vitest-environment jsdom
import { act, useEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AgentStudioSession, ConversationState, MessageSource, Run, RunEvent } from "./types";
import { useAgentStudio } from "./use-agent-studio";

const navigation = vi.hoisted(() => {
  const state = { query: new URLSearchParams("conversation=A") };
  const router = { replace: vi.fn((url: string) => { state.query = new URLSearchParams(url.split("?")[1] || ""); }) };
  return { state, router };
});
const api = vi.hoisted(() => ({
  getAgentStudioOptions: vi.fn(), listAgentStudioSessions: vi.fn(), listAgentStudioDefinitions: vi.fn(),
  listAgentStudioSubjects: vi.fn(), getAgentStudioSession: vi.fn(), getConversationState: vi.fn(),
  getRelationshipMemories: vi.fn(), getMemoryDeliveries: vi.fn(), getMemoryOperations: vi.fn(), getMemorySource: vi.fn(), retryMemoryDelivery: vi.fn(), retryRun: vi.fn(),
  listConversationRuns: vi.fn(), listConversationActivity: vi.fn(), getRun: vi.fn(), getRunEventLog: vi.fn(),
  acceptTurn: vi.fn(), createAgentStudioSession: vi.fn(), archiveAgentStudioDefinition: vi.fn(),
  archiveAgentStudioSession: vi.fn(), archiveAgentStudioSubject: vi.fn(), cancelRun: vi.fn(),
  restoreAgentStudioDefinition: vi.fn(), restoreAgentStudioSession: vi.fn(),
  restoreAgentStudioSubject: vi.fn(), updateAgentStudioSubject: vi.fn(),
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

const evidence: MessageSource = { message_id: "message-5", conversation_id: "A", message_sequence: 5 };
const run = (status: Run["status"]): Run => ({ id: "run-A", conversation_id: "A", status,
  qualification_state: "qualified", attempt_count: 1, timeout_seconds: 180, retry_count: 0,
  cancellation_requested_at: null, error_code: null, error_message: null, paused_at: null,
  created_at: "2026-09-22T00:00:00Z", started_at: null, finished_at: null });
const terminalEvent: RunEvent = { id: "event-1", schema_version: 1, run_id: "run-A", sequence: 1,
  attempt: 1, type: "run.completed", occurred_at: "2026-09-22T00:00:00Z", correlation_id: "run-A",
  causation_id: null, visibility: "operator", payload: {} };
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
    key: "bundle", name: "Bundle", model_key: "model", compaction_model_key: "compaction",
    prompt_key: "prompt", persona_key: "persona", tool_names: [],
    memory_policy_version: "v1", qualification_state: "qualified", deployments: [],
  }], default_timeout_seconds: 180, default_retry_count: 0, max_retry_count: 5 });
  api.listAgentStudioSessions.mockResolvedValue({ items: [session("A"), session("B")], total: 2 });
  api.listAgentStudioDefinitions.mockResolvedValue({ items: [session("A").agent_definition], total: 1 });
  api.listAgentStudioSubjects.mockResolvedValue({ items: [session("A").memory_subject, session("B").memory_subject], total: 2 });
  api.getAgentStudioSession.mockImplementation(async (id: string) => session(id));
  api.getConversationState.mockImplementation(async (id: string, before?: number) => state(id, before));
  const read = async (id: string, root: string) => ({ relationship: { subject_id: id, character_root_id: root }, items: [], total: 0, counts: {} });
  api.getRelationshipMemories.mockImplementation(read);
  api.getMemoryDeliveries.mockImplementation(read);
  api.getMemoryOperations.mockImplementation(read);
  api.listConversationRuns.mockResolvedValue({ items: [], total: 0 });
  api.listConversationActivity.mockResolvedValue({ items: [] });
  api.getRun.mockResolvedValue(run("succeeded"));
  api.getRunEventLog.mockResolvedValue({ items: [], total: 0 });
});
afterEach(async () => {
  await act(async () => root.unmount());
  vi.useRealTimers();
  container.remove();
  vi.unstubAllGlobals();
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = false;
});

describe("Agent Studio async ownership", () => {
  it("does not silently select a character based only on a person", async () => {
    navigation.state.query = new URLSearchParams();
    api.listAgentStudioSessions.mockImplementation(async (includeArchived: boolean) =>
      includeArchived ? { items: [session("archived")], total: 1 } : { items: [], total: 0 });
    await render();
    await act(async () => { controller.selectSubjectForNewConversation("subject-archived"); });
    expect(controller.definitionChoice).toBe("__new__");
  });

  it("keeps hidden identities through failed starts, separates same-name people, and reuses selected bindings", async () => {
    navigation.state.query = new URLSearchParams();
    const createdSessions = new Map<string, AgentStudioSession>();
    api.getAgentStudioSession.mockImplementation(async (id: string) => createdSessions.get(id) || session(id));
    api.createAgentStudioSession.mockRejectedValueOnce(new Error("network lost"));
    api.createAgentStudioSession.mockImplementation(async (payload: { new_subject?: { external_key: string } }) => {
      const created = { ...session(`created-${api.createAgentStudioSession.mock.calls.length}`),
        memory_subject: { ...session("created").memory_subject,
        id: `person-${api.createAgentStudioSession.mock.calls.length}`,
        external_key: payload.new_subject?.external_key || "existing" } };
      createdSessions.set(created.conversation.id, created);
      return created;
    });
    await render();
    await act(async () => { controller.setSubjectName("Alex"); });
    await act(async () => { await controller.createSession(); });
    const first = api.createAgentStudioSession.mock.calls[0][0];
    expect(first.new_subject.display_name).toBe("Alex");
    expect(first.new_subject.external_key).toMatch(/^studio-person-/);
    await act(async () => { await controller.createSession(); });
    const retried = api.createAgentStudioSession.mock.calls[1][0];
    expect(retried.new_subject.external_key).toBe(first.new_subject.external_key);
    expect(retried.idempotency_key).toBe(first.idempotency_key);
    expect(controller.subjectChoice).toBe("person-2");
    expect(controller.definitionChoice).toBe("definition-v1");
    await act(async () => { await controller.createSession(); });
    const reused = api.createAgentStudioSession.mock.calls[2][0];
    expect(reused.memory_subject_id).toBe("person-2");
    expect(reused.agent_definition_id).toBe("definition-v1");
    expect(reused.new_subject).toBeUndefined();
    await act(async () => { controller.selectSubjectForNewConversation("__new__"); controller.setSubjectName("Alex"); });
    await act(async () => { await controller.createSession(); });
    const distinct = api.createAgentStudioSession.mock.calls[3][0];
    expect(distinct.new_subject.display_name).toBe("Alex");
    expect(distinct.new_subject.external_key).not.toBe(first.new_subject.external_key);
  });

  it("keeps a live run monitored through same-conversation evidence navigation and refreshes on terminal", async () => {
    api.getAgentStudioSession.mockImplementation(async (id: string) => session(id, id === "A" ? run("running") : null));
    await render();
    expect(streams.calls).toHaveLength(1);
    await act(async () => { await controller.openEvidence(evidence); });
    expect(controller.evidenceMessageId).toBe("message-5");
    await act(async () => { streams.calls[0].handlers.onTerminal(terminalEvent); await Promise.resolve(); });
    await flush();
    expect(controller.run?.status).toBe("succeeded");
    expect(controller.conversation?.id).toBe("A");
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

  it("keeps monitoring through ordinary edits and stream failure, then recovers through polling", async () => {
    vi.useFakeTimers();
    api.getAgentStudioSession.mockImplementation(async (id: string) => session(id, run("succeeded")))
      .mockResolvedValueOnce(session("A", run("running")));
    await render();
    const closed = streams.close.mock.calls.length;
    await act(async () => { controller.setMessage("draft"); controller.setTimeoutSeconds(90); });
    await render();
    expect(controller.message).toBe("draft");
    expect(streams.calls).toHaveLength(1);
    expect(streams.close).toHaveBeenCalledTimes(closed);
    await act(async () => {
      const handlers = streams.calls[0].handlers;
      handlers.onEvent({ ...terminalEvent, id: "event-2", sequence: 2, type: "run.started" });
      handlers.onEvent({ ...terminalEvent, type: "run.accepted" });
      handlers.onEvent({ ...terminalEvent, type: "run.accepted" });
    });
    expect(controller.events.map((event) => event.sequence)).toEqual([1, 2]);
    await act(async () => { streams.calls[0].handlers.onError(); });
    expect(controller.streamWarning).toContain("polling remains active");
    await act(async () => { await vi.advanceTimersByTimeAsync(1500); });
    expect(controller.run?.status).toBe("succeeded");
    expect(controller.streamWarning).toBe("");
    expect(streams.close).toHaveBeenCalledTimes(closed + 1);
    expect(vi.getTimerCount()).toBe(3); // Independent Memory polling remains active.
  });

  it("deduplicates terminal fetches and allows a later retry after a fetch failure", async () => {
    const result = deferred<Run>();
    api.getAgentStudioSession.mockImplementation(async (id: string) => session(id, run("running")));
    api.getRun.mockReturnValueOnce(result.promise);
    await render();
    const handlers = streams.calls[0].handlers;
    await act(async () => { handlers.onTerminal(terminalEvent); handlers.onTerminal(terminalEvent); });
    expect(api.getRun).toHaveBeenCalledTimes(1);
    expect(api.getRunEventLog).toHaveBeenCalledTimes(1);
    await act(async () => { result.reject(new Error("terminal read failed")); });
    expect(controller.error).toBe("terminal read failed");
    await act(async () => { handlers.onTerminal(terminalEvent); });
    await flush();
    expect(api.getRun).toHaveBeenCalledTimes(2);
    expect(controller.run?.status).toBe("succeeded");
  });

  it("rejects an old poll and stream after A to B to A, even for the same run ID", async () => {
    vi.useFakeTimers();
    const oldPoll = deferred<Run>();
    api.getAgentStudioSession.mockImplementation(async (id: string) => session(id, id === "A" ? run("running") : null));
    api.getRun.mockReturnValueOnce(oldPoll.promise);
    await render();
    const old = streams.calls[0].handlers;
    await act(async () => { await vi.advanceTimersByTimeAsync(1500); });
    await act(async () => { controller.selectConversation("B"); });
    await render();
    await act(async () => { controller.selectConversation("A"); });
    await render();
    await act(async () => { oldPoll.resolve(run("failed")); old.onEvent(terminalEvent); old.onError(); old.onTerminal(terminalEvent); });
    expect(streams.calls).toHaveLength(2);
    expect(controller.run?.status).toBe("running");
    expect(controller.events).toEqual([]);
    expect(controller.streamWarning).toBe("");
    expect(api.getRun).toHaveBeenCalledTimes(1);
  });

  it("rejects terminal readback after selecting another conversation during completion", async () => {
    const completionRead = deferred<AgentStudioSession>();
    api.getAgentStudioSession.mockImplementation(async (id: string) => session(id, id === "A" ? run("running") : null));
    await render();
    api.getAgentStudioSession.mockReturnValueOnce(completionRead.promise);
    await act(async () => { streams.calls[0].handlers.onTerminal(terminalEvent); });
    expect(api.getAgentStudioSession).toHaveBeenCalledTimes(2);
    await act(async () => { controller.selectConversation("B"); });
    await render();
    await act(async () => { completionRead.resolve(session("A", run("succeeded"))); });
    await flush();
    expect(controller.session?.conversation.id).toBe("B");
    expect(controller.memory.scope?.subjectId).toBe("subject-B");
    expect(controller.run).toBeNull();
  });

  it("keeps cancellation in the controller and disposes polling and streaming on unmount", async () => {
    vi.useFakeTimers();
    api.getAgentStudioSession.mockImplementation(async (id: string) => session(id, run("running")));
    api.cancelRun.mockResolvedValue(run("cancelled"));
    await render();
    await act(async () => { await controller.cancelActiveRun(); });
    expect(controller.run?.status).toBe("cancelled");
    expect(api.cancelRun).toHaveBeenCalledWith("run-A");
    const closed = streams.close.mock.calls.length;
    const old = streams.calls[0].handlers;
    await act(async () => { root.render(<></>); });
    expect(streams.close).toHaveBeenCalledTimes(closed + 1);
    expect(vi.getTimerCount()).toBe(0);
    await act(async () => { old.onTerminal(terminalEvent); await vi.advanceTimersByTimeAsync(3000); });
    expect(api.getRun).not.toHaveBeenCalled();
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

  it("loads saved chat and runs even when Memory inspection fails", async () => {
    api.getRelationshipMemories.mockRejectedValue(new Error("Memory unavailable"));
    api.getMemoryOperations.mockRejectedValue(new Error("Memory unavailable"));
    await render();
    expect(controller.session?.conversation.id).toBe("A");
    expect(controller.conversation?.id).toBe("A");
    expect(controller.error).toBe("");
    expect(controller.memory.memories.data).toBeNull();
    expect(controller.memory.memories.error).toBe("Memory unavailable");
    expect(controller.memory.deliveries.data).not.toBeNull();
  });

  it("keeps paused input guarded and reuses the Retry key after an ambiguous response", async () => {
    api.getAgentStudioSession.mockImplementation(async (id: string) => session(id, run("paused")));
    api.retryRun.mockRejectedValueOnce(new Error("response lost")).mockResolvedValueOnce({ run_id: "run-A", status: "pending", events_url: "/events", idempotent_replay: true });
    api.getRun.mockResolvedValue(run("pending"));
    await render();
    expect(controller.activeRun).toBe(true);
    expect(streams.calls).toHaveLength(0);
    await act(async () => { controller.setMessage("must not send"); });
    await act(async () => { await controller.sendMessage(); });
    expect(api.acceptTurn).not.toHaveBeenCalled();
    await act(async () => { await controller.retryPausedRun(); });
    expect(controller.error).toBe("response lost");
    await act(async () => { await controller.retryPausedRun(); });
    expect(api.retryRun.mock.calls[0]).toEqual(api.retryRun.mock.calls[1]);
    expect(api.retryRun.mock.calls[1].slice(0, 2)).toEqual(["run-A", 1]);
    expect(streams.calls).toHaveLength(1);
    expect(api.getRun).toHaveBeenCalledWith("run-A");
    expect(api.acceptTurn).not.toHaveBeenCalled();
  });

  it("rejects a mismatched Retry receipt before opening a monitor", async () => {
    api.getAgentStudioSession.mockImplementation(async (id: string) => session(id, run("paused")));
    api.retryRun.mockResolvedValue({ run_id: "other-run", status: "pending" });
    await render();
    await act(async () => { await controller.retryPausedRun(); });
    expect(controller.error).toContain("unexpected saved run identity");
    expect(api.getRun).not.toHaveBeenCalled();
    expect(streams.calls).toHaveLength(0);
  });

  it("reuses one turn key after ambiguous acceptance and does not restore known-saved input", async () => {
    api.acceptTurn.mockRejectedValueOnce(new Error("accept response lost")).mockResolvedValueOnce({ run_id: "run-A", status: "pending" });
    await render();
    await act(async () => { controller.setMessage("one immutable input"); });
    await act(async () => { await controller.sendMessage(); });
    expect(controller.message).toBe("one immutable input");
    api.getRun.mockRejectedValueOnce(new Error("run read failed"));
    await act(async () => { await controller.sendMessage(); });
    expect(api.acceptTurn.mock.calls[0]).toEqual(api.acceptTurn.mock.calls[1]);
    expect(controller.message).toBe("");
    expect(controller.error).toBe("run read failed");
  });
});
