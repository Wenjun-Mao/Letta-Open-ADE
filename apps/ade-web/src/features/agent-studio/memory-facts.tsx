"use client";

import type { MemoryFact, MemoryEvidence } from "./types";

type Translate = (english: string, chinese: string) => string;

export function MemoryFacts({ facts, t, openEvidence, prepareAction, removeSaved, canCorrect, canRemove }: {
  facts: MemoryFact[];
  t: Translate;
  openEvidence: (evidence: MemoryEvidence) => Promise<void>;
  prepareAction: (factId: string, version: number, operation: "correct" | "forget") => void;
  removeSaved?: (factId: string, version: number) => Promise<void>;
  canCorrect: boolean;
  canRemove?: boolean;
}) {
  const active = facts.filter((fact) => fact.status === "active");
  const historical = facts.filter((fact) => fact.status !== "active");
  return <div className="studio-fact-list">
    <h3>{t("Saved facts", "已保存事实")}</h3>
    <p className="muted">{t("These facts are shared by conversations bound to this subject, not a private character relationship history.", "这些事实由绑定此主体的对话共享，并非角色的私人关系历史。")}</p>
    {active.length ? active.map((fact) => <FactRow key={fact.id} fact={fact} t={t} openEvidence={openEvidence} prepareAction={prepareAction} removeSaved={removeSaved} canCorrect={canCorrect} canRemove={Boolean(canRemove)} />) : <p className="muted">{t("No active saved facts.", "没有活跃的已保存事实。")}</p>}
    <details><summary>{t("Inactive and removed facts", "非活跃及已移除事实")} ({historical.length})</summary>
      <p className="muted">{t("Inactive facts are former assertions, not current preferences. Removal excludes a fact chain from model fact selection; past messages, summaries and audit revisions remain.", "非活跃事实是过往陈述，不是当前偏好。移除会将该事实链排除出模型事实选择；过去的消息、摘要和审计修订仍会保留。")}</p>
      {historical.map((fact) => <FactRow key={fact.id} fact={fact} t={t} openEvidence={openEvidence} prepareAction={prepareAction} removeSaved={removeSaved} canCorrect={false} canRemove={Boolean(canRemove)} />)}
    </details>
  </div>;
}

function FactRow({ fact, t, openEvidence, prepareAction, removeSaved, canCorrect, canRemove }: {
  fact: MemoryFact;
  t: Translate;
  openEvidence: (evidence: MemoryEvidence) => Promise<void>;
  prepareAction: (factId: string, version: number, operation: "correct" | "forget") => void;
  removeSaved?: (factId: string, version: number) => Promise<void>;
  canCorrect: boolean;
  canRemove: boolean;
}) {
  const current = fact.revisions.find((revision) => revision.fact_version === fact.version);
  return <details><summary><span><strong>{fact.fact_type}</strong> · {fact.entity_label || fact.entity_kind}</span><span className={fact.status === "active" ? "studio-status studio-status-good" : "studio-status studio-status-bad"}>{fact.status} · v{fact.version}</span></summary>
    <p className="studio-fact-value">{fact.status === "inactive" ? t("Former assertion: ", "过往陈述：") : null}{fact.value || t("Removed from model fact selection", "已从模型事实选择中移除")}</p>
    {current?.reason ? <p className="muted">{t("Lifecycle reason", "生命周期原因")}: {current.reason}</p> : null}
    {fact.qualifier ? <p className="muted">{t("Qualifier", "限定词")}: {fact.qualifier}</p> : null}
    {canCorrect && fact.status === "active" ? <div className="toolbar"><button className="button muted" onClick={() => prepareAction(fact.id, fact.version, "correct")}>{t("Prepare reviewed correction", "准备审核更正")}</button></div> : null}
    {canRemove && fact.status !== "forgotten" && removeSaved ? <button className="button muted" onClick={() => void removeSaved(fact.id, fact.version)}>{t("Remove exact saved assertion", "移除这条已保存陈述")}</button> : null}
    <div className="studio-revisions">{fact.revisions.map((revision) => <article key={revision.id}><strong>{revision.operation} · v{revision.fact_version}{revision.reason ? ` · ${revision.reason}` : ""}</strong><span>{revision.action_id ? `${t("operator action", "操作员动作")} ${revision.action_id.slice(0, 12)}` : `${t("run", "运行")} ${revision.run_id?.slice(0, 12) || "-"}`}</span>{revision.predecessor_revision_ids.length ? <small>{t("Predecessors", "前序修订")}: {revision.predecessor_revision_ids.join(", ")}</small> : null}{revision.evidence.map((evidence) => <blockquote key={`${evidence.message_id}-${evidence.start_char}-${evidence.authority_role || "legacy"}`}><button className="studio-citation" onClick={() => void openEvidence(evidence)}>“{evidence.quote}” <cite>{evidence.authority_role || "user_assertion"} · {t("Open original message", "打开原始消息")} #{evidence.message_sequence}</cite></button></blockquote>)}</article>)}</div>
  </details>;
}
