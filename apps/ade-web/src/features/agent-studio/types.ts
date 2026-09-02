export type QualificationState = "qualified" | "unqualified";
export type RunStatus = "pending" | "running" | "succeeded" | "failed" | "cancelled";
export type MemoryOperation = "add" | "correct" | "forget";

export type DeploymentSnapshot = {
  deployment_id: string;
  route_alias: string;
  fingerprint: string;
  role: "conversation" | "reviewer" | "retriever";
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
  reviewer_model_key: string;
  embedding_model_key: string;
  prompt_key: string;
  persona_key: string;
  tool_names: string[];
  memory_policy_version: string;
  qualification_state: QualificationState;
  deployments: DeploymentSnapshot[];
};

export type AgentStudioOptions = {
  runtime: "ade_native_v3";
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

export type MemoryEvidence = {
  message_id: string;
  start_char: number;
  end_char: number;
  quote: string;
  message_sha256: string;
};

export type MemoryRevision = {
  id: string;
  operation: MemoryOperation;
  fact_version: number;
  value: string | null;
  run_id: string;
  predecessor_revision_ids: string[];
  evidence: MemoryEvidence[];
  created_at: string;
};

export type MemoryFact = {
  id: string;
  key: string;
  fact_type: string;
  entity_id: string;
  entity_kind: string;
  entity_label: string;
  qualifier: string | null;
  value: string | null;
  status: "active" | "superseded" | "forgotten";
  version: number;
  revisions: MemoryRevision[];
  updated_at: string;
};

export type SubjectMemories = { subject_id: string; facts: MemoryFact[] };

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

export type CreateDefinition = {
  definition_key: string;
  name: string;
  model_key: string;
  reviewer_model_key: string;
  embedding_model_key: string;
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
