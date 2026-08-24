import type { COMMENT_LAB_COPY } from "./copy";
import { previewText } from "./provider-payload-formatters";
import type { CommentLabController, PopOutCard } from "./use-comment-lab";
import { formatModelOptionLabel } from "@/shared/generation-controls";
import { formatLocalTimestamp } from "@/shared/json-display";

type Copy = (typeof COMMENT_LAB_COPY)[keyof typeof COMMENT_LAB_COPY];

type PanelProps = {
  copy: Copy;
  controller: CommentLabController;
};

export function CommentLabSettingsPanel({ copy, controller }: PanelProps) {
  const { form } = controller;
  const disabled = controller.submitting;

  return (
    <div className="card studio-panel">
      <h3>{copy.tuningTitle}</h3>
      <div className="form-grid" style={{ marginTop: 10 }}>
        <label className="field">
          <span>{copy.model}</span>
          <select
            className="input"
            value={form.model}
            onChange={(event) => controller.setModel(event.target.value)}
            disabled={controller.loadingOptions || disabled}
          >
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
          <span>{copy.persona}</span>
          <select className="input" value={form.personaKey} onChange={(event) => controller.setPersonaKey(event.target.value)} disabled={controller.loadingOptions || disabled}>
            {controller.personas.map((item) => <option key={item.key} value={item.key}>{formatModelOptionLabel(item)}</option>)}
          </select>
        </label>
        <NumberField label={copy.maxTokens} value={form.maxTokens} onChange={controller.setMaxTokens} disabled={disabled} min={0} max={8192} hint={copy.maxTokensHint} />
        <NumberField label={copy.timeoutSeconds} value={form.timeoutSeconds} onChange={controller.setTimeoutSeconds} disabled={disabled} min={5} max={600} />
        <NumberField label={copy.retryCount} value={form.retryCount} onChange={controller.setRetryCount} disabled={disabled} min={0} max={5} hint={copy.retryCountHint} />
        <label className="field">
          <span>{copy.taskShape}</span>
          <select className="input" value={form.taskShape} onChange={(event) => controller.setTaskShape(event.target.value as typeof form.taskShape)} disabled={disabled}>
            <option value="classic">{copy.taskShapeClassic}</option>
            <option value="all_in_system">{copy.taskShapeAllInSystem}</option>
            <option value="structured_output">{copy.taskShapeStructuredOutput}</option>
          </select>
        </label>
        <NumberField label={copy.temperature} value={form.temperature} onChange={controller.setTemperature} disabled={disabled} min={0} max={2} step={0.1} />
        <NumberField label={copy.topP} value={form.topP} onChange={controller.setTopP} disabled={disabled} min={0.01} max={1} step={0.05} />
        <NumberField label={copy.topK} value={form.topK} onChange={controller.setTopK} disabled={disabled} min={1} placeholder="64" />
        <ToggleField label={copy.cachePrompt} hint={copy.cachePromptHint} checked={form.cachePrompt} onChange={controller.setCachePrompt} disabled={disabled} />
        <ToggleField label={copy.enableThinking} hint={copy.enableThinkingHint} checked={form.enableThinking} onChange={controller.setEnableThinking} disabled={disabled} />
      </div>
      <div className="toolbar" style={{ marginTop: 12 }}>
        <button className="button" onClick={() => void controller.generate()} disabled={controller.loadingOptions || disabled}>
          {disabled ? copy.generating : copy.generate}
        </button>
        <button className="button muted" onClick={() => void controller.loadOptions(true)} disabled={disabled}>{copy.refreshOptions}</button>
      </div>
      <p className="muted" style={{ marginTop: 10, fontSize: 12 }}>{copy.defaultsFromEnv}</p>
    </div>
  );
}

type NumberFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
  min: number;
  max?: number;
  step?: number;
  placeholder?: string;
  hint?: string;
};

function NumberField({ label, value, onChange, disabled, min, max, step = 1, placeholder, hint }: NumberFieldProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <input className="input" type="number" min={min} max={max} step={step} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} disabled={disabled} />
      {hint ? <span className="muted" style={{ fontSize: 12 }}>{hint}</span> : null}
    </label>
  );
}

type ToggleFieldProps = {
  label: string;
  hint: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled: boolean;
};

function ToggleField({ label, hint, checked, onChange, disabled }: ToggleFieldProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <label className="muted" style={{ fontSize: 12 }}>
        <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} disabled={disabled} style={{ marginRight: 8 }} />
        {hint}
      </label>
    </label>
  );
}

export function CommentLabWorkspacePanel({ copy, controller }: PanelProps) {
  const { form, result } = controller;
  return (
    <div className="card studio-panel">
      <h3>{copy.mainContentTitle}</h3>
      <label className="field" style={{ marginTop: 10 }}>
        <span>{copy.userInput}</span>
        <textarea className="input" rows={12} style={{ minHeight: 240 }} value={form.userInput} onChange={(event) => controller.setUserInput(event.target.value)} placeholder={copy.userInputPlaceholder} disabled={controller.submitting} />
      </label>
      <hr className="studio-divider" />
      <h3>{copy.outputTitle}</h3>
      <div style={metadataGridStyle}>
        <MetadataCard title={copy.runtimeMetaTitle} rows={[
          [copy.provider, result.provider], [copy.modelUsed, result.modelUsed], [copy.taskShapeUsed, result.taskShapeUsed],
          [copy.cachePromptUsed, result.cachePromptUsed], [copy.enableThinkingUsed, result.enableThinkingUsed],
          [copy.temperatureUsed, result.temperatureUsed], [copy.topPUsed, result.topPUsed], [copy.topKUsed, result.topKUsed],
          [copy.maxTokensUsed, result.maxTokensUsed], [copy.timeoutUsed, result.timeoutUsed],
        ]} />
        <MetadataCard title={copy.timingMetaTitle} rows={[
          [copy.responseSeconds, result.responseSeconds], [copy.receivedAt, result.receivedAt ? formatLocalTimestamp(result.receivedAt) : ""],
        ]} />
        <MetadataCard title={copy.tokenMetaTitle} rows={[
          [copy.usagePromptTokens, result.usagePromptTokens], [copy.usageCompletionTokens, result.usageCompletionTokens],
          [copy.usageReasoningTokens, result.usageReasoningTokens], [copy.usageTotalTokens, result.usageTotalTokens],
        ]} />
      </div>
      <div className="code" style={{ marginTop: 10, minHeight: 280 }}>{result.output || copy.outputPlaceholder}</div>
    </div>
  );
}

const metadataGridStyle = { marginTop: 10, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 } as const;

function MetadataCard({ title, rows }: { title: string; rows: Array<[string, string]> }) {
  return (
    <div className="card" style={{ margin: 0, padding: "10px 12px" }}>
      <div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>{title}</div>
      <div className="list" style={{ marginTop: 6 }}>
        {rows.map(([label, value]) => <div key={label}>{label}: {value || "-"}</div>)}
      </div>
    </div>
  );
}

export function CommentLabDiagnosticsPanel({ copy, controller }: PanelProps) {
  const { result } = controller;
  const openCard = (title: string, readable: string, raw: string) => controller.setPopOutCard({ title, readable, raw });
  return (
    <div className="card studio-panel">
      <h3>{copy.innerWorksTitle}</h3>
      <div className="list" style={{ marginTop: 0 }}>
        <div>{copy.selectedAttempt}: {result.selectedAttempt || "-"}</div>
        <div>{copy.finishReason}: {result.finishReason || "-"}</div>
      </div>
      <PayloadPreview title={copy.rawRequestTitle} readable={result.rawRequestReadable} raw={result.rawRequest} placeholder={copy.rawRequestPlaceholder} openLabel={copy.popOutCard} onOpen={openCard} />
      <PayloadPreview title={copy.rawReplyTitle} readable={result.rawReplyReadable} raw={result.rawReply} placeholder={copy.rawReplyPlaceholder} openLabel={copy.popOutCard} onOpen={openCard} />
      <h3 style={{ marginTop: 14 }}>{copy.notesTitle}</h3>
      <ul className="list"><li>{copy.notesOne}</li><li>{copy.notesTwo}</li><li>{copy.notesThree}</li><li>{copy.notesFour}</li></ul>
    </div>
  );
}

function PayloadPreview({ title, readable, raw, placeholder, openLabel, onOpen }: { title: string; readable: string; raw: string; placeholder: string; openLabel: string; onOpen: (title: string, readable: string, raw: string) => void }) {
  return (
    <>
      <div className="toolbar" style={{ marginTop: 14, justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>{title}</h3>
        <button className="button muted" onClick={() => onOpen(title, readable, raw)} disabled={!raw}>{openLabel}</button>
      </div>
      <div className="code" style={{ marginTop: 10, minHeight: 150, maxHeight: 220, overflowY: "auto" }}>{previewText(readable) || placeholder}</div>
    </>
  );
}

export function CommentLabPayloadModal({ copy, card, onClose }: { copy: Copy; card: PopOutCard | null; onClose: () => void }) {
  if (!card) return null;
  return (
    <div className="editor-overlay" onClick={onClose}>
      <div className="editor-card" style={{ width: "min(1100px, 100%)", maxHeight: "88vh", overflowY: "auto" }} onClick={(event) => event.stopPropagation()}>
        <div className="toolbar" style={{ justifyContent: "space-between" }}><h3 style={{ margin: 0 }}>{card.title}</h3><button className="button muted" onClick={onClose}>{copy.closeCard}</button></div>
        <h3 style={{ marginTop: 14 }}>{copy.readableView}</h3>
        <div className="code" style={{ marginTop: 10, minHeight: 220, maxHeight: 380, overflowY: "auto" }}>{card.readable || "-"}</div>
        <details style={{ marginTop: 14 }}><summary>{copy.rawJsonView}</summary><div className="code" style={{ marginTop: 10, minHeight: 180, maxHeight: 420, overflowY: "auto" }}>{card.raw || "-"}</div></details>
      </div>
    </div>
  );
}
