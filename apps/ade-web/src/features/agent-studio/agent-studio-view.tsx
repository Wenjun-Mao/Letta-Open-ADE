"use client";

import type { useAgentStudio } from "./use-agent-studio";
import { NEW_RESOURCE_VALUE, defaultBundle, defaultSubjectLabel, isArchived } from "./selection";
import type { AgentDefinition, MemoryFact, RunEvent } from "./types";

type Controller = ReturnType<typeof useAgentStudio>;
type Translate = (english: string, chinese: string) => string;

function short(value: string | null | undefined): string {
  if (!value) return "-";
  return value.length > 22 ? `${value.slice(0, 9)}...${value.slice(-8)}` : value;
}

function date(value: string | null | undefined): string {
  if (!value) return "-";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function statusClass(status: string): string {
  if (["qualified", "succeeded", "active"].includes(status)) return "studio-status studio-status-good";
  if (["failed", "cancelled", "forgotten"].includes(status)) return "studio-status studio-status-bad";
  return "studio-status studio-status-warn";
}

function identity(definition: AgentDefinition): string {
  return `${definition.definition_key} v${definition.version}`;
}

function Library({ controller, t }: { controller: Controller; t: Translate }) {
  return (
    <aside className="studio-library" aria-label={t("Agent Studio resources", "智能体工作台资源")}>
      <section className="card studio-setup-card">
        <div className="kicker">{t("New binding", "新建绑定")}</div>
        <h2>{t("Start a conversation", "开始对话")}</h2>
        <p className="muted">{t("A conversation binds one frozen definition version to one explicit memory subject.", "每个对话都绑定一个冻结的定义版本和一个明确的记忆主体。")}</p>
        <div className="studio-form-stack">
          <label className="field"><span>{t("Conversation title", "对话标题")}</span><input className="input" value={controller.title} onChange={(event) => controller.setTitle(event.target.value)} disabled={controller.busy} /></label>
          <label className="field"><span>{t("Definition version", "定义版本")}</span>
            <select className="input" value={controller.definitionChoice} onChange={(event) => controller.setDefinitionChoice(event.target.value)} disabled={controller.busy}>
              <option value={NEW_RESOURCE_VALUE}>{t("Create from qualified bundle", "从已认证套件创建")}</option>
              {controller.definitions.map((definition) => <option key={definition.id} value={definition.id} disabled={isArchived(definition)}>{identity(definition)}{isArchived(definition) ? ` (${t("archived", "已归档")})` : ""}</option>)}
            </select>
          </label>
          {controller.definitionChoice === NEW_RESOURCE_VALUE ? <DefinitionDraft controller={controller} t={t} /> : null}
          <label className="field"><span>{t("Memory subject", "记忆主体")}</span>
            <select className="input" value={controller.subjectChoice} onChange={(event) => controller.setSubjectChoice(event.target.value)} disabled={controller.busy}>
              <option value={NEW_RESOURCE_VALUE}>{t("Create a new subject", "创建新主体")}</option>
              {controller.subjects.map((subject) => <option key={subject.id} value={subject.id} disabled={isArchived(subject)}>{defaultSubjectLabel(subject)} · {subject.external_key}{isArchived(subject) ? ` (${t("archived", "已归档")})` : ""}</option>)}
            </select>
          </label>
          {controller.subjectChoice === NEW_RESOURCE_VALUE ? <SubjectDraft controller={controller} t={t} /> : null}
          <button className="button" disabled={controller.busy || !defaultBundle(controller.options)} onClick={() => void controller.createSession()}>
            {controller.busy ? t("Creating...", "创建中...") : t("Create immutable binding", "创建不可变绑定")}
          </button>
        </div>
      </section>

      <section className="card studio-session-library">
        <div className="toolbar studio-section-heading">
          <div><div className="kicker">{t("Conversations", "对话")}</div><h2>{controller.sessions.length}</h2></div>
          <label className="studio-check"><input type="checkbox" checked={controller.includeArchived} onChange={(event) => controller.setIncludeArchived(event.target.checked)} /> {t("Archived", "已归档")}</label>
        </div>
        <div className="studio-session-list">
          {controller.sessions.length ? controller.sessions.map((item) => (
            <button className={controller.session?.conversation.id === item.conversation.id ? "studio-session studio-session-active" : "studio-session"} key={item.conversation.id} onClick={() => controller.selectConversation(item.conversation.id)} aria-current={controller.session?.conversation.id === item.conversation.id ? "page" : undefined}>
              <strong>{item.conversation.title}</strong><span>{item.memory_subject.display_name || item.memory_subject.external_key}</span><small>{identity(item.agent_definition)}{isArchived(item.conversation) ? ` · ${t("archived", "已归档")}` : ""}</small>
            </button>
          )) : <p className="muted">{t("No conversations yet. Create one above.", "尚无对话。请在上方创建一个。")}</p>}
        </div>
      </section>
    </aside>
  );
}

function DefinitionDraft({ controller, t }: { controller: Controller; t: Translate }) {
  const bundle = defaultBundle(controller.options);
  return <div className="studio-draft">
    <label className="field"><span>{t("Definition name", "定义名称")}</span><input className="input" value={controller.definitionName} onChange={(event) => controller.setDefinitionName(event.target.value)} /></label>
    <label className="field"><span>{t("Definition key", "定义键")}</span><input className="input" value={controller.definitionKey} onChange={(event) => controller.setDefinitionKey(event.target.value)} /></label>
    {bundle ? <div className="studio-bundle-note"><strong>{t("Qualified bundle", "已认证套件")}</strong><span>{bundle.name}</span><code>{bundle.model_key}</code><small>{bundle.prompt_key} · {bundle.persona_key} · {bundle.tool_names.join(", ")}</small></div> : null}
  </div>;
}

function SubjectDraft({ controller, t }: { controller: Controller; t: Translate }) {
  return <div className="studio-draft">
    <label className="field"><span>{t("Subject display name", "主体显示名称")}</span><input className="input" value={controller.subjectName} onChange={(event) => controller.setSubjectName(event.target.value)} /></label>
    <label className="field"><span>{t("Stable external key", "稳定外部键")}</span><input className="input" value={controller.subjectKey} onChange={(event) => controller.setSubjectKey(event.target.value)} /></label>
    <p className="studio-hint">{t("Choose an existing subject to share its memory across conversations. A new key creates an isolated memory boundary.", "选择已有主体可在多个对话间共享记忆。新键会创建隔离的记忆边界。")}</p>
  </div>;
}

function Conversation({ controller, t }: { controller: Controller; t: Translate }) {
  const archived = Boolean(controller.session && isArchived(controller.session.conversation));
  if (!controller.session || !controller.conversation) {
    return <section className="card studio-empty-state"><div className="kicker">{t("ADE-native v3", "ADE 原生 v3")}</div><h2>{t("Definitions first, then memory subjects", "先定义，再选择记忆主体")}</h2><p>{t("Create a reusable immutable definition version, choose an explicit person or organization to own memory, then start a conversation. This keeps memory shared only where you deliberately bind the same subject.", "创建可复用的不可变定义版本，选择拥有记忆的明确个人或组织，然后开始对话。只有在明确绑定同一主体时，记忆才会被共享。")}</p></section>;
  }
  return <section className="card studio-conversation-card">
    <div className="studio-conversation-heading"><div><div className="kicker">{t("Immutable messages", "不可变消息")}</div><h2>{controller.session.conversation.title}</h2><p>{t("Definition", "定义")}: {identity(controller.session.agent_definition)} · {t("Subject", "主体")}: {defaultSubjectLabel(controller.session.memory_subject)}</p></div><div className="toolbar">{archived ? <button className="button muted" disabled={controller.busy} onClick={() => void controller.setSessionArchived(false)}>{t("Restore conversation", "恢复对话")}</button> : <button className="button muted" disabled={controller.busy || controller.activeRun} onClick={() => void controller.setSessionArchived(true)}>{t("Archive conversation", "归档对话")}</button>}{controller.run ? <span className={statusClass(controller.run.status)}>{controller.run.status}</span> : null}</div></div>
    {archived ? <div className="studio-boundary-warning">{t("This conversation is archived. Restore it before sending another turn.", "此对话已归档。请先恢复再发送新轮次。")}</div> : null}
    <div className="studio-message-list" aria-live="polite">{controller.conversation.messages.length ? controller.conversation.messages.map((entry) => <article className={`studio-message studio-message-${entry.role}`} key={entry.id}><header><strong>{entry.role === "user" ? t("User", "用户") : t("Assistant", "助手")}</strong><span>#{entry.sequence} · {date(entry.created_at)}</span></header><p>{entry.content}</p></article>) : <p className="muted">{t("No messages yet. Durable facts may be proposed by the runtime and appear in the typed memory panel after review.", "尚无消息。持久事实可由运行时提出，并在审核后显示在类型化记忆面板中。")}</p>}</div>
    <label className="field studio-message-input"><span>{t("User message", "用户消息")}</span><textarea className="input" rows={4} value={controller.message} disabled={archived || controller.activeRun} onChange={(event) => controller.setMessage(event.target.value)} /></label>
    <div className="studio-run-controls"><label className="field"><span>{t("Timeout (seconds)", "超时（秒）")}</span><input className="input" type="number" min={5} max={600} value={controller.timeoutSeconds} disabled={controller.activeRun} onChange={(event) => controller.setTimeoutSeconds(Number(event.target.value))} /></label><label className="field"><span>{t("Additional retries", "额外重试")}</span><input className="input" type="number" min={0} max={controller.options?.max_retry_count || 5} value={controller.retryCount} disabled={controller.activeRun} onChange={(event) => controller.setRetryCount(Number(event.target.value))} /></label><button className="button" disabled={controller.busy || archived || controller.activeRun || !controller.message.trim()} onClick={() => void controller.sendMessage()}>{controller.activeRun ? t("Run in progress", "运行中") : t("Run turn", "运行轮次")}</button>{controller.activeRun ? <button className="button muted" disabled={controller.busy} onClick={() => void controller.cancelActiveRun()}>{t("Cancel run", "取消运行")}</button> : null}</div>
    {controller.streamWarning ? <p className="studio-stream-warning">{controller.streamWarning}</p> : null}
    {controller.run?.error_message ? <p className="studio-run-error"><strong>{controller.run.error_code || t("Run failed", "运行失败")}</strong> {controller.run.error_message}</p> : null}
  </section>;
}

function DefinitionEvidence({ controller, t }: { controller: Controller; t: Translate }) {
  const definition = controller.session?.agent_definition;
  if (!definition) return null;
  const archived = isArchived(definition);
  return <section className="card studio-evidence-card"><div className="studio-card-heading"><div><div className="kicker">{t("Frozen definition", "冻结定义")}</div><h2>{definition.name}</h2></div><span className={statusClass(definition.qualification_state)}>{definition.qualification_state}</span></div><p className="studio-definition-version">{identity(definition)} · {t("created", "创建于")} {date(definition.created_at)}</p><dl className="studio-metadata"><div><dt>{t("Prompt snapshot", "提示词快照")}</dt><dd>{definition.prompt_key}<code>{short(definition.prompt_sha256)}</code></dd></div><div><dt>{t("Persona snapshot", "人设快照")}</dt><dd>{definition.persona_key}<code>{short(definition.persona_sha256)}</code></dd></div><div><dt>{t("Memory policy", "记忆策略")}</dt><dd>{definition.memory_policy_version}</dd></div><div><dt>{t("Curated tools", "受限工具")}</dt><dd>{definition.tool_names.join(", ") || "-"}</dd></div></dl><div className="studio-deployments">{definition.deployments.map((deployment) => <article key={deployment.deployment_id}><strong>{deployment.role}</strong><span>{deployment.route_alias}</span><code>{short(deployment.fingerprint)}</code></article>)}</div>{definition.agent_definition_id ? <button className="button muted" disabled={controller.busy} onClick={() => void controller.setDefinitionArchived(!archived)}>{archived ? t("Restore definition", "恢复定义") : t("Archive definition", "归档定义")}</button> : null}</section>;
}

function SubjectEvidence({ controller, t }: { controller: Controller; t: Translate }) {
  const subject = controller.session?.memory_subject;
  if (!subject) return null;
  const archived = isArchived(subject);
  return <section className="card studio-evidence-card"><div className="studio-card-heading"><div><div className="kicker">{t("Memory subject", "记忆主体")}</div><h2>{defaultSubjectLabel(subject)}</h2></div><span className={archived ? statusClass("forgotten") : statusClass("active")}>{archived ? t("archived", "已归档") : t("active", "活跃")}</span></div><p className="muted"><code>{subject.external_key}</code> · {t("version", "版本")} {subject.version}</p><div className="studio-inline-form"><label className="field"><span>{t("Display name", "显示名称")}</span><input className="input" value={controller.subjectRename} disabled={controller.busy || archived} onChange={(event) => controller.setSubjectRename(event.target.value)} /></label><button className="button muted" disabled={controller.busy || archived || !controller.subjectRename.trim()} onClick={() => void controller.renameSubject()}>{t("Rename", "重命名")}</button></div><button className="button muted" disabled={controller.busy} onClick={() => void controller.setSubjectArchived(!archived)}>{archived ? t("Restore subject", "恢复主体") : t("Archive subject", "归档主体")}</button><MemoryFacts facts={controller.memories?.facts || []} t={t} /></section>;
}

function MemoryFacts({ facts, t }: { facts: MemoryFact[]; t: Translate }) {
  return <div className="studio-fact-list"><h3>{t("Typed facts and evidence", "类型化事实与证据")}</h3>{facts.length ? facts.map((fact) => <details key={fact.id}><summary><span><strong>{fact.fact_type}</strong> · {fact.entity_label || fact.entity_kind}</span><span className={statusClass(fact.status)}>{fact.status} · v{fact.version}</span></summary><p className="studio-fact-value">{fact.value || t("Forgotten", "已遗忘")}</p>{fact.qualifier ? <p className="muted">{t("Qualifier", "限定词")}: {fact.qualifier}</p> : null}<div className="studio-revisions">{fact.revisions.map((revision) => <article key={revision.id}><strong>{revision.operation} · v{revision.fact_version}</strong><span>{t("run", "运行")} {short(revision.run_id)}</span>{revision.predecessor_revision_ids.length ? <small>{t("Supersedes", "取代")}: {revision.predecessor_revision_ids.map(short).join(", ")}</small> : null}{revision.evidence.map((evidence) => <blockquote key={`${evidence.message_id}-${evidence.start_char}`}>“{evidence.quote}”<cite>#{short(evidence.message_id)}</cite></blockquote>)}</article>)}</div></details>) : <p className="muted">{t("No durable facts are committed for this subject yet.", "此主体尚未提交持久事实。")}</p>}</div>;
}

function RunEvidence({ controller, t }: { controller: Controller; t: Translate }) {
  if (!controller.session) return null;
  return <section className="card studio-evidence-card studio-run-evidence"><div className="kicker">{t("Run trace", "运行轨迹")}</div><h2>{t("Async runs and provenance", "异步运行与来源")}</h2>{controller.conversation?.summary ? <article className="studio-summary"><strong>{t("Summary", "摘要")} v{controller.conversation.summary.version}</strong><p>{controller.conversation.summary.content}</p><small>{t("Source through message", "来源覆盖至消息")} #{controller.conversation.summary.source_boundary.through_sequence} · {t("Run", "运行")} {short(controller.conversation.summary.provenance.run_id)}</small><code>{t("Model", "模型")}: {controller.conversation.summary.provenance.model_key}</code></article> : <p className="muted">{t("No conversation summary has been committed yet.", "尚未提交对话摘要。")}</p>}<div className="studio-run-list"><h3>{t("Run history", "运行历史")}</h3>{controller.runs.length ? controller.runs.map((item) => <div className={controller.run?.id === item.id ? "studio-run-row studio-run-row-active" : "studio-run-row"} key={item.id}><span className={statusClass(item.status)}>{item.status}</span><span>{date(item.created_at)}</span><small>{item.timeout_seconds}s · +{item.retry_count} {t("retries", "重试")}</small></div>) : <p className="muted">{t("No runs yet.", "尚无运行。")}</p>}</div><EventLog events={controller.events} t={t} /></section>;
}

function EventLog({ events, t }: { events: RunEvent[]; t: Translate }) {
  return <div className="studio-event-list"><h3>{t("Normalized events", "标准化事件")}</h3>{events.length ? events.map((event) => <details key={event.id}><summary><span><strong>#{event.sequence}</strong> {event.type}</span><span>{date(event.occurred_at)}</span></summary><pre>{JSON.stringify(event.payload, null, 2)}</pre></details>) : <p className="muted">{t("Events appear here while a run is active and are retained as an operator trace.", "运行期间事件会显示在这里，并保留为运维轨迹。")}</p>}</div>;
}

export function AgentStudioView({ controller, t }: { controller: Controller; t: Translate }) {
  return <div className="agent-studio-root"><header className="studio-page-header"><div><div className="kicker">{t("ADE-native agent runtime", "ADE 原生智能体运行时")}</div><h1>{t("Agent Studio", "智能体工作台")}</h1><p>{t("Reusable definitions, explicit memory subjects, immutable conversations, and inspectable runs.", "可复用定义、明确记忆主体、不可变对话及可检查运行。")}</p></div><div className="studio-runtime-badge"><strong>{controller.options?.runtime || "ade_native_v3"}</strong><span>{t("no fallback", "无回退")}</span></div></header>{controller.error ? <section className="studio-error" role="alert"><strong>{t("Agent Studio error", "智能体工作台错误")}</strong><span>{controller.error}</span></section> : null}{controller.loading ? <p className="muted">{t("Loading Agent Studio resources...", "正在加载智能体工作台资源...")}</p> : null}<div className="agent-studio-layout"><Library controller={controller} t={t} /><main className="studio-conversation"><Conversation controller={controller} t={t} /></main><aside className="studio-evidence"><DefinitionEvidence controller={controller} t={t} /><SubjectEvidence controller={controller} t={t} /><RunEvidence controller={controller} t={t} /></aside></div></div>;
}
