"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { listAgents } from "@/features/agent-studio/api";
import { fetchCapabilities } from "@/features/model-catalog/api";
import { listTestRuns } from "@/features/test-center/api";
import { useI18n } from "@/shared/i18n";

const DOCS_HREF = "/api-docs";

const COPY = {
  en: {
    kicker: "ADE Operator Workspace",
    title: "Improve Agent Behavior",
    intro: "Build an agent, inspect behavioral evidence, then refine the prompt, persona, or tool configuration with confidence.",
    journeyKicker: "Primary workflow",
    journeyTitle: "Improve Agent Behavior",
    journeyIntro: "Start with a real agent configuration, evaluate its memory and self-disclosure behavior, then make the next change from evidence.",
    startJourney: "Start in Agent Studio",
    reviewBehavior: "Review Behavior Evaluations",
    journeySteps: {
      buildTitle: "1. Build a configuration",
      buildDescription: "Set the model, prompt, persona, memory, and tools in Agent Studio.",
      evaluateTitle: "2. Evaluate behavior",
      evaluateDescription: "Run chat-memory evaluation and inspect facts, memory changes, tool use, and disclosure signals.",
      refineTitle: "3. Refine with evidence",
      refineDescription: "Open the selected prompt or persona, make a focused change, then rerun the setup.",
    },
    workspacesTitle: "Workspaces by Purpose",
    workspacesIntro: "Use the focused workspaces below when you need to build, manage content, or operate the platform.",
    workspaceGroups: {
      build: "Build and Experiment",
      content: "Content Configuration",
      operations: "Platform Operations",
    },
    backendHealth: "Backend Health",
    checking: "Checking...",
    statusPrefix: "Status",
    adeApiEnabled: "ADE API enabled",
    strictMode: "Strict capabilities mode",
    operationalSnapshot: "Operational Snapshot",
    knownAgents: "Known agents",
    observedRuns: "Observed test runs",
    missingRequired: "Missing required capabilities",
    qualityGate: "Quality Gate",
    qualityGateSummary: "Backend E2E green plus ADE smoke suite green.",
    qualityGateHint: "Use this signal as the release-readiness baseline.",
    dashboardError: "Dashboard Error",
    openModule: "Open module",
    yes: "yes",
    no: "no",
    on: "on",
    off: "off",
    platformDisabled: "platform-disabled",
    degraded: "degraded",
    ready: "ready",
    modules: {
      agentStudioTitle: "Agent Studio",
      agentStudioDescription:
        "Runtime chat, prompt and persona editing, tool management, execution trace, and persistent state inspection.",
      commentLabTitle: "Comment Lab",
      commentLabDescription:
        "Stateless comment generation workspace with independent model, prompt, and persona controls.",
      labelLabTitle: "Label Lab",
      labelLabDescription:
        "Stateless structured extraction workspace for grouped article entities, with JSON output and provider capability hints.",
      schemaCenterTitle: "Schema Center",
      schemaCenterDescription: "Manage Label Lab JSON schemas as workspace files with CRUD and archive/restore.",
      promptCenterTitle: "Prompt Center",
      promptCenterDescription: "Manage system prompts and persona templates with workspace-persisted CRUD and archive/restore.",
      toolCenterTitle: "Tool Center",
      toolCenterDescription: "Create and maintain managed custom tools, then attach them in Agent Studio without restart.",
      testCenterTitle: "Test Center",
      testCenterDescription: "Evaluate agent behavior with evidence, or open a separate operations area for health checks and qualification.",
      apiDocsTitle: "API Docs",
      apiDocsDescription: "OpenAPI-backed interactive API documentation rendered directly inside ADE.",
    },
  },
  zh: {
    kicker: "ADE 运营工作台",
    title: "改善智能体行为",
    intro: "构建智能体、查看行为证据，再基于证据迭代提示词、人设或工具配置。",
    journeyKicker: "主要工作流",
    journeyTitle: "改善智能体行为",
    journeyIntro: "从真实的智能体配置开始，评估记忆与自我暴露行为，再基于证据完成下一次改动。",
    startJourney: "从智能体工作台开始",
    reviewBehavior: "查看行为评估",
    journeySteps: {
      buildTitle: "1. 构建配置",
      buildDescription: "在智能体工作台设置模型、提示词、人设、记忆和工具。",
      evaluateTitle: "2. 评估行为",
      evaluateDescription: "运行聊天记忆评估，查看事实、记忆变更、工具使用和自我暴露信号。",
      refineTitle: "3. 基于证据迭代",
      refineDescription: "打开所选提示词或人设，完成聚焦改动后再运行同一配置。",
    },
    workspacesTitle: "按目的浏览工作区",
    workspacesIntro: "需要构建、管理内容或运维平台时，可使用下方对应的聚焦工作区。",
    workspaceGroups: {
      build: "构建与试验",
      content: "内容配置",
      operations: "平台运维",
    },
    backendHealth: "后端健康状态",
    checking: "检查中...",
    statusPrefix: "状态",
    adeApiEnabled: "ADE API 开关",
    strictMode: "严格能力模式",
    operationalSnapshot: "运行快照",
    knownAgents: "已知智能体数量",
    observedRuns: "已观察测试运行数",
    missingRequired: "缺失必需能力数",
    qualityGate: "质量门禁",
    qualityGateSummary: "后端 E2E 与 ADE 烟雾测试均已通过。",
    qualityGateHint: "该信号可作为发布就绪基线。",
    dashboardError: "仪表盘错误",
    openModule: "打开模块",
    yes: "是",
    no: "否",
    on: "开启",
    off: "关闭",
    platformDisabled: "platform-disabled",
    degraded: "degraded",
    ready: "ready",
    modules: {
      agentStudioTitle: "智能体工作台",
      agentStudioDescription: "支持运行时对话、提示词和 Persona 编辑、工具管理、执行轨迹及持久化状态查看。",
      commentLabTitle: "评论实验室",
      commentLabDescription: "独立的无状态评论生成空间，可分别控制模型、Prompt 与 Persona。",
      labelLabTitle: "标注实验室",
      labelLabDescription: "用于文章结构化实体提取的无状态工作区，支持分组 JSON 输出和模型能力提示。",
      schemaCenterTitle: "Schema 中心",
      schemaCenterDescription: "以工作区文件方式管理 Label Lab JSON Schema，支持 CRUD 与归档恢复。",
      promptCenterTitle: "提示词中心",
      promptCenterDescription: "管理 System Prompt 与 Persona 模板，支持工作区持久化 CRUD 与归档恢复。",
      toolCenterTitle: "工具中心",
      toolCenterDescription: "创建并维护受管自定义工具，无需重启即可在智能体工作台挂载使用。",
      testCenterTitle: "测试中心",
      testCenterDescription: "用证据评估智能体行为，或进入独立的运维区域执行健康检查与运行时资格验证。",
      apiDocsTitle: "API 文档",
      apiDocsDescription: "基于 OpenAPI 的交互式 API 文档，直接在 ADE 内渲染。",
    },
  },
} as const;

function isExternalLink(href: string): boolean {
  return /^https?:\/\//i.test(href);
}

export default function DashboardPage() {
  const { locale } = useI18n();
  const copy = COPY[locale];

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [agentCount, setAgentCount] = useState(0);
  const [runCount, setRunCount] = useState(0);
  const [adeApiEnabled, setPlatformEnabled] = useState(false);
  const [strictMode, setStrictMode] = useState(false);
  const [missingCapabilities, setMissingCapabilities] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError("");
      try {
        const [capabilities, agents, runs] = await Promise.all([
          fetchCapabilities(),
          listAgents(200),
          listTestRuns(),
        ]);

        if (cancelled) {
          return;
        }

        setPlatformEnabled(Boolean(capabilities.enabled));
        setStrictMode(Boolean(capabilities.strict_mode));
        setMissingCapabilities(Array.isArray(capabilities.missing_required) ? capabilities.missing_required : []);
        setAgentCount(Number(agents.total || 0));
        setRunCount(Array.isArray(runs.items) ? runs.items.length : 0);
      } catch (exc) {
        if (!cancelled) {
          setError(exc instanceof Error ? exc.message : String(exc));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  const healthLabel = useMemo(() => {
    if (!adeApiEnabled) {
      return copy.platformDisabled;
    }
    if (missingCapabilities.length > 0) {
      return copy.degraded;
    }
    return copy.ready;
  }, [copy.degraded, copy.platformDisabled, copy.ready, missingCapabilities.length, adeApiEnabled]);

  const modules = useMemo(
    () => [
      {
        title: copy.modules.agentStudioTitle,
        description: copy.modules.agentStudioDescription,
        href: "/agent-studio",
      },
      {
        title: copy.modules.commentLabTitle,
        description: copy.modules.commentLabDescription,
        href: "/comment-lab",
      },
      {
        title: copy.modules.labelLabTitle,
        description: copy.modules.labelLabDescription,
        href: "/label-lab",
      },
      {
        title: copy.modules.schemaCenterTitle,
        description: copy.modules.schemaCenterDescription,
        href: "/schema-center",
      },
      {
        title: copy.modules.promptCenterTitle,
        description: copy.modules.promptCenterDescription,
        href: "/prompt-center",
      },
      {
        title: copy.modules.toolCenterTitle,
        description: copy.modules.toolCenterDescription,
        href: "/tool-center",
      },
      {
        title: copy.modules.testCenterTitle,
        description: copy.modules.testCenterDescription,
        href: "/test-center",
      },
      {
        title: copy.modules.apiDocsTitle,
        description: copy.modules.apiDocsDescription,
        href: DOCS_HREF,
      },
    ],
    [copy.modules],
  );

  const workspaceGroups = useMemo(
    () => [
      {
        title: copy.workspaceGroups.build,
        hrefs: ["/agent-studio", "/comment-lab", "/label-lab"],
      },
      {
        title: copy.workspaceGroups.content,
        hrefs: ["/schema-center", "/prompt-center", "/tool-center"],
      },
      {
        title: copy.workspaceGroups.operations,
        hrefs: [DOCS_HREF],
      },
    ],
    [copy.workspaceGroups],
  );

  return (
    <section>
      <div className="kicker">{copy.kicker}</div>
      <h1 className="section-title">{copy.title}</h1>
      <p className="muted" style={{ maxWidth: 760 }}>
        {copy.intro}
      </p>

      <section className="card dashboard-journey" aria-labelledby="improve-agent-behavior-title">
        <div className="dashboard-journey-copy">
          <div className="kicker">{copy.journeyKicker}</div>
          <h2 id="improve-agent-behavior-title">{copy.journeyTitle}</h2>
          <p>{copy.journeyIntro}</p>
          <div className="dashboard-journey-actions">
            <Link className="button" href="/agent-studio">{copy.startJourney}</Link>
            <Link className="button muted" href="/test-center">{copy.reviewBehavior}</Link>
          </div>
        </div>
        <div className="dashboard-journey-steps">
          <div className="dashboard-journey-step">
            <strong>{copy.journeySteps.buildTitle}</strong>
            <span>{copy.journeySteps.buildDescription}</span>
          </div>
          <div className="dashboard-journey-step">
            <strong>{copy.journeySteps.evaluateTitle}</strong>
            <span>{copy.journeySteps.evaluateDescription}</span>
          </div>
          <div className="dashboard-journey-step">
            <strong>{copy.journeySteps.refineTitle}</strong>
            <span>{copy.journeySteps.refineDescription}</span>
          </div>
        </div>
      </section>

      <div className="dashboard-workspace-heading">
        <div className="kicker">{copy.workspacesTitle}</div>
        <h2>{copy.workspacesTitle}</h2>
        <p className="muted">{copy.workspacesIntro}</p>
      </div>

      {workspaceGroups.map((group) => (
        <section className="dashboard-workspace-group" key={group.title}>
          <h3>{group.title}</h3>
          <div className="card-grid">
            {modules.filter((module) => group.hrefs.includes(module.href)).map((module) => {
              const content = (
                <>
                  <h3>{module.title}</h3>
                  <p>{module.description}</p>
                  <p className="dashboard-module-hint">{copy.openModule}</p>
                </>
              );

              if (isExternalLink(module.href)) {
                return (
                  <a key={module.title} className="card dashboard-module-link" href={module.href} target="_blank" rel="noreferrer">
                    {content}
                  </a>
                );
              }

              return (
                <Link key={module.title} className="card dashboard-module-link" href={module.href}>
                  {content}
                </Link>
              );
            })}
          </div>
        </section>
      ))}

      <div className="dashboard-workspace-heading">
        <div className="kicker">{copy.operationalSnapshot}</div>
        <h2>{copy.operationalSnapshot}</h2>
      </div>

      <div className="card-grid" style={{ marginTop: 14 }}>
        <div className="card">
          <h3>{copy.backendHealth}</h3>
          <p className="muted">{loading ? copy.checking : `${copy.statusPrefix}: ${healthLabel}`}</p>
          <ul className="list">
            <li>{copy.adeApiEnabled}: {adeApiEnabled ? copy.yes : copy.no}</li>
            <li>{copy.strictMode}: {strictMode ? copy.on : copy.off}</li>
          </ul>
        </div>

        <div className="card">
          <h3>{copy.operationalSnapshot}</h3>
          <ul className="list">
            <li>{copy.knownAgents}: {agentCount}</li>
            <li>{copy.observedRuns}: {runCount}</li>
            <li>{copy.missingRequired}: {missingCapabilities.length}</li>
          </ul>
        </div>

        <div className="card">
          <h3>{copy.qualityGate}</h3>
          <p className="muted">{copy.qualityGateSummary}</p>
          <p className="muted" style={{ marginTop: 8 }}>
            {copy.qualityGateHint}
          </p>
        </div>
      </div>

      {error ? (
        <div className="card" style={{ marginTop: 14, borderColor: "#fecaca" }}>
          <h3>{copy.dashboardError}</h3>
          <p className="muted">{error}</p>
        </div>
      ) : null}
    </section>
  );
}
