"use client";

import { useEffect, useEffectEvent, useMemo, useState } from "react";

import {
  archiveLabelSchema,
  createLabelSchema,
  listLabelSchemas,
  purgeLabelSchema,
  restoreLabelSchema,
  updateLabelSchema,
  type LabelSchemaRecord,
} from "./api";
import type { SchemaCenterCopy } from "./copy";
import { parseSchema, stringifySchema, toErrorMessage } from "./helpers";

export function useSchemaCenter(copy: SchemaCenterCopy) {
  const [includeArchived, setIncludeArchived] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [items, setItems] = useState<LabelSchemaRecord[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [editingExisting, setEditingExisting] = useState(false);
  const [draftKey, setDraftKey] = useState("");
  const [draftLabel, setDraftLabel] = useState("");
  const [draftDescription, setDraftDescription] = useState("");
  const [draftSchema, setDraftSchema] = useState("");

  const selected = useMemo(
    () => items.find((item) => item.key === selectedKey) || null,
    [items, selectedKey],
  );

  const resetDraft = () => {
    setSelectedKey("");
    setEditingExisting(false);
    setDraftKey("");
    setDraftLabel("");
    setDraftDescription("");
    setDraftSchema("");
  };

  const hydrateDraft = (item: LabelSchemaRecord) => {
    setSelectedKey(item.key);
    setEditingExisting(true);
    setDraftKey(item.key);
    setDraftLabel(item.label || "");
    setDraftDescription(item.description || "");
    setDraftSchema(stringifySchema(item.schema));
  };

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = await listLabelSchemas(includeArchived);
      const nextItems = payload.items || [];
      setItems(nextItems);
      if (selectedKey) {
        const matched = nextItems.find((item) => item.key === selectedKey);
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
    void refreshEffect();
  }, [includeArchived]);

  const save = async () => {
    if (!draftKey.trim()) {
      setError(`${copy.key} is required.`);
      return;
    }
    if (!draftSchema.trim()) {
      setError(`${copy.schema} is required.`);
      return;
    }
    if (selected?.archived) {
      setError(copy.readOnly);
      return;
    }

    setBusy(true);
    setError("");
    setStatus("");
    try {
      const schema = parseSchema(draftSchema);
      const payload = {
        key: draftKey.trim().toLowerCase(),
        label: draftLabel.trim() || undefined,
        description: draftDescription.trim() || undefined,
        schema,
      };
      const result = editingExisting
        ? await updateLabelSchema(draftKey.trim(), payload)
        : await createLabelSchema(payload);
      hydrateDraft(result);
      setStatus(`${result.key}: ${editingExisting ? copy.saveUpdate : copy.saveCreate} OK`);
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
      await archiveLabelSchema(selected.key);
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
      const result = await restoreLabelSchema(selected.key);
      hydrateDraft(result);
      setStatus(`${result.key}: ${copy.restore} OK`);
      await refresh();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const purge = async () => {
    if (!selected?.archived) return;
    if (typeof window !== "undefined" && !window.confirm(copy.confirmPurge)) return;

    setBusy(true);
    setError("");
    setStatus("");
    try {
      await purgeLabelSchema(selected.key);
      setStatus(`${selected.key}: ${copy.purge} OK`);
      resetDraft();
      await refresh();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  return {
    includeArchived,
    setIncludeArchived,
    loading,
    busy,
    error,
    status,
    items,
    selected,
    selectedKey,
    editingExisting,
    draftKey,
    setDraftKey,
    draftLabel,
    setDraftLabel,
    draftDescription,
    setDraftDescription,
    draftSchema,
    setDraftSchema,
    resetDraft,
    hydrateDraft,
    refresh,
    save,
    archive,
    restore,
    purge,
    labelLabHref: selectedKey ? `/label-lab?schemaKey=${encodeURIComponent(selectedKey)}` : "/label-lab",
  };
}

export type SchemaCenterController = ReturnType<typeof useSchemaCenter>;
