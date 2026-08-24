import Link from "next/link";

import type { LABEL_LAB_COPY } from "./copy";
import { formatGroupLabel } from "./extraction-presenters";
import type { LabelLabController } from "./use-label-lab";
import { formatModelOptionLabel } from "@/shared/generation-controls";
import { formatLocalTimestamp, prettyJson } from "@/shared/json-display";

type Copy = (typeof LABEL_LAB_COPY)[keyof typeof LABEL_LAB_COPY];
type PanelProps = { copy: Copy; controller: LabelLabController };

export function LabelLabSettingsPanel({ copy, controller }: PanelProps) {
  const { form } = controller;
  const disabled = controller.submitting;
  return (
    <div className="card studio-panel">
      <h3>{copy.tuningTitle}</h3>
      <div className="form-grid" style={{ marginTop: 10 }}>
        <label className="field">
          <span>{copy.model}</span>
          <select className="input" value={form.model} onChange={(event) => controller.setModel(event.target.value)} disabled={controller.loadingOptions || disabled}>
            <option value="">{copy.selectModel}</option>
            {controller.models.map((item) => <option key={item.key} value={item.key}>{formatModelOptionLabel(item)}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{copy.prompt}</span>
          <select className="input" value={form.promptKey} onChange={(event) => controller.setPromptKey(event.target.value)} disabled={controller.loadingOptions || disabled}>
            {controller.prompts.map((item) => <option key={item.key} value={item.key}>{formatModelOptionLabel(item)}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{copy.schema}</span>
          <select className="input" value={form.schemaKey} onChange={(event) => controller.setSchemaKey(event.target.value)} disabled={controller.loadingOptions || disabled}>
            {controller.schemas.map((item) => <option key={item.key} value={item.key}>{formatModelOptionLabel(item)}</option>)}
          </select>
        </label>
        <label className="field"><span>{copy.capability}</span><input className="input" value={controller.capabilityLabel} disabled /></label>
        <NumberField label={copy.maxTokens} value={form.maxTokens} onChange={controller.setMaxTokens} disabled={disabled} min={0} max={8192} />
        <NumberField label={copy.timeoutSeconds} value={form.timeoutSeconds} onChange={controller.setTimeoutSeconds} disabled={disabled} min={5} max={600} />
        <NumberField label={copy.repairRetryCount} value={form.repairRetryCount} onChange={controller.setRepairRetryCount} disabled={disabled} min={0} max={3} />
        <NumberField label={copy.temperature} value={form.temperature} onChange={controller.setTemperature} disabled={disabled} min={0} max={2} step={0.1} />
        <NumberField label={copy.topP} value={form.topP} onChange={controller.setTopP} disabled={disabled} min={0.01} max={1} step={0.05} />
        <NumberField label={copy.topK} value={form.topK} onChange={controller.setTopK} disabled={disabled} min={1} placeholder="64" />
      </div>
      <div className="toolbar" style={{ marginTop: 12 }}>
        <button className="button" onClick={() => void controller.generate()} disabled={controller.loadingOptions || disabled}>{disabled ? copy.generating : copy.generate}</button>
        <button className="button muted" onClick={() => void controller.loadOptions(true)} disabled={disabled}>{copy.refreshOptions}</button>
        <Link className="button muted" href="/schema-center">{copy.manageSchemas}</Link>
      </div>
      <p className="muted" style={{ marginTop: 10, fontSize: 12 }}>{copy.defaultsFromRuntime}</p>
    </div>
  );
}

function NumberField({ label, value, onChange, disabled, min, max, step = 1, placeholder }: { label: string; value: string; onChange: (value: string) => void; disabled: boolean; min: number; max?: number; step?: number; placeholder?: string }) {
  return <label className="field"><span>{label}</span><input className="input" type="number" min={min} max={max} step={step} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} disabled={disabled} /></label>;
}

export function LabelLabWorkspacePanel({ copy, controller }: PanelProps) {
  const { form, selectedPrompt, selectedSchema } = controller;
  return (
    <div className="card studio-panel">
      <h3>{copy.mainContentTitle}</h3>
      <label className="field" style={{ marginTop: 10 }}>
        <span>{copy.articleInput}</span>
        <textarea className="input" rows={12} style={{ minHeight: 220 }} value={form.articleInput} onChange={(event) => controller.setArticleInput(event.target.value)} placeholder={copy.articleInputPlaceholder} disabled={controller.submitting} />
      </label>
      <h3 style={{ marginTop: 14 }}>{copy.promptPreview}</h3>
      <div className="code" style={{ marginTop: 10, minHeight: 110, maxHeight: 180, overflowY: "auto", whiteSpace: "pre-wrap" }}>{selectedPrompt?.content || copy.rawPlaceholder}</div>
      <h3 style={{ marginTop: 14 }}>{copy.schemaPreview}</h3>
      <div className="code" style={{ marginTop: 10, minHeight: 150, maxHeight: 220, overflowY: "auto" }}>{selectedSchema ? prettyJson(selectedSchema.schema) : selectedPrompt?.output_schema || copy.rawPlaceholder}</div>
    </div>
  );
}

export function LabelLabResultPanel({ copy, controller }: PanelProps) {
  const { extractedGroups, result } = controller;
  return (
    <div className="card studio-panel">
      <h3>{copy.outputTitle}</h3>
      <div style={metadataGridStyle}>
        <MetadataCard title={copy.runtimeMetaTitle} rows={[
          [copy.provider, result.provider], [copy.modelUsed, result.modelUsed], [copy.outputMode, result.outputMode],
          [copy.temperatureUsed, result.temperatureUsed], [copy.topPUsed, result.topPUsed], [copy.topKUsed, result.topKUsed],
          [copy.selectedAttempt, result.selectedAttempt], [copy.finishReason, result.finishReason], [copy.responseSeconds, result.responseSeconds],
          [copy.receivedAt, result.receivedAt ? formatLocalTimestamp(result.receivedAt) : ""],
        ]} />
        <MetadataCard title={copy.tokenMetaTitle} rows={[
          [copy.usagePromptTokens, result.usagePromptTokens], [copy.usageCompletionTokens, result.usageCompletionTokens], [copy.usageTotalTokens, result.usageTotalTokens],
        ]} />
      </div>
      <h3 style={{ marginTop: 14 }}>{copy.extractedGroupsTitle}</h3>
      {extractedGroups.length ? <div style={metadataGridStyle}>
        {extractedGroups.map((group) => <div key={group.key} className="card" style={{ margin: 0, padding: "10px 12px" }}>
          <div style={{ fontWeight: 700 }}>{formatGroupLabel(group.key)}</div>
          {group.items.length ? <ul className="list" style={{ marginTop: 8 }}>{group.items.map((item, index) => <li key={`${group.key}-${index}`}>{item}</li>)}</ul> : <p className="muted" style={{ marginTop: 8 }}>{copy.emptyGroup}</p>}
        </div>)}
      </div> : <div className="code" style={{ marginTop: 10, minHeight: 120, whiteSpace: "pre-wrap" }}>{copy.extractedGroupsPlaceholder}</div>}
      <h3 style={{ marginTop: 14 }}>{copy.resultJsonTitle}</h3>
      <div className="code" style={{ marginTop: 10, minHeight: 220, whiteSpace: "pre-wrap" }}>{result.resultJson || copy.resultJsonPlaceholder}</div>
    </div>
  );
}

const metadataGridStyle = { marginTop: 10, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 } as const;

function MetadataCard({ title, rows }: { title: string; rows: Array<[string, string]> }) {
  return <div className="card" style={{ margin: 0, padding: "10px 12px" }}><div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>{title}</div><div className="list" style={{ marginTop: 6 }}>{rows.map(([label, value]) => <div key={label}>{label}: {value || "-"}</div>)}</div></div>;
}

export function LabelLabDiagnosticsPanels({ copy, controller }: PanelProps) {
  const { result } = controller;
  return (
    <div className="studio-layout" style={{ marginTop: 14 }}>
      <div className="card studio-panel">
        <h3>{copy.internalsTitle}</h3>
        <h3 style={{ marginTop: 14 }}>{copy.validationErrors}</h3>
        <div className="code" style={{ marginTop: 10, minHeight: 90 }}>{result.validationErrors.length ? result.validationErrors.join("\n") : "-"}</div>
        <h3 style={{ marginTop: 14 }}>{copy.rawRequestTitle}</h3>
        <div className="code" style={{ marginTop: 10, minHeight: 160, maxHeight: 320, overflowY: "auto" }}>{result.rawRequest || copy.rawPlaceholder}</div>
      </div>
      <div className="card studio-panel">
        <h3>{copy.rawReplyTitle}</h3>
        <div className="code" style={{ marginTop: 10, minHeight: 280, maxHeight: 480, overflowY: "auto" }}>{result.rawReply || copy.rawPlaceholder}</div>
        <h3 style={{ marginTop: 14 }}>{copy.notesTitle}</h3>
        <ul className="list"><li>{copy.notesOne}</li><li>{copy.notesTwo}</li><li>{copy.notesThree}</li></ul>
      </div>
    </div>
  );
}
