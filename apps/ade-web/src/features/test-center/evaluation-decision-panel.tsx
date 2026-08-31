"use client";

import { useEffect, useState } from "react";

import type {
  EvaluationComparison,
  EvaluationDecisionOutcome,
  EvaluationDetail,
  EvaluationListItem,
  EvaluationTemplateSnapshot,
} from "./api";
import type { TestCenterCopy } from "./test-center-copy";

type Props = {
  copy: TestCenterCopy;
  busy: boolean;
  items: EvaluationListItem[];
  candidate: EvaluationDetail | null;
  baselineRunId: string;
  comparison: EvaluationComparison | null;
  onSelectBaseline: (runId: string) => void;
  onRecordDecision: (outcome: EvaluationDecisionOutcome, note: string) => void;
};

export function isPromotableEvaluation(item: EvaluationListItem | null): boolean {
  const metrics = item?.metrics;
  return Boolean(
    item?.ready
      && item.provenance
      && item.evidence_sha256
      && metrics
      && metrics.rounds_total > 0
      && metrics.rounds_passed === metrics.rounds_total
      && metrics.rounds_failed === 0
      && metrics.errors === 0,
  );
}

export function decisionLabel(
  outcome: EvaluationDecisionOutcome,
  copy: TestCenterCopy,
): string {
  if (outcome === "promote") {
    return copy.decisionPromote;
  }
  if (outcome === "reject") {
    return copy.decisionReject;
  }
  return copy.decisionKeep;
}

function shortHash(value: string | null | undefined): string {
  return value ? `${value.slice(0, 10)}...${value.slice(-6)}` : "-";
}

function humanize(value: string): string {
  return value
    .replaceAll(".", " / ")
    .replaceAll("_", " ")
    .replace(/^./, (first) => first.toUpperCase());
}

function compactValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "string") {
    return value.length > 80 ? `${value.slice(0, 77)}...` : value;
  }
  return JSON.stringify(value);
}

function exactValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function formatDelta(value: number): string {
  const rounded = Math.round(value * 1000) / 1000;
  return `${rounded > 0 ? "+" : ""}${rounded}`;
}

function SnapshotDiff({
  label,
  change,
  copy,
}: {
  label: string;
  change: EvaluationComparison["configuration_changes"][string] | undefined;
  copy: TestCenterCopy;
}) {
  if (!change?.changed) {
    return null;
  }
  return (
    <details className="card" style={{ padding: 12, boxShadow: "none" }}>
      <summary><strong>{label}</strong></summary>
      <div className="card-grid" style={{ marginTop: 10 }}>
        <div>
          <div className="muted" style={{ fontSize: 12 }}>{copy.baselineValue}</div>
          <pre className="code" style={{ marginTop: 4, maxHeight: 220, overflow: "auto", whiteSpace: "pre-wrap" }}>
            {exactValue(change.baseline)}
          </pre>
        </div>
        <div>
          <div className="muted" style={{ fontSize: 12 }}>{copy.candidateValue}</div>
          <pre className="code" style={{ marginTop: 4, maxHeight: 220, overflow: "auto", whiteSpace: "pre-wrap" }}>
            {exactValue(change.candidate)}
          </pre>
        </div>
      </div>
    </details>
  );
}

function CapturedSnapshot({
  label,
  snapshot,
}: {
  label: string;
  snapshot: EvaluationTemplateSnapshot;
}) {
  return (
    <details className="card" style={{ padding: 12, boxShadow: "none" }}>
      <summary>
        <strong>{label}</strong>
        <span className="muted" style={{ marginLeft: 8, fontSize: 12 }}>
          {snapshot.key} / {shortHash(snapshot.content_sha256)}
        </span>
      </summary>
      <pre className="code" style={{ marginTop: 10, maxHeight: 360, overflow: "auto", whiteSpace: "pre-wrap" }}>
        {snapshot.content}
      </pre>
    </details>
  );
}

export function EvaluationDecisionPanel(props: Props) {
  const [note, setNote] = useState("");
  const decision = props.candidate?.decision;
  const provenance = props.candidate?.provenance;
  const provenanceDetail = props.candidate?.provenance_detail;
  const baselineOptions = props.items.filter(
    (item) => item.ready && item.provenance && item.run_id !== props.candidate?.run_id,
  );

  useEffect(() => {
    setNote(decision?.note || "");
  }, [decision?.decision_id, decision?.note, props.candidate?.run_id]);

  if (!props.candidate) {
    return null;
  }

  const changedEntries = Object.entries(
    props.comparison?.configuration_changes || {},
  ).filter(([key, value]) => value.changed && !["prompt_content", "persona_content", "model_deployment"].includes(key));

  return (
    <div className="card evaluation-decision-panel" style={{ marginTop: 14 }}>
      <div className="toolbar" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h3>{props.copy.experimentDecisionTitle}</h3>
          <p className="muted">{props.copy.experimentDecisionIntro}</p>
        </div>
        {provenance ? (
          <span style={{ border: "1px solid #86efac", borderRadius: 999, color: "#166534", padding: "5px 9px", fontSize: 12 }}>
            {props.copy.verifiedProvenance}
          </span>
        ) : null}
      </div>

      {!provenance ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#fbbf24", boxShadow: "none" }}>
          <p className="muted">{props.copy.legacyProvenanceMissing}</p>
        </div>
      ) : (
        <>
          <div className="card-grid" style={{ marginTop: 12 }}>
            <div className="card" style={{ padding: 12, boxShadow: "none" }}>
              <strong>{props.copy.candidateEvaluation}</strong>
              <p className="muted" style={{ marginTop: 6 }}>{props.candidate.run_id}</p>
              <div className="muted" style={{ display: "grid", gap: 3, fontSize: 12 }}>
                <span>{props.copy.evaluationIdentity}: {shortHash(provenance.configuration_sha256)}</span>
                <span>{props.copy.evidenceIdentity}: {shortHash(props.candidate.evidence_sha256)}</span>
                <span>{props.copy.modelIdentity}: {shortHash(provenance.model_identity_sha256)}</span>
                <span>{props.copy.promptIdentity}: {shortHash(provenance.prompt_content_sha256)}</span>
                <span>{props.copy.personaIdentity}: {shortHash(provenance.persona_content_sha256)}</span>
              </div>
            </div>
            <div className="card" style={{ padding: 12, boxShadow: "none" }}>
              <label className="field">
                <span>{props.copy.baselineEvaluation}</span>
                <select
                  className="input"
                  value={props.baselineRunId === props.candidate.run_id ? "" : props.baselineRunId}
                  onChange={(event) => props.onSelectBaseline(event.target.value)}
                >
                  <option value="">{props.copy.noComparisonBaseline}</option>
                  {baselineOptions.map((item) => (
                    <option key={item.run_id} value={item.run_id}>
                      {item.preferred_baseline ? `${props.copy.preferredBaseline}: ` : ""}
                      {item.run_id}
                    </option>
                  ))}
                </select>
              </label>
              {props.comparison ? (
                <p className="muted" style={{ marginTop: 8 }}>
                  {props.comparison.same_configuration
                    ? props.copy.sameConfiguration
                    : props.copy.differentConfiguration}
                </p>
              ) : null}
            </div>
          </div>

          {provenanceDetail ? (
            <div className="card-grid" style={{ marginTop: 12 }}>
              <CapturedSnapshot label={props.copy.capturedPromptSnapshot} snapshot={provenanceDetail.prompt} />
              <CapturedSnapshot label={props.copy.capturedPersonaSnapshot} snapshot={provenanceDetail.persona} />
            </div>
          ) : null}

          {props.comparison ? (
            <div className="card-grid" style={{ marginTop: 12 }}>
              <div className="card" style={{ padding: 12, boxShadow: "none" }}>
                <h4>{props.copy.configurationChanges}</h4>
                {changedEntries.length ? (
                  <div className="table-wrap" style={{ marginTop: 8 }}>
                    <table className="table">
                      <thead><tr><th>{props.copy.action}</th><th>{props.copy.baselineValue}</th><th>{props.copy.candidateValue}</th></tr></thead>
                      <tbody>
                        {changedEntries.map(([key, value]) => (
                          <tr key={key}>
                            <td>{humanize(key)}</td>
                            <td>{compactValue(value.baseline)}</td>
                            <td>{compactValue(value.candidate)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : <p className="muted">{props.copy.noConfigurationChanges}</p>}
              </div>
              <div className="card" style={{ padding: 12, boxShadow: "none" }}>
                <h4>{props.copy.metricChanges}</h4>
                <div className="muted" style={{ display: "grid", gap: 4, marginTop: 8 }}>
                  {Object.entries(props.comparison.metric_deltas).map(([key, value]) => (
                    <span key={key}>{humanize(key)}: <strong>{formatDelta(value)}</strong></span>
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          {props.comparison ? (
            <div className="card-grid" style={{ marginTop: 12 }}>
              <SnapshotDiff label={props.copy.exactPromptDiff} change={props.comparison.configuration_changes.prompt_content} copy={props.copy} />
              <SnapshotDiff label={props.copy.exactPersonaDiff} change={props.comparison.configuration_changes.persona_content} copy={props.copy} />
            </div>
          ) : null}

          <div className="card" style={{ marginTop: 12, padding: 12, boxShadow: "none" }}>
            <div className="toolbar" style={{ justifyContent: "space-between" }}>
              <strong>{props.copy.currentDecision}</strong>
              <span className="muted">
                {decision ? decisionLabel(decision.outcome, props.copy) : props.copy.noDecision}
              </span>
            </div>
            <label className="field" style={{ marginTop: 10 }}>
              <span>{props.copy.decisionNote}</span>
              <textarea
                className="input"
                rows={3}
                maxLength={2000}
                placeholder={props.copy.decisionNotePlaceholder}
                value={note}
                onChange={(event) => setNote(event.target.value)}
              />
            </label>
            <div className="toolbar" style={{ marginTop: 10 }}>
              <button className="button muted" disabled={props.busy} onClick={() => props.onRecordDecision("keep", note)} title={props.copy.keepDecisionHelp}>
                {props.copy.keepDecision}
              </button>
              <button className="button" disabled={props.busy || !isPromotableEvaluation(props.candidate)} onClick={() => props.onRecordDecision("promote", note)} title={props.copy.promoteDecisionHelp}>
                {props.copy.promoteDecision}
              </button>
              <button className="button muted" disabled={props.busy} onClick={() => props.onRecordDecision("reject", note)} title={props.copy.rejectDecisionHelp}>
                {props.copy.rejectDecision}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
