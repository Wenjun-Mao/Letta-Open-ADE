export type Scenario = "chat" | "comment" | "label";
export type LabelingOutputMode = "strict_json_schema" | "json_schema" | "best_effort_prompt_json";

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

export type ScenarioOptions = {
  scenario: Scenario;
  models: OptionEntry[];
  embeddings: OptionEntry[];
  prompts: OptionEntry[];
  personas: OptionEntry[];
  schemas: OptionEntry[];
  defaults: {
    scenario: Scenario;
    model: string;
    prompt_key: string;
    persona_key: string;
    embedding: string;
    schema_key: string;
  };
  commenting?: {
    max_tokens: number;
    timeout_seconds: number;
    task_shape: "classic" | "all_in_system" | "structured_output";
    cache_prompt: boolean;
    temperature: number;
    top_p: number;
    top_k?: number | null;
  };
  labeling?: {
    max_tokens: number;
    timeout_seconds: number;
    repair_retry_count: number;
    temperature: number;
    top_p: number;
    top_k?: number | null;
  };
  agent_studio?: {
    temperature?: number | null;
    top_p?: number | null;
    top_k?: number | null;
  };
};
