import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";

import { TurnActivityView } from "./turn-activity-view";
import type { TurnActivity } from "./types";

const translate = (english: string) => english;

function activity(): TurnActivity {
  return {
    run_id: "run", status: "succeeded",
    provider: { generation: 1, reviewer: 1, embedding: 3, other: 0 },
    provider_complete: true, provider_observed: true,
    tools: [], tools_complete: true,
    context: { current_chat: false, profile_fact_ids: [], history_run_ids: ["older-run"],
      history_sources: [{ run_id: "older-run", conversation_id: "older-chat" }] },
  };
}

it("shows exact separated counts and links admitted sources", () => {
  const html = renderToStaticMarkup(<TurnActivityView activity={activity()} t={translate} />);
  expect(html).toContain("Provider requests: 5");
  expect(html).toContain("Generation");
  expect(html).toContain("Embeddings");
  expect(html).toContain("Tools: none");
  expect(html).toContain("/agent-studio?conversation=older-chat");
});

it("does not render missing historical telemetry as zero", () => {
  const old = activity();
  old.provider = { generation: 0, reviewer: 0, embedding: 0, other: 0 };
  old.provider_complete = false;
  old.provider_observed = false;
  old.tools_complete = false;
  old.context = { current_chat: null, profile_fact_ids: null, history_run_ids: null, history_sources: null };
  const html = renderToStaticMarkup(<TurnActivityView activity={old} t={translate} />);
  expect(html).toContain("Provider requests: unavailable");
  expect(html).toContain("Tools: unavailable");
  expect(html).toContain("Provider breakdown unavailable");
});
