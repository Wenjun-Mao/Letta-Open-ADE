// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { MemoryFacts } from "./memory-facts";
import type { MemoryFact } from "./types";

const fact = (id: string, status: MemoryFact["status"]): MemoryFact => ({
  id, key: id, fact_type: "person.preference", entity_id: "subject-1", entity_kind: "subject",
  entity_label: "Person", qualifier: null, value: status === "active" ? "tea" : null,
  status, version: 2, updated_at: "2026-09-22T00:00:00Z",
  revisions: [{ id: `${id}-revision`, operation: "forget", fact_version: 2, value: null,
    run_id: "run-1", predecessor_revision_ids: [], created_at: "2026-09-22T00:00:00Z",
    evidence: [{ message_id: "message-1", conversation_id: "conversation-1", message_sequence: 15,
      start_char: 0, end_char: 3, quote: "tea", message_sha256: "a".repeat(64) }] }],
});

describe("saved fact display", () => {
  it("separates active and historical facts and states the limited removal semantics", () => {
    const html = renderToStaticMarkup(<MemoryFacts facts={[fact("active", "active"), fact("ended", "inactive"), fact("removed", "forgotten")]}
      t={(english) => english} openEvidence={async () => {}} prepareAction={() => {}} removeSaved={async () => {}} canCorrect canRemove />);

    expect(html).toContain("Saved facts");
    expect(html).toContain("Inactive and removed facts");
    expect(html).toContain("past messages, summaries and audit revisions remain");
    expect(html).toContain("Open original message");
    expect(html.match(/Remove exact saved assertion/g)).toHaveLength(2);
    expect(html).toContain("Former assertion:");
  });

  it("requires an exact in-panel confirmation before removal", async () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const removeSaved = vi.fn(async () => {});
    const container = document.createElement("div");
    const root = createRoot(container);
    try {
      await act(async () => root.render(<MemoryFacts facts={[fact("active", "active")]}
        t={(english) => english} openEvidence={async () => {}} prepareAction={() => {}}
        removeSaved={removeSaved} canCorrect={false} canRemove />));
      const click = async (label: string) => {
        const button = [...container.querySelectorAll("button")].find((item) => item.textContent === label);
        expect(button).toBeDefined();
        await act(async () => button?.click());
      };
      await click("Remove exact saved assertion");
      expect(removeSaved).not.toHaveBeenCalled();
      expect(container.textContent).toContain("person.preference v2: tea");
      expect(container.textContent).toContain("past messages, summaries, and audit revisions remain");
      await click("Cancel removal");
      expect(removeSaved).not.toHaveBeenCalled();
      await click("Remove exact saved assertion");
      await click("Confirm exact removal");
      expect(removeSaved).toHaveBeenCalledOnce();
      expect(removeSaved).toHaveBeenCalledWith("active", 2);
    } finally {
      await act(async () => root.unmount());
    }
  });
});
