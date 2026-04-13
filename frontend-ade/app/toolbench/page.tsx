"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "../../lib/i18n";

const COPY = {
  en: {
    kicker: "Consolidated Module",
    title: "Toolbench",
    movedTitle: "Moved Into Agent Studio",
    movedText: "Tool discovery and attach/detach flows now live in the Agent Studio tools tab. Redirecting now.",
    openButton: "Open Agent Studio (Tools Tab)",
  },
  zh: {
    kicker: "模块已合并",
    title: "工具台",
    movedTitle: "已迁入智能体工作台",
    movedText: "工具发现与挂载/卸载流程现已迁至智能体工作台的 Tools 标签，正在跳转。",
    openButton: "打开智能体工作台（Tools 标签）",
  },
} as const;

export default function ToolbenchPage() {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const router = useRouter();

  useEffect(() => {
    router.replace("/agent-studio?focus=tools");
  }, [router]);

  return (
    <section>
      <div className="kicker">{copy.kicker}</div>
      <h1 className="section-title">{copy.title}</h1>
      <div className="card">
        <h3>{copy.movedTitle}</h3>
        <p>{copy.movedText}</p>
        <div className="toolbar" style={{ marginTop: 10 }}>
          <Link className="button" href="/agent-studio?focus=tools">
            {copy.openButton}
          </Link>
        </div>
      </div>
    </section>
  );
}
