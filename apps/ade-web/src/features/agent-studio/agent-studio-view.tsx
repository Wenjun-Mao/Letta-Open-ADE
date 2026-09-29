"use client";

import type { useAgentStudio } from "./use-agent-studio";
import { NEW_RESOURCE_VALUE, defaultBundle, defaultSubjectLabel, isArchived } from "./selection";
import type { AgentDefinition, RunEvent } from "./types";
import { TurnActivityView } from "./turn-activity-view";
import { MemoryFacts } from "./memory-facts";
import { DefinitionVersion } from "./definition-version";
import { HISTORY_TRIAL } from "./api";
import { FieldCaption, fieldCaptionId } from "./field-caption";

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
    <aside className="studio-library" aria-label={t("Chats and people", "对话与人物")}>
      <section className="card studio-setup-card">
        <h2>{t("Start a chat", "开始聊天")}</h2>
        <p className="muted">{t("Choose who is chatting. Pick the same person for later chats so their memory carries over.", "选择聊天的人。以后选同一个人，她的记忆就能延续。")}</p>
        <div className="studio-form-stack">
          <div className="field"><FieldCaption inputId="studio-chat-title">{t("Chat title", "聊天标题")}</FieldCaption><input id="studio-chat-title" aria-labelledby={fieldCaptionId("studio-chat-title")} className="input" value={controller.title} onChange={(event) => controller.setTitle(event.target.value)} disabled={controller.busy} /></div>
          <div className="field"><FieldCaption inputId="studio-character-choice">{t("Character", "角色")}</FieldCaption>
            <select id="studio-character-choice" aria-labelledby={fieldCaptionId("studio-character-choice")} className="input" value={controller.definitionChoice} onChange={(event) => controller.setDefinitionChoice(event.target.value)} disabled={controller.busy}>
              <option value={NEW_RESOURCE_VALUE}>{HISTORY_TRIAL ? t("Create Lin Xiaotang", "创建林小棠") : t("Create a character", "创建角色")}</option>
              {controller.definitions.map((definition) => <option key={definition.id} value={definition.id} disabled={isArchived(definition)}>{definition.name} · v{definition.version}{isArchived(definition) ? ` (${t("archived", "已归档")})` : ""}</option>)}
            </select>
          </div>
          {!HISTORY_TRIAL && controller.definitionChoice === NEW_RESOURCE_VALUE ? <DefinitionDraft controller={controller} t={t} /> : null}
          <div className="field"><FieldCaption inputId="studio-person-choice">{t("Who is chatting?", "谁在聊天？")}</FieldCaption>
            <select id="studio-person-choice" aria-labelledby={fieldCaptionId("studio-person-choice")} className="input" value={controller.subjectChoice} onChange={(event) => controller.selectSubjectForNewConversation(event.target.value)} disabled={controller.busy}>
              <option value={NEW_RESOURCE_VALUE}>{t("A new person", "新的人")}</option>
              {controller.subjects.map((subject) => <option key={subject.id} value={subject.id} disabled={isArchived(subject)}>{defaultSubjectLabel(subject)}{isArchived(subject) ? ` (${t("archived", "已归档")})` : ""}</option>)}
            </select>
          </div>
          {controller.subjectChoice === NEW_RESOURCE_VALUE ? <SubjectDraft controller={controller} t={t} /> : null}
          <button className="button" disabled={controller.busy || !defaultBundle(controller.options)
            || (controller.subjectChoice === NEW_RESOURCE_VALUE && !controller.subjectName.trim())
            || (controller.definitionChoice === NEW_RESOURCE_VALUE && !controller.definitionName.trim())}
            onClick={() => void controller.createSession()}>
            {controller.busy ? t("Starting...", "正在开始...") : t("Start chat", "开始聊天")}
          </button>
        </div>
      </section>

      <section className="card studio-session-library">
        <div className="toolbar studio-section-heading">
          <div><h2>{t("Chats", "聊天")}</h2></div>
          <label className="studio-check"><input type="checkbox" checked={controller.includeArchived} onChange={(event) => controller.setIncludeArchived(event.target.checked)} /> {t("Archived", "已归档")}</label>
        </div>
        <div className="studio-session-list">
          {controller.sessions.length ? controller.sessions.map((item) => (
            <button className={controller.session?.conversation.id === item.conversation.id ? "studio-session studio-session-active" : "studio-session"} key={item.conversation.id} onClick={() => controller.selectConversation(item.conversation.id)} aria-current={controller.session?.conversation.id === item.conversation.id ? "page" : undefined}>
              <strong>{item.conversation.title}</strong><span>{defaultSubjectLabel(item.memory_subject)} · {item.agent_definition.name}{isArchived(item.conversation) ? ` · ${t("archived", "已归档")}` : ""}</span>
            </button>
          )) : <p className="muted">{t("No chats yet. Start one above.", "还没有聊天。请在上方开始。")}</p>}
        </div>
      </section>
      <section className="card studio-session-library">
        <h2>{t("People", "人物")}</h2>
        <p className="muted">{t("Select a person to see what is saved about them.", "选择一个人，查看已保存的内容。")}</p>
        <div className="studio-session-list">{controller.subjects.map((subject) => <button
          key={subject.id}
          className={controller.inspectedSubject?.id === subject.id ? "studio-session studio-session-active" : "studio-session"}
          onClick={() => void controller.inspectSubject(subject.id)}
        >{defaultSubjectLabel(subject)}</button>)}</div>
      </section>
    </aside>
  );
}

function DefinitionDraft({ controller, t }: { controller: Controller; t: Translate }) {
  const bundle = defaultBundle(controller.options);
  return <div className="studio-draft">
    <div className="field"><FieldCaption inputId="studio-character-name">{t("Character name", "角色名称")}</FieldCaption><input id="studio-character-name" aria-labelledby={fieldCaptionId("studio-character-name")} className="input" value={controller.definitionName} onChange={(event) => controller.setDefinitionName(event.target.value)} /></div>
    {bundle ? <details className="studio-technical-details"><summary>{t("Character setup details", "角色设置详情")}</summary><p>{bundle.name}</p><code>{bundle.model_key} · {bundle.prompt_key} · {bundle.persona_key}</code></details> : null}
  </div>;
}

function SubjectDraft({ controller, t }: { controller: Controller; t: Translate }) {
  return <div className="studio-draft">
    <div className="field"><FieldCaption inputId="studio-person-name">{t("Your name", "你的名字")}</FieldCaption><input id="studio-person-name" aria-labelledby={fieldCaptionId("studio-person-name")} className="input" value={controller.subjectName} onChange={(event) => controller.setSubjectName(event.target.value)} /></div>
    <p className="studio-hint">{t("Use a fictional name for this trial. A new person starts with separate memory.", "试用时请用虚构名字。新的人会有独立的记忆。")}</p>
  </div>;
}

function Conversation({ controller, t }: { controller: Controller; t: Translate }) {
  const archived = Boolean(controller.session && isArchived(controller.session.conversation));
  if (!controller.session || !controller.conversation) {
    return <section className="studio-empty-state"><h2>{t("Ready when you are", "准备好了就开始")}</h2><p>{t("Start a chat on the left. For the next chat, choose the same person to continue their story.", "请在左侧开始聊天。下次聊天选择同一个人，就能接着聊。")}</p></section>;
  }
  return <section className="card studio-conversation-card">
    <div className="studio-conversation-heading"><div><h2>{controller.session.conversation.title}</h2><p>{controller.session.agent_definition.name} · {defaultSubjectLabel(controller.session.memory_subject)}</p></div><div className="toolbar">{archived ? <button className="button muted" disabled={controller.busy} onClick={() => void controller.setSessionArchived(false)}>{t("Restore chat", "恢复聊天")}</button> : <button className="button muted" disabled={controller.busy || controller.activeRun} onClick={() => void controller.setSessionArchived(true)}>{t("Archive chat", "归档聊天")}</button>}{controller.run ? <span className={statusClass(controller.run.status)}>{controller.run.status}</span> : null}</div></div>
    {archived ? <div className="studio-boundary-warning">{t("This conversation is archived. Restore it before sending another turn.", "此对话已归档。请先恢复再发送新轮次。")}</div> : null}
    <div className="studio-message-list" aria-live="polite">{controller.conversation.messages.length ? controller.conversation.messages.map((entry) => {
      const activity = controller.activity.find((item) => item.run_id === entry.run_id);
      const hasReply = controller.conversation?.messages.some((item) => item.role === "assistant" && item.run_id === entry.run_id);
      return <article id={`message-${entry.id}`} className={`studio-message studio-message-${entry.role}${controller.evidenceMessageId === entry.id ? " studio-message-cited" : ""}`} key={entry.id}><header><strong>{entry.role === "user" ? t("User", "用户") : t("Assistant", "助手")}</strong><span>#{entry.sequence} · {date(entry.created_at)}</span></header><p>{entry.content}</p>{activity && (entry.role === "assistant" || !hasReply) ? <TurnActivityView activity={activity} t={t} /> : null}</article>;
    }) : <p className="muted">{t("No messages yet. Durable facts may be proposed by the runtime and appear in the typed memory panel after review.", "尚无消息。持久事实可由运行时提出，并在审核后显示在类型化记忆面板中。")}</p>}</div>
    {controller.conversation.next_before_sequence ? <button className="button muted" onClick={() => void controller.loadOlderMessages()}>{t("Load older messages", "加载更早的消息")}</button> : null}
    {controller.evidenceError ? <p role="alert" className="studio-run-error">{controller.evidenceError}</p> : null}
    {controller.evidenceMessageId ? <p><a href={`#message-${controller.evidenceMessageId}`}>{t("Jump to cited original message", "跳转至引用的原始消息")}</a> · <button className="button muted" onClick={() => void controller.returnToLatestMessages()}>{t("Return to latest messages", "返回最新消息")}</button></p> : null}
    <div className="field studio-message-input"><FieldCaption inputId="studio-message">{t("Message", "消息")}</FieldCaption><textarea id="studio-message" aria-labelledby={fieldCaptionId("studio-message")} className="input" rows={4} value={controller.message} disabled={archived || controller.activeRun} onChange={(event) => controller.setMessage(event.target.value)} /></div>
    {controller.memoryAction ? <p className="studio-boundary-warning" role="status">{controller.memoryAction.outcome}</p> : null}
    <div className="studio-run-controls"><button className="button" disabled={controller.busy || archived || controller.activeRun || !controller.message.trim()} onClick={() => void controller.sendMessage()}>{controller.activeRun ? t("Sending...", "正在发送...") : t("Send", "发送")}</button>{controller.activeRun ? <button className="button muted" disabled={controller.busy} onClick={() => void controller.cancelActiveRun()}>{t("Cancel", "取消")}</button> : null}</div>
    {!HISTORY_TRIAL ? <details className="studio-technical-details"><summary>{t("Request settings", "请求设置")}</summary><div className="studio-run-controls"><div className="field"><FieldCaption inputId="studio-timeout">{t("Timeout (seconds)", "超时（秒）")}</FieldCaption><input id="studio-timeout" aria-labelledby={fieldCaptionId("studio-timeout")} className="input" type="number" min={5} max={600} value={controller.timeoutSeconds} disabled={controller.activeRun} onChange={(event) => controller.setTimeoutSeconds(Number(event.target.value))} /></div><div className="field"><FieldCaption inputId="studio-retries">{t("Additional retries", "额外重试")}</FieldCaption><input id="studio-retries" aria-labelledby={fieldCaptionId("studio-retries")} className="input" type="number" min={0} max={controller.options?.max_retry_count || 5} value={controller.retryCount} disabled={controller.activeRun} onChange={(event) => controller.setRetryCount(Number(event.target.value))} /></div></div></details> : null}
    {controller.streamWarning ? <p className="studio-stream-warning">{controller.streamWarning}</p> : null}
    {controller.run?.error_message ? <p className="studio-run-error"><strong>{controller.run.error_code || t("Run failed", "运行失败")}</strong> {controller.run.error_message}</p> : null}
  </section>;
}

function DefinitionEvidence({ controller, t }: { controller: Controller; t: Translate }) {
  const definition = controller.session?.agent_definition;
  if (!definition) return null;
  const archived = isArchived(definition);
  return <section className="card studio-evidence-card">
    <h2>{t("Character", "角色")}: {definition.name}</h2>
    {!HISTORY_TRIAL ? <details className="studio-technical-details"><summary>{t("Manage character versions", "管理角色版本")}</summary><DefinitionVersion controller={controller} t={t} />{definition.agent_definition_id ? <button className="button muted" disabled={controller.busy} onClick={() => void controller.setDefinitionArchived(!archived)}>{archived ? t("Restore character", "恢复角色") : t("Archive character", "归档角色")}</button> : null}</details> : null}
    <details className="studio-technical-details"><summary>{t("Technical details", "技术详情")}</summary>
      <p className="studio-definition-version">{identity(definition)} · {date(definition.created_at)} · {definition.qualification_state}</p>
      <dl className="studio-metadata"><div><dt>{t("Prompt snapshot", "提示词快照")}</dt><dd>{definition.prompt_key}<code>{short(definition.prompt_sha256)}</code></dd></div><div><dt>{t("Persona snapshot", "人设快照")}</dt><dd>{definition.persona_key}<code>{short(definition.persona_sha256)}</code></dd></div><div><dt>{t("Memory policy", "记忆策略")}</dt><dd>{definition.memory_policy_version}</dd></div><div><dt>{t("Tools", "工具")}</dt><dd>{definition.tool_names.join(", ") || "-"}</dd></div></dl>
      <div className="studio-deployments">{definition.deployments.map((deployment) => <article key={`${deployment.role}:${deployment.deployment_id}`}><strong>{deployment.role}</strong><span>{deployment.route_alias}</span><code>{short(deployment.fingerprint)}</code></article>)}</div>
    </details>
  </section>;
}

function SubjectEvidence({ controller, t }: { controller: Controller; t: Translate }) {
  const subject = controller.inspectedSubject || controller.session?.memory_subject;
  if (!subject) return null;
  const archived = isArchived(subject);
  const factState = controller.inspectedSubject ? controller.inspectedMemories : controller.memories;
  return <section className="card studio-evidence-card">
    <div className="studio-card-heading"><h2>{t("Saved memory", "已保存的记忆")}: {defaultSubjectLabel(subject)}</h2><span className={archived ? statusClass("forgotten") : statusClass("active")}>{archived ? t("archived", "已归档") : t("active", "活跃")}</span></div>
    {!HISTORY_TRIAL && controller.session && !controller.inspectedSubject ? <details className="studio-technical-details"><summary>{t("Manage person", "管理人物")}</summary><div className="studio-inline-form"><div className="field"><FieldCaption inputId="studio-rename-person">{t("Name", "名字")}</FieldCaption><input id="studio-rename-person" aria-labelledby={fieldCaptionId("studio-rename-person")} className="input" value={controller.subjectRename} disabled={controller.busy || archived} onChange={(event) => controller.setSubjectRename(event.target.value)} /></div><button className="button muted" disabled={controller.busy || archived || !controller.subjectRename.trim()} onClick={() => void controller.renameSubject()}>{t("Rename", "重命名")}</button></div><button className="button muted" disabled={controller.busy} onClick={() => void controller.setSubjectArchived(!archived)}>{archived ? t("Restore person", "恢复人物") : t("Archive person", "归档人物")}</button></details> : null}
    {controller.removal ? <p className="studio-boundary-warning" role="status">{controller.removal.outcome}{controller.removal.unconfirmed && !controller.removal.receipt ? <button className="button muted" disabled={controller.busy} onClick={() => void controller.retryRemoval()}>{t("Recover same action key", "使用同一动作键恢复")}</button> : null}</p> : null}
    <MemoryFacts facts={factState?.facts || []} t={t} openEvidence={controller.openEvidence} prepareAction={controller.prepareMemoryAction} removeSaved={controller.removeSavedFact} canCorrect={!archived && !controller.activeRun && Boolean(controller.session && !isArchived(controller.session.conversation))} canRemove={!HISTORY_TRIAL && !archived && !controller.busy && Boolean(factState?.memory_generation) && !controller.removal?.unconfirmed} />
    <details className="studio-technical-details"><summary>{t("Technical details", "技术详情")}</summary><p><code>{subject.external_key}</code> · {t("version", "版本")} {subject.version} · {t("memory generation", "记忆代次")} {factState?.memory_generation ?? "-"}</p></details>
  </section>;
}


function RunEvidence({ controller, t }: { controller: Controller; t: Translate }) {
  if (!controller.session) return null;
  return <details className="card studio-evidence-card studio-run-evidence studio-technical-details"><summary>{t("Technical run details", "运行技术详情")}</summary>{controller.conversation?.summary ? <article className="studio-summary"><strong>{t("Summary", "摘要")} v{controller.conversation.summary.version}</strong><p>{controller.conversation.summary.content}</p><small>{t("Source through message", "来源覆盖至消息")} #{controller.conversation.summary.source_boundary.through_sequence} · {t("Run", "运行")} {short(controller.conversation.summary.provenance.run_id)}</small><code>{t("Model", "模型")}: {controller.conversation.summary.provenance.model_key}</code></article> : <p className="muted">{t("No conversation summary has been committed yet.", "尚未提交对话摘要。")}</p>}<div className="studio-run-list"><h3>{t("Run history", "运行历史")}</h3>{controller.runs.length ? controller.runs.map((item) => <div className={controller.run?.id === item.id ? "studio-run-row studio-run-row-active" : "studio-run-row"} key={item.id}><span className={statusClass(item.status)}>{item.status}</span><span>{date(item.created_at)}</span><small>{item.timeout_seconds}s · +{item.retry_count} {t("retries", "重试")}</small></div>) : <p className="muted">{t("No runs yet.", "尚无运行。")}</p>}</div><EventLog events={controller.events} t={t} /></details>;
}

function EventLog({ events, t }: { events: RunEvent[]; t: Translate }) {
  return <div className="studio-event-list"><h3>{t("Normalized events", "标准化事件")}</h3>{events.length ? events.map((event) => <details key={event.id}><summary><span><strong>#{event.sequence}</strong> {event.type}</span><span>{date(event.occurred_at)}</span></summary><pre>{JSON.stringify(event.payload, null, 2)}</pre></details>) : <p className="muted">{t("Events appear here while a run is active and are retained as an operator trace.", "运行期间事件会显示在这里，并保留为运维轨迹。")}</p>}</div>;
}

export function AgentStudioView({ controller, t }: { controller: Controller; t: Translate }) {
  return <div className="agent-studio-root"><header className="studio-page-header"><div><div className="kicker">{HISTORY_TRIAL ? t("Experimental development trial · isolated evaluation data", "实验性开发试用 · 隔离的评估数据") : t("Chat with a character", "与角色聊天")}</div><h1>{HISTORY_TRIAL ? t("Lin Xiaotang Trial", "林小棠试用") : t("Agent Studio", "智能体工作台")}</h1><p>{HISTORY_TRIAL ? t("Chat naturally. Choose the same person in a new chat to see what Lin Xiaotang remembers.", "自然聊天。在新聊天中选择同一个人，看看林小棠记得什么。") : t("Start a chat, continue with someone you know, or create a new character.", "开始聊天、与熟悉的人接着聊，或创建新角色。")}</p></div></header>{controller.error ? <section className="studio-error" role="alert"><strong>{t("Chat error", "聊天错误")}</strong><span>{controller.error}</span></section> : null}{controller.loading ? <p className="muted">{t("Loading chats...", "正在加载聊天...")}</p> : null}<div className="agent-studio-layout"><Library controller={controller} t={t} /><main className="studio-conversation"><Conversation controller={controller} t={t} /></main><aside className="studio-evidence"><DefinitionEvidence controller={controller} t={t} /><SubjectEvidence controller={controller} t={t} /><RunEvidence controller={controller} t={t} /></aside></div></div>;
}
