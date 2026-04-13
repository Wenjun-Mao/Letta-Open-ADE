"use client";

import Link from "next/link";
import { useI18n } from "../../lib/i18n";

const DOCS_PATH = process.env.NEXT_PUBLIC_MINTLIFY_DOCS_URL || "/docs";

const COPY = {
  en: {
    kicker: "Docs Integration",
    title: "API Documentation",
    description:
      "Mintlify documentation is configured under the repository docs folder and ingests committed OpenAPI artifacts generated from the backend.",
    config: "Config",
    spec: "Spec",
    exporter: "Exporter",
    openEntry: "Open docs entry",
  },
  zh: {
    kicker: "文档集成",
    title: "API 文档",
    description: "Mintlify 文档位于仓库 docs 目录，并会读取后端生成并提交的 OpenAPI 产物。",
    config: "配置",
    spec: "规范",
    exporter: "导出脚本",
    openEntry: "打开文档入口",
  },
} as const;

function isExternalLink(href: string): boolean {
  return /^https?:\/\//i.test(href);
}

export default function ApiDocsPage() {
  const { locale } = useI18n();
  const copy = COPY[locale];

  return (
    <section>
      <div className="kicker">{copy.kicker}</div>
      <h1 className="section-title">{copy.title}</h1>
      <div className="card">
        <p>{copy.description}</p>
        <ul className="list">
          <li>{copy.config}: docs/docs.json</li>
          <li>{copy.spec}: docs/openapi/agent-platform-openapi.json</li>
          <li>{copy.exporter}: scripts/export_openapi.py</li>
        </ul>
        <p style={{ marginTop: 14 }}>
          {isExternalLink(DOCS_PATH) ? (
            <a href={DOCS_PATH} className="nav-link" target="_blank" rel="noreferrer">
              {copy.openEntry}
            </a>
          ) : (
            <Link href={DOCS_PATH} className="nav-link">
              {copy.openEntry}
            </Link>
          )}
        </p>
      </div>
    </section>
  );
}
