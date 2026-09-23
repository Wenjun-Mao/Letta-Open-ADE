"use client";

import { useCallback, useEffect, useState } from "react";

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

  const fetchTemplates = useCallback(() => Promise.all([listPromptTemplates(false, "chat"), listPersonaTemplates(false, "chat")]), []);

  const refreshTemplates = useCallback(async () => {
    try {
      const [nextPrompts, nextPersonas] = await fetchTemplates();
      setPrompts(nextPrompts.items);
      setPersonas(nextPersonas.items);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    }
  }, [fetchTemplates, setError]);

  useEffect(() => {
    let active = true;
    void fetchTemplates()
      .then(([nextPrompts, nextPersonas]) => {
        if (!active) return;
        setPrompts(nextPrompts.items);
        setPersonas(nextPersonas.items);
      })
      .catch((exc) => { if (active) setError(exc instanceof Error ? exc.message : String(exc)); });
    return () => { active = false; };
  }, [fetchTemplates, setError]);

  useEffect(() => {
    const onFocus = () => { void refreshTemplates(); };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [refreshTemplates]);

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
      const [freshPrompts, freshPersonas] = await fetchTemplates();
      const priorPrompt = prompts.find((item) => item.key === versionPromptKey);
      const priorPersona = personas.find((item) => item.key === versionPersonaKey);
      const freshPrompt = freshPrompts.items.find((item) => item.key === versionPromptKey);
      const freshPersona = freshPersonas.items.find((item) => item.key === versionPersonaKey);
      setPrompts(freshPrompts.items);
      setPersonas(freshPersonas.items);
      if (!freshPrompt || !freshPersona || priorPrompt?.content !== freshPrompt.content || priorPersona?.content !== freshPersona.content) {
        setError("Templates changed in Prompt Center. Review the refreshed previews before creating a version.");
        return;
      }
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
    setVersionPromptKey, setVersionPersonaKey, setVersionName, refreshTemplates, createDefinitionVersion };
}
