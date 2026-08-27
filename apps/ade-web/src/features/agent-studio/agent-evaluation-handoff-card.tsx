import Link from "next/link";

import { buildChatMemoryEvaluationHref } from "./evaluation-handoff";
import type { Translate } from "./types";

type AgentEvaluationHandoffCardProps = {
  t: Translate;
  createModel: string;
  createPromptKey: string;
  createPersonaKey: string;
  createEmbedding: string;
  timeoutSeconds: string;
  retryCount: string;
};

export function AgentEvaluationHandoffCard({
  t,
  createModel,
  createPromptKey,
  createPersonaKey,
  createEmbedding,
  timeoutSeconds,
  retryCount,
}: AgentEvaluationHandoffCardProps) {
  const hasModel = Boolean(createModel.trim());
  const href = hasModel
    ? buildChatMemoryEvaluationHref({
        model: createModel,
        promptKey: createPromptKey,
        personaKey: createPersonaKey,
        embedding: createEmbedding,
        timeoutSeconds,
        retryCount,
      })
    : "";

  return (
    <section className="card" style={{ marginTop: 14, padding: 12 }} aria-label={t("Evaluate this setup", "评估此配置")}>
      <div className="toolbar" style={{ alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <h3 style={{ margin: 0 }}>{t("Evaluate this setup", "评估此配置")}</h3>
          <p className="muted" style={{ marginBottom: 0 }}>
            {t(
              "Send the current new-agent configuration to Test Center's chat-memory evaluation.",
              "将当前新建智能体配置发送到 Test Center 的聊天记忆评估。",
            )}
          </p>
        </div>
        {hasModel ? (
          <Link className="button" href={href}>
            {t("Open evaluation", "打开评估")}
          </Link>
        ) : (
          <button className="button muted" disabled title={t("Choose a model to evaluate this setup.", "请选择模型后再评估此配置。")}>
            {t("Select a model to evaluate", "请选择模型后评估")}
          </button>
        )}
      </div>
      {!hasModel ? (
        <p className="muted" style={{ color: "#92400e", marginBottom: 0 }}>
          {t("Choose a model to make this action available.", "请选择模型以启用此操作。")}
        </p>
      ) : null}
      <p className="muted" style={{ marginBottom: 0 }}>
        {t(
          "Test Center creates disposable fresh agents for this evaluation, then archives and purges them. It does not mutate the currently selected Agent Studio agent.",
          "Test Center 会为此评估创建一次性的新智能体，并在完成后归档和清理它们；不会修改当前在 Agent Studio 中选择的智能体。",
        )}
      </p>
    </section>
  );
}
