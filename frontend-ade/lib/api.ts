export const DEV_UI_BASE_URL = process.env.NEXT_PUBLIC_DEV_UI_BASE_URL || "http://127.0.0.1:8284";

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
};

export type OptionEntry = {
  key: string;
  label: string;
  description: string;
  available?: boolean;
  is_default?: boolean;
};

export type AgentListItem = {
  id: string;
  name: string;
  model: string;
  created_at: string;
  last_updated_at: string;
  last_interaction_at: string;
};

export type AgentDetails = {
  id: string;
  name: string;
  model: string;
  system: string;
  tools: Record<string, string>;
  memory: Record<string, string>;
};

export type PersistentState = {
  memory_blocks: Array<{
    label: string;
    value: string;
    description: string;
    limit: number | null;
  }>;
  conversation_history: {
    total_persisted: number;
    displayed: number;
    items: Array<{
      id: string;
      created_at: string;
      role: string;
      message_type: string;
      content: string;
      name?: string | null;
      tool_arguments?: string | null;
    }>;
  };
};

export type ChatStep = {
  type: string;
  content?: string;
  name?: string;
  status?: string;
  arguments?: string;
};

export type ChatResult = {
  total_steps: number;
  sequence: ChatStep[];
  memory_diff: {
    old: Record<string, string>;
    new: Record<string, string>;
  };
};

export type PlatformTool = {
  id: string;
  name: string;
  description: string;
  tool_type: string;
  source_type: string;
  created_at: string;
  last_updated_at: string;
  tags: string[];
  attached_to_agent?: boolean;
};

export type PlatformRunRecord = {
  run_id: string;
  run_type: string;
  status: string;
  command: string[];
  created_at: string;
  started_at: string;
  finished_at: string;
  exit_code: number | null;
  log_file: string;
  cancel_requested: boolean;
  output_tail: string[];
  error: string;
  artifacts?: PlatformArtifact[];
};

export type PlatformArtifact = {
  artifact_id: string;
  type: string;
  path: string;
  exists: boolean;
  size_bytes: number;
};

async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${DEV_UI_BASE_URL}${path}`, {
    method: options.method || "GET",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (!response.ok) {
    const payload = await response.text();
    throw new Error(payload || `Request failed ${response.status}: ${path}`);
  }

  return (await response.json()) as T;
}

export function fetchMigrationStatus() {
  return requestJson<{
    migration_mode: string;
    platform_api_enabled: boolean;
    legacy_api_enabled: boolean;
    strict_capabilities: boolean;
  }>("/api/platform/migration-status");
}

export function fetchCapabilities() {
  return requestJson<{
    enabled: boolean;
    strict_mode: boolean;
    missing_required: string[];
    runtime: Record<string, boolean>;
    control: Record<string, boolean>;
  }>("/api/platform/capabilities");
}

export function fetchOptions() {
  return requestJson<{
    models: OptionEntry[];
    embeddings: OptionEntry[];
    prompts: OptionEntry[];
    defaults: {
      model: string;
      prompt_key: string;
      embedding: string;
    };
  }>("/api/options");
}

export function listAgents(limit = 200) {
  return requestJson<{
    total: number;
    items: AgentListItem[];
  }>(`/api/agents?limit=${limit}`);
}

export function createAgent(payload: {
  name: string;
  model: string;
  prompt_key: string;
  embedding?: string | null;
}) {
  return requestJson<{
    id: string;
    name: string;
    model: string;
    embedding?: string | null;
    prompt_key: string;
  }>("/api/agents", {
    method: "POST",
    body: payload,
  });
}

export function getAgentDetails(agentId: string) {
  return requestJson<AgentDetails>(`/api/agents/${agentId}/details`);
}

export function getPersistentState(agentId: string, limit = 120) {
  return requestJson<PersistentState>(`/api/agents/${agentId}/persistent_state?limit=${limit}`);
}

export function getRawPrompt(agentId: string) {
  return requestJson<{ messages: Array<{ role: string; content: string }> }>(`/api/agents/${agentId}/raw_prompt`);
}

export function sendChat(agentId: string, message: string) {
  return requestJson<ChatResult>("/api/chat", {
    method: "POST",
    body: {
      agent_id: agentId,
      message,
    },
  });
}

export function fetchPromptPersonaMetadata() {
  return requestJson<{
    defaults: {
      prompt_key: string;
      persona_key: string;
    };
    prompts: Array<{
      key: string;
      label: string;
      description: string;
      preview: string;
      length: number;
    }>;
    personas: Array<{
      key: string;
      preview: string;
      length: number;
    }>;
  }>("/api/platform/metadata/prompts-personas");
}

export function updateSystemPrompt(agentId: string, system: string) {
  return requestJson<{ system_after: string; system_before: string }>(`/api/platform/agents/${agentId}/system`, {
    method: "PATCH",
    body: { system },
  });
}

export function updateCoreMemoryBlock(agentId: string, blockLabel: string, value: string) {
  return requestJson<{ value_before: string; value_after: string }>(
    `/api/platform/agents/${agentId}/core-memory/blocks/${blockLabel}`,
    {
      method: "PATCH",
      body: { value },
    },
  );
}

export function listTools(search = "", limit = 200, agentId = "") {
  const params = new URLSearchParams();
  params.set("limit", `${limit}`);
  if (search.trim()) {
    params.set("search", search.trim());
  }
  if (agentId.trim()) {
    params.set("agent_id", agentId.trim());
  }

  return requestJson<{
    total: number;
    items: PlatformTool[];
  }>(`/api/platform/tools?${params.toString()}`);
}

export function attachTool(agentId: string, toolId: string) {
  return requestJson(`/api/platform/agents/${agentId}/tools/attach/${toolId}`, {
    method: "PATCH",
  });
}

export function detachTool(agentId: string, toolId: string) {
  return requestJson(`/api/platform/agents/${agentId}/tools/detach/${toolId}`, {
    method: "PATCH",
  });
}

export function listTestRuns() {
  return requestJson<{ items: PlatformRunRecord[] }>("/api/platform/test-runs");
}

export function createTestRun(payload: {
  run_type: string;
  model?: string;
  embedding?: string;
  rounds?: number;
  config_path?: string;
}) {
  return requestJson<PlatformRunRecord>("/api/platform/test-runs", {
    method: "POST",
    body: payload,
  });
}

export function getTestRun(runId: string) {
  return requestJson<PlatformRunRecord>(`/api/platform/test-runs/${runId}`);
}

export function cancelTestRun(runId: string) {
  return requestJson<PlatformRunRecord>(`/api/platform/test-runs/${runId}/cancel`, {
    method: "POST",
  });
}

export function listRunArtifacts(runId: string) {
  return requestJson<{
    run_id: string;
    items: PlatformArtifact[];
  }>(`/api/platform/test-runs/${runId}/artifacts`);
}

export function readRunArtifact(runId: string, artifactId: string, maxLines = 400) {
  return requestJson<{
    run_id: string;
    artifact: PlatformArtifact;
    content: string;
    truncated: boolean;
    line_count: number;
  }>(`/api/platform/test-runs/${runId}/artifacts/${artifactId}?max_lines=${maxLines}`);
}
