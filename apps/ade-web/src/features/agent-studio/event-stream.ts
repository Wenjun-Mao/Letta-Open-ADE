import { runEventsUrl } from "./api";
import type { RunEvent } from "./types";

export const TERMINAL_RUN_EVENT_TYPES = new Set(["run.completed", "run.failed", "run.cancelled"]);

const RUN_EVENT_TYPES = [
  "run.accepted", "run.started", "run.recovered", "run.cancel_requested", "run.completed", "run.failed", "run.cancelled",
  "attempt.started", "retry.scheduled", "context.built", "model.request.started", "model.response.completed",
  "model.request.failed", "model.request.cancelled", "model.protocol_repaired", "tool.call.requested",
  "tool.call.completed", "memory.proposed", "memory.committed", "message.committed", "summary.committed",
] as const;

export function parseRunEvent(value: string): RunEvent {
  const parsed = JSON.parse(value) as RunEvent;
  if (!parsed || typeof parsed !== "object" || typeof parsed.id !== "string" || typeof parsed.type !== "string") {
    throw new Error("Agent Studio run event payload is invalid.");
  }
  return parsed;
}

export function openRunEventStream(
  runId: string,
  handlers: { onEvent: (event: RunEvent) => void; onTerminal: (event: RunEvent) => void; onError: () => void },
): EventSource {
  const source = new EventSource(runEventsUrl(runId));
  for (const eventType of RUN_EVENT_TYPES) {
    source.addEventListener(eventType, (message) => {
      try {
        const event = parseRunEvent((message as MessageEvent<string>).data);
        handlers.onEvent(event);
        if (TERMINAL_RUN_EVENT_TYPES.has(event.type)) {
          handlers.onTerminal(event);
          source.close();
        }
      } catch {
        handlers.onError();
      }
    });
  }
  source.onerror = handlers.onError;
  return source;
}
