"use client";

import { useEffect, useState } from "react";

import { listPersonaTemplates, listPromptTemplates, type PromptTemplateRecord } from "@/features/prompt-center/api";

import { createAgentStudioDefinition } from "./api";
import type { AgentDefinition, AgentStudioSession } from "./types";

type Params = {
  session: AgentStudioSession | null;
  definitions: AgentDefinition[];
  refreshWorkspace: () => Promise<void>;
  setDefinitionChoice: (id: string) => void;
  setBusy: (busy: boolean) => void;
  setError: (error: string) => void;
};

export function useDefinitionVersion({ session, definitions, refreshWorkspace, setDefinitionChoice, setBusy, setError }: Params) {
  const [prompts, setPrompts] = useState<PromptTemplateRecord[]>([]);
  const [personas, setPersonas] = useState<PromptTemplateRecord[]>([]);
  const [versionPromptKey, setVersionPromptKey] = useState("");
  const [versionPersonaKey, setVersionPersonaKey] = useState("");
  const [versionName, setVersionName] = useState("");

  useEffect(() => {
    let active = true;
    void Promise.all([listPromptTemplates(false, "chat"), listPersonaTemplates(false, "chat")])
      .then(([nextPrompts, nextPersonas]) => {
        if (!active) return;
        setPrompts(nextPrompts.items);
        setPersonas(nextPersonas.items);
      })
      .catch((exc) => { if (active) setError(exc instanceof Error ? exc.message : String(exc)); });
    return () => { active = false; };
  }, [setError]);

  const selectedDefinition = session?.agent_definition;
  useEffect(() => {
    setVersionPromptKey(selectedDefinition?.prompt_key || "");
    setVersionPersonaKey(selectedDefinition?.persona_key || "");
    setVersionName(selectedDefinition?.name || "");
  }, [selectedDefinition?.id, selectedDefinition?.name, selectedDefinition?.persona_key, selectedDefinition?.prompt_key]);

  async function createDefinitionVersion() {
    const prior = selectedDefinition;
    if (!prior?.agent_definition_id || !versionName.trim()) return;
    const current = definitions.filter((item) => item.agent_definition_id === prior.agent_definition_id)
      .sort((left, right) => right.version - left.version)[0] || prior;
    const route = (role: "conversation" | "reviewer" | "retriever") => current.deployments.find((item) => item.role === role)?.route_alias;
    const model = route("conversation");
    const reviewer = route("reviewer");
    const retriever = route("retriever");
    if (!model || !reviewer || !retriever || !prompts.some((item) => item.key === versionPromptKey) || !personas.some((item) => item.key === versionPersonaKey)) {
      setError("Choose active prompt and persona templates with a complete qualified deployment snapshot.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const created = await createAgentStudioDefinition({
        definition_key: prior.definition_key,
        name: versionName.trim(),
        model_key: model,
        reviewer_model_key: reviewer,
        embedding_model_key: retriever,
        prompt_key: versionPromptKey,
        persona_key: versionPersonaKey,
        tool_names: current.tool_names.filter((tool): tool is "search_memory" | "get_weather" => tool === "search_memory" || tool === "get_weather"),
        expected_current_version: current.version,
      });
      await refreshWorkspace();
      setDefinitionChoice(created.id);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  }

  return { prompts, personas, versionPromptKey, versionPersonaKey, versionName,
    setVersionPromptKey, setVersionPersonaKey, setVersionName, createDefinitionVersion };
}
