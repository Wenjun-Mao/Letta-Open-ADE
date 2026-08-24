"use client";

import { useEffect, useEffectEvent, useMemo, useState } from "react";

import {
  archiveToolCenterTool,
  createToolCenterTool,
  getToolCenterTool,
  listToolCenterTools,
  purgeToolCenterTool,
  restoreToolCenterTool,
  updateToolCenterTool,
  type ToolCenterItem,
} from "./api";
import type { ToolCenterCopy } from "./copy";
import {
  DEFAULT_TOOL_SOURCE,
  getToolIdentifier,
  isPrimaryActionDisabled,
  parseTags,
  toErrorMessage,
  type ViewMode,
} from "./helpers";

export function useToolCenter(copy: ToolCenterCopy) {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [includeBuiltin, setIncludeBuiltin] = useState(true);
  const [includeSourceInList, setIncludeSourceInList] = useState(false);
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<ToolCenterItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [mode, setMode] = useState<ViewMode>("create");
  const [draftSlug, setDraftSlug] = useState("");
  const [draftDescription, setDraftDescription] = useState("");
  const [draftTags, setDraftTags] = useState("");
  const [draftSource, setDraftSource] = useState(DEFAULT_TOOL_SOURCE);

  const selected = useMemo(
    () => items.find((item) => getToolIdentifier(item) === selectedId) || null,
    [items, selectedId],
  );
  const primaryDisabled = isPrimaryActionDisabled({ busy, loading, mode, selected });

  const resetDraft = () => {
    setMode("create");
    setSelectedId("");
    setDraftSlug("");
    setDraftDescription("");
    setDraftTags("");
    setDraftSource(DEFAULT_TOOL_SOURCE);
  };

  const hydrateDraft = (item: ToolCenterItem, withSource = true) => {
    setMode(item.managed ? "edit" : "create");
    setSelectedId(getToolIdentifier(item));
    setDraftSlug(item.slug || "");
    setDraftDescription(item.description || "");
    setDraftTags((item.tags || []).join(", "));
    if (withSource) setDraftSource(item.source_code || "");
  };

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = await listToolCenterTools({
        includeArchived,
        includeBuiltin,
        includeSource: includeSourceInList,
        search,
      });
      const nextItems = payload.items || [];
      setItems(nextItems);

      if (selectedId) {
        const stillThere = nextItems.find((item) => getToolIdentifier(item) === selectedId);
        if (stillThere) {
          if (stillThere.managed && stillThere.slug && !includeSourceInList) {
            hydrateDraft(await getToolCenterTool(stillThere.slug, true), true);
          } else {
            hydrateDraft(stillThere, true);
          }
        } else {
          resetDraft();
        }
      }
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setLoading(false);
    }
  };

  const refreshEffect = useEffectEvent(refresh);

  useEffect(() => {
    void refreshEffect();
  }, [includeArchived, includeBuiltin, includeSourceInList]);

  const select = async (item: ToolCenterItem) => {
    setError("");
    setStatus("");
    if (item.managed && item.slug) {
      try {
        hydrateDraft(await getToolCenterTool(item.slug, true), true);
      } catch (exc) {
        setError(toErrorMessage(exc));
      }
      return;
    }
    hydrateDraft(item, false);
  };

  const create = async () => {
    if (!draftSlug.trim()) {
      setError(`${copy.slug} is required.`);
      return;
    }
    if (!draftSource.trim()) {
      setError(`${copy.source} is required.`);
      return;
    }

    setBusy(true);
    setError("");
    setStatus("");
    try {
      const created = await createToolCenterTool({
        slug: draftSlug.trim(),
        source_code: draftSource,
        description: draftDescription.trim(),
        tags: parseTags(draftTags),
      });
      hydrateDraft(created, true);
      setStatus(`${created.slug || created.name}: ${copy.create} OK`);
      await refresh();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const update = async () => {
    if (!selected?.managed || !selected.slug) return;
    if (selected.archived) {
      setError(`${copy.archivedBadge}: restore before update.`);
      return;
    }

    setBusy(true);
    setError("");
    setStatus("");
    try {
      const updated = await updateToolCenterTool(selected.slug, {
        source_code: draftSource,
        description: draftDescription.trim(),
        tags: parseTags(draftTags),
      });
      hydrateDraft(updated, true);
      setStatus(`${updated.slug || updated.name}: ${copy.update} OK`);
      await refresh();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const archive = async () => {
    if (!selected?.managed || !selected.slug || selected.archived) return;

    setBusy(true);
    setError("");
    setStatus("");
    try {
      const archived = await archiveToolCenterTool(selected.slug);
      hydrateDraft(archived, true);
      setStatus(`${archived.slug || archived.name}: ${copy.archive} OK`);
      await refresh();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const restore = async () => {
    if (!selected?.managed || !selected.slug || !selected.archived) return;

    setBusy(true);
    setError("");
    setStatus("");
    try {
      const restored = await restoreToolCenterTool(selected.slug);
      hydrateDraft(restored, true);
      setStatus(`${restored.slug || restored.name}: ${copy.restore} OK`);
      await refresh();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const purge = async () => {
    if (!selected?.managed || !selected.slug || !selected.archived) return;
    if (typeof window !== "undefined" && !window.confirm(copy.confirmPurge)) return;

    setBusy(true);
    setError("");
    setStatus("");
    try {
      await purgeToolCenterTool(selected.slug);
      setStatus(`${selected.slug}: ${copy.purge} OK`);
      resetDraft();
      await refresh();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  return {
    loading,
    busy,
    error,
    status,
    includeArchived,
    setIncludeArchived,
    includeBuiltin,
    setIncludeBuiltin,
    includeSourceInList,
    setIncludeSourceInList,
    search,
    setSearch,
    items,
    selected,
    selectedId,
    mode,
    draftSlug,
    setDraftSlug,
    draftDescription,
    setDraftDescription,
    draftTags,
    setDraftTags,
    draftSource,
    setDraftSource,
    primaryDisabled,
    resetDraft,
    refresh,
    select,
    create,
    update,
    archive,
    restore,
    purge,
  };
}

export type ToolCenterController = ReturnType<typeof useToolCenter>;
