import type {
  ChatMemoryEvaluationConfig,
  EvaluationDetail,
  EvaluationListItem,
  EvaluationMemoryBlock,
  EvaluationRound,
  EvaluationToolCall,
  EvaluationTurn,
} from "./api";
import {
  buildPromptCenterEvaluationHref,
  diffMemoryLines,
  formatElapsedSeconds,
  formatPassRate,
  metricFraction,
  summarizeDeterministicFailures,
} from "./chat-memory-evaluation-helpers";
import type { TestCenterCopy } from "./test-center-copy";

type Props = {
  copy: TestCenterCopy;
  items: EvaluationListItem[];
  selectedEvaluationId: string;
  selectedEvaluationSummary: EvaluationListItem | null;
  selectedEvaluation: EvaluationDetail | null;
  onSelectEvaluation: (runId: string) => void;
  onRefreshEvaluations: () => void;
  onRerunSetup: (config: ChatMemoryEvaluationConfig) => void;
};

function formatDateTime(value: string): string {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function toolCallName(call: EvaluationToolCall): string {
  const name = call.name || call.tool_name || call.function_name || call.id;
  return typeof name === "string" && name.trim() ? name : "tool call";
}

function prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function Signal({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ minWidth: 118 }}>
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
      <strong style={{ fontSize: 16 }}>{value}</strong>
    </div>
  );
}

function EvaluationSetup({ config, copy }: { config: ChatMemoryEvaluationConfig; copy: TestCenterCopy }) {
  return (
    <div className="muted" style={{ display: "grid", gap: 4, fontSize: 12 }}>
      <span>{copy.model}: {config.model}</span>
      <span>{copy.prompt}: {config.prompt_key}</span>
      <span>{copy.persona}: {config.persona_key}</span>
      <span>{copy.embedding}: {config.embedding || copy.serverDefault}</span>
      <span>{copy.fixture}: {config.fixture_key}</span>
    </div>
  );
}

function EvaluationComparison(props: Props) {
  return (
    <div className="card" style={{ marginTop: 14 }}>
      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <div>
          <h3>{props.copy.evaluationRunsTitle}</h3>
          <p className="muted">{props.copy.evaluationRunsIntro}</p>
        </div>
        <button className="button muted" onClick={props.onRefreshEvaluations}>{props.copy.refreshEvaluations}</button>
      </div>
      {props.items.length === 0 ? (
        <p className="muted" style={{ marginTop: 12 }}>{props.copy.noEvaluations}</p>
      ) : (
        <div className="table-wrap" style={{ marginTop: 12 }}>
          <table className="table">
            <thead>
              <tr>
                <th>{props.copy.evaluationRun}</th>
                <th>{props.copy.evaluationSetup}</th>
                <th>{props.copy.evaluationStatus}</th>
                <th>{props.copy.passRate}</th>
                <th>{props.copy.evaluationSignals}</th>
                <th>{props.copy.action}</th>
              </tr>
            </thead>
            <tbody>
              {props.items.map((item) => {
                const metrics = item.metrics;
                const selected = item.run_id === props.selectedEvaluationId;
                return (
                  <tr key={item.run_id} style={selected ? { background: "#eff6ff" } : undefined}>
                    <td>
                      <strong>{item.run_id}</strong>
                      <div className="muted" style={{ fontSize: 12 }}>{formatDateTime(item.created_at)}</div>
                    </td>
                    <td><EvaluationSetup config={item.config} copy={props.copy} /></td>
                    <td>
                      <strong>{item.run_status}</strong>
                      <div className="muted" style={{ fontSize: 12 }}>
                        {item.ready ? props.copy.ready : props.copy.evaluationPreparing}
                      </div>
                    </td>
                    <td>{metrics ? formatPassRate(metrics.pass_rate) : props.copy.pending}</td>
                    <td>
                      {metrics ? (
                        <div className="muted" style={{ display: "grid", gap: 2, fontSize: 12 }}>
                          <span>{props.copy.facts}: {metricFraction(metrics.expected_facts_passed_rounds, metrics.rounds_total)}</span>
                          <span>{props.copy.memory}: {metricFraction(metrics.memory_changed_rounds, metrics.rounds_total)}</span>
                          <span>{props.copy.disclosure}: {metrics.forbidden_hit_count}</span>
                          <span>{props.copy.tools}: {metricFraction(metrics.memory_tool_call_count, metrics.total_tool_call_count)}</span>
                          <span>{props.copy.cleanup}: {metricFraction(metrics.cleanup_passed_rounds, metrics.rounds_total)}</span>
                          <span>{props.copy.latency}: {formatElapsedSeconds(metrics.average_elapsed_seconds)}</span>
                        </div>
                      ) : props.copy.pending}
                    </td>
                    <td>
                      <button className="button muted" onClick={() => props.onSelectEvaluation(item.run_id)}>
                        {selected ? props.copy.selected : props.copy.inspectEvaluation}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function MemoryLayers({ blocks, copy }: { blocks: EvaluationMemoryBlock[]; copy: TestCenterCopy }) {
  if (blocks.length === 0) {
    return <p className="muted">{copy.noMemoryLayers}</p>;
  }
  return (
    <div className="card-grid" style={{ marginTop: 8 }}>
      {blocks.map((block) => (
        <div className="card" key={block.label} style={{ padding: 12, boxShadow: "none" }}>
          <div className="toolbar" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
            <strong>{block.label}</strong>
            {typeof block.limit === "number" ? <span className="muted" style={{ fontSize: 12 }}>{copy.memoryLimit}: {block.limit}</span> : null}
          </div>
          {block.description ? <p className="muted" style={{ marginTop: 6 }}>{block.description}</p> : null}
          <div className="code" style={{ marginTop: 8, minHeight: 64 }}>{block.value || copy.emptyMemory}</div>
        </div>
      ))}
    </div>
  );
}

function MemoryDelta({ before, after, copy }: { before: string; after: string; copy: TestCenterCopy }) {
  const delta = diffMemoryLines(before, after);
  if (delta.added.length === 0 && delta.removed.length === 0) {
    return <p className="muted" style={{ marginTop: 4 }}>{copy.noMemoryDelta}</p>;
  }
  return (
    <div className="card-grid" style={{ marginTop: 6 }}>
      <div>
        <div className="muted" style={{ fontSize: 12 }}>{copy.removedMemoryLines}</div>
        <div className="code" style={{ marginTop: 4, minHeight: 44 }}>
          {delta.removed.length ? delta.removed.map((line) => `- ${line}`).join("\n") : copy.no}
        </div>
      </div>
      <div>
        <div className="muted" style={{ fontSize: 12 }}>{copy.addedMemoryLines}</div>
        <div className="code" style={{ marginTop: 4, minHeight: 44 }}>
          {delta.added.length ? delta.added.map((line) => `+ ${line}`).join("\n") : copy.no}
        </div>
      </div>
    </div>
  );
}

function ToolCallList({ calls, emptyText }: { calls: EvaluationToolCall[]; emptyText: string }) {
  if (calls.length === 0) {
    return <p className="muted" style={{ marginTop: 4 }}>{emptyText}</p>;
  }
  return (
    <div className="code" style={{ marginTop: 4 }}>
      {calls.map((call) => `${toolCallName(call)}\n${prettyJson(call)}`).join("\n\n")}
    </div>
  );
}

function TurnEvidence({ turn, copy }: { turn: EvaluationTurn; copy: TestCenterCopy }) {
  return (
    <div className="card" style={{ marginTop: 10, padding: 12, borderColor: turn.memory_changed_this_turn ? "#86efac" : undefined }}>
      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <strong>{propsText(copy.turn, turn.turn_index)}</strong>
        <span className="muted" style={{ fontSize: 12 }}>{copy.latency}: {formatElapsedSeconds(turn.elapsed_seconds)}</span>
      </div>
      <div style={{ marginTop: 8 }}>
        <div className="muted" style={{ fontSize: 12 }}>{copy.userInput}</div>
        <div className="code" style={{ marginTop: 4, minHeight: 44 }}>{turn.user_input}</div>
      </div>
      <div style={{ marginTop: 8 }}>
        <div className="muted" style={{ fontSize: 12 }}>{copy.assistantReplies}</div>
        <div className="code" style={{ marginTop: 4, minHeight: 44 }}>
          {turn.assistant_replies.length ? turn.assistant_replies.join("\n\n") : copy.noAssistantReply}
        </div>
      </div>
      <div className="card-grid" style={{ marginTop: 8 }}>
        <div>
          <div className="muted" style={{ fontSize: 12 }}>{copy.humanMemoryBefore}</div>
          <div className="code" style={{ marginTop: 4, minHeight: 56 }}>{turn.human_memory_before_turn || copy.emptyMemory}</div>
        </div>
        <div>
          <div className="muted" style={{ fontSize: 12 }}>{copy.humanMemoryAfter}</div>
          <div className="code" style={{ marginTop: 4, minHeight: 56 }}>{turn.human_memory_after_turn || copy.emptyMemory}</div>
        </div>
      </div>
      <p className="muted" style={{ marginTop: 8 }}>
        {copy.memoryChanged}: <strong>{turn.memory_changed_this_turn ? copy.yes : copy.no}</strong>
      </p>
      <div style={{ marginTop: 8 }}>
        <div className="muted" style={{ fontSize: 12 }}>{copy.memoryDelta}</div>
        <MemoryDelta
          before={turn.human_memory_before_turn}
          after={turn.human_memory_after_turn}
          copy={copy}
        />
      </div>
      <div style={{ marginTop: 8 }}>
        <div className="muted" style={{ fontSize: 12 }}>{copy.toolCalls}</div>
        <ToolCallList calls={turn.tool_calls} emptyText={copy.noToolCalls} />
      </div>
      <div style={{ marginTop: 8 }}>
        <div className="muted" style={{ fontSize: 12 }}>{copy.memoryToolCalls}</div>
        <ToolCallList calls={turn.memory_tool_calls} emptyText={copy.noMemoryToolCalls} />
      </div>
    </div>
  );
}

function propsText(label: string, index: number): string {
  return `${label} ${index}`;
}

function DeterministicFailureReasons({ round, copy }: { round: EvaluationRound; copy: TestCenterCopy }) {
  if (round.passed) {
    return null;
  }
  const failures = summarizeDeterministicFailures(round.deterministic_score);
  const reasons: string[] = [];
  if (failures.forbiddenHits.length) {
    reasons.push(`${copy.forbiddenHitsFailure}: ${failures.forbiddenHits.join(", ")}`);
  }
  if (failures.memoryDidNotChange) {
    reasons.push(copy.memoryUnchangedFailure);
  }
  if (failures.missingExpectedFacts.length) {
    reasons.push(`${copy.missingFactsFailure}: ${failures.missingExpectedFacts.join(", ")}`);
  } else if (failures.expectedFactsFailed) {
    reasons.push(copy.expectedFactsFailure);
  }
  if (reasons.length === 0 && !round.error) {
    reasons.push(copy.deterministicFailureFallback);
  }
  if (reasons.length === 0) {
    return null;
  }
  return (
    <div className="card" style={{ marginTop: 12, padding: 12, borderColor: "#fecaca" }}>
      <strong>{copy.failureReasons}</strong>
      <ul style={{ marginBottom: 0 }}>
        {reasons.map((reason) => <li key={reason}>{reason}</li>)}
      </ul>
    </div>
  );
}

function RoundEvidence({ round, copy, open }: { round: EvaluationRound; copy: TestCenterCopy; open: boolean }) {
  return (
    <details className="card" open={open} style={{ marginTop: 12 }}>
      <summary>
        <strong>{propsText(copy.round, round.round)}</strong> · {round.status} · {round.passed ? copy.passed : copy.failed} · {formatElapsedSeconds(round.elapsed_seconds)}
      </summary>
      <div className="toolbar" style={{ marginTop: 12 }}>
        <Signal label={copy.agentId} value={round.agent_id || "-"} />
        <Signal label={copy.archived} value={round.archived ? copy.yes : copy.no} />
        <Signal label={copy.purged} value={round.purged ? copy.yes : copy.no} />
        <Signal label={copy.memoryChanged} value={round.initial_human_memory !== round.final_human_memory ? copy.yes : copy.no} />
      </div>
      {round.error ? (
        <div className="card" style={{ marginTop: 12, padding: 12, borderColor: "#fecaca" }}>
          <strong>{copy.errorTitle}</strong>
          <div className="code" style={{ marginTop: 6 }}>{round.error}</div>
        </div>
      ) : null}
      <DeterministicFailureReasons round={round} copy={copy} />
      <div style={{ marginTop: 14 }}>
        <h4 style={{ marginBottom: 6 }}>{copy.finalMemoryLayers}</h4>
        <MemoryLayers blocks={round.memory_blocks} copy={copy} />
      </div>
      <div className="card-grid" style={{ marginTop: 14 }}>
        <div>
          <div className="muted" style={{ fontSize: 12 }}>{copy.initialHumanMemory}</div>
          <div className="code" style={{ marginTop: 4, minHeight: 64 }}>{round.initial_human_memory || copy.emptyMemory}</div>
        </div>
        <div>
          <div className="muted" style={{ fontSize: 12 }}>{copy.finalHumanMemory}</div>
          <div className="code" style={{ marginTop: 4, minHeight: 64 }}>{round.final_human_memory || copy.emptyMemory}</div>
        </div>
      </div>
      <details style={{ marginTop: 12 }}>
        <summary>{copy.assessmentDetails}</summary>
        <div className="card-grid" style={{ marginTop: 8 }}>
          <div>
            <div className="muted" style={{ fontSize: 12 }}>{copy.deterministicScore}</div>
            <div className="code" style={{ marginTop: 4 }}>{prettyJson(round.deterministic_score)}</div>
          </div>
          <div>
            <div className="muted" style={{ fontSize: 12 }}>{copy.judge}</div>
            <div className="code" style={{ marginTop: 4 }}>{prettyJson(round.judge || {})}</div>
          </div>
        </div>
      </details>
      <div style={{ marginTop: 14 }}>
        <h4 style={{ marginBottom: 6 }}>{copy.turnEvidence}</h4>
        {round.turns.map((turn) => <TurnEvidence key={turn.turn_index} turn={turn} copy={copy} />)}
      </div>
    </details>
  );
}

function EvaluationScorecard({ props }: { props: Props }) {
  const evaluation = props.selectedEvaluation;
  const summary = props.selectedEvaluationSummary;
  if (!summary) {
    return null;
  }
  if (!evaluation) {
    return (
      <div className="card" style={{ marginTop: 14 }}>
        <h3>{props.copy.evaluationDetailsTitle}</h3>
        <p className="muted">{summary.ready ? props.copy.loadingEvaluation : props.copy.evaluationPreparing}</p>
      </div>
    );
  }

  const metrics = evaluation.metrics;
  const config = evaluation.config;
  return (
    <div className="card" style={{ marginTop: 14 }}>
      <div className="toolbar" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h3>{props.copy.evaluationDetailsTitle}</h3>
          <p className="muted">{evaluation.run_id} · {formatDateTime(evaluation.finished_at || evaluation.created_at)}</p>
        </div>
        <div className="toolbar">
          <button className="button muted" onClick={() => props.onRerunSetup(config)}>{props.copy.rerunSetup}</button>
          <a className="button muted" href={buildPromptCenterEvaluationHref("prompt", config)}>{props.copy.openPrompt}</a>
          <a className="button muted" href={buildPromptCenterEvaluationHref("persona", config)}>{props.copy.openPersona}</a>
        </div>
      </div>
      <div className="card-grid" style={{ marginTop: 12 }}>
        <div className="card" style={{ padding: 12, boxShadow: "none" }}>
          <h3>{props.copy.evaluationSetup}</h3>
          <EvaluationSetup config={config} copy={props.copy} />
          <p className="muted" style={{ marginTop: 8 }}>{props.copy.rounds}: {config.rounds} · {props.copy.timeoutSeconds}: {config.timeout_seconds}s · {props.copy.retryCount}: {config.retry_count}</p>
        </div>
        <div className="card" style={{ padding: 12, boxShadow: "none" }}>
          <h3>{props.copy.scorecard}</h3>
          {metrics ? (
            <div className="toolbar" style={{ gap: 16 }}>
              <Signal label={props.copy.passRate} value={formatPassRate(metrics.pass_rate)} />
              <Signal label={props.copy.passedRounds} value={metricFraction(metrics.rounds_passed, metrics.rounds_total)} />
              <Signal label={props.copy.errors} value={String(metrics.errors)} />
              <Signal label={props.copy.latency} value={formatElapsedSeconds(metrics.average_elapsed_seconds)} />
            </div>
          ) : <p className="muted">{props.copy.pending}</p>}
        </div>
        <div className="card" style={{ padding: 12, boxShadow: "none" }}>
          <h3>{props.copy.behaviorSignals}</h3>
          {metrics ? (
            <div className="toolbar" style={{ gap: 16 }}>
              <Signal label={props.copy.facts} value={metricFraction(metrics.expected_facts_passed_rounds, metrics.rounds_total)} />
              <Signal label={props.copy.memory} value={metricFraction(metrics.memory_changed_rounds, metrics.rounds_total)} />
              <Signal label={props.copy.disclosure} value={String(metrics.forbidden_hit_count)} />
              <Signal label={props.copy.cleanup} value={metricFraction(metrics.cleanup_passed_rounds, metrics.rounds_total)} />
              <Signal label={props.copy.tools} value={metricFraction(metrics.memory_tool_call_count, metrics.total_tool_call_count)} />
            </div>
          ) : <p className="muted">{props.copy.pending}</p>}
        </div>
      </div>
      <div style={{ marginTop: 18 }}>
        <h3>{props.copy.roundEvidence}</h3>
        {evaluation.rounds.length === 0 ? (
          <p className="muted">{props.copy.noRoundEvidence}</p>
        ) : evaluation.rounds.map((round, index) => (
          <RoundEvidence key={round.round} round={round} copy={props.copy} open={index === 0} />
        ))}
      </div>
    </div>
  );
}

export function ChatMemoryEvaluationView(props: Props) {
  return (
    <>
      <EvaluationComparison {...props} />
      <EvaluationScorecard props={props} />
    </>
  );
}
