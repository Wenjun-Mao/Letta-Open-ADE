"use client";

import type { useAgentStudio } from "./use-agent-studio";
import { defaultSubjectLabel } from "./selection";
import { FieldCaption, fieldCaptionId } from "./field-caption";

type Translate = (english: string, chinese: string) => string;
type Props = { controller: ReturnType<typeof useAgentStudio>; t: Translate };

function Pagination({ offset, total, change, t }: { offset: number; total: number; change: (value: number) => void; t: Translate }) {
  if (total <= 100 && !offset) return null;
  return <div className="toolbar">
    <button className="button muted" disabled={!offset} onClick={() => change(Math.max(0, offset - 100))}>{t("Previous", "上一页")}</button>
    <span>{offset + 1}–{Math.min(total, offset + 100)} / {total}</span>
    <button className="button muted" disabled={offset + 100 >= total} onClick={() => change(offset + 100)}>{t("Next", "下一页")}</button>
  </div>;
}

export function RelationshipMemoryView({ controller, t }: Props) {
  const memory = controller.memory;
  if (!memory) return null;
  const { scope, memories, deliveries, operations } = memory;
  const definitions = controller.session ? [controller.session.agent_definition, ...controller.definitions] : controller.definitions;
  const characters = [...new Map(definitions.filter((item) => item.agent_definition_id)
    .map((item) => [item.agent_definition_id!, item])).values()];
  const subjects = controller.session ? [controller.session.memory_subject, ...controller.subjects.filter((item) => item.id !== controller.session?.memory_subject.id)] : controller.subjects;
  return <section className="card studio-evidence-card studio-relationship-memory">
    <h2>{t("Relationship memory", "关系记忆")}</h2>
    <p className="muted">{t("Only this person and character share these memories. Processing completion is not a judgment of correctness.", "记忆只属于这位人物与这个角色。处理完成不代表语义正确。")}</p>
    <div className="field"><FieldCaption inputId="memory-person">{t("Memory person", "记忆所属人物")}</FieldCaption>
      <select id="memory-person" className="input" aria-labelledby={fieldCaptionId("memory-person")} value={scope?.subjectId || ""} onChange={(event) => memory.selectScope({ subjectId: event.target.value, characterRootId: scope?.characterRootId || "" })}>
        <option value="" disabled>{t("Choose a person", "选择人物")}</option>
        {subjects.map((item) => <option key={item.id} value={item.id}>{defaultSubjectLabel(item)}</option>)}
      </select>
    </div>
    <div className="field"><FieldCaption inputId="memory-character">{t("Memory character", "记忆所属角色")}</FieldCaption>
      <select id="memory-character" className="input" aria-labelledby={fieldCaptionId("memory-character")} value={scope?.characterRootId || ""} onChange={(event) => memory.selectScope({ subjectId: scope?.subjectId || "", characterRootId: event.target.value })}>
        <option value="" disabled>{t("Choose a character", "选择角色")}</option>
        {characters.map((item) => <option key={item.agent_definition_id} value={item.agent_definition_id!}>{item.name}</option>)}
      </select>
    </div>
    {scope?.subjectId && scope.characterRootId ? <>
      <h3>{t("Delivery queue", "投递队列")}</h3>
      <button className="button muted" onClick={deliveries.refresh}>{t("Refresh delivery state", "刷新投递状态")}</button>
      {deliveries.loading ? <p role="status">{t("Loading delivery state...", "正在加载投递状态...")}</p> : null}
      {deliveries.error ? <p role="alert">{t("Delivery state unavailable: ", "投递状态不可用：")}{deliveries.error}</p> : null}
      {memory.actionError ? <p role="alert">{memory.actionError}</p> : null}
      {deliveries.data ? <>
        <p>{Object.entries(deliveries.data.counts).map(([status, count]) => `${status}: ${count}`).join(" · ") || t("No messages queued.", "还没有消息进入队列。")}</p>
        <div className="studio-memory-list">{deliveries.data.items.map((item) => <article className="studio-memory-fact" key={item.operation_id}>
          <strong>#{item.relationship_sequence} · {item.role} · {item.status}</strong>
          <p>{t("Accepted by Memory", "Memory 已受理")}: {item.accepted_at || t("not confirmed", "尚未确认")}</p>
          <p>{t("Retention completed", "留存已完成")}: {item.retained_at || t("not confirmed", "尚未确认")}</p>
          {item.status !== "retained" ? <p>{t("Queue age", "排队时长")}: {Math.floor(item.queue_age_seconds)}s</p> : null}
          {item.blocked_by_operation_id ? <p>{t("Waiting behind", "等待前置投递")}: <code>{item.blocked_by_operation_id}</code></p> : null}
          {item.last_error_code ? <p role="status">{item.last_error_code}</p> : null}
          <button className="button muted" onClick={() => void controller.openEvidence(item)}>{t("Open saved message", "查看已保存消息")}</button>
          {["failed", "uncertain"].includes(item.status) ? <button className="button muted" disabled={Boolean(memory.retrying)} onClick={() => void memory.retryDelivery(item)}>{t("Retry delivery", "重试投递")}</button> : null}
          {Object.keys(item.native_progress).length ? <details><summary>{t("Last reported progress (not a percentage)", "最近上报进度（不是完成百分比）")}</summary><pre>{JSON.stringify(item.native_progress, null, 2)}</pre></details> : null}
        </article>)}</div>
        <Pagination offset={memory.deliveryOffset} total={deliveries.data.total} change={memory.setDeliveryOffset} t={t} />
      </> : null}
      <h3>{t("Learned memories", "已形成的记忆")}</h3>
      <button className="button muted" onClick={memories.refresh}>{t("Reload memories", "重新加载记忆")}</button>
      {memories.loading ? <p role="status">{t("Loading Memory...", "正在加载 Memory...")}</p> : null}
      {memories.error ? <p role="alert">{t("Memory inspection unavailable. This is not an empty result. ", "Memory 检视不可用，这不表示记忆为空。")}{memories.error}</p> : null}
      {memories.data ? <>
        {!memories.data.total ? <p>{t("No retained memories were returned for this relationship.", "此关系当前没有返回已留存记忆。")}</p> : null}
        {memories.data.items.map((item) => <article className="studio-memory-fact" key={item.id}>
          <strong>{item.fact_type || t("Memory", "记忆")} · {item.state}</strong><p>{item.text}</p><p className="muted">{item.context}</p>
          <small>{item.occurred_start || item.date} {item.occurred_end ? ` / ${item.occurred_end}` : ""}</small>
          {item.document_id ? <button className="button muted" onClick={() => void memory.openSource(item.document_id!)}>{t("Inspect source", "检视来源")}</button> : null}
          {item.source_memory_ids.length ? <details><summary>{t("Observation source memories", "归纳记忆的来源")}</summary><code>{item.source_memory_ids.join(", ")}</code></details> : null}
        </article>)}
        <Pagination offset={memory.memoryOffset} total={memories.data.total} change={memory.setMemoryOffset} t={t} />
      </> : null}
      {memory.source ? <article className="studio-summary">
        <h3>{t("Original source", "原始来源")}</h3>
        {memory.source.error ? <p role="alert">{memory.source.error}</p> : memory.source.data ? <>
          <p>{memory.source.data.delivery.role} · {memory.source.data.occurred_at}</p><p>{memory.source.data.content}</p>
          <button className="button muted" onClick={() => void controller.openEvidence(memory.source!.data!.delivery)}>{t("Open original conversation", "查看原始对话")}</button>
          <details><summary>{t("Attribution and antecedent context", "归属与前文上下文")}</summary><p>{memory.source.data.native_context}</p></details>
        </> : <p>{t("Loading source...", "正在加载来源...")}</p>}
      </article> : null}
      <details className="studio-technical-details"><summary>{t("Native processing and consolidation", "原生处理与归纳")}</summary>
        {operations.loading ? <p>{t("Loading operations...", "正在加载操作...")}</p> : null}
        {operations.error ? <p role="alert">{operations.error}</p> : null}
        {operations.data?.items.map((item) => <article key={item.operation_id}><strong>{item.operation_type || "operation"} · {item.status}</strong><code>{item.operation_id}</code><pre>{JSON.stringify(item.native_progress, null, 2)}</pre></article>)}
        {operations.data ? <Pagination offset={memory.operationOffset} total={operations.data.total} change={memory.setOperationOffset} t={t} /> : null}
      </details>
    </> : <p>{t("Choose both a person and a character. Inspection does not create a relationship.", "请同时选择人物与角色。检视不会创建新关系。")}</p>}
  </section>;
}
