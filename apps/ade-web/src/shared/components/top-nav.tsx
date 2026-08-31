"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import packageJson from "../../../package.json";
import { HOME_NAVIGATION_ITEM, NAVIGATION_GROUPS } from "./navigation-items";
import { useI18n } from "@/shared/i18n";

const COPY = {
  en: {
    navAriaLabel: "ADE navigation",
    languageAriaLabel: "Language",
    releaseAriaLabel: "UI release",
    releaseTag: "UI",
    dashboard: "Dashboard",
    build: "Build",
    content: "Content",
    evaluate: "Evaluate",
    operations: "Operations",
    agentStudio: "Agent Studio",
    commentLab: "Comment Lab",
    labelLab: "Label Lab",
    schemaCenter: "Schema Center",
    promptCenter: "Prompt Center",
    toolCenter: "Tool Center",
    testCenter: "Test Center",
    nativeRuntimePreview: "Native Runtime Preview",
    apiDocs: "API Docs",
  },
  zh: {
    navAriaLabel: "ADE 导航",
    languageAriaLabel: "语言",
    releaseAriaLabel: "界面版本",
    releaseTag: "版本",
    dashboard: "仪表盘",
    build: "构建",
    content: "内容",
    evaluate: "评估",
    operations: "运维",
    agentStudio: "智能体工作台",
    commentLab: "评论实验室",
    labelLab: "标注实验室",
    schemaCenter: "Schema 中心",
    promptCenter: "提示词中心",
    toolCenter: "工具中心",
    testCenter: "测试中心",
    nativeRuntimePreview: "原生运行时预览",
    apiDocs: "API 文档",
  },
} as const;

const PACKAGE_VERSION = typeof packageJson.version === "string" ? packageJson.version : "0.0.0";

function resolveReleaseLabel(): string {
  const version = (process.env.NEXT_PUBLIC_ADE_UI_VERSION || PACKAGE_VERSION).trim();
  const build = (process.env.NEXT_PUBLIC_ADE_UI_BUILD || "").trim();
  return build ? `v${version} (${build})` : `v${version}`;
}

function isActivePath(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function TopNav() {
  const { locale, setLocale } = useI18n();
  const copy = COPY[locale];
  const pathname = usePathname() || "/";
  const releaseLabel = resolveReleaseLabel();

  return (
    <div className="top-nav-group">
      <nav className="nav" aria-label={copy.navAriaLabel}>
        <Link
          className={isActivePath(pathname, HOME_NAVIGATION_ITEM.href) ? "nav-link nav-link-active" : "nav-link"}
          href={HOME_NAVIGATION_ITEM.href}
        >
          {copy[HOME_NAVIGATION_ITEM.key]}
        </Link>
        {NAVIGATION_GROUPS.map((group) => (
          <div className="nav-section" key={group.key}>
            <span className="nav-section-label">{copy[group.key]}</span>
            <div className="nav-section-links">
              {group.items.map((item) => {
                const active = isActivePath(pathname, item.href);
                return (
                  <Link className={active ? "nav-link nav-link-active" : "nav-link"} key={item.href} href={item.href}>
                    {copy[item.key]}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
      <div className="release-chip" role="status" aria-label={copy.releaseAriaLabel} title={releaseLabel}>
        <span className="release-chip-tag">{copy.releaseTag}</span>
        <span className="release-chip-value">{releaseLabel}</span>
      </div>
      <div className="locale-switch" role="group" aria-label={copy.languageAriaLabel}>
        <button
          type="button"
          className={locale === "en" ? "locale-button locale-active" : "locale-button"}
          onClick={() => setLocale("en")}
        >
          EN
        </button>
        <button
          type="button"
          className={locale === "zh" ? "locale-button locale-active" : "locale-button"}
          onClick={() => setLocale("zh")}
        >
          中文
        </button>
      </div>
    </div>
  );
}
