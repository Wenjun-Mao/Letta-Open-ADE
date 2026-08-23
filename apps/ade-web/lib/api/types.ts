export type Scenario = "chat" | "comment" | "label";
export type CommentingTaskShape = "classic" | "all_in_system" | "structured_output";
export type LabelingOutputMode = "strict_json_schema" | "json_schema" | "best_effort_prompt_json";
export type PlatformRunType = "platform_api_e2e_check" | "ade_mvp_smoke_e2e_check" | "chat_memory_eval";

export type SamplingDefaults = {
  temperature?: number | null;
  top_p?: number | null;
  top_k?: number | null;
  min_p?: number | null;
  presence_penalty?: number | null;
  repetition_penalty?: number | null;
};

export type OptionEntry = {
  key: string;
  label: string;
  description: string;
  scenario?: Scenario | null;
  available?: boolean;
  is_default?: boolean;
  source_id?: string | null;
  source_label?: string | null;
  provider_model_id?: string | null;
  label_lab_available?: boolean | null;
  structured_output_mode?: LabelingOutputMode | null;
  sampling_defaults?: SamplingDefaults;
  scenario_sampling_defaults?: Record<string, SamplingDefaults>;
  supports_top_k?: boolean | null;
  supports_thinking?: boolean | null;
  thinking_default_enabled?: boolean | null;
  profile_applied?: boolean | null;
  profile_source?: string | null;
  agent_studio_candidate?: boolean | null;
  agent_studio_compatible?: boolean | null;
};

export type AgentListItem = {
  id: string;
  name: string;
  model: string;
  created_at: string;
  last_updated_at: string;
  last_interaction_at: string;
  archived: boolean;
};

export type AgentLifecycleRecord = {
  id: string;
  name: string;
  model: string;
  archived: boolean;
  archived_at?: string | null;
  updated_at: string;
};

export type AgentDetails = {
  id: string;
  name: string;
  agent_type?: string;
  model: string;
  embedding?: string | null;
  created_at?: string;
  last_updated_at?: string;
  last_interaction_at?: string;
  llm_config?: unknown;
  embedding_config?: unknown;
  tool_rules?: unknown;
  context_window_limit?: number | null;
  system: string;
  tools: Record<string, string>;
  memory: Record<string, string>;
};

export type PersistentState = {
  source?: string;
  agent?: {
    id: string;
    name: string;
    agent_type: string;
    model: string;
    embedding?: string | null;
    created_at?: string;
    last_updated_at?: string;
    context_window_limit?: number | null;
    tool_rules?: string;
  };
  memory_blocks: Array<{
    label: string;
    value: string;
    description: string;
    limit: number | null;
  }>;
  tools?: Array<{
    id: string;
    name: string;
    description: string;
  }>;
  conversation_history: {
    total_persisted: number;
    displayed: number;
    limit?: number;
    counts_by_type?: Record<string, number>;
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
  tool_arguments?: string;
  message_type?: string;
};

export type ChatResult = {
  total_steps: number;
  sequence: ChatStep[];
  memory_diff: {
    old: Record<string, string>;
    new: Record<string, string>;
  };
};

export type CommentingGenerateResponse = {
  scenario: Scenario;
  model_key: string;
  source_id: string;
  source_label: string;
  provider_model_id: string;
  prompt_key: string;
  persona_key: string;
  model: string;
  content: string;
  provider: string;
  max_tokens: number;
  timeout_seconds: number;
  task_shape: CommentingTaskShape;
  cache_prompt: boolean;
  enable_thinking: boolean;
  temperature: number;
  top_p: number;
  top_k?: number | null;
  content_source?: string | null;
  selected_attempt: string;
  finish_reason?: string | null;
  usage: Record<string, unknown>;
  received_at?: string | null;
  raw_request: Record<string, unknown>;
  raw_reply: Record<string, unknown>;
};

export type LabelExtractionResult = Record<string, string[]>;

export type LabelingGenerateResponse = {
  scenario: Scenario;
  model_key: string;
  source_id: string;
  source_label: string;
  provider_model_id: string;
  prompt_key: string;
  schema_key: string;
  output_mode: LabelingOutputMode;
  selected_attempt: "primary" | "repair";
  result: LabelExtractionResult;
  finish_reason?: string | null;
  usage: Record<string, unknown>;
  received_at?: string | null;
  raw_request: Record<string, unknown>;
  raw_reply: Record<string, unknown>;
  validation_errors: string[];
  temperature: number;
  top_p: number;
  top_k?: number | null;
};

export type LabelSchemaRecord = {
  key: string;
  label: string;
  description: string;
  schema: Record<string, unknown>;
  preview: string;
  archived: boolean;
  source_path: string;
  updated_at: string;
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
  managed?: boolean;
  read_only?: boolean;
  archived?: boolean;
  slug?: string | null;
};

export type PromptTemplateRecord = {
  kind: "prompt" | "persona";
  scenario: Scenario;
  key: string;
  label: string;
  description: string;
  content: string;
  preview: string;
  length: number;
  archived: boolean;
  source_path: string;
  updated_at: string;
  output_schema?: string | null;
};

export type ToolCenterItem = {
  slug?: string | null;
  tool_id: string;
  name: string;
  description: string;
  tool_type: string;
  source_type: string;
  tags: string[];
  managed: boolean;
  read_only: boolean;
  archived: boolean;
  source_path?: string | null;
  source_code?: string | null;
  created_at?: string;
  last_updated_at?: string;
  updated_at?: string | null;
  archived_at?: string | null;
};

export type PlatformToolTestInvokeResult = {
  agent_id: string;
  input: string;
  expected_tool_name?: string | null;
  expected_tool_matched?: boolean | null;
  tool_call_count: number;
  tool_return_count: number;
  result: ChatResult;
};

export type PromptPersonaRevisionRecord = {
  revision_id: string;
  recorded_at: string;
  agent_id: string;
  field: "system" | "persona" | "human";
  source: string;
  before: string;
  after: string;
  before_preview: string;
  after_preview: string;
  before_length: number;
  after_length: number;
  delta_length: number;
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

export type CreateTestRunPayload = {
  run_type: PlatformRunType;
  model?: string;
  prompt_key?: string;
  persona_key?: string;
  embedding?: string;
  rounds?: number;
  fixture_key?: string;
  timeout_seconds?: number;
  retry_count?: number;
  judge_enabled?: boolean;
  judge_model_key?: string;
};
