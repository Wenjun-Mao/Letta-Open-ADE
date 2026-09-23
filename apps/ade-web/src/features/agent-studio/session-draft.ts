import { defaultBundle, NEW_RESOURCE_VALUE } from "./selection";
import type { AgentStudioOptions, CreateSession } from "./types";

export type SessionDraft = {
  title: string;
  definitionChoice: string;
  definitionName: string;
  definitionKey: string;
  subjectChoice: string;
  subjectName: string;
  subjectKey: string;
};

export function sessionDraftPayload(options: AgentStudioOptions | null, draft: SessionDraft, idempotencyKey: string): CreateSession {
  const bundle = defaultBundle(options);
  if (!bundle) throw new Error("No configured Agent Studio bundle is available.");
  if (!draft.title.trim()) throw new Error("Conversation title is required.");
  if (draft.definitionChoice === NEW_RESOURCE_VALUE && (!draft.definitionName.trim() || !draft.definitionKey.trim())) {
    throw new Error("A definition name and key are required.");
  }
  if (draft.subjectChoice === NEW_RESOURCE_VALUE && (!draft.subjectName.trim() || !draft.subjectKey.trim())) {
    throw new Error("A memory subject name and external key are required.");
  }
  return {
    idempotency_key: idempotencyKey,
    title: draft.title.trim(),
    ...(draft.definitionChoice === NEW_RESOURCE_VALUE ? { new_definition: {
      definition_key: draft.definitionKey.trim(),
      name: draft.definitionName.trim(),
      model_key: bundle.model_key,
      reviewer_model_key: bundle.reviewer_model_key,
      embedding_model_key: bundle.embedding_model_key,
      prompt_key: bundle.prompt_key,
      persona_key: bundle.persona_key,
      tool_names: bundle.tool_names.filter((tool): tool is "search_memory" | "get_weather" => tool === "search_memory" || tool === "get_weather"),
    } } : { agent_definition_id: draft.definitionChoice }),
    ...(draft.subjectChoice === NEW_RESOURCE_VALUE
      ? { new_subject: { external_key: draft.subjectKey.trim(), display_name: draft.subjectName.trim() } }
      : { memory_subject_id: draft.subjectChoice }),
  };
}
