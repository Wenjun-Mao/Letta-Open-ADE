import type { CreateTestRunPayload, TestArtifact, TestRunRecord } from "./api";
import { RunArtifactViewer } from "./run-artifact-viewer";
import type { TestCenterCopy } from "./test-center-copy";
import { TestRunLauncher } from "./test-run-launcher";

type Props = {
  copy: TestCenterCopy;
  loading: boolean;
  busy: boolean;
  error: string;
  status: string;
  runs: TestRunRecord[];
  selectedRunId: string;
  selectedRunSummary: TestRunRecord | null;
  selectedRun: TestRunRecord | null;
  artifacts: TestArtifact[];
  selectedArtifactId: string;
  artifactContent: string;
  onCreateRun: (payload: CreateTestRunPayload) => Promise<void>;
  onRefreshRuns: () => Promise<void>;
  onLauncherError: (message: string) => void;
  onSelectRun: (runId: string) => void;
  onRefreshSelectedRun: () => void;
  onCancelSelectedRun: () => void;
  onRefreshArtifacts: () => void;
  onReadArtifact: (artifactId: string) => void;
};

export function TestCenterView(props: Props) {
  return (
    <section>
      <div className="kicker">{props.copy.kicker}</div>
      <h1 className="section-title">{props.copy.title}</h1>

      <TestRunLauncher
        copy={props.copy}
        busy={props.busy}
        loading={props.loading}
        onCreateRun={props.onCreateRun}
        onRefreshRuns={props.onRefreshRuns}
        onError={props.onLauncherError}
      />

      <RunArtifactViewer
        copy={props.copy}
        busy={props.busy}
        runs={props.runs}
        selectedRunId={props.selectedRunId}
        selectedRunSummary={props.selectedRunSummary}
        selectedRun={props.selectedRun}
        artifacts={props.artifacts}
        selectedArtifactId={props.selectedArtifactId}
        artifactContent={props.artifactContent}
        onSelectRun={props.onSelectRun}
        onRefreshSelectedRun={props.onRefreshSelectedRun}
        onCancelSelectedRun={props.onCancelSelectedRun}
        onRefreshArtifacts={props.onRefreshArtifacts}
        onReadArtifact={props.onReadArtifact}
      />

      {props.status ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#bbf7d0" }}>
          <h3>{props.copy.statusTitle}</h3>
          <p className="muted">{props.status}</p>
        </div>
      ) : null}

      {props.error ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#fecaca" }}>
          <h3>{props.copy.errorTitle}</h3>
          <p className="muted">{props.error}</p>
        </div>
      ) : null}
    </section>
  );
}
