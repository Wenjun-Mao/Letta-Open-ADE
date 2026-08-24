"use client";

import Link from "next/link";

import type { ToolCenterCopy } from "./copy";
import { getToolIdentifier } from "./helpers";
import type { ToolCenterController } from "./use-tool-center";

export function ToolCenterToolbar({
  copy,
  controller,
}: {
  copy: ToolCenterCopy;
  controller: ToolCenterController;
}) {
  return (
    <div className="card" style={{ marginTop: 14 }}>
      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <div className="toolbar" style={{ flexWrap: "wrap" }}>
          <label className="field" style={{ display: "inline-flex", flexDirection: "row", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={controller.includeArchived} onChange={(event) => controller.setIncludeArchived(event.target.checked)} />
            <span>{copy.includeArchived}</span>
          </label>
          <label className="field" style={{ display: "inline-flex", flexDirection: "row", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={controller.includeBuiltin} onChange={(event) => controller.setIncludeBuiltin(event.target.checked)} />
            <span>{copy.includeBuiltin}</span>
          </label>
          <label className="field" style={{ display: "inline-flex", flexDirection: "row", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={controller.includeSourceInList} onChange={(event) => controller.setIncludeSourceInList(event.target.checked)} />
            <span>{copy.includeSourceInList}</span>
          </label>
        </div>

        <div className="toolbar">
          <input className="input" style={{ minWidth: 220 }} placeholder={copy.search} value={controller.search} onChange={(event) => controller.setSearch(event.target.value)} />
          <button className="button muted" onClick={() => void controller.refresh()} disabled={controller.loading || controller.busy}>{copy.refresh}</button>
          <button className="button muted" onClick={controller.resetDraft} disabled={controller.busy}>{copy.createNew}</button>
          <Link className="button muted" href="/agent-studio?focus=tools">{copy.attachStudio}</Link>
        </div>
      </div>
    </div>
  );
}

export function ToolList({
  copy,
  controller,
}: {
  copy: ToolCenterCopy;
  controller: ToolCenterController;
}) {
  return (
    <div className="card">
      <h3>Tools</h3>
      {controller.loading ? <p className="muted">Loading...</p> : null}
      {!controller.loading && controller.items.length === 0 ? <p className="muted">{copy.noResults}</p> : null}
      <div className="studio-stack" style={{ marginTop: 8, maxHeight: 540, overflowY: "auto" }}>
        {controller.items.map((item) => {
          const id = getToolIdentifier(item);
          return (
            <button
              key={id}
              type="button"
              className={id === controller.selectedId ? "tab-active" : "tab-item"}
              style={{ width: "100%", textAlign: "left" }}
              onClick={() => void controller.select(item)}
            >
              <div style={{ fontWeight: 700 }}>{item.name || item.slug || item.tool_id}</div>
              <div className="muted" style={{ fontSize: 12 }}>{item.slug || item.tool_id}</div>
              <div className="muted" style={{ fontSize: 12 }}>
                {item.managed ? copy.managedTool : copy.readOnlyBuiltin} | {item.archived ? copy.archivedBadge : copy.activeBadge}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function ToolEditor({
  copy,
  controller,
}: {
  copy: ToolCenterCopy;
  controller: ToolCenterController;
}) {
  const isReadOnly = controller.selected ? Boolean(!controller.selected.managed || controller.selected.archived) : false;

  return (
    <div className="card">
      <h3>{controller.mode === "create" ? copy.createNew : controller.selected?.name || "Tool"}</h3>

      <div className="form-grid" style={{ marginTop: 8 }}>
        <label className="field">
          <span>{copy.slug}</span>
          <input className="input" value={controller.draftSlug} onChange={(event) => controller.setDraftSlug(event.target.value)} disabled={controller.mode === "edit"} />
        </label>
        <label className="field" style={{ gridColumn: "1 / -1" }}>
          <span>{copy.description}</span>
          <textarea className="input" style={{ minHeight: 88, resize: "vertical" }} value={controller.draftDescription} onChange={(event) => controller.setDraftDescription(event.target.value)} disabled={isReadOnly} />
        </label>
        <label className="field" style={{ gridColumn: "1 / -1" }}>
          <span>{copy.tags}</span>
          <input className="input" value={controller.draftTags} onChange={(event) => controller.setDraftTags(event.target.value)} disabled={isReadOnly} />
        </label>
        <label className="field" style={{ gridColumn: "1 / -1" }}>
          <span>{copy.source}</span>
          <textarea className="input" style={{ minHeight: 340, resize: "vertical", fontFamily: "Consolas, monospace" }} value={controller.draftSource} onChange={(event) => controller.setDraftSource(event.target.value)} disabled={isReadOnly} />
        </label>
      </div>

      <div className="toolbar" style={{ marginTop: 10 }}>
        <button className="button" onClick={() => void (controller.mode === "create" ? controller.create() : controller.update())} disabled={controller.primaryDisabled}>
          {controller.busy ? "..." : controller.mode === "create" ? copy.create : copy.update}
        </button>
        <button className="button muted" onClick={() => void controller.archive()} disabled={controller.busy || !controller.selected?.managed || Boolean(controller.selected?.archived)}>{copy.archive}</button>
        <button className="button muted" onClick={() => void controller.restore()} disabled={controller.busy || !controller.selected?.managed || !Boolean(controller.selected?.archived)}>{copy.restore}</button>
        <button className="button danger" onClick={() => void controller.purge()} disabled={controller.busy || !controller.selected?.managed || !Boolean(controller.selected?.archived)}>{copy.purge}</button>
      </div>
    </div>
  );
}
