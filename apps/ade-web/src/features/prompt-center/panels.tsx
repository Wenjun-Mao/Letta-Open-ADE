"use client";

import Link from "next/link";

import type { PromptCenterCopy } from "./copy";
import { normalizeScenarioKey } from "./helpers";
import type { PromptCenterController } from "./use-prompt-center";

export function PromptCenterToolbar({
  copy,
  controller,
}: {
  copy: PromptCenterCopy;
  controller: PromptCenterController;
}) {
  return (
    <div className="card" style={{ marginTop: 14 }}>
      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <div className="toolbar">
          <button className={controller.tab === "prompts" ? "tab-active" : "tab-item"} onClick={() => controller.setTab("prompts")}>{copy.promptsTab}</button>
          {controller.scenario !== "label" ? (
            <button className={controller.tab === "personas" ? "tab-active" : "tab-item"} onClick={() => controller.setTab("personas")}>{copy.personasTab}</button>
          ) : null}
        </div>

        <div className="toolbar">
          <span className="muted" style={{ fontSize: 12 }}>{copy.scenarioLabel}</span>
          <button className={controller.scenario === "chat" ? "tab-active" : "tab-item"} onClick={() => controller.setScenario("chat")}>{copy.chatScenario}</button>
          <button className={controller.scenario === "comment" ? "tab-active" : "tab-item"} onClick={() => controller.setScenario("comment")}>{copy.commentScenario}</button>
          <button className={controller.scenario === "label" ? "tab-active" : "tab-item"} onClick={() => controller.setScenario("label")}>{copy.labelScenario}</button>
        </div>

        <div className="toolbar">
          <label className="field" style={{ display: "inline-flex", flexDirection: "row", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={controller.includeArchived} onChange={(event) => controller.setIncludeArchived(event.target.checked)} />
            <span>{copy.includeArchived}</span>
          </label>
          <button className="button muted" onClick={() => void controller.refresh()} disabled={controller.loading || controller.busy}>{copy.refresh}</button>
          <button className="button muted" onClick={controller.resetDraft} disabled={controller.busy}>{copy.createNew}</button>
        </div>
      </div>
    </div>
  );
}

export function PromptTemplateList({
  copy,
  controller,
}: {
  copy: PromptCenterCopy;
  controller: PromptCenterController;
}) {
  return (
    <div className="card">
      <h3>{copy.activeList}</h3>
      {controller.loading ? <p className="muted">Loading...</p> : null}
      {!controller.loading && controller.activeItems.length === 0 ? <p className="muted">{copy.noTemplates}</p> : null}
      <div className="studio-stack" style={{ marginTop: 8, maxHeight: 480, overflowY: "auto" }}>
        {controller.activeItems.map((item) => (
          <button
            key={item.key}
            type="button"
            className={item.key === controller.selectedKey ? "tab-active" : "tab-item"}
            style={{ width: "100%", textAlign: "left" }}
            onClick={() => controller.hydrateDraft(item)}
          >
            <div style={{ fontWeight: 700 }}>{item.label || item.key}</div>
            <div className="muted" style={{ fontSize: 12 }}>{item.key}</div>
            <div className="muted" style={{ fontSize: 12 }}>{item.scenario}</div>
            <div className="muted" style={{ fontSize: 12 }}>{item.archived ? copy.archivedBadge : copy.activeBadge}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

export function PromptTemplateEditor({
  copy,
  controller,
}: {
  copy: PromptCenterCopy;
  controller: PromptCenterController;
}) {
  return (
    <div className="card">
      <h3>{copy.editor}</h3>
      {!controller.selected && !controller.editingExisting ? <p className="muted">{copy.selectHint}</p> : null}
      {controller.selected?.archived ? <p className="muted">{copy.saveDisabledArchived}</p> : null}

      <div className="form-grid" style={{ marginTop: 8 }}>
        <label className="field">
          <span>{copy.scenarioLabel}</span>
          <input className="input" value={controller.scenario} disabled />
        </label>
        <label className="field">
          <span>{copy.key}</span>
          <input
            className="input"
            value={controller.draftKey}
            onChange={(event) => controller.setDraftKey(event.target.value)}
            onBlur={(event) => {
              if (!controller.editingExisting) {
                controller.setDraftKey(normalizeScenarioKey(event.target.value, controller.scenario));
              }
            }}
            disabled={controller.editingExisting}
          />
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
          <span>{copy.content}</span>
          <textarea className="input" style={{ minHeight: 320, resize: "vertical", fontFamily: "Consolas, monospace" }} value={controller.draftContent} onChange={(event) => controller.setDraftContent(event.target.value)} />
        </label>
      </div>

      <div className="toolbar" style={{ marginTop: 10 }}>
        <button className="button" onClick={() => void controller.save()} disabled={controller.busy || controller.loading || Boolean(controller.selected?.archived)}>
          {controller.busy ? "..." : controller.editingExisting ? copy.saveUpdate : copy.saveCreate}
        </button>
        <button className="button muted" onClick={() => void controller.archive()} disabled={controller.busy || !controller.selected || Boolean(controller.selected.archived)}>{copy.archive}</button>
        <button className="button muted" onClick={() => void controller.restore()} disabled={controller.busy || !controller.selected || !Boolean(controller.selected.archived)}>{copy.restore}</button>
        <button className="button danger" onClick={() => void controller.purge()} disabled={controller.busy || !controller.selected || !Boolean(controller.selected.archived)}>{copy.purge}</button>
        <Link className="button muted" href={controller.workspaceHref}>{controller.workspaceLabel}</Link>
      </div>
    </div>
  );
}
