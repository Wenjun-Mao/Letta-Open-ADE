import { nativeRunEventsUrl, type NativeRunEvent } from "./api";

export const TERMINAL_NATIVE_EVENT_TYPES = new Set([
  "run.completed",
  "run.failed",
  "run.cancelled",
]);

const NATIVE_EVENT_TYPES = [
  "run.accepted",
  "run.started",
  "run.recovered",
  "run.cancel_requested",
  "run.completed",
  "run.failed",
  "run.cancelled",
  "attempt.started",
  "retry.scheduled",
  "context.built",
  "model.request.started",
  "model.response.completed",
  "model.request.failed",
  "model.request.cancelled",
  "model.protocol_repaired",
  "tool.call.requested",
  "tool.call.completed",
  "memory.proposed",
  "memory.committed",
  "message.committed",
  "summary.committed",
] as const;

export function parseNativeRunEvent(value: string): NativeRunEvent {
  const parsed = JSON.parse(value) as NativeRunEvent;
  if (!parsed || typeof parsed !== "object" || typeof parsed.type !== "string") {
    throw new Error("Native runtime event payload is invalid");
  }
  return parsed;
}

export function openNativeRunEventStream(
  runId: string,
  handlers: {
    onEvent: (event: NativeRunEvent) => void;
    onTerminal: (event: NativeRunEvent) => void;
    onError: () => void;
  },
): EventSource {
  const source = new EventSource(nativeRunEventsUrl(runId));
  for (const eventType of NATIVE_EVENT_TYPES) {
    source.addEventListener(eventType, (message) => {
      try {
        const event = parseNativeRunEvent((message as MessageEvent<string>).data);
        handlers.onEvent(event);
        if (TERMINAL_NATIVE_EVENT_TYPES.has(event.type)) {
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
