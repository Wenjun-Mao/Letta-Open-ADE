import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";

import { TurnActivityView } from "./turn-activity-view";
import type { TurnActivity } from "./types";

const translate = (english: string) => english;

function activity(): TurnActivity {
  return {
    run_id: "run", status: "succeeded",
    provider: { generation: 1, compaction: 2, other: 0 },
    provider_complete: true, provider_observed: true,
    tools: [], tools_complete: true,
    context: { current_chat: false, automatic_memory_ids: ["memory-A"], tool_memory_ids: [] },
  };
}

it("separates ADE model counts and supplied Hindsight context without a native reviewer", () => {
  const html = renderToStaticMarkup(<TurnActivityView activity={activity()} t={translate} />);
  expect(html).toContain("Provider requests: 3");
  expect(html).toContain("Generation");
  expect(html).toContain("Compaction");
  expect(html).toContain("Tools: none");
  expect(html).toContain("automatically supplied memory IDs");
  expect(html).toContain("not Hindsight extraction or consolidation calls");
  expect(html).not.toContain("Review:");
});

it("does not render missing historical telemetry as zero", () => {
  const old = activity();
  old.provider = { generation: 0, compaction: 0, other: 0 };
  old.provider_complete = false;
  old.provider_observed = false;
  old.tools_complete = false;
  old.context = { current_chat: null, automatic_memory_ids: null, tool_memory_ids: null };
  const html = renderToStaticMarkup(<TurnActivityView activity={old} t={translate} />);
  expect(html).toContain("Provider requests: unavailable");
  expect(html).toContain("Tools: unavailable");
  expect(html).toContain("Provider breakdown unavailable");
});
