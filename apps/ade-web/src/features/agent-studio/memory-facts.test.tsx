import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

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
});
