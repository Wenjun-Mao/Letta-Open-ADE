"use client";

import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react";

import { getMemoryDeliveries, getMemoryOperations, getMemorySource, getRelationshipMemories, retryMemoryDelivery } from "./api";
import type { AgentStudioSession, MemoryDelivery, MemorySource } from "./types";

type Scope = { subjectId: string; characterRootId: string };
type ReadState<T> = { key: string; data: T | null; error: string; loading: boolean };
const errorText = (value: unknown) => value instanceof Error ? value.message : String(value);

function useMemoryRead<T>(key: string, read: () => Promise<T>, enabled: boolean) {
  const [state, setState] = useState<ReadState<T>>({ key: "", data: null, error: "", loading: false });
  const [revision, setRevision] = useState(0);
  const readLatest = useEffectEvent(read);
  const refresh = useCallback(() => setRevision((value) => value + 1), []);
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const data = await readLatest();
        if (active) setState({ key, data, error: "", loading: false });
      } catch (error) {
        if (active) setState({ key, data: null, error: errorText(error), loading: false });
      } finally {
        if (active) timer = setTimeout(() => { void poll(); }, 2500);
      }
    }
    setState({ key, data: null, error: "", loading: true });
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [key, enabled, revision]);
  return { ...(state.key === key && enabled ? state : { data: null, error: "", loading: enabled }), refresh };
}

export function useRelationshipMemory(session: AgentStudioSession | null) {
  const [selection, setSelection] = useState<Scope | null>(null);
  const [memoryOffset, setMemoryOffset] = useState(0);
  const [deliveryOffset, setDeliveryOffset] = useState(0);
  const [operationOffset, setOperationOffset] = useState(0);
  const [source, setSource] = useState<{ key: string; data: MemorySource | null; error: string } | null>(null);
  const [retrying, setRetrying] = useState("");
  const [actionError, setActionError] = useState("");
  const sourceEpoch = useRef(0);
  const retryEpoch = useRef(0);
  const boundConversation = session?.conversation.id;
  const scope = selection || (session?.agent_definition.agent_definition_id ? {
    subjectId: session.memory_subject.id, characterRootId: session.agent_definition.agent_definition_id,
  } : null);
  const enabled = Boolean(scope?.subjectId && scope.characterRootId);
  const key = enabled ? `${scope!.subjectId}:${scope!.characterRootId}` : "";
  const currentKey = useRef(key);
  useEffect(() => {
    currentKey.current = key;
    sourceEpoch.current += 1; retryEpoch.current += 1;
    setRetrying(""); setActionError("");
  }, [key]);
  useEffect(() => {
    sourceEpoch.current += 1; retryEpoch.current += 1;
    setSelection(null);
    setMemoryOffset(0); setDeliveryOffset(0); setOperationOffset(0);
    setSource(null); setActionError("");
  }, [boundConversation]);
  useEffect(() => () => { sourceEpoch.current += 1; retryEpoch.current += 1; }, []);

  const memories = useMemoryRead(`${key}:${memoryOffset}`, () => getRelationshipMemories(scope!.subjectId, scope!.characterRootId, memoryOffset), enabled);
  const deliveries = useMemoryRead(`${key}:${deliveryOffset}`, () => getMemoryDeliveries(scope!.subjectId, scope!.characterRootId, deliveryOffset), enabled);
  const operations = useMemoryRead(`${key}:${operationOffset}`, () => getMemoryOperations(scope!.subjectId, scope!.characterRootId, operationOffset), enabled);

  function selectScope(next: Scope) {
    sourceEpoch.current += 1; retryEpoch.current += 1;
    setSelection(next);
    setMemoryOffset(0); setDeliveryOffset(0); setOperationOffset(0);
    setSource(null); setActionError(""); setRetrying("");
  }

  async function openSource(documentId: string) {
    if (!scope) return;
    const epoch = ++sourceEpoch.current;
    setSource({ key, data: null, error: "" });
    try {
      const data = await getMemorySource(scope.subjectId, scope.characterRootId, documentId);
      if (epoch === sourceEpoch.current && currentKey.current === key) setSource({ key, data, error: "" });
    } catch (error) {
      if (epoch === sourceEpoch.current && currentKey.current === key) setSource({ key, data: null, error: errorText(error) });
    }
  }

  async function retryDelivery(delivery: MemoryDelivery) {
    if (!scope) return;
    const epoch = ++retryEpoch.current;
    setRetrying(delivery.operation_id); setActionError("");
    try {
      await retryMemoryDelivery(scope.subjectId, scope.characterRootId, delivery);
      if (epoch === retryEpoch.current && currentKey.current === key) deliveries.refresh();
    } catch (error) {
      if (epoch === retryEpoch.current && currentKey.current === key) setActionError(errorText(error));
    } finally {
      if (epoch === retryEpoch.current && currentKey.current === key) setRetrying("");
    }
  }

  return { scope, memories, deliveries, operations, selectScope, openSource, retryDelivery, retrying, actionError,
    source: source?.key === key ? source : null,
    memoryOffset, setMemoryOffset, deliveryOffset, setDeliveryOffset, operationOffset, setOperationOffset };
}
