"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "../../lib/i18n";

const COPY = {
  en: {
    kicker: "Consolidated Module",
    title: "Prompt and Persona Lab",
    movedTitle: "Moved Into Agent Studio",
    movedText: "Prompt and persona editing is now part of the unified Agent Studio inspector. Redirecting now.",
    openButton: "Open Agent Studio (Prompt Tab)",
  },
  zh: {
    kicker: "模块已合并",
    title: "提示词与 Persona 实验室",
    movedTitle: "已迁入智能体工作台",
    movedText: "提示词与 Persona 编辑现已并入统一的智能体工作台检查面板，正在跳转。",
    openButton: "打开智能体工作台（Prompt 标签）",
  },
} as const;

export default function PromptPersonaLabPage() {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const router = useRouter();

  useEffect(() => {
    router.replace("/agent-studio?focus=prompt");
  }, [router]);

  return (
    <section>
      <div className="kicker">{copy.kicker}</div>
      <h1 className="section-title">{copy.title}</h1>
      <div className="card">
        <h3>{copy.movedTitle}</h3>
        <p>{copy.movedText}</p>
        <div className="toolbar" style={{ marginTop: 10 }}>
          <Link className="button" href="/agent-studio?focus=prompt">
            {copy.openButton}
          </Link>
        </div>
      </div>
    </section>
  );
}
