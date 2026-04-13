"use client";

import { useEffect, useMemo, useState } from "react";

import {
  fetchPromptPersonaMetadata,
  getAgentDetails,
  getPersistentState,
  listAgents,
  updateCoreMemoryBlock,
  updateSystemPrompt,
} from "../../lib/api";

function toErrorMessage(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

export default function PromptPersonaLabPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const [agents, setAgents] = useState<Array<{ id: string; name: string; model: string }>>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");

  const [metadata, setMetadata] = useState<{
    prompts: Array<{ key: string; label: string; description: string; preview: string }>;
    personas: Array<{ key: string; preview: string; length: number }>;
  }>({ prompts: [], personas: [] });

  const [systemPrompt, setSystemPrompt] = useState("");
  const [personaBlock, setPersonaBlock] = useState("");
  const [humanBlock, setHumanBlock] = useState("");

  const selectedAgent = useMemo(() => agents.find((agent) => agent.id === selectedAgentId), [agents, selectedAgentId]);

  const refreshAgentContext = async (agentId: string) => {
    const [details, persistent] = await Promise.all([getAgentDetails(agentId), getPersistentState(agentId, 60)]);

    setSystemPrompt(details.system || "");

    const blockMap = new Map((persistent.memory_blocks || []).map((block) => [block.label, block.value]));
    setPersonaBlock(blockMap.get("persona") || details.memory?.persona || "");
    setHumanBlock(blockMap.get("human") || details.memory?.human || "");
  };

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError("");
      try {
        const [meta, agentsPayload] = await Promise.all([fetchPromptPersonaMetadata(), listAgents(200)]);
        if (cancelled) {
          return;
        }

        setMetadata({ prompts: meta.prompts, personas: meta.personas });
        const mapped = agentsPayload.items.map((item) => ({
          id: item.id,
          name: item.name || item.id,
          model: item.model || "",
        }));
        setAgents(mapped);
        if (mapped.length > 0) {
          setSelectedAgentId(mapped[0].id);
        }
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
      setError("");
      try {
        await refreshAgentContext(selectedAgentId);
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

  const withBusy = async (fn: () => Promise<void>) => {
    setBusy(true);
    setStatus("");
    setError("");
    try {
      await fn();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const onApplySystem = async () => {
    if (!selectedAgentId) {
      setError("Select an agent first.");
      return;
    }
    await withBusy(async () => {
      const payload = await updateSystemPrompt(selectedAgentId, systemPrompt);
      setStatus(`System prompt updated. New length: ${(payload.system_after || "").length}`);
    });
  };

  const onApplyPersona = async () => {
    if (!selectedAgentId) {
      setError("Select an agent first.");
      return;
    }
    await withBusy(async () => {
      await updateCoreMemoryBlock(selectedAgentId, "persona", personaBlock);
      setStatus("Persona block updated.");
    });
  };

  const onApplyHuman = async () => {
    if (!selectedAgentId) {
      setError("Select an agent first.");
      return;
    }
    await withBusy(async () => {
      await updateCoreMemoryBlock(selectedAgentId, "human", humanBlock);
      setStatus("Human block updated.");
    });
  };

  return (
    <section>
      <div className="kicker">MVP Module</div>
      <h1 className="section-title">Prompt and Persona Lab</h1>

      <div className="card">
        <h3>Target Agent</h3>
        <div className="toolbar">
          <select
            className="input"
            value={selectedAgentId}
            onChange={(e) => setSelectedAgentId(e.target.value)}
            disabled={loading}
          >
            <option value="">Select agent</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name} ({agent.model})
              </option>
            ))}
          </select>
          <button
            className="button muted"
            onClick={() => (selectedAgentId ? void refreshAgentContext(selectedAgentId) : undefined)}
            disabled={!selectedAgentId || busy}
          >
            Reload agent state
          </button>
        </div>
        <p className="muted" style={{ marginTop: 8 }}>
          Active agent: {selectedAgent ? selectedAgent.name : "none"}
        </p>
      </div>

      <div className="card-grid" style={{ marginTop: 14 }}>
        <div className="card">
          <h3>System Prompt</h3>
          <textarea
            className="input"
            style={{ minHeight: 220, resize: "vertical" }}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
          />
          <div className="toolbar" style={{ marginTop: 10 }}>
            <button className="button" onClick={() => void onApplySystem()} disabled={busy || !selectedAgentId}>
              Apply System Prompt
            </button>
          </div>
        </div>

        <div className="card">
          <h3>Persona Block</h3>
          <textarea
            className="input"
            style={{ minHeight: 220, resize: "vertical" }}
            value={personaBlock}
            onChange={(e) => setPersonaBlock(e.target.value)}
          />
          <div className="toolbar" style={{ marginTop: 10 }}>
            <button className="button" onClick={() => void onApplyPersona()} disabled={busy || !selectedAgentId}>
              Apply Persona Block
            </button>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h3>Human Block</h3>
        <textarea
          className="input"
          style={{ minHeight: 180, resize: "vertical" }}
          value={humanBlock}
          onChange={(e) => setHumanBlock(e.target.value)}
        />
        <div className="toolbar" style={{ marginTop: 10 }}>
          <button className="button" onClick={() => void onApplyHuman()} disabled={busy || !selectedAgentId}>
            Apply Human Block
          </button>
        </div>
      </div>

      <div className="card-grid" style={{ marginTop: 14 }}>
        <div className="card">
          <h3>Prompt Templates Metadata</h3>
          <div className="code" style={{ minHeight: 150 }}>
            {JSON.stringify(metadata.prompts, null, 2)}
          </div>
        </div>

        <div className="card">
          <h3>Persona Metadata</h3>
          <div className="code" style={{ minHeight: 150 }}>
            {JSON.stringify(metadata.personas, null, 2)}
          </div>
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
