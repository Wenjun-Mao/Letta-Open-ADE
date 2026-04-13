"use client";

import { useEffect, useMemo, useState } from "react";

import { PlatformTool, attachTool, detachTool, listAgents, listTools } from "../../lib/api";

function toErrorMessage(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

export default function ToolbenchPage() {
  const [loading, setLoading] = useState(true);
  const [busyToolId, setBusyToolId] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const [agents, setAgents] = useState<Array<{ id: string; name: string; model: string }>>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [search, setSearch] = useState("");
  const [tools, setTools] = useState<PlatformTool[]>([]);

  const selectedAgent = useMemo(() => agents.find((agent) => agent.id === selectedAgentId), [agents, selectedAgentId]);

  const refreshTools = async (searchValue: string, agentId: string) => {
    const payload = await listTools(searchValue, 300, agentId);
    setTools(payload.items || []);
  };

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError("");
      try {
        const agentsPayload = await listAgents(200);
        if (cancelled) {
          return;
        }

        const mapped = agentsPayload.items.map((item) => ({
          id: item.id,
          name: item.name || item.id,
          model: item.model || "",
        }));
        setAgents(mapped);

        const firstId = mapped[0]?.id || "";
        setSelectedAgentId(firstId);
        await refreshTools("", firstId);
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
        await refreshTools(search, selectedAgentId);
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

  const onRefresh = async () => {
    setError("");
    try {
      await refreshTools(search, selectedAgentId);
    } catch (exc) {
      setError(toErrorMessage(exc));
    }
  };

  const onAttachOrDetach = async (tool: PlatformTool) => {
    if (!selectedAgentId) {
      setError("Select an agent first.");
      return;
    }

    setBusyToolId(tool.id);
    setError("");
    setStatus("");
    try {
      if (tool.attached_to_agent) {
        await detachTool(selectedAgentId, tool.id);
        setStatus(`Detached tool ${tool.name}`);
      } else {
        await attachTool(selectedAgentId, tool.id);
        setStatus(`Attached tool ${tool.name}`);
      }
      await refreshTools(search, selectedAgentId);
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusyToolId("");
    }
  };

  return (
    <section>
      <div className="kicker">MVP Module</div>
      <h1 className="section-title">Toolbench</h1>

      <div className="card">
        <h3>Context</h3>
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
          <input
            className="input"
            placeholder="Search tools"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button className="button muted" onClick={() => void onRefresh()}>
            Refresh
          </button>
        </div>
        <p className="muted" style={{ marginTop: 8 }}>
          Active agent: {selectedAgent ? selectedAgent.name : "none"}
        </p>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h3>Tool Catalog</h3>
        {tools.length === 0 ? (
          <p className="muted">No tools found for current search filter.</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Source</th>
                  <th>Attached</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {tools.map((tool) => (
                  <tr key={tool.id}>
                    <td>
                      <strong>{tool.name}</strong>
                      <p className="muted" style={{ margin: 0 }}>{tool.description || "No description"}</p>
                    </td>
                    <td>{tool.tool_type || "-"}</td>
                    <td>{tool.source_type || "-"}</td>
                    <td>{tool.attached_to_agent ? "yes" : "no"}</td>
                    <td>
                      <button
                        className="button"
                        disabled={!selectedAgentId || busyToolId === tool.id}
                        onClick={() => void onAttachOrDetach(tool)}
                      >
                        {busyToolId === tool.id
                          ? "Working..."
                          : tool.attached_to_agent
                            ? "Detach"
                            : "Attach"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
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
