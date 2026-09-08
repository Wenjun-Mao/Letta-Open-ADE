import { useEffect, useState } from "react";

import type {
  AgentRuntimeAcceptanceDefaults,
  CreateTestRunPayload,
  TestCenterCatalogOptions,
  TestCenterOptions,
} from "./api";
import type { TestCenterCopy } from "./test-center-copy";

export type NativeRuntimeQualificationForm = {
  conversationModelKey: string;
  reviewerModelKey: string;
  embeddingModelKey: string;
  promptKey: string;
  personaKey: string;
  rounds: string;
  timeoutSeconds: string;
  retryCount: string;
  includeLlamaCompatibility: boolean;
  caseKeys: string[];
};

export function nativeRuntimeQualificationFormFromDefaults(
  defaults: AgentRuntimeAcceptanceDefaults,
): NativeRuntimeQualificationForm {
  return {
    conversationModelKey: defaults.conversation_model_key,
    reviewerModelKey: defaults.reviewer_model_key,
    embeddingModelKey: defaults.embedding_model_key,
    promptKey: defaults.prompt_key,
    personaKey: defaults.persona_key,
    rounds: String(defaults.rounds),
    timeoutSeconds: String(defaults.timeout_seconds),
    retryCount: String(defaults.retry_count),
    includeLlamaCompatibility: defaults.include_llama_compatibility,
    caseKeys: [],
  };
}

export function buildNativeRuntimeQualificationPayload(
  form: NativeRuntimeQualificationForm,
  defaults: AgentRuntimeAcceptanceDefaults,
  caseOrder: readonly string[],
): CreateTestRunPayload {
  const caseKeys = caseOrder.filter((key) => form.caseKeys.includes(key));
  const focusedDiagnostic = caseKeys.length > 0;
  const rounds = Number.parseInt(form.rounds, 10);
  const timeoutSeconds = Number.parseFloat(form.timeoutSeconds);
  const retryCount = Number.parseInt(form.retryCount, 10);

  return {
    run_type: "agent_runtime_acceptance",
    conversation_model_key: form.conversationModelKey.trim() || defaults.conversation_model_key,
    reviewer_model_key: form.reviewerModelKey.trim() || defaults.reviewer_model_key,
    embedding_model_key: form.embeddingModelKey.trim() || defaults.embedding_model_key,
    prompt_key: form.promptKey.trim() || defaults.prompt_key,
    persona_key: form.personaKey.trim() || defaults.persona_key,
    ...(focusedDiagnostic ? { case_keys: caseKeys } : {}),
    rounds: focusedDiagnostic ? 1 : (Number.isInteger(rounds) ? Math.min(3, Math.max(1, rounds)) : defaults.rounds),
    timeout_seconds: Number.isFinite(timeoutSeconds)
      ? Math.min(600, Math.max(5, timeoutSeconds))
      : defaults.timeout_seconds,
    retry_count: Number.isInteger(retryCount)
      ? Math.min(5, Math.max(0, retryCount))
      : defaults.retry_count,
    include_llama_compatibility: focusedDiagnostic ? false : form.includeLlamaCompatibility,
  };
}

type Props = {
  copy: TestCenterCopy;
  options: TestCenterOptions["agent_runtime_acceptance"];
  catalog: TestCenterCatalogOptions;
  busy: boolean;
  onCreateRun: (payload: CreateTestRunPayload) => void;
};

export function NativeRuntimeQualificationLauncher(props: Props) {
  const { defaults } = props.options;
  const [form, setForm] = useState(() => nativeRuntimeQualificationFormFromDefaults(defaults));

  useEffect(() => {
    setForm(nativeRuntimeQualificationFormFromDefaults(defaults));
  }, [defaults]);

  const toggleCase = (caseKey: string, selected: boolean) => {
    setForm({
      ...form,
      caseKeys: selected
        ? [...form.caseKeys, caseKey]
        : form.caseKeys.filter((current) => current !== caseKey),
    });
  };

  return (
    <div className="card">
      <p className="muted">{props.copy.qualificationHelp}</p>
      <div className="form-grid">
        <label className="field">
          <span>{props.copy.conversationModel}</span>
          <select className="input" value={form.conversationModelKey} onChange={(event) => setForm({ ...form, conversationModelKey: event.target.value })}>
            {props.catalog.models.map((option) => <option disabled={!option.available} key={option.key} value={option.key}>{option.label}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{props.copy.reviewerModel}</span>
          <select className="input" value={form.reviewerModelKey} onChange={(event) => setForm({ ...form, reviewerModelKey: event.target.value })}>
            {props.catalog.models.map((option) => <option disabled={!option.available} key={option.key} value={option.key}>{option.label}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{props.copy.retrieverModel}</span>
          <select className="input" value={form.embeddingModelKey} onChange={(event) => setForm({ ...form, embeddingModelKey: event.target.value })}>
            {props.catalog.embeddings.map((option) => <option disabled={!option.available} key={option.key} value={option.key}>{option.label}</option>)}
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
          <span>{props.copy.rounds}</span>
          <input className="input" disabled={form.caseKeys.length > 0} min="1" max="3" type="number" value={form.caseKeys.length > 0 ? "1" : form.rounds} onChange={(event) => setForm({ ...form, rounds: event.target.value })} />
        </label>
        <label className="field">
          <span>{props.copy.timeoutSeconds}</span>
          <input className="input" min="5" max="600" type="number" value={form.timeoutSeconds} onChange={(event) => setForm({ ...form, timeoutSeconds: event.target.value })} />
        </label>
        <label className="field">
          <span>{props.copy.retryCount}</span>
          <input className="input" min="0" max="5" type="number" value={form.retryCount} onChange={(event) => setForm({ ...form, retryCount: event.target.value })} />
        </label>
        <label className="field" style={{ alignSelf: "end" }}>
          <span>{props.copy.llamaCompatibility}</span>
          <input checked={form.includeLlamaCompatibility} disabled={form.caseKeys.length > 0} type="checkbox" onChange={(event) => setForm({ ...form, includeLlamaCompatibility: event.target.checked })} />
        </label>
      </div>
      <fieldset className="card" style={{ marginTop: 12, padding: 12 }}>
        <legend>{props.copy.diagnosticCases}</legend>
        <p className="muted">{props.copy.diagnosticCasesHelp}</p>
        <div className="form-grid">
          {props.options.cases.map((testCase) => (
            <label className="field" key={testCase.key}>
              <span>{testCase.label}</span>
              <input checked={form.caseKeys.includes(testCase.key)} type="checkbox" onChange={(event) => toggleCase(testCase.key, event.target.checked)} />
            </label>
          ))}
        </div>
      </fieldset>
      <div className="toolbar" style={{ marginTop: 10 }}>
        <button className="button" disabled={props.busy} onClick={() => props.onCreateRun(buildNativeRuntimeQualificationPayload(form, defaults, props.options.cases.map((testCase) => testCase.key)))}>
          {props.busy ? props.copy.submitting : props.copy.createRun}
        </button>
      </div>
    </div>
  );
}
