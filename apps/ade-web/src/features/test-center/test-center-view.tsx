import type {
  ChatMemoryEvaluationConfig,
  EvaluationComparison,
  EvaluationDecisionOutcome,
  EvaluationDetail,
  EvaluationListItem,
  CreateTestRunPayload,
  TestArtifact,
  TestRunRecord,
} from "./api";
import { ChatMemoryEvaluationView } from "./chat-memory-evaluation-view";
import type { ChatMemoryEvaluationForm } from "./chat-memory-evaluation-helpers";
import { RunArtifactViewer } from "./run-artifact-viewer";
import {
  BEHAVIOR_EVALUATION_RUN_TYPES,
  OPERATIONAL_RUN_TYPES,
  type TestCenterCopy,
} from "./test-center-copy";
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
  evaluationBaselineRunId: string;
  evaluationComparison: EvaluationComparison | null;
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
  onSelectEvaluationBaseline: (runId: string) => void;
  onRecordEvaluationDecision: (
    outcome: EvaluationDecisionOutcome,
    note: string,
  ) => void;
  onRefreshEvaluations: () => void;
  onRerunEvaluationSetup: (config: ChatMemoryEvaluationConfig) => void;
};

export function TestCenterView(props: Props) {
  const operationalRuns = props.runs.filter((run) => run.run_type !== "chat_memory_eval");
  const hasSelectedOperationalRun = operationalRuns.some((run) => run.run_id === props.selectedRunId);
  const selectedOperationalRunId = hasSelectedOperationalRun ? props.selectedRunId : "";

  return (
    <section>
      <div className="kicker">{props.copy.kicker}</div>
      <h1 className="section-title">{props.copy.title}</h1>
      <p className="muted" style={{ maxWidth: 820 }}>{props.copy.intro}</p>

      <section className="test-center-section" aria-labelledby="behavior-evaluation-title">
        <div className="test-center-section-heading">
          <div className="kicker">{props.copy.behaviorKicker}</div>
          <h2 id="behavior-evaluation-title">{props.copy.behaviorTitle}</h2>
          <p className="muted">{props.copy.behaviorIntro}</p>
        </div>

        <TestRunLauncher
          copy={props.copy}
          title={props.copy.behaviorLaunchTitle}
          intro={props.copy.behaviorLaunchIntro}
          availableRunTypes={BEHAVIOR_EVALUATION_RUN_TYPES}
          initialRunType="chat_memory_eval"
          hydrateLaunchState
          busy={props.busy}
          loading={props.loading}
          preset={props.launcherPreset}
          onCreateRun={props.onCreateRun}
          onRefreshRuns={props.onRefreshRuns}
          onError={props.onLauncherError}
        />

        <ChatMemoryEvaluationView
          copy={props.copy}
          busy={props.busy}
          items={props.evaluationItems}
          selectedEvaluationId={props.selectedEvaluationId}
          selectedEvaluationSummary={props.selectedEvaluationSummary}
          selectedEvaluation={props.selectedEvaluation}
          baselineRunId={props.evaluationBaselineRunId}
          comparison={props.evaluationComparison}
          onSelectEvaluation={props.onSelectEvaluation}
          onSelectBaseline={props.onSelectEvaluationBaseline}
          onRecordDecision={props.onRecordEvaluationDecision}
          onRefreshEvaluations={props.onRefreshEvaluations}
          onRerunSetup={props.onRerunEvaluationSetup}
        />
      </section>

      <details className="card test-center-operations">
        <summary><strong>{props.copy.operationsTitle}</strong></summary>
        <p className="muted test-center-operations-intro">{props.copy.operationsIntro}</p>
        <TestRunLauncher
          copy={props.copy}
          title={props.copy.operationsLaunchTitle}
          intro={props.copy.operationsLaunchIntro}
          availableRunTypes={OPERATIONAL_RUN_TYPES}
          initialRunType="ade_api_e2e_check"
          busy={props.busy}
          loading={props.loading}
          preset={null}
          onCreateRun={props.onCreateRun}
          onRefreshRuns={props.onRefreshRuns}
          onError={props.onLauncherError}
        />
        <RunArtifactViewer
          copy={props.copy}
          busy={props.busy}
          runs={operationalRuns}
          selectedRunId={selectedOperationalRunId}
          selectedRunSummary={hasSelectedOperationalRun ? props.selectedRunSummary : null}
          selectedRun={hasSelectedOperationalRun ? props.selectedRun : null}
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
