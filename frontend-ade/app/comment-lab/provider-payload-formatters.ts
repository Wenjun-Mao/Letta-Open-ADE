import { asRecord as asObject } from "../../lib/json-display";

function normalizeChatContent(value: unknown): string {
  if (typeof value === "string") {
    return value.trim();
  }
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        const obj = asObject(item);
        const text = typeof obj.text === "string" ? obj.text : "";
        return text.trim();
      })
      .filter((part) => part.length > 0)
      .join("\n")
      .trim();
  }
  if (value === undefined || value === null) {
    return "";
  }
  return String(value).trim();
}

export function formatRawRequestForHuman(value: unknown): string {
  const payload = asObject(value);
  if (!Object.keys(payload).length) {
    return "-";
  }

  const lines: string[] = [];
  lines.push(`Model: ${String(payload.model ?? "-")}`);
  lines.push(`Temperature: ${String(payload.temperature ?? "-")}`);
  lines.push(`Top P: ${String(payload.top_p ?? "-")}`);
  lines.push(`Top K: ${String(payload.top_k ?? "-")}`);
  lines.push(`Cache Prompt: ${String(payload.cache_prompt ?? "-")}`);
  const chatTemplateKwargs = asObject(payload.chat_template_kwargs);
  lines.push(`Enable Thinking: ${String(chatTemplateKwargs.enable_thinking ?? "-")}`);
  lines.push(`Max Tokens: ${String(payload.max_tokens ?? "-")}`);

  const messages = Array.isArray(payload.messages) ? payload.messages : [];
  lines.push(`Message Count: ${messages.length}`);

  messages.forEach((message, index) => {
    const obj = asObject(message);
    const role = String(obj.role ?? "unknown");
    const content = normalizeChatContent(obj.content);
    lines.push("");
    lines.push(`Message ${index + 1} (${role})`);
    lines.push(content || "-");
  });

  return lines.join("\n").trim();
}

export function formatRawReplyForHuman(value: unknown): string {
  const payload = asObject(value);
  if (!Object.keys(payload).length) {
    return "-";
  }

  const lines: string[] = [];
  lines.push(`ID: ${String(payload.id ?? "-")}`);
  lines.push(`Model: ${String(payload.model ?? "-")}`);

  const usage = asObject(payload.usage);
  if (Object.keys(usage).length) {
    lines.push(
      `Usage: prompt=${String(usage.prompt_tokens ?? "-")}, completion=${String(usage.completion_tokens ?? "-")}, total=${String(usage.total_tokens ?? "-")}`,
    );
  }

  const choices = Array.isArray(payload.choices) ? payload.choices : [];
  lines.push(`Choices: ${choices.length}`);

  choices.forEach((choice, index) => {
    const choiceObj = asObject(choice);
    const finishReason = String(choiceObj.finish_reason ?? "-");
    const message = asObject(choiceObj.message);
    const content = normalizeChatContent(message.content);
    const reasoning = normalizeChatContent(message.reasoning_content || message.reasoning);

    lines.push("");
    lines.push(`Choice ${index + 1}`);
    lines.push(`Finish Reason: ${finishReason}`);
    lines.push("Assistant Content:");
    lines.push(content || "-");
    if (reasoning) {
      lines.push("");
      lines.push("Reasoning Content:");
      lines.push(reasoning);
    }
  });

  return lines.join("\n").trim();
}

export function previewText(value: string, maxChars = 760): string {
  const text = String(value || "").trim();
  if (!text) {
    return "";
  }
  if (text.length <= maxChars) {
    return text;
  }
  return `${text.slice(0, maxChars)}\n\n...`;
}
