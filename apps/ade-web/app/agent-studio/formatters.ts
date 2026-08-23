import type { ChatResult } from "../../lib/api";

import type { TimelineFilter } from "./types";

export function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function extractAssistantReply(result: ChatResult): string {
  const reversed = [...(result.sequence || [])].reverse();
  const assistant = reversed.find((step) => step.type === "assistant" && step.content);
  return assistant?.content || "";
}

export function shortId(value: string): string {
  if (value.length <= 28) {
    return value;
  }
  return `${value.slice(0, 14)}...${value.slice(-8)}`;
}

export function formatTimestamp(value: string | undefined | null, locale: "en" | "zh" = "en"): string {
  if (!value) {
    return "N/A";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString(locale === "zh" ? "zh-CN" : "en-US", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function formatLatency(valueMs: number | null): string {
  if (valueMs === null || !Number.isFinite(valueMs) || valueMs < 0) {
    return "";
  }
  if (valueMs < 1000) {
    return `${Math.round(valueMs)} ms`;
  }
  return `${(valueMs / 1000).toFixed(2)} s`;
}

export function summarizeDescription(description: string, fallbackText = "No description.", maxLength = 190): string {
  const normalized = (description || "").replace(/\s+/g, " ").trim();
  if (!normalized) {
    return fallbackText;
  }
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength)}...`;
}

export function parseToolExamples(
  description: string,
  fallbackNoDescription = "No description.",
  fallbackNoOverview = "No overview provided.",
): { overview: string; examples: string[] } {
  const text = (description || "").replace(/\r\n/g, "\n").trim();
  if (!text) {
    return { overview: fallbackNoDescription, examples: [] };
  }

  const marker = text.search(/examples?:/i);
  if (marker === -1) {
    return { overview: text, examples: [] };
  }

  const overview = text.slice(0, marker).trim() || fallbackNoOverview;
  const exampleBody = text.slice(marker).replace(/^examples?:\s*/i, "").trim();
  if (!exampleBody) {
    return { overview, examples: [] };
  }

  const examples = exampleBody
    .split(/\s+#\s+/)
    .map((segment) => segment.trim())
    .filter(Boolean);

  return { overview, examples: examples.length ? examples : [exampleBody] };
}

export function stepTone(stepType: string): string {
  const normalized = String(stepType || "").toLowerCase();
  if (normalized.includes("assistant")) {
    return "timeline-step assistant";
  }
  if (normalized.includes("tool_call")) {
    return "timeline-step tool-call";
  }
  if (normalized.includes("tool_return")) {
    return "timeline-step tool-return";
  }
  if (normalized.includes("reasoning")) {
    return "timeline-step reasoning";
  }
  return "timeline-step";
}

export function stepMatchesFilter(stepType: string, filter: TimelineFilter): boolean {
  if (filter === "all") {
    return true;
  }

  const normalized = String(stepType || "").toLowerCase();
  if (filter === "assistant") {
    return normalized.includes("assistant");
  }
  if (filter === "tool") {
    return normalized.includes("tool_call") || normalized.includes("tool_return");
  }
  if (filter === "reasoning") {
    return normalized.includes("reasoning");
  }
  return true;
}
