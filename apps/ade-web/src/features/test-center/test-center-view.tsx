import type {
  CreateTestRunPayload,
  TestArtifact,
  TestCenterOptions,
  TestRunRecord,
} from "./api";
import { BehaviorEvaluationLauncher } from "./behavior-evaluation-launcher";
import { CurrentStackSmokeLauncher } from "./current-stack-smoke-launcher";
import { NativeRuntimeQualificationLauncher } from "./native-runtime-qualification-launcher";
import { RunArtifactViewer } from "./run-artifact-viewer";
import type { TestCenterCopy } from "./test-center-copy";

export type TestCenterArea = "behavior" | "native" | "smoke";

type AreaDefinition = {
  id: TestCenterArea;
  runType: CreateTestRunPayload["run_type"];
  tabLabel: keyof TestCenterCopy;
  title: keyof TestCenterCopy;
  intro: keyof TestCenterCopy;
};

const AREAS: readonly AreaDefinition[] = [
  {
    id: "behavior",
    runType: "chat_memory_eval",
    tabLabel: "behaviorTab",
    title: "behaviorTitle",
    intro: "behaviorIntro",
  },
  {
    id: "native",
    runType: "agent_runtime_acceptance",
    tabLabel: "nativeTab",
    title: "nativeTitle",
    intro: "nativeIntro",
  },
  {
    id: "smoke",
    runType: "ade_api_e2e_check",
    tabLabel: "smokeTab",
    title: "smokeTitle",
    intro: "smokeIntro",
  },
];

type Props = {
  activeArea: TestCenterArea;
  artifactContent: string;
  artifacts: TestArtifact[];
  busy: boolean;
  copy: TestCenterCopy;
  error: string;
  onCancelSelectedRun: () => void;
  onCreateRun: (payload: CreateTestRunPayload) => void;
  onReadArtifact: (artifactId: string) => void;
  onRefreshArtifacts: () => void;
  onRefreshRuns: () => void;
  onRefreshSelectedRun: () => void;
  onSelectArea: (area: TestCenterArea) => void;
  onSelectRun: (runId: string) => void;
  options: TestCenterOptions | null;
  optionsLoading: boolean;
  runs: TestRunRecord[];
  selectedArtifactId: string;
  selectedRun: TestRunRecord | null;
  selectedRunId: string;
  selectedRunSummary: TestRunRecord | null;
  status: string;
};

export function TestCenterView(props: Props) {
  const active = AREAS.find((area) => area.id === props.activeArea) || AREAS[0];
  const areaRuns = props.runs.filter((run) => run.run_type === active.runType);

  return (
    <section>
      <div className="kicker">{props.copy.kicker}</div>
      <h1 className="section-title">{props.copy.title}</h1>
      <p className="muted" style={{ maxWidth: 820 }}>{props.copy.intro}</p>

      <div className="toolbar" role="tablist" aria-label={props.copy.title} style={{ marginTop: 18 }}>
        {AREAS.map((area) => (
          <button
            aria-controls={`${area.id}-panel`}
            aria-selected={area.id === active.id}
            className={area.id === active.id ? "button" : "button muted"}
            id={`${area.id}-tab`}
            key={area.id}
            onClick={() => props.onSelectArea(area.id)}
            role="tab"
          >
            {props.copy[area.tabLabel]}
          </button>
        ))}
      </div>

      <section aria-labelledby={`${active.id}-tab`} id={`${active.id}-panel`} role="tabpanel" style={{ marginTop: 18 }}>
        <div className="test-center-section-heading">
          <h2>{props.copy[active.title]}</h2>
          <p className="muted">{props.copy[active.intro]}</p>
        </div>

        {props.optionsLoading || !props.options ? (
          <div className="card"><p className="muted">{props.copy.loadingOptions}</p></div>
        ) : null}
        {props.options && active.id === "behavior" ? (
          <BehaviorEvaluationLauncher
            busy={props.busy}
            catalog={props.options.catalog}
            copy={props.copy}
            onCreateRun={props.onCreateRun}
            options={props.options.chat_memory_eval}
          />
        ) : null}
        {props.options && active.id === "native" ? (
          <NativeRuntimeQualificationLauncher
            busy={props.busy}
            catalog={props.options.catalog}
            copy={props.copy}
            onCreateRun={props.onCreateRun}
            options={props.options.agent_runtime_acceptance}
          />
        ) : null}
        {props.options && active.id === "smoke" ? (
          <CurrentStackSmokeLauncher
            busy={props.busy}
            copy={props.copy}
            onCreateRun={props.onCreateRun}
          />
        ) : null}

        <RunArtifactViewer
          artifactContent={props.artifactContent}
          artifacts={props.artifacts}
          busy={props.busy}
          copy={props.copy}
          onCancelSelectedRun={props.onCancelSelectedRun}
          onReadArtifact={props.onReadArtifact}
          onRefreshArtifacts={props.onRefreshArtifacts}
          onRefreshSelectedRun={props.onRefreshSelectedRun}
          onSelectRun={props.onSelectRun}
          runs={areaRuns}
          selectedArtifactId={props.selectedArtifactId}
          selectedRun={props.selectedRun}
          selectedRunId={props.selectedRunId}
          selectedRunSummary={props.selectedRunSummary}
        />
      </section>

      <div className="toolbar" style={{ marginTop: 14 }}>
        <button className="button muted" disabled={props.busy} onClick={props.onRefreshRuns}>
          {props.copy.refreshRuns}
        </button>
      </div>

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
