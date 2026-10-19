// @vitest-environment jsdom
import { act, useEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { useRelationshipMemory } from "./use-relationship-memory";
import type { AgentStudioSession, MemoryDeliveries, MemoryDelivery, MemorySource, RelationshipMemories } from "./types";

const api = vi.hoisted(() => ({ getRelationshipMemories: vi.fn(), getMemoryDeliveries: vi.fn(), getMemoryOperations: vi.fn(), getMemorySource: vi.fn(), retryMemoryDelivery: vi.fn() }));
vi.mock("./api", () => api);
const relationship = (subject = "person-A", root = "root-A") => ({ subject_id: subject, character_root_id: root, state: "ready", last_error_code: null });
const result = (subject = "person-A", root = "root-A"): RelationshipMemories => ({ relationship: relationship(subject, root), items: [], total: 0, limit: 100, offset: 0 });
const session = { conversation: { id: "chat-A" }, memory_subject: { id: "person-A" }, agent_definition: { agent_definition_id: "root-A" } } as AgentStudioSession;
const delivery = { operation_id: "op-A", check_count: 5 } as MemoryDelivery;

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

let root: Root;
let container: HTMLDivElement;
let controller: ReturnType<typeof useRelationshipMemory>;
function Probe({ binding = session }: { binding?: AgentStudioSession | null }) {
  const current = useRelationshipMemory(binding);
  useEffect(() => { controller = current; });
  return null;
}
async function render(binding: AgentStudioSession | null = session) {
  await act(async () => { root.render(<Probe binding={binding} />); await Promise.resolve(); });
}
beforeEach(() => {
  vi.resetAllMocks();
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div"); document.body.append(container); root = createRoot(container);
  api.getRelationshipMemories.mockImplementation(async (subject, character) => result(subject, character));
  api.getMemoryDeliveries.mockImplementation(async (subject, character) => ({ ...result(subject, character), counts: {}, blocked_operation_id: null }));
  api.getMemoryOperations.mockImplementation(async (subject, character) => result(subject, character));
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove(); vi.useRealTimers();
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = false;
});

it("reads ADE delivery state while native Memory hangs or fails", async () => {
  const remote = deferred<RelationshipMemories>();
  api.getRelationshipMemories.mockReturnValue(remote.promise);
  await render();
  expect(controller.memories.loading).toBe(true);
  expect(controller.deliveries.data?.relationship.subject_id).toBe("person-A");
  await act(async () => { remote.reject(new Error("native unavailable")); });
  expect(controller.memories.error).toBe("native unavailable");
  expect(controller.memories.data).toBeNull();
  expect(controller.deliveries.error).toBe("");
});

it("rejects late A responses after switching A to B to A", async () => {
  const obsolete = deferred<RelationshipMemories>();
  api.getRelationshipMemories.mockReturnValueOnce(obsolete.promise);
  await render();
  await act(async () => { controller.selectScope({ subjectId: "person-B", characterRootId: "root-B" }); });
  expect(controller.memories.data?.relationship.subject_id).toBe("person-B");
  await act(async () => { controller.selectScope({ subjectId: "person-A", characterRootId: "root-A" }); });
  await act(async () => { obsolete.resolve({ ...result(), total: 999 }); });
  expect(controller.memories.data?.total).toBe(0);
});

it("drops sources from a previous character even if the person is unchanged", async () => {
  const obsolete = deferred<MemorySource>();
  api.getMemorySource.mockReturnValue(obsolete.promise);
  await render();
  await act(async () => { void controller.openSource("doc-A"); });
  await act(async () => { controller.selectScope({ subjectId: "person-A", characterRootId: "root-B" }); });
  await act(async () => { obsolete.resolve({ content: "must-not-display" } as MemorySource); });
  expect(controller.source).toBeNull();
  expect(api.getMemorySource).toHaveBeenCalledWith("person-A", "root-A", "doc-A");
});

it("does not request an incomplete relationship or manufacture an empty bank", async () => {
  await render(null);
  await act(async () => { controller.selectScope({ subjectId: "person-A", characterRootId: "" }); });
  expect(api.getRelationshipMemories).not.toHaveBeenCalled();
  expect(api.getMemoryDeliveries).not.toHaveBeenCalled();
  expect(controller.memories.data).toBeNull();
  expect(controller.memories.loading).toBe(false);
});

it("keeps delivery Retry independent of an in-flight source read", async () => {
  const retry = deferred<MemoryDelivery>();
  api.retryMemoryDelivery.mockReturnValue(retry.promise);
  api.getMemorySource.mockResolvedValue({ relationship: relationship(), content: "original" });
  await render();
  await act(async () => { void controller.retryDelivery(delivery); });
  await act(async () => { await controller.openSource("doc-A"); });
  await act(async () => { retry.resolve(delivery); });
  expect(controller.retrying).toBe("");
  expect(controller.source?.data?.content).toBe("original");
  expect(api.retryMemoryDelivery).toHaveBeenCalledWith("person-A", "root-A", delivery);
  expect(api.getMemoryDeliveries).toHaveBeenCalledTimes(2);
});

it("polls status changes and cleans up all poll timers on unmount", async () => {
  vi.useFakeTimers();
  await render();
  const queued = { ...result(), counts: { queued: 1 }, items: [delivery] } as unknown as MemoryDeliveries;
  api.getMemoryDeliveries.mockResolvedValue(queued);
  await act(async () => { await vi.advanceTimersByTimeAsync(2500); });
  expect(controller.deliveries.data?.counts).toEqual({ queued: 1 });
  await act(async () => { root.render(<></>); });
  expect(vi.getTimerCount()).toBe(0);
});
