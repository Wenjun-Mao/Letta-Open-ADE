import type {
  ChatMemoryEvaluationConfig,
  EvaluationDetail,
  EvaluationListItem,
  CreateTestRunPayload,
  TestArtifact,
  TestRunRecord,
} from "./api";
import { ChatMemoryEvaluationView } from "./chat-memory-evaluation-view";
import type { ChatMemoryEvaluationForm } from "./chat-memory-evaluation-helpers";
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
  evaluationItems: EvaluationListItem[];
  selectedEvaluationId: string;
  selectedEvaluationSummary: EvaluationListItem | null;
  selectedEvaluation: EvaluationDetail | null;
  launcherPreset: ChatMemoryEvaluationForm | null;
  onCreateRun: (payload: CreateTestRunPayload) => Promise<void>;
  onRefreshRuns: () => Promise<void>;
  onLauncherError: (message: string) => void;
  onSelectRun: (runId: string) => void;
  onRefreshSelectedRun: () => void;
  onCancelSelectedRun: () => void;
  onRefreshArtifacts: () => void;
  onReadArtifact: (artifactId: string) => void;
  onSelectEvaluation: (runId: string) => void;
  onRefreshEvaluations: () => void;
  onRerunEvaluationSetup: (config: ChatMemoryEvaluationConfig) => void;
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
        preset={props.launcherPreset}
        onCreateRun={props.onCreateRun}
        onRefreshRuns={props.onRefreshRuns}
        onError={props.onLauncherError}
      />

      <ChatMemoryEvaluationView
        copy={props.copy}
        items={props.evaluationItems}
        selectedEvaluationId={props.selectedEvaluationId}
        selectedEvaluationSummary={props.selectedEvaluationSummary}
        selectedEvaluation={props.selectedEvaluation}
        onSelectEvaluation={props.onSelectEvaluation}
        onRefreshEvaluations={props.onRefreshEvaluations}
        onRerunSetup={props.onRerunEvaluationSetup}
      />

      <details className="card" style={{ marginTop: 14 }}>
        <summary><strong>{props.copy.rawDiagnostics}</strong></summary>
        <p className="muted" style={{ marginTop: 8 }}>{props.copy.rawDiagnosticsIntro}</p>
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
      </details>

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
