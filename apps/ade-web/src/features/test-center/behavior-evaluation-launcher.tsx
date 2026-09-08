import { useEffect, useState } from "react";

import type {
  ChatMemoryEvaluationDefaults,
  CreateTestRunPayload,
  TestCenterCatalogOptions,
  TestCenterOptions,
} from "./api";
import type { TestCenterCopy } from "./test-center-copy";

export type BehaviorEvaluationForm = {
  model: string;
  promptKey: string;
  personaKey: string;
  embedding: string;
  fixtureKey: string;
  rounds: string;
  timeoutSeconds: string;
  retryCount: string;
  judgeEnabled: boolean;
};

export function behaviorEvaluationFormFromDefaults(
  defaults: ChatMemoryEvaluationDefaults,
): BehaviorEvaluationForm {
  return {
    model: defaults.model,
    promptKey: defaults.prompt_key,
    personaKey: defaults.persona_key,
    embedding: defaults.embedding,
    fixtureKey: defaults.fixture_key,
    rounds: String(defaults.rounds),
    timeoutSeconds: String(defaults.timeout_seconds),
    retryCount: String(defaults.retry_count),
    judgeEnabled: defaults.judge_enabled,
  };
}

export function buildBehaviorEvaluationPayload(
  form: BehaviorEvaluationForm,
  defaults: ChatMemoryEvaluationDefaults,
): CreateTestRunPayload {
  const rounds = Number.parseInt(form.rounds, 10);
  const timeoutSeconds = Number.parseFloat(form.timeoutSeconds);
  const retryCount = Number.parseInt(form.retryCount, 10);

  return {
    run_type: "chat_memory_eval",
    model: form.model.trim() || defaults.model,
    prompt_key: form.promptKey.trim() || defaults.prompt_key,
    persona_key: form.personaKey.trim() || defaults.persona_key,
    embedding: form.embedding.trim() || defaults.embedding,
    fixture_key: form.fixtureKey || defaults.fixture_key,
    rounds: Number.isInteger(rounds) ? Math.min(100, Math.max(1, rounds)) : defaults.rounds,
    timeout_seconds: Number.isFinite(timeoutSeconds)
      ? Math.min(600, Math.max(1, timeoutSeconds))
      : defaults.timeout_seconds,
    retry_count: Number.isInteger(retryCount)
      ? Math.min(5, Math.max(0, retryCount))
      : defaults.retry_count,
    judge_enabled: form.judgeEnabled,
  };
}

type Props = {
  copy: TestCenterCopy;
  options: TestCenterOptions["chat_memory_eval"];
  catalog: TestCenterCatalogOptions;
  busy: boolean;
  onCreateRun: (payload: CreateTestRunPayload) => void;
};

export function BehaviorEvaluationLauncher(props: Props) {
  const { defaults } = props.options;
  const [form, setForm] = useState(() => behaviorEvaluationFormFromDefaults(defaults));

  useEffect(() => {
    setForm(behaviorEvaluationFormFromDefaults(defaults));
  }, [defaults]);

  return (
    <div className="card">
      <div className="form-grid">
        <label className="field">
          <span>{props.copy.model}</span>
          <select className="input" value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })}>
            {props.catalog.models.map((option) => <option disabled={!option.available} key={option.key} value={option.key}>{option.label}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{props.copy.prompt}</span>
          <select className="input" value={form.promptKey} onChange={(event) => setForm({ ...form, promptKey: event.target.value })}>
            {props.catalog.prompts.map((option) => <option disabled={!option.available} key={option.key} value={option.key}>{option.label}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{props.copy.persona}</span>
          <select className="input" value={form.personaKey} onChange={(event) => setForm({ ...form, personaKey: event.target.value })}>
            {props.catalog.personas.map((option) => <option disabled={!option.available} key={option.key} value={option.key}>{option.label}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{props.copy.embedding}</span>
          <select className="input" value={form.embedding} onChange={(event) => setForm({ ...form, embedding: event.target.value })}>
            {props.catalog.embeddings.map((option) => <option disabled={!option.available} key={option.key} value={option.key}>{option.label}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{props.copy.fixture}</span>
          <select className="input" value={form.fixtureKey} onChange={(event) => setForm({ ...form, fixtureKey: event.target.value })}>
            {props.options.fixtures.map((fixture) => <option key={fixture.key} value={fixture.key}>{fixture.label}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{props.copy.rounds}</span>
          <input className="input" min="1" max="100" type="number" value={form.rounds} onChange={(event) => setForm({ ...form, rounds: event.target.value })} />
        </label>
        <label className="field">
          <span>{props.copy.timeoutSeconds}</span>
          <input className="input" min="1" max="600" type="number" value={form.timeoutSeconds} onChange={(event) => setForm({ ...form, timeoutSeconds: event.target.value })} />
        </label>
        <label className="field">
          <span>{props.copy.retryCount}</span>
          <input className="input" min="0" max="5" type="number" value={form.retryCount} onChange={(event) => setForm({ ...form, retryCount: event.target.value })} />
        </label>
        <label className="field" style={{ alignSelf: "end" }}>
          <span>{props.copy.judgeEnabled}</span>
          <input checked={form.judgeEnabled} type="checkbox" onChange={(event) => setForm({ ...form, judgeEnabled: event.target.checked })} />
        </label>
      </div>
      <div className="toolbar" style={{ marginTop: 10 }}>
        <button className="button" disabled={props.busy} onClick={() => props.onCreateRun(buildBehaviorEvaluationPayload(form, defaults))}>
          {props.busy ? props.copy.submitting : props.copy.createRun}
        </button>
      </div>
    </div>
  );
}
