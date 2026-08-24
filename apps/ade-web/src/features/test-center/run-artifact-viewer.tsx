import type { TestArtifact, TestRunRecord } from "./api";
import type { TestCenterCopy } from "./test-center-copy";

type Props = {
  copy: TestCenterCopy;
  busy: boolean;
  runs: TestRunRecord[];
  selectedRunId: string;
  selectedRunSummary: TestRunRecord | null;
  selectedRun: TestRunRecord | null;
  artifacts: TestArtifact[];
  selectedArtifactId: string;
  artifactContent: string;
  onSelectRun: (runId: string) => void;
  onRefreshSelectedRun: () => void;
  onCancelSelectedRun: () => void;
  onRefreshArtifacts: () => void;
  onReadArtifact: (artifactId: string) => void;
};

export function RunArtifactViewer(props: Props) {
  const hasSelectedRun = Boolean(props.selectedRunId);
  return (
    <>
      <div className="card-grid" style={{ marginTop: 14 }}>
        <div className="card">
          <h3>{props.copy.runsTitle}</h3>
          <label className="field">
            <span>{props.copy.selectRun}</span>
            <select
              className="input"
              value={props.selectedRunId}
              onChange={(e) => props.onSelectRun(e.target.value)}
              disabled={props.runs.length === 0}
            >
              <option value="">{props.copy.selectRunPlaceholder}</option>
              {props.runs.map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {run.run_type} ({run.status})
                </option>
              ))}
            </select>
          </label>

          <div className="toolbar" style={{ marginTop: 10 }}>
            <button className="button muted" onClick={props.onRefreshSelectedRun} disabled={!hasSelectedRun}>
              {props.copy.refreshSelectedRun}
            </button>
            <button className="button" onClick={props.onCancelSelectedRun} disabled={!hasSelectedRun || props.busy}>
              {props.copy.cancelRun}
            </button>
          </div>

          <div className="code" style={{ marginTop: 10, minHeight: 180 }}>
            {JSON.stringify(props.selectedRunSummary, null, 2)}
          </div>
        </div>

        <div className="card">
          <h3>{props.copy.artifactsTitle}</h3>
          <div className="toolbar" style={{ marginBottom: 10 }}>
            <button className="button muted" onClick={props.onRefreshArtifacts} disabled={!hasSelectedRun}>
              {props.copy.refreshArtifacts}
            </button>
          </div>

          {props.artifacts.length === 0 ? (
            <p className="muted">{props.copy.noArtifacts}</p>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{props.copy.id}</th>
                    <th>{props.copy.type}</th>
                    <th>{props.copy.exists}</th>
                    <th>{props.copy.action}</th>
                  </tr>
                </thead>
                <tbody>
                  {props.artifacts.map((artifact) => (
                    <tr key={artifact.artifact_id}>
                      <td>{artifact.artifact_id}</td>
                      <td>{artifact.type}</td>
                      <td>{artifact.exists ? props.copy.yes : props.copy.no}</td>
                      <td>
                        <button className="button" onClick={() => props.onReadArtifact(artifact.artifact_id)}>
                          {props.copy.open}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="muted" style={{ marginTop: 10 }}>
            {props.copy.activeArtifact}: {props.selectedArtifactId || props.copy.noActiveArtifact}
          </p>
          <div className="code" style={{ minHeight: 180 }}>
            {props.artifactContent || props.copy.artifactContentPlaceholder}
          </div>
        </div>
      </div>

      {props.selectedRun?.output_tail?.length ? (
        <div className="card" style={{ marginTop: 14 }}>
          <h3>{props.copy.outputTail}</h3>
          <div className="code" style={{ minHeight: 180 }}>
            {(props.selectedRun.output_tail || []).join("\n")}
          </div>
        </div>
      ) : null}
    </>
  );
}
