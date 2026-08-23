"use client";

import { useEffect, useEffectEvent, useState } from "react";

import { createAgent, fetchOptions, type OptionEntry } from "../../lib/api";
import {
  parseOptionalPositiveInteger,
  parseOptionalTemperature,
  parseOptionalTopP,
  samplingDefaultString,
} from "../../lib/generation-controls";
import { reconcileAgentCreationSettings, resolveInitialAgentCreationSettings } from "./creation-settings";
import { AGENT_CREATE_SCENARIO, type Translate } from "./types";

type AgentCreationNotices = {
  clear: () => void;
  clearError: () => void;
  reportError: (error: unknown) => void;
  setStatus: (status: string) => void;
};

type UseAgentCreationArgs = {
  t: Translate;
  notices: AgentCreationNotices;
  onCreated: (agentId: string) => Promise<void>;
};

export function useAgentCreation({ t, notices, onCreated }: UseAgentCreationArgs) {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [models, setModels] = useState<OptionEntry[]>([]);
  const [embeddings, setEmbeddings] = useState<OptionEntry[]>([]);
  const [prompts, setPrompts] = useState<OptionEntry[]>([]);
  const [personas, setPersonas] = useState<OptionEntry[]>([]);
  const [createName, setCreateName] = useState("ade-agent");
  const [createModel, setCreateModel] = useState("");
  const [createPromptKey, setCreatePromptKey] = useState("chat_v20260516");
  const [createPersonaKey, setCreatePersonaKey] = useState("chat_linxiaotang");
  const [createEmbedding, setCreateEmbedding] = useState("");
  const [createTemperature, setCreateTemperature] = useState("");
  const [createTopP, setCreateTopP] = useState("");
  const [createTopK, setCreateTopK] = useState("");
  const clearInitialError = useEffectEvent(notices.clearError);
  const reportInitialError = useEffectEvent(notices.reportError);

  const applySettings = (settings: ReturnType<typeof reconcileAgentCreationSettings>) => {
    setCreateModel(settings.model);
    setCreatePromptKey(settings.promptKey);
    setCreatePersonaKey(settings.personaKey);
    setCreateEmbedding(settings.embedding);
    setCreateTemperature(settings.temperature);
    setCreateTopP(settings.topP);
    setCreateTopK(settings.topK);
  };

  const applyOptions = (payload: Awaited<ReturnType<typeof fetchOptions>>) => {
    setModels(payload.models || []);
    setEmbeddings(payload.embeddings || []);
    setPrompts(payload.prompts || []);
    setPersonas(payload.personas || []);
  };

  const refreshCreationOptions = async (forceRefresh = false) => {
    const payload = await fetchOptions(AGENT_CREATE_SCENARIO, forceRefresh ? { refresh: true } : undefined);
    applyOptions(payload);
    applySettings(
      reconcileAgentCreationSettings(
        {
          model: createModel,
          promptKey: createPromptKey,
          personaKey: createPersonaKey,
          embedding: createEmbedding,
          temperature: createTemperature,
          topP: createTopP,
          topK: createTopK,
        },
        payload,
      ),
    );
  };

  useEffect(() => {
    let cancelled = false;

    const loadOptions = async () => {
      setLoading(true);
      clearInitialError();
      try {
        const payload = await fetchOptions(AGENT_CREATE_SCENARIO);
        if (cancelled) {
          return;
        }
        applyOptions(payload);
        applySettings(
          resolveInitialAgentCreationSettings(
            payload,
            typeof window === "undefined" ? "" : window.location.search,
          ),
        );
      } catch (error) {
        if (!cancelled) {
          reportInitialError(error);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadOptions();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const selected = models.find((item) => item.key === createModel);
    if (!selected) {
      return;
    }
    const nextTemperature = samplingDefaultString(selected, "agent_studio", "temperature");
    const nextTopP = samplingDefaultString(selected, "agent_studio", "top_p");
    const nextTopK = samplingDefaultString(selected, "agent_studio", "top_k");
    if (nextTemperature !== null) {
      setCreateTemperature(nextTemperature);
    }
    if (nextTopP !== null) {
      setCreateTopP(nextTopP);
    }
    setCreateTopK(nextTopK ?? "");
  }, [createModel, models]);

  const create = async () => {
    if (!createModel.trim()) {
      notices.setStatus("");
      notices.reportError(t("Please select a model before creating an agent.", "创建智能体前请先选择模型。"));
      return;
    }
    const temperature = parseOptionalTemperature(createTemperature);
    if (temperature === null) {
      notices.reportError(t("Temperature must be between 0 and 2.", "Temperature 必须在 0 到 2 之间。"));
      return;
    }
    const topP = parseOptionalTopP(createTopP);
    if (topP === null) {
      notices.reportError(t("Top P must be greater than 0 and at most 1.", "Top P 必须大于 0 且不超过 1。"));
      return;
    }
    const topK = parseOptionalPositiveInteger(createTopK);
    if (topK === null) {
      notices.reportError(t("Top K must be a positive integer, or blank to use the model default.", "Top K 必须是正整数，或留空使用模型默认值。"));
      return;
    }

    setBusy(true);
    notices.clear();
    try {
      const created = await createAgent({
        scenario: AGENT_CREATE_SCENARIO,
        name: createName.trim() || "ade-agent",
        model: createModel,
        prompt_key: createPromptKey,
        persona_key: createPersonaKey,
        embedding: createEmbedding.trim() || null,
        temperature,
        top_p: topP,
        top_k: topK,
      });
      await onCreated(created.id);
      notices.setStatus(t(`Created agent ${created.name} (${created.id})`, `已创建智能体 ${created.name} (${created.id})`));
    } catch (error) {
      notices.reportError(error);
    } finally {
      setBusy(false);
    }
  };

  const reloadModels = async () => {
    setBusy(true);
    notices.clearError();
    try {
      await refreshCreationOptions(true);
      notices.setStatus(t("Model options reloaded from backend.", "模型选项已从后端重新加载。"));
    } catch (error) {
      notices.reportError(error);
    } finally {
      setBusy(false);
    }
  };

  return {
    loading,
    busy,
    models,
    embeddings,
    prompts,
    personas,
    createName,
    createModel,
    createPromptKey,
    createPersonaKey,
    createEmbedding,
    createTemperature,
    createTopP,
    createTopK,
    setCreateName,
    setCreateModel,
    setCreatePromptKey,
    setCreatePersonaKey,
    setCreateEmbedding,
    setCreateTemperature,
    setCreateTopP,
    setCreateTopK,
    create,
    reloadModels,
  };
}
