"use client";

import type { MemoryFact, MemoryEvidence } from "./types";

type Translate = (english: string, chinese: string) => string;

export function MemoryFacts({ facts, t, openEvidence, prepareAction, canAct }: {
  facts: MemoryFact[];
  t: Translate;
  openEvidence: (evidence: MemoryEvidence) => Promise<void>;
  prepareAction: (factId: string, version: number, operation: "correct" | "forget") => void;
  canAct: boolean;
}) {
  const active = facts.filter((fact) => fact.status === "active");
  const historical = facts.filter((fact) => fact.status !== "active");
  return <div className="studio-fact-list">
    <h3>{t("Saved facts", "已保存事实")}</h3>
    <p className="muted">{t("These facts are shared by conversations bound to this subject, not a private character relationship history.", "这些事实由绑定此主体的对话共享，并非角色的私人关系历史。")}</p>
    {active.length ? active.map((fact) => <FactRow key={fact.id} fact={fact} t={t} openEvidence={openEvidence} prepareAction={prepareAction} canAct={canAct} />) : <p className="muted">{t("No active saved facts.", "没有活跃的已保存事实。")}</p>}
    <details><summary>{t("Historical and removed facts", "历史及已移除事实")} ({historical.length})</summary>
      <p className="muted">{t("Removal excludes a fact from active memory and search. Past conversations, summaries, and revision evidence remain.", "移除会将事实从活跃记忆和搜索中排除。过去的对话、摘要及修订证据仍会保留。")}</p>
      {historical.map((fact) => <FactRow key={fact.id} fact={fact} t={t} openEvidence={openEvidence} prepareAction={prepareAction} canAct={false} />)}
    </details>
  </div>;
}

function FactRow({ fact, t, openEvidence, prepareAction, canAct }: {
  fact: MemoryFact;
  t: Translate;
  openEvidence: (evidence: MemoryEvidence) => Promise<void>;
  prepareAction: (factId: string, version: number, operation: "correct" | "forget") => void;
  canAct: boolean;
}) {
  return <details><summary><span><strong>{fact.fact_type}</strong> · {fact.entity_label || fact.entity_kind}</span><span className={fact.status === "active" ? "studio-status studio-status-good" : "studio-status studio-status-bad"}>{fact.status} · v{fact.version}</span></summary>
    <p className="studio-fact-value">{fact.value || t("Removed from active memory", "已从活跃记忆中移除")}</p>
    {fact.qualifier ? <p className="muted">{t("Qualifier", "限定词")}: {fact.qualifier}</p> : null}
    {canAct ? <div className="toolbar"><button className="button muted" onClick={() => prepareAction(fact.id, fact.version, "correct")}>{t("Prepare correction", "准备更正")}</button><button className="button muted" onClick={() => prepareAction(fact.id, fact.version, "forget")}>{t("Remove saved information", "移除已保存信息")}</button></div> : null}
    <div className="studio-revisions">{fact.revisions.map((revision) => <article key={revision.id}><strong>{revision.operation} · v{revision.fact_version}</strong><span>{t("run", "运行")} {revision.run_id.slice(0, 12)}</span>{revision.predecessor_revision_ids.length ? <small>{t("Supersedes", "取代")}: {revision.predecessor_revision_ids.join(", ")}</small> : null}{revision.evidence.map((evidence) => <blockquote key={`${evidence.message_id}-${evidence.start_char}`}><button className="studio-citation" onClick={() => void openEvidence(evidence)}>“{evidence.quote}” <cite>{t("Open original message", "打开原始消息")} #{evidence.message_sequence}</cite></button></blockquote>)}</article>)}</div>
  </details>;
}
