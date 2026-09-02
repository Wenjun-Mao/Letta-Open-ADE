import type {
  AgentRuntimeParityDetail,
  AgentRuntimeParityListItem,
  TestArtifact,
} from "./api";
import type { TestCenterCopy } from "./test-center-copy";

type ArtifactKind = "summary" | "comparison" | "provenance" | "spec" | "turns";

function artifactKind(artifact: TestArtifact): ArtifactKind | null {
  const reference = `${artifact.artifact_id} ${artifact.path}`.toLowerCase();
  if (reference.includes("summary")) return "summary";
  if (reference.includes("comparison")) return "comparison";
  if (reference.includes("provenance")) return "provenance";
  if (reference.includes("parity-spec") || reference.includes("parity_spec")) return "spec";
  if (reference.includes("normalized-turns") || reference.includes("normalized_turns")) return "turns";
  return null;
}

function shortHash(value: string): string {
  return value.length > 18 ? `${value.slice(0, 10)}...${value.slice(-6)}` : value || "-";
}

function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function resultLabel(value: boolean | null, passed: string, failed: string, pending: string): string {
  if (value === true) return passed;
  if (value === false) return failed;
  return pending;
}

export function parityRoundProgress(result: AgentRuntimeParityListItem): string {
  if (result.rounds_requested === null) return "-";
  return `${result.rounds_passed ?? 0}/${result.rounds_completed ?? 0}/${result.rounds_requested}`;
}

function ArtifactButton({
  artifact,
  label,
  selected,
  onOpen,
  unavailableLabel,
}: {
  artifact: TestArtifact | undefined;
  label: string;
  selected: boolean;
  onOpen: (artifactId: string) => void;
  unavailableLabel: string;
}) {
  if (!artifact?.exists) return <span className="muted">{label}: {unavailableLabel}</span>;
  return (
    <button className="button muted" onClick={() => onOpen(artifact.artifact_id)} disabled={selected}>
      {label}
    </button>
  );
}

function EvidenceOverview({ result, copy }: { result: AgentRuntimeParityListItem; copy: TestCenterCopy }) {
  return (
    <div className="card-grid" style={{ marginTop: 12 }}>
      <div className="card" style={{ padding: 12, boxShadow: "none" }}>
        <div className="muted" style={{ fontSize: 12 }}>{copy.paritySummary}</div>
        <strong style={{ color: result.passed === false ? "#b91c1c" : result.passed === true ? "#166534" : undefined }}>
          {resultLabel(result.passed, copy.parityPassed, copy.parityFailed, copy.pending)}
        </strong>
        <p className="muted" style={{ marginBottom: 0 }}>{result.run_id}</p>
      </div>
      <div className="card" style={{ padding: 12, boxShadow: "none" }}>
        <div className="muted" style={{ fontSize: 12 }}>{copy.parityRoundsCompleted}</div>
        <strong>{parityRoundProgress(result)}</strong>
        <p className="muted" style={{ marginBottom: 0 }}>{copy.parityControlsFixed}</p>
      </div>
      <div className="card" style={{ padding: 12, boxShadow: "none" }}>
        <div className="muted" style={{ fontSize: 12 }}>{copy.parityControlEvidence}</div>
        <strong>{resultLabel(result.inputs_comparable, copy.parityComparable, copy.parityNotComparable, copy.pending)}</strong>
        <br />
        <strong>{resultLabel(result.cleanup_complete, copy.parityCleanupComplete, copy.parityCleanupIncomplete, copy.pending)}</strong>
      </div>
    </div>
  );
}

function VerifiedEvidence({ detail, copy }: { detail: AgentRuntimeParityDetail; copy: TestCenterCopy }) {
  const artifactDigests = Object.entries(detail.artifact_digests || {});
  return (
    <>
      <div style={{ marginTop: 16 }}>
        <h4>{copy.parityRoundResults}</h4>
        <div className="toolbar" style={{ gap: 8 }}>
          {detail.rounds.map((round) => (
            <span key={round.round} className="muted">
              {copy.round} {round.round}: {resultLabel(round.passed, copy.passed, copy.failed, copy.pending)}
            </span>
          ))}
        </div>
      </div>
      <div className="card-grid" style={{ marginTop: 12 }}>
        <div className="card" style={{ padding: 12, boxShadow: "none" }}>
          <h4>{copy.parityVerificationChecks}</h4>
          <div className="muted" style={{ display: "grid", gap: 4 }}>
            {Object.entries(detail.checks).map(([check, passed]) => (
              <span key={check}>{humanize(check)}: <strong>{passed ? copy.passed : copy.failed}</strong></span>
            ))}
          </div>
        </div>
        <div className="card" style={{ padding: 12, boxShadow: "none" }}>
          <h4>{copy.parityArtifactEvidence}</h4>
          <div className="muted" style={{ display: "grid", gap: 4 }}>
            {artifactDigests.map(([name, hash]) => <span key={name}>{humanize(name)}: {shortHash(hash)}</span>)}
          </div>
        </div>
        <div className="card" style={{ padding: 12, boxShadow: "none" }}>
          <h4>{copy.parityProvenance}</h4>
          <pre className="code" style={{ margin: 0, maxHeight: 180, overflow: "auto", whiteSpace: "pre-wrap" }}>
            {JSON.stringify(detail.provenance, null, 2)}
          </pre>
        </div>
      </div>
      <div style={{ marginTop: 16 }}>
        <h4>{copy.parityTurnEvidence}</h4>
        <p className="muted">{copy.parityTurnEvidenceIntro}</p>
        <div style={{ display: "grid", gap: 8 }}>
          {detail.turns.map((turn) => (
            <details className="card" style={{ padding: 12, boxShadow: "none" }} key={`${turn.engine}-${turn.round}-${turn.turn_index}`}>
              <summary>
                {turn.engine} · {copy.round} {turn.round} · #{turn.turn_index} · {humanize(turn.terminal_status)} · {turn.elapsed_seconds.toFixed(2)}s
              </summary>
              <p><strong>User:</strong> {turn.user_content}</p>
              <p><strong>Assistant:</strong> {turn.assistant_replies.join("\n") || copy.parityNoAssistantReply}</p>
              <p className="muted">
                Attempts: {turn.attempt_count ?? "n/a"} · Tools: {turn.tool_names.join(", ") || "none"} · Events: {turn.event_types.join(", ") || "none"}
              </p>
            </details>
          ))}
        </div>
      </div>
    </>
  );
}

type Props = {
  copy: TestCenterCopy;
  busy: boolean;
  items: AgentRuntimeParityListItem[];
  selectedId: string;
  selectedSummary: AgentRuntimeParityListItem | null;
  selected: AgentRuntimeParityDetail | null;
  artifacts: TestArtifact[];
  selectedArtifactId: string;
  artifactContent: string;
  onSelect: (runId: string) => void;
  onRefresh: () => void;
  onReadArtifact: (artifactId: string) => void;
};

export function AgentRuntimeParityResultView(props: Props) {
  const result = props.selected || props.selectedSummary;
  const artifactsByKind = Object.fromEntries(
    props.artifacts.flatMap((artifact) => {
      const kind = artifactKind(artifact);
      return kind ? [[kind, artifact]] : [];
    }),
  ) as Partial<Record<ArtifactKind, TestArtifact>>;

  return (
    <div className="card" style={{ marginTop: 14 }}>
      <div className="toolbar" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <div><h3>{props.copy.parityRunsTitle}</h3><p className="muted">{props.copy.parityRunsIntro}</p></div>
        <button className="button muted" onClick={props.onRefresh} disabled={!props.selectedId || props.busy}>
          {props.copy.refreshSelectedRun}
        </button>
      </div>
      <label className="field">
        <span>{props.copy.selectRun}</span>
        <select className="input" value={props.selectedId} onChange={(event) => props.onSelect(event.target.value)} disabled={!props.items.length}>
          <option value="">{props.copy.selectRunPlaceholder}</option>
          {props.items.map((item) => <option key={item.run_id} value={item.run_id}>{item.run_id} ({item.run_status})</option>)}
        </select>
      </label>
      {!result ? <p className="muted" style={{ marginTop: 12 }}>{props.copy.parityNoSelectedRun}</p> : (
        <>
          <p className="muted" style={{ marginTop: 12 }}>{props.copy.evaluationStatus}: {result.run_status}</p>
          <div className="toolbar" style={{ marginTop: 10 }}>
            <ArtifactButton artifact={artifactsByKind.summary} label={props.copy.parityOpenSummary} selected={props.selectedArtifactId === artifactsByKind.summary?.artifact_id} onOpen={props.onReadArtifact} unavailableLabel={props.copy.parityArtifactUnavailable} />
            <ArtifactButton artifact={artifactsByKind.comparison} label={props.copy.parityOpenComparison} selected={props.selectedArtifactId === artifactsByKind.comparison?.artifact_id} onOpen={props.onReadArtifact} unavailableLabel={props.copy.parityArtifactUnavailable} />
            <ArtifactButton artifact={artifactsByKind.provenance} label={props.copy.parityOpenProvenance} selected={props.selectedArtifactId === artifactsByKind.provenance?.artifact_id} onOpen={props.onReadArtifact} unavailableLabel={props.copy.parityArtifactUnavailable} />
            <ArtifactButton artifact={artifactsByKind.spec} label={props.copy.parityOpenSpec} selected={props.selectedArtifactId === artifactsByKind.spec?.artifact_id} onOpen={props.onReadArtifact} unavailableLabel={props.copy.parityArtifactUnavailable} />
            <ArtifactButton artifact={artifactsByKind.turns} label={props.copy.parityOpenTurns} selected={props.selectedArtifactId === artifactsByKind.turns?.artifact_id} onOpen={props.onReadArtifact} unavailableLabel={props.copy.parityArtifactUnavailable} />
          </div>
          {result.ready ? <EvidenceOverview result={result} copy={props.copy} /> : <p className="muted" style={{ marginTop: 14 }}>{props.copy.parityPending}</p>}
          {props.selected ? <VerifiedEvidence detail={props.selected} copy={props.copy} /> : null}
          {props.selectedArtifactId ? (
            <details style={{ marginTop: 14 }}>
              <summary>{props.copy.paritySourceArtifact}: {props.selectedArtifactId}</summary>
              <pre className="code" style={{ maxHeight: 360, overflow: "auto", whiteSpace: "pre-wrap" }}>{props.artifactContent}</pre>
            </details>
          ) : null}
        </>
      )}
    </div>
  );
}
