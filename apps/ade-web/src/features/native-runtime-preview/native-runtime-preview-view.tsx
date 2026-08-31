"use client";

import type { useNativeRuntimePreview } from "./use-native-runtime-preview";

type Controller = ReturnType<typeof useNativeRuntimePreview>;
type Translate = (english: string, chinese: string) => string;

function short(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return value.length > 22 ? `${value.slice(0, 10)}...${value.slice(-8)}` : value;
}

function pretty(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function statusTone(status: string | undefined): string {
  if (status === "ready" || status === "qualified" || status === "succeeded") {
    return "native-status native-status-good";
  }
  if (status === "failed" || status === "not_ready") {
    return "native-status native-status-bad";
  }
  return "native-status native-status-warn";
}

function ConfigurationPanel({ controller, t }: { controller: Controller; t: Translate }) {
  const locked = Boolean(controller.session);
  return (
    <section className="card native-preview-config">
      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <div>
          <div className="kicker">{t("Session contract", "会话契约")}</div>
          <h2>{t("Create one isolated preview", "创建独立预览")}</h2>
        </div>
        {locked ? (
          <button className="button muted" onClick={controller.resetSession} disabled={controller.busy}>
            {t("New session identity", "新建会话标识")}
          </button>
        ) : null}
      </div>
      <p className="muted">
        {t(
          "The server creates the exact definition, memory subject, and conversation atomically. This pilot fixes its tool scope to search_memory.",
          "服务端会原子化创建精确定义、记忆主体与对话。该试点的工具范围固定为 search_memory。",
        )}
      </p>

      <div className="native-form-grid" style={{ marginTop: 14 }}>
        <label className="field">
          <span>{t("Preview name", "预览名称")}</span>
          <input className="input" value={controller.name} disabled={locked} onChange={(event) => controller.setName(event.target.value)} />
        </label>
        <label className="field">
          <span>{t("Memory subject", "记忆主体")}</span>
          <input className="input" value={controller.subjectDisplayName} disabled={locked} onChange={(event) => controller.setSubjectDisplayName(event.target.value)} />
        </label>
        <label className="field native-span-2">
          <span>{t("Conversation model route", "对话模型路由")}</span>
          <input className="input" value={controller.modelKey} disabled />
        </label>
        <label className="field native-span-2">
          <span>{t("Memory reviewer model route", "记忆审查模型路由")}</span>
          <input className="input" value={controller.reviewerModelKey} disabled />
        </label>
        <label className="field native-span-2">
          <span>{t("Retriever embedding route", "检索嵌入路由")}</span>
          <input className="input" value={controller.embeddingModelKey} disabled />
        </label>
        <label className="field">
          <span>{t("Prompt snapshot", "提示词快照")}</span>
          <input className="input" value={controller.promptKey} disabled />
        </label>
        <label className="field">
          <span>{t("Persona snapshot", "人设快照")}</span>
          <input className="input" value={controller.personaKey} disabled />
        </label>
      </div>
      {!locked ? (
        <button
          className="button"
          style={{ marginTop: 14 }}
          disabled={controller.busy || controller.health?.status !== "ready"}
          onClick={() => void controller.createSession()}
        >
          {controller.busy ? t("Creating...", "创建中...") : t("Create atomic preview session", "创建原子预览会话")}
        </button>
      ) : null}
    </section>
  );
}

function DefinitionEvidence({ controller, t }: { controller: Controller; t: Translate }) {
  const session = controller.session;
  if (!session) {
    return null;
  }
  const definition = session.agent_definition;
  return (
    <section className="card" style={{ marginTop: 16 }}>
      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <div>
          <div className="kicker">{t("Frozen runtime identity", "冻结运行时标识")}</div>
          <h2>{definition.name}</h2>
        </div>
        <span className={statusTone(definition.qualification_state)}>{definition.qualification_state}</span>
      </div>
      <div className="native-evidence-grid">
        <div><span>{t("Definition", "定义")}</span><strong>{short(definition.id)}</strong></div>
        <div><span>{t("Subject", "主体")}</span><strong>{short(session.memory_subject.id)}</strong></div>
        <div><span>{t("Conversation", "对话")}</span><strong>{short(session.conversation.id)}</strong></div>
        <div><span>{t("Memory policy", "记忆策略")}</span><strong>{definition.memory_policy_version}</strong></div>
        <div><span>{t("Prompt digest", "提示词摘要")}</span><strong>{short(definition.prompt_sha256)}</strong></div>
        <div><span>{t("Persona digest", "人设摘要")}</span><strong>{short(definition.persona_sha256)}</strong></div>
      </div>
      <div className="native-deployment-grid">
        {definition.deployments.map((deployment) => (
          <article className="native-deployment" key={`${deployment.role}-${deployment.deployment_id}`}>
            <div className="toolbar" style={{ justifyContent: "space-between" }}>
              <strong>{deployment.role}</strong>
              <span className={statusTone(deployment.qualification_state)}>{deployment.qualification_state}</span>
            </div>
            <p>{deployment.route_alias}</p>
            <code>{short(deployment.fingerprint)}</code>
          </article>
        ))}
      </div>
    </section>
  );
}

function ConversationPanel({ controller, t }: { controller: Controller; t: Translate }) {
  if (!controller.session) {
    return null;
  }
  const active = controller.run && !["succeeded", "failed", "cancelled"].includes(controller.run.status);
  return (
    <section className="card native-chat-card">
      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <div>
          <div className="kicker">{t("Immutable conversation history", "不可变对话历史")}</div>
          <h2>{t("Talk to the native runtime", "与原生运行时对话")}</h2>
        </div>
        {controller.run ? <span className={statusTone(controller.run.status)}>{controller.run.status}</span> : null}
      </div>
      <div className="native-message-list">
        {controller.conversation?.messages.length ? controller.conversation.messages.map((item) => (
          <article className={`native-message native-message-${item.role}`} key={item.id}>
            <div className="toolbar" style={{ justifyContent: "space-between" }}>
              <strong>{item.role}</strong>
              <span>#{item.sequence} · {short(item.run_id)}</span>
            </div>
            <p>{item.content}</p>
          </article>
        )) : <p className="muted">{t("No turns yet. Reveal a durable fact, then refine or correct it in a later turn.", "尚无对话。先透露一个持久事实，再在后续轮次补充或纠正。")}</p>}
      </div>
      <label className="field" style={{ marginTop: 12 }}>
        <span>{t("User message", "用户消息")}</span>
        <textarea className="input" rows={4} value={controller.message} disabled={Boolean(active)} onChange={(event) => controller.setMessage(event.target.value)} />
      </label>
      <div className="toolbar" style={{ marginTop: 10 }}>
        <label className="field native-compact-field">
          <span>{t("Timeout (seconds)", "超时（秒）")}</span>
          <input className="input" type="number" min={5} max={600} value={controller.timeoutSeconds} onChange={(event) => controller.setTimeoutSeconds(Number(event.target.value))} />
        </label>
        <label className="field native-compact-field">
          <span>{t("Additional retries", "额外重试")}</span>
          <input className="input" type="number" min={0} max={5} value={controller.retryCount} onChange={(event) => controller.setRetryCount(Number(event.target.value))} />
        </label>
        <button className="button" disabled={controller.busy || Boolean(active) || !controller.message.trim()} onClick={() => void controller.sendMessage()}>
          {active ? t("Running...", "运行中...") : t("Run native turn", "运行原生轮次")}
        </button>
        {active ? <button className="button muted" disabled={controller.busy} onClick={() => void controller.cancelRun()}>{t("Cancel", "取消")}</button> : null}
      </div>
    </section>
  );
}

function MemoryPanel({ controller, t }: { controller: Controller; t: Translate }) {
  if (!controller.session) {
    return null;
  }
  return (
    <section className="card">
      <div className="kicker">{t("Typed subject projection", "类型化主体投影")}</div>
      <h2>{t("Memory facts and revisions", "记忆事实与修订")}</h2>
      <div className="native-memory-list">
        {controller.memories?.facts.length ? controller.memories.facts.map((fact) => (
          <details className="native-memory-fact" key={fact.id} open>
            <summary>
              <span><strong>{fact.fact_type}</strong> · {fact.entity_kind}:{fact.entity_label || short(fact.entity_id)}</span>
              <span className={statusTone(fact.status)}>{fact.status} · v{fact.version}</span>
            </summary>
            <p className="native-memory-value">{fact.value ?? t("Forgotten", "已遗忘")}</p>
            {fact.qualifier ? <p className="muted">{t("Qualifier", "限定词")}: {fact.qualifier}</p> : null}
            <div className="native-revision-list">
              {fact.revisions.map((revision) => (
                <article key={revision.id}>
                  <div><strong>{revision.operation}</strong> · v{revision.fact_version} · run {short(revision.run_id)}</div>
                  <div className="muted">{t("Predecessors", "前序修订")}: {revision.predecessor_revision_ids.map(short).join(", ") || "-"}</div>
                  {revision.evidence.map((evidence) => (
                    <blockquote key={`${evidence.message_id}-${evidence.start_char}`}>“{evidence.quote}” · {short(evidence.message_id)}</blockquote>
                  ))}
                </article>
              ))}
            </div>
          </details>
        )) : <p className="muted">{t("No durable memory has been committed yet.", "尚未提交持久记忆。")}</p>}
      </div>

      {controller.conversation?.summary ? (
        <article className="native-summary-card">
          <div className="toolbar" style={{ justifyContent: "space-between" }}>
            <strong>{t("Versioned conversation summary", "版本化对话摘要")} v{controller.conversation.summary.version}</strong>
            <span>{t("through message", "覆盖至消息")} #{controller.conversation.summary.source_boundary.through_sequence}</span>
          </div>
          <p>{controller.conversation.summary.content}</p>
          <div className="muted">{t("Source messages", "来源消息")}: {controller.conversation.summary.source_boundary.message_ids.map(short).join(", ")}</div>
          <div className="muted">{t("Model fingerprint", "模型指纹")}: {short(controller.conversation.summary.provenance.model_fingerprint)}</div>
        </article>
      ) : null}
    </section>
  );
}

function EventPanel({ controller, t }: { controller: Controller; t: Translate }) {
  if (!controller.session) {
    return null;
  }
  return (
    <section className="card native-event-card">
      <div className="kicker">{t("Normalized execution evidence", "标准化执行证据")}</div>
      <h2>{t("Run event timeline", "运行事件时间线")}</h2>
      {controller.run ? (
        <div className="native-evidence-grid">
          <div><span>{t("Run", "运行")}</span><strong>{short(controller.run.id)}</strong></div>
          <div><span>{t("Attempts", "尝试次数")}</span><strong>{controller.run.attempt_count}</strong></div>
          <div><span>{t("Timeout", "超时")}</span><strong>{controller.run.timeout_seconds}s</strong></div>
          <div><span>{t("Retries", "重试")}</span><strong>{controller.run.retry_count}</strong></div>
        </div>
      ) : null}
      <div className="native-event-list">
        {controller.events.length ? controller.events.map((event) => (
          <details key={event.id} className="native-event-row">
            <summary><span>#{event.sequence} · {event.type}</span><span>{event.attempt ? `attempt ${event.attempt}` : ""}</span></summary>
            <pre>{pretty(event.payload)}</pre>
          </details>
        )) : <p className="muted">{t("Events appear here as the worker builds context, calls models or tools, reviews memory, and commits state.", "工作器构建上下文、调用模型或工具、审查记忆并提交状态时，事件会显示在这里。")}</p>}
      </div>
    </section>
  );
}

export function NativeRuntimePreviewView({
  enabled,
  controller,
  t,
}: {
  enabled: boolean;
  controller: Controller;
  t: Translate;
}) {
  return (
    <section className="native-preview-root">
      <div className="kicker">{t("Explicit product pilot", "明确的产品试点")}</div>
      <h1 className="section-title">{t("ADE-Native Runtime Preview", "ADE 原生运行时预览")}</h1>
      <div className="native-preview-boundary">
        <strong>{t("Separate from Agent Studio", "与智能体工作台分离")}</strong>
        <span>{t("This route never switches or migrates Letta-backed agents. It talks only to the isolated PostgreSQL + worker native lane.", "此页面不会切换或迁移由 Letta 支撑的智能体，只连接独立的 PostgreSQL + worker 原生通道。")}</span>
      </div>

      {!enabled ? (
        <section className="card" style={{ marginTop: 16 }}>
          <h2>{t("Preview remains gated", "预览仍处于门禁状态")}</h2>
          <p className="muted">{t("The implementation exists, but navigation and execution stay disabled until the exact deployment fingerprints pass the reviewed three-round qualification gate.", "实现已经存在，但在精确部署指纹通过经审查的三轮资格门禁前，导航与执行保持禁用。")}</p>
        </section>
      ) : (
        <>
          <section className="card native-health-card" style={{ marginTop: 16 }}>
            <div>
              <div className="kicker">{t("Native-only readiness", "仅原生就绪状态")}</div>
              <h2>{controller.healthLoading ? t("Checking worker...", "正在检查工作器...") : t("Runtime lane", "运行时通道")}</h2>
            </div>
            <span className={statusTone(controller.health?.status)}>{controller.health?.status || t("unknown", "未知")}</span>
            <div className="native-health-details">
              <span>{t("Database", "数据库")}: {controller.health?.database_ready ? t("ready", "就绪") : t("not ready", "未就绪")}</span>
              <span>{t("Matching workers", "匹配工作器")}: {controller.health?.matching_build_worker_count ?? 0}</span>
              <span>{t("Source", "源码")}: {short(controller.health?.source_revision)}</span>
              <span>{t("Fingerprint", "指纹")}: {short(controller.health?.source_fingerprint)}</span>
            </div>
            <button className="button muted" disabled={controller.healthLoading} onClick={() => void controller.refreshHealth()}>{t("Refresh readiness", "刷新就绪状态")}</button>
          </section>

          {controller.error ? <div className="notice error"><strong>{t("Error", "错误")}</strong><div>{controller.error}</div></div> : null}
          {controller.streamWarning ? <div className="notice"><strong>{t("Stream status", "事件流状态")}</strong><div>{t("Event stream reconnecting; status polling remains active.", "事件流正在重连；状态轮询仍在运行。")}</div></div> : null}

          <ConfigurationPanel controller={controller} t={t} />
          <DefinitionEvidence controller={controller} t={t} />
          {controller.session ? (
            <div className="native-runtime-layout">
              <ConversationPanel controller={controller} t={t} />
              <MemoryPanel controller={controller} t={t} />
              <EventPanel controller={controller} t={t} />
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
