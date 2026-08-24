"use client";

import Link from "next/link";

import type { SchemaCenterCopy } from "./copy";
import type { SchemaCenterController } from "./use-schema-center";

export function SchemaCenterToolbar({
  copy,
  controller,
}: {
  copy: SchemaCenterCopy;
  controller: SchemaCenterController;
}) {
  return (
    <div className="card" style={{ marginTop: 14 }}>
      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <label className="field" style={{ display: "inline-flex", flexDirection: "row", alignItems: "center", gap: 8 }}>
          <input type="checkbox" checked={controller.includeArchived} onChange={(event) => controller.setIncludeArchived(event.target.checked)} />
          <span>{copy.includeArchived}</span>
        </label>
        <div className="toolbar">
          <button className="button muted" onClick={() => void controller.refresh()} disabled={controller.loading || controller.busy}>{copy.refresh}</button>
          <button className="button muted" onClick={controller.resetDraft} disabled={controller.busy}>{copy.createNew}</button>
          <Link className="button muted" href={controller.labelLabHref}>{copy.openInLabelLab}</Link>
        </div>
      </div>
    </div>
  );
}

export function LabelSchemaList({
  copy,
  controller,
}: {
  copy: SchemaCenterCopy;
  controller: SchemaCenterController;
}) {
  return (
    <div className="card">
      <h3>{copy.schemas}</h3>
      {controller.loading ? <p className="muted">Loading...</p> : null}
      {!controller.loading && controller.items.length === 0 ? <p className="muted">{copy.noSchemas}</p> : null}
      <div className="studio-stack" style={{ marginTop: 8, maxHeight: 480, overflowY: "auto" }}>
        {controller.items.map((item) => (
          <button
            key={item.key}
            type="button"
            className={item.key === controller.selectedKey ? "tab-active" : "tab-item"}
            style={{ width: "100%", textAlign: "left" }}
            onClick={() => controller.hydrateDraft(item)}
          >
            <div style={{ fontWeight: 700 }}>{item.label || item.key}</div>
            <div className="muted" style={{ fontSize: 12 }}>{item.key}</div>
            <div className="muted" style={{ fontSize: 12 }}>{item.archived ? copy.archived : copy.active}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

export function LabelSchemaEditor({
  copy,
  controller,
}: {
  copy: SchemaCenterCopy;
  controller: SchemaCenterController;
}) {
  return (
    <div className="card">
      <h3>{copy.editor}</h3>
      {!controller.selected && !controller.editingExisting ? <p className="muted">{copy.selectHint}</p> : null}
      {controller.selected?.archived ? <p className="muted">{copy.readOnly}</p> : null}

      <div className="form-grid" style={{ marginTop: 8 }}>
        <label className="field">
          <span>{copy.key}</span>
          <input className="input" value={controller.draftKey} onChange={(event) => controller.setDraftKey(event.target.value)} disabled={controller.editingExisting} />
        </label>
        <label className="field">
          <span>{copy.label}</span>
          <input className="input" value={controller.draftLabel} onChange={(event) => controller.setDraftLabel(event.target.value)} />
        </label>
        <label className="field" style={{ gridColumn: "1 / -1" }}>
          <span>{copy.description}</span>
          <input className="input" value={controller.draftDescription} onChange={(event) => controller.setDraftDescription(event.target.value)} />
        </label>
        <label className="field" style={{ gridColumn: "1 / -1" }}>
          <span>{copy.schema}</span>
          <textarea
            className="input"
            style={{ minHeight: 420, resize: "vertical", fontFamily: "Consolas, monospace" }}
            value={controller.draftSchema}
            onChange={(event) => controller.setDraftSchema(event.target.value)}
          />
        </label>
      </div>

      <div className="toolbar" style={{ marginTop: 10 }}>
        <button className="button" onClick={() => void controller.save()} disabled={controller.busy || controller.loading || Boolean(controller.selected?.archived)}>
          {controller.busy ? "..." : controller.editingExisting ? copy.saveUpdate : copy.saveCreate}
        </button>
        <button className="button muted" onClick={() => void controller.archive()} disabled={controller.busy || !controller.selected || Boolean(controller.selected.archived)}>{copy.archive}</button>
        <button className="button muted" onClick={() => void controller.restore()} disabled={controller.busy || !controller.selected || !Boolean(controller.selected.archived)}>{copy.restore}</button>
        <button className="button danger" onClick={() => void controller.purge()} disabled={controller.busy || !controller.selected || !Boolean(controller.selected.archived)}>{copy.purge}</button>
      </div>
    </div>
  );
}
