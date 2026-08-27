"use client";

import { useEffect, useEffectEvent, useMemo, useState } from "react";

import {
  archivePersonaTemplate,
  archivePromptTemplate,
  createPersonaTemplate,
  createPromptTemplate,
  listPersonaTemplates,
  listPromptTemplates,
  purgePersonaTemplate,
  purgePromptTemplate,
  restorePersonaTemplate,
  restorePromptTemplate,
  updatePersonaTemplate,
  updatePromptTemplate,
  type PromptTemplateRecord,
} from "./api";
import type { PromptCenterCopy } from "./copy";
import {
  buildWorkspaceLink,
  normalizeScenarioKey,
  resolvePromptCenterLaunchState,
  type CenterTab,
  toErrorMessage,
} from "./helpers";
import type { Scenario } from "@/features/model-catalog/api";

export function usePromptCenter(copy: PromptCenterCopy) {
  const [tab, setTabState] = useState<CenterTab>("prompts");
  const [scenario, setScenarioState] = useState<Scenario>("chat");
  const [launchHydrated, setLaunchHydrated] = useState(false);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [promptItems, setPromptItems] = useState<PromptTemplateRecord[]>([]);
  const [personaItems, setPersonaItems] = useState<PromptTemplateRecord[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [editingExisting, setEditingExisting] = useState(false);
  const [draftKey, setDraftKey] = useState("");
  const [draftLabel, setDraftLabel] = useState("");
  const [draftDescription, setDraftDescription] = useState("");
  const [draftContent, setDraftContent] = useState("");

  const activeItems = tab === "prompts" ? promptItems : personaItems;
  const selected = useMemo(
    () => activeItems.find((item) => item.key === selectedKey) || null,
    [activeItems, selectedKey],
  );
  const activePromptKeys = useMemo(
    () => promptItems.filter((item) => !item.archived).map((item) => item.key),
    [promptItems],
  );
  const activePersonaKeys = useMemo(
    () => personaItems.filter((item) => !item.archived).map((item) => item.key),
    [personaItems],
  );

  const resetDraft = () => {
    setSelectedKey("");
    setEditingExisting(false);
    setDraftKey("");
    setDraftLabel("");
    setDraftDescription("");
    setDraftContent("");
  };

  const hydrateDraft = (item: PromptTemplateRecord) => {
    setSelectedKey(item.key);
    setEditingExisting(true);
    setDraftKey(item.key);
    setDraftLabel(item.label || "");
    setDraftDescription(item.description || "");
    setDraftContent(item.content || "");
  };

  const setTab = (nextTab: CenterTab) => {
    if (nextTab === tab || (scenario === "label" && nextTab === "personas")) {
      return;
    }
    resetDraft();
    setError("");
    setStatus("");
    setTabState(nextTab);
  };

  const setScenario = (nextScenario: Scenario) => {
    if (nextScenario === scenario) {
      return;
    }
    resetDraft();
    setError("");
    setStatus("");
    if (nextScenario === "label") {
      setTabState("prompts");
    }
    setScenarioState(nextScenario);
  };

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      const [promptPayload, personaPayload] = await Promise.all([
        listPromptTemplates(includeArchived, scenario),
        listPersonaTemplates(includeArchived, scenario),
      ]);
      setPromptItems(promptPayload.items || []);
      setPersonaItems(personaPayload.items || []);

      if (selectedKey) {
        const currentList = tab === "prompts" ? promptPayload.items || [] : personaPayload.items || [];
        const matched = currentList.find((item) => item.key === selectedKey);
        if (matched) hydrateDraft(matched);
        else resetDraft();
      }
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setLoading(false);
    }
  };

  const refreshEffect = useEffectEvent(refresh);

  useEffect(() => {
    const launchState = resolvePromptCenterLaunchState(
      typeof window === "undefined" ? "" : window.location.search,
    );
    setTabState(launchState.tab);
    setScenarioState(launchState.scenario);
    setSelectedKey(launchState.key);
    setLaunchHydrated(true);
  }, []);

  useEffect(() => {
    if (!launchHydrated) {
      return;
    }
    void refreshEffect();
  }, [includeArchived, launchHydrated, scenario]);

  const save = async () => {
    if (!draftKey.trim()) {
      setError(`${copy.key} is required.`);
      return;
    }
    if (!draftContent.trim()) {
      setError(`${copy.content} is required.`);
      return;
    }
    if (selected?.archived) {
      setError(copy.saveDisabledArchived);
      return;
    }

    setBusy(true);
    setError("");
    setStatus("");
    try {
      const resolvedKey = editingExisting ? draftKey.trim() : normalizeScenarioKey(draftKey, scenario);
      setDraftKey(resolvedKey);
      const templateBody = {
        label: draftLabel.trim() || undefined,
        description: draftDescription.trim() || undefined,
        content: draftContent,
      };
      const createPayload = { scenario, key: resolvedKey, ...templateBody };
      const updateScenario = selected?.scenario || scenario;
      const result =
        tab === "prompts"
          ? editingExisting
            ? await updatePromptTemplate(draftKey.trim(), templateBody, updateScenario)
            : await createPromptTemplate(createPayload)
          : editingExisting
            ? await updatePersonaTemplate(draftKey.trim(), templateBody, updateScenario)
            : await createPersonaTemplate(createPayload);
      hydrateDraft(result);
      setStatus(`${tab === "prompts" ? copy.promptsTab : copy.personasTab}: ${editingExisting ? copy.saveUpdate : copy.saveCreate} OK`);
      await refresh();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const archive = async () => {
    if (!selected) return;

    setBusy(true);
    setError("");
    setStatus("");
    try {
      if (tab === "prompts") await archivePromptTemplate(selected.key, selected.scenario);
      else await archivePersonaTemplate(selected.key, selected.scenario);
      setStatus(`${selected.key}: ${copy.archive} OK`);
      await refresh();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const restore = async () => {
    if (!selected) return;

    setBusy(true);
    setError("");
    setStatus("");
    try {
      const result =
        tab === "prompts"
          ? await restorePromptTemplate(selected.key, selected.scenario)
          : await restorePersonaTemplate(selected.key, selected.scenario);
      hydrateDraft(result);
      setStatus(`${selected.key}: ${copy.restore} OK`);
      await refresh();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const purge = async () => {
    if (!selected || !selected.archived) return;
    if (typeof window !== "undefined" && !window.confirm(copy.confirmPurge)) return;

    setBusy(true);
    setError("");
    setStatus("");
    try {
      if (tab === "prompts") await purgePromptTemplate(selected.key, selected.scenario);
      else await purgePersonaTemplate(selected.key, selected.scenario);
      setStatus(`${selected.key}: ${copy.purge} OK`);
      resetDraft();
      await refresh();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const selectedScenario = selected?.scenario || scenario;
  const workspaceLink = buildWorkspaceLink({
    tab,
    scenario: selectedScenario,
    selectedKey: selected?.key || "",
    activePromptKeys,
    activePersonaKeys,
  });
  const workspaceLabel =
    workspaceLink.destination === "comment-lab"
      ? copy.openInCommentLab
      : workspaceLink.destination === "label-lab"
        ? copy.openInLabelLab
        : copy.openInAgentStudio;

  return {
    tab,
    setTab,
    scenario,
    setScenario,
    includeArchived,
    setIncludeArchived,
    loading,
    busy,
    error,
    status,
    activeItems,
    selected,
    selectedKey,
    editingExisting,
    draftKey,
    setDraftKey,
    draftLabel,
    setDraftLabel,
    draftDescription,
    setDraftDescription,
    draftContent,
    setDraftContent,
    resetDraft,
    hydrateDraft,
    refresh,
    save,
    archive,
    restore,
    purge,
    workspaceHref: workspaceLink.href,
    workspaceLabel,
  };
}

export type PromptCenterController = ReturnType<typeof usePromptCenter>;
