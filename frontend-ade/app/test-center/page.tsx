"use client";

import { useEffect, useMemo, useState } from "react";

import {
  PlatformArtifact,
  PlatformRunRecord,
  cancelTestRun,
  createTestRun,
  getTestRun,
  listRunArtifacts,
  listTestRuns,
  readRunArtifact,
} from "../../lib/api";

const RUN_TYPES = [
  "agent_bootstrap_check",
  "provider_embedding_matrix_check",
  "prompt_strategy_check",
  "platform_api_e2e_check",
  "ade_mvp_smoke_e2e_check",
  "migration_flag_rollout_check",
  "platform_dual_run_gate",
  "persona_guardrail_runner",
  "memory_update_runner",
];

function toErrorMessage(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

export default function TestCenterPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const [runs, setRuns] = useState<PlatformRunRecord[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedRun, setSelectedRun] = useState<PlatformRunRecord | null>(null);

  const [runType, setRunType] = useState("platform_api_e2e_check");
  const [model, setModel] = useState("");
  const [embedding, setEmbedding] = useState("");
  const [rounds, setRounds] = useState("10");
  const [configPath, setConfigPath] = useState("tests/configs/suites/lmstudio_custom_v2.json");

  const [artifacts, setArtifacts] = useState<PlatformArtifact[]>([]);
  const [selectedArtifactId, setSelectedArtifactId] = useState("");
  const [artifactContent, setArtifactContent] = useState("");

  const selectedRunSummary = useMemo(() => {
    if (selectedRun) {
      return selectedRun;
    }
    return runs.find((item) => item.run_id === selectedRunId) || null;
  }, [runs, selectedRun, selectedRunId]);

  const refreshRuns = async () => {
    const payload = await listTestRuns();
    const items = Array.isArray(payload.items) ? payload.items : [];
    setRuns(items);

    if (!selectedRunId && items.length > 0) {
      setSelectedRunId(items[0].run_id);
    }
  };

  const refreshSelectedRun = async (runId: string) => {
    if (!runId) {
      return;
    }
    const [run, artifactPayload] = await Promise.all([getTestRun(runId), listRunArtifacts(runId)]);
    setSelectedRun(run);
    setArtifacts(artifactPayload.items || []);
  };

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError("");
      try {
        await refreshRuns();
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

    const timer = setInterval(() => {
      void refreshRuns().catch(() => undefined);
      if (selectedRunId) {
        void refreshSelectedRun(selectedRunId).catch(() => undefined);
      }
    }, 4000);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [selectedRunId]);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }
    void refreshSelectedRun(selectedRunId).catch((exc) => {
      setError(toErrorMessage(exc));
    });
  }, [selectedRunId]);

  const onCreateRun = async () => {
    setBusy(true);
    setError("");
    setStatus("");
    try {
      const created = await createTestRun({
        run_type: runType,
        model: model.trim() || undefined,
        embedding: embedding.trim() || undefined,
        rounds: Number(rounds) || undefined,
        config_path: configPath.trim() || undefined,
      });
      setStatus(`Created run ${created.run_id}`);
      setSelectedRunId(created.run_id);
      await refreshRuns();
      await refreshSelectedRun(created.run_id);
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const onCancelSelected = async () => {
    if (!selectedRunId) {
      return;
    }
    setBusy(true);
    setError("");
    setStatus("");
    try {
      const payload = await cancelTestRun(selectedRunId);
      setStatus(`Cancel requested for ${payload.run_id}`);
      await refreshSelectedRun(selectedRunId);
      await refreshRuns();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const onReadArtifact = async (artifactId: string) => {
    if (!selectedRunId) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      const payload = await readRunArtifact(selectedRunId, artifactId, 250);
      setSelectedArtifactId(artifactId);
      setArtifactContent(payload.content || "");
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <div className="kicker">MVP Module</div>
      <h1 className="section-title">Test Center</h1>

      <div className="card">
        <h3>Create Test Run</h3>
        <div className="form-grid">
          <label className="field">
            <span>Run type</span>
            <select className="input" value={runType} onChange={(e) => setRunType(e.target.value)}>
              {RUN_TYPES.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Model (optional)</span>
            <input className="input" value={model} onChange={(e) => setModel(e.target.value)} />
          </label>
          <label className="field">
            <span>Embedding (optional)</span>
            <input className="input" value={embedding} onChange={(e) => setEmbedding(e.target.value)} />
          </label>
          <label className="field">
            <span>Rounds (optional)</span>
            <input className="input" value={rounds} onChange={(e) => setRounds(e.target.value)} />
          </label>
          <label className="field" style={{ gridColumn: "1 / -1" }}>
            <span>Config path (optional)</span>
            <input className="input" value={configPath} onChange={(e) => setConfigPath(e.target.value)} />
          </label>
        </div>
        <div className="toolbar" style={{ marginTop: 10 }}>
          <button className="button" onClick={() => void onCreateRun()} disabled={busy || loading}>
            {busy ? "Submitting..." : "Create Run"}
          </button>
          <button className="button muted" onClick={() => void refreshRuns()} disabled={busy || loading}>
            Refresh Runs
          </button>
        </div>
      </div>

      <div className="card-grid" style={{ marginTop: 14 }}>
        <div className="card">
          <h3>Runs</h3>
          <label className="field">
            <span>Select run</span>
            <select
              className="input"
              value={selectedRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
              disabled={runs.length === 0}
            >
              <option value="">Select run</option>
              {runs.map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {run.run_type} ({run.status})
                </option>
              ))}
            </select>
          </label>

          <div className="toolbar" style={{ marginTop: 10 }}>
            <button className="button muted" onClick={() => void refreshSelectedRun(selectedRunId)} disabled={!selectedRunId}>
              Refresh Selected Run
            </button>
            <button className="button" onClick={() => void onCancelSelected()} disabled={!selectedRunId || busy}>
              Cancel Run
            </button>
          </div>

          <div className="code" style={{ marginTop: 10, minHeight: 180 }}>
            {JSON.stringify(selectedRunSummary, null, 2)}
          </div>
        </div>

        <div className="card">
          <h3>Artifacts</h3>
          <div className="toolbar" style={{ marginBottom: 10 }}>
            <button
              className="button muted"
              onClick={() => (selectedRunId ? void refreshSelectedRun(selectedRunId) : undefined)}
              disabled={!selectedRunId}
            >
              Refresh Artifacts
            </button>
          </div>

          {artifacts.length === 0 ? (
            <p className="muted">No artifacts discovered yet.</p>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Type</th>
                    <th>Exists</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {artifacts.map((artifact) => (
                    <tr key={artifact.artifact_id}>
                      <td>{artifact.artifact_id}</td>
                      <td>{artifact.type}</td>
                      <td>{artifact.exists ? "yes" : "no"}</td>
                      <td>
                        <button className="button" onClick={() => void onReadArtifact(artifact.artifact_id)}>
                          Open
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="muted" style={{ marginTop: 10 }}>
            Active artifact: {selectedArtifactId || "none"}
          </p>
          <div className="code" style={{ minHeight: 180 }}>{artifactContent || "Artifact content appears here."}</div>
        </div>
      </div>

      {selectedRun?.output_tail?.length ? (
        <div className="card" style={{ marginTop: 14 }}>
          <h3>Run Output Tail</h3>
          <div className="code" style={{ minHeight: 180 }}>
            {(selectedRun.output_tail || []).join("\n")}
          </div>
        </div>
      ) : null}

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
