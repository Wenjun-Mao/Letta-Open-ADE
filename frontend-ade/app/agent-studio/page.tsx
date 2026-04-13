"use client";

import { useEffect, useMemo, useState } from "react";

import {
  ChatResult,
  OptionEntry,
  createAgent,
  fetchOptions,
  getAgentDetails,
  getPersistentState,
  getRawPrompt,
  listAgents,
  sendChat,
} from "../../lib/api";

type TurnEntry = {
  id: string;
  user: string;
  assistant: string;
  result: ChatResult;
};

function toErrorMessage(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

function extractAssistantReply(result: ChatResult): string {
  const reversed = [...(result.sequence || [])].reverse();
  const assistant = reversed.find((step) => step.type === "assistant" && step.content);
  return assistant?.content || "";
}

export default function AgentStudioPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [chatBusy, setChatBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const [models, setModels] = useState<OptionEntry[]>([]);
  const [embeddings, setEmbeddings] = useState<OptionEntry[]>([]);
  const [prompts, setPrompts] = useState<OptionEntry[]>([]);

  const [agents, setAgents] = useState<Array<{ id: string; name: string; model: string }>>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");

  const [createName, setCreateName] = useState("ade-agent");
  const [createModel, setCreateModel] = useState("");
  const [createPromptKey, setCreatePromptKey] = useState("custom_v2");
  const [createEmbedding, setCreateEmbedding] = useState("");

  const [chatInput, setChatInput] = useState("");
  const [turns, setTurns] = useState<TurnEntry[]>([]);

  const [agentSystem, setAgentSystem] = useState("");
  const [agentMemory, setAgentMemory] = useState<Record<string, string>>({});
  const [memoryBlocks, setMemoryBlocks] = useState<
    Array<{ label: string; value: string; description: string; limit: number | null }>
  >([]);
  const [rawPromptMessages, setRawPromptMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [historyCount, setHistoryCount] = useState(0);

  const selectedAgentName = useMemo(() => {
    const found = agents.find((item) => item.id === selectedAgentId);
    return found ? found.name : "";
  }, [agents, selectedAgentId]);

  const refreshAgentList = async () => {
    const payload = await listAgents(200);
    const mapped = payload.items.map((item) => ({
      id: item.id,
      name: item.name || item.id,
      model: item.model || "",
    }));
    setAgents(mapped);

    if (!selectedAgentId && mapped.length > 0) {
      setSelectedAgentId(mapped[0].id);
    }
  };

  const refreshSelectedAgent = async (agentId: string) => {
    if (!agentId) {
      return;
    }
    const [details, persistent, rawPrompt] = await Promise.all([
      getAgentDetails(agentId),
      getPersistentState(agentId, 120),
      getRawPrompt(agentId),
    ]);

    setAgentSystem(details.system || "");
    setAgentMemory(details.memory || {});
    setMemoryBlocks(Array.isArray(persistent.memory_blocks) ? persistent.memory_blocks : []);
    setHistoryCount(Number(persistent.conversation_history?.total_persisted || 0));
    setRawPromptMessages(Array.isArray(rawPrompt.messages) ? rawPrompt.messages : []);
  };

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError("");
      try {
        const [optionsPayload] = await Promise.all([fetchOptions()]);
        if (cancelled) {
          return;
        }

        setModels(optionsPayload.models || []);
        setEmbeddings(optionsPayload.embeddings || []);
        setPrompts(optionsPayload.prompts || []);
        setCreateModel(optionsPayload.defaults?.model || optionsPayload.models?.[0]?.key || "");
        setCreatePromptKey(optionsPayload.defaults?.prompt_key || "custom_v2");
        setCreateEmbedding(optionsPayload.defaults?.embedding || "");

        await refreshAgentList();
      } catch (exc) {
        if (!cancelled) {
          setError(toErrorMessage(exc));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedAgentId) {
      return;
    }
    let cancelled = false;
    const run = async () => {
      try {
        await refreshSelectedAgent(selectedAgentId);
      } catch (exc) {
        if (!cancelled) {
          setError(toErrorMessage(exc));
        }
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [selectedAgentId]);

  const onCreateAgent = async () => {
    if (!createModel.trim()) {
      setError("Please select a model before creating an agent.");
      return;
    }

    setBusy(true);
    setError("");
    setStatus("");
    try {
      const created = await createAgent({
        name: createName.trim() || "ade-agent",
        model: createModel,
        prompt_key: createPromptKey,
        embedding: createEmbedding.trim() || null,
      });

      await refreshAgentList();
      setSelectedAgentId(created.id);
      setTurns([]);
      setStatus(`Created agent ${created.name} (${created.id})`);
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const onSendMessage = async () => {
    if (!selectedAgentId) {
      setError("Select an agent first.");
      return;
    }
    const text = chatInput.trim();
    if (!text) {
      return;
    }

    setChatBusy(true);
    setError("");
    setStatus("");
    try {
      const result = await sendChat(selectedAgentId, text);
      const assistant = extractAssistantReply(result);

      setTurns((prev) => [
        {
          id: `${Date.now()}`,
          user: text,
          assistant,
          result,
        },
        ...prev,
      ]);
      setChatInput("");

      await refreshSelectedAgent(selectedAgentId);
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setChatBusy(false);
    }
  };

  return (
    <section>
      <div className="kicker">MVP Module</div>
      <h1 className="section-title">Agent Studio</h1>

      <div className="card-grid">
        <div className="card">
          <h3>Create Agent</h3>
          <div className="form-grid">
            <label className="field">
              <span>Agent name</span>
              <input className="input" value={createName} onChange={(e) => setCreateName(e.target.value)} />
            </label>
            <label className="field">
              <span>Model</span>
              <select className="input" value={createModel} onChange={(e) => setCreateModel(e.target.value)}>
                <option value="">Select model</option>
                {models.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Prompt</span>
              <select className="input" value={createPromptKey} onChange={(e) => setCreatePromptKey(e.target.value)}>
                {prompts.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Embedding (optional)</span>
              <select className="input" value={createEmbedding} onChange={(e) => setCreateEmbedding(e.target.value)}>
                <option value="">No explicit override</option>
                {embeddings.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="toolbar" style={{ marginTop: 10 }}>
            <button className="button" onClick={onCreateAgent} disabled={busy || loading}>
              {busy ? "Creating..." : "Create Agent"}
            </button>
            <button className="button muted" onClick={() => void refreshAgentList()} disabled={busy || loading}>
              Refresh Agent List
            </button>
          </div>
        </div>

        <div className="card">
          <h3>Current Agent</h3>
          <label className="field">
            <span>Select agent</span>
            <select
              className="input"
              value={selectedAgentId}
              onChange={(e) => setSelectedAgentId(e.target.value)}
              disabled={loading}
            >
              <option value="">Select agent</option>
              {agents.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} ({item.model})
                </option>
              ))}
            </select>
          </label>

          <div className="toolbar" style={{ marginTop: 10 }}>
            <button
              className="button muted"
              onClick={() => (selectedAgentId ? void refreshSelectedAgent(selectedAgentId) : undefined)}
              disabled={!selectedAgentId}
            >
              Refresh Selected Agent
            </button>
          </div>

          <p className="muted" style={{ marginTop: 10 }}>
            Active: {selectedAgentName || "none"}
          </p>
          <p className="muted">Conversation history rows: {historyCount}</p>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h3>Runtime Chat</h3>
        <div className="toolbar">
          <textarea
            className="input"
            style={{ minHeight: 78, resize: "vertical", flex: 1 }}
            placeholder="Say something to the selected agent"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
          />
          <button className="button" onClick={onSendMessage} disabled={chatBusy || !selectedAgentId}>
            {chatBusy ? "Sending..." : "Send"}
          </button>
        </div>

        {turns.length === 0 ? (
          <p className="muted" style={{ marginTop: 10 }}>
            Send a message to view execution steps and memory diff.
          </p>
        ) : (
          <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
            {turns.map((turn) => (
              <details key={turn.id} className="card" open>
                <summary>
                  <strong>User</strong>: {turn.user}
                </summary>
                <p className="muted" style={{ marginTop: 8 }}>
                  Assistant: {turn.assistant || "(no assistant text in result)"}
                </p>
                <div className="code" style={{ marginTop: 10 }}>
                  {JSON.stringify(turn.result.sequence, null, 2)}
                </div>
                <div className="code" style={{ marginTop: 10 }}>
                  {JSON.stringify(turn.result.memory_diff, null, 2)}
                </div>
              </details>
            ))}
          </div>
        )}
      </div>

      <div className="card-grid" style={{ marginTop: 14 }}>
        <div className="card">
          <h3>Agent System Prompt</h3>
          <div className="code" style={{ minHeight: 130 }}>{agentSystem || "No system prompt loaded."}</div>
        </div>

        <div className="card">
          <h3>Core Memory Snapshot</h3>
          <div className="code" style={{ minHeight: 130 }}>
            {JSON.stringify(agentMemory, null, 2) || "{}"}
          </div>
        </div>
      </div>

      <div className="card-grid" style={{ marginTop: 14 }}>
        <div className="card">
          <h3>Memory Blocks</h3>
          <div className="code" style={{ minHeight: 160 }}>{JSON.stringify(memoryBlocks, null, 2)}</div>
        </div>

        <div className="card">
          <h3>Raw Prompt View</h3>
          <div className="code" style={{ minHeight: 160 }}>{JSON.stringify(rawPromptMessages, null, 2)}</div>
        </div>
      </div>

      {status ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#bbf7d0" }}>
          <h3>Status</h3>
          <p className="muted">{status}</p>
        </div>
      ) : null}

      {error ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#fecaca" }}>
          <h3>Error</h3>
          <p className="muted">{error}</p>
        </div>
      ) : null}
    </section>
  );
}
