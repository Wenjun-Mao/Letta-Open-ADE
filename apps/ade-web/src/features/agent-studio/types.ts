export type QualificationState = "qualified" | "unqualified";
export type RunStatus = "pending" | "running" | "paused" | "succeeded" | "failed" | "cancelled";

export type DeploymentSnapshot = {
  deployment_id: string;
  route_alias: string;
  fingerprint: string;
  role: "conversation" | "compaction";
  lifecycle: string;
  qualification_state: QualificationState;
  fingerprint_payload: Record<string, unknown>;
};

export type AgentDefinition = {
  id: string;
  agent_definition_id: string | null;
  definition_key: string;
  version: number;
  name: string;
  prompt_key: string;
  prompt_sha256: string;
  persona_key: string;
  persona_sha256: string;
  tool_names: string[];
  memory_policy_version: string;
  qualification_state: QualificationState;
  deployments: DeploymentSnapshot[];
  archived_at: string | null;
  created_at: string;
};

export type MemorySubject = {
  id: string;
  external_key: string;
  display_name: string;
  version: number;
  archived_at: string | null;
  created_at: string;
  updated_at: string | null;
};

export type Conversation = {
  id: string;
  agent_definition_id: string;
  memory_subject_id: string;
  title: string;
  purpose: "agent_studio" | "development" | "evaluation" | "preview";
  version: number;
  archived_at: string | null;
  created_at: string;
};

export type Run = {
  id: string;
  conversation_id: string;
  status: RunStatus;
  paused_at: string | null;
  qualification_state: QualificationState;
  attempt_count: number;
  timeout_seconds: number;
  retry_count: number;
  cancellation_requested_at: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type TurnAccepted = {
  run_id: string; status: RunStatus; events_url: string; idempotent_replay: boolean;
};

export type AgentStudioSession = {
  session_id: string;
  idempotent_replay: boolean;
  agent_definition: AgentDefinition;
  memory_subject: MemorySubject;
  conversation: Conversation;
  latest_run: Run | null;
};

export type AgentStudioBundle = {
  key: string;
  name: string;
  model_key: string;
  compaction_model_key: string;
  prompt_key: string;
  persona_key: string;
  tool_names: string[];
  memory_policy_version: string;
  qualification_state: QualificationState;
  deployments: DeploymentSnapshot[];
};

export type AgentStudioOptions = {
  runtime: "ade_native";
  default_bundle_key: string;
  bundles: AgentStudioBundle[];
  default_timeout_seconds: number;
  default_retry_count: number;
  max_retry_count: number;
};

export type Message = {
  id: string;
  sequence: number;
  role: "user" | "assistant";
  content: string;
  run_id: string | null;
  created_at: string;
};

export type Summary = {
  id: string;
  version: number;
  previous_summary_id: string | null;
  content: string;
  source_boundary: { through_sequence: number; message_ids: string[] };
  provenance: {
    run_id: string;
    model_key: string;
    model_fingerprint: string;
    provider_request_id: string | null;
    content_sha256: string;
    prompt_sha256: string;
    input_sha256: string;
    policy_sha256: string;
  };
  created_at: string;
};

export type ConversationState = Conversation & {
  messages: Message[];
  message_total: number;
  messages_truncated: boolean;
  next_before_sequence: number | null;
  summary: Summary | null;
};

export type MessageSource = {
  message_id: string;
  conversation_id: string;
  message_sequence: number;
};

export type Relationship = {
  subject_id: string;
  character_root_id: string;
  state: string;
  last_error_code: string | null;
};

export type LearnedMemory = {
  id: string;
  text: string;
  context: string;
  fact_type: string | null;
  document_id: string | null;
  date: string;
  occurred_start: string | null;
  occurred_end: string | null;
  mentioned_at: string | null;
  entities: string;
  state: string;
  source_memory_ids: string[];
  consolidated_at: string | null;
  consolidation_failed_at: string | null;
};

export type RelationshipMemories = {
  relationship: Relationship; total: number; limit: number; offset: number; items: LearnedMemory[];
};

export type MemoryDelivery = MessageSource & {
  operation_id: string; document_id: string; relationship_sequence: number;
  role: "user" | "assistant";
  status: "queued" | "submitting" | "processing" | "retained" | "failed" | "uncertain";
  attempt_count: number; check_count: number; retry_requested: boolean;
  last_error_code: string | null; native_status: string | null;
  native_progress: Record<string, unknown>;
  accepted_at: string | null; retained_at: string | null; last_checked_at: string | null;
  created_at: string; updated_at: string; queue_age_seconds: number; blocked_by_operation_id: string | null;
};

export type MemoryDeliveries = {
  relationship: Relationship; total: number; limit: number; offset: number;
  counts: Record<string, number>; blocked_operation_id: string | null; items: MemoryDelivery[];
};

export type MemorySource = {
  relationship: Relationship; delivery: MemoryDelivery; content: string; occurred_at: string;
  definition_version_id: string; native_original_text: string | null; native_context: string | null;
};

export type MemoryOperation = {
  operation_id: string; operation_type: string | null; status: string;
  created_at: string | null; updated_at: string | null; native_progress: Record<string, unknown>;
};

export type MemoryOperations = {
  relationship: Relationship; total: number; limit: number; offset: number; items: MemoryOperation[];
};

export type RunEvent = {
  id: string;
  schema_version: number;
  run_id: string;
  sequence: number;
  attempt: number | null;
  type: string;
  occurred_at: string;
  correlation_id: string;
  causation_id: string | null;
  visibility: "operator";
  payload: Record<string, unknown>;
};

export type TurnActivity = {
  run_id: string;
  status: RunStatus;
  provider: Record<"generation" | "compaction" | "other", number>;
  provider_complete: boolean;
  provider_observed: boolean;
  tools: Array<{ name: string; succeeded: number; failed: number; unresolved: number }>;
  tools_complete: boolean;
  context: {
    current_chat: boolean | null;
    automatic_memory_ids: string[] | null;
    tool_memory_ids: string[] | null;
  };
};

export type CreateDefinition = {
  definition_key: string;
  name: string;
  model_key: string;
  compaction_model_key: string;
  prompt_key: string;
  persona_key: string;
  tool_names: Array<"search_memory" | "get_weather">;
  expected_current_version?: number;
};

export type CreateSession = {
  idempotency_key: string;
  title: string;
  agent_definition_id?: string;
  new_definition?: CreateDefinition;
  memory_subject_id?: string;
  new_subject?: { external_key: string; display_name: string };
};
